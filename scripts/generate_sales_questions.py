"""Resumable sales-QA generation. Defaults to a bounded sample; never publishes."""
import argparse
import concurrent.futures
import fcntl
import itertools
import json
import math
import random
from collections import Counter
from pathlib import Path
from salestranscriptqa.sales_questions import SalesQuestionsReliable, READY_PROMPT
from salestranscriptqa.answer_consistency import JUDGE
from salestranscriptqa.transport import RATES
from salestranscriptqa.corpus import write_json
from salestranscriptqa.query_coherence import select_output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--sample',type=int,default=100)
    mode.add_argument('--all',action='store_true')
    parser.add_argument('--seed',type=int,default=20260917)
    parser.add_argument('--workers',type=int,default=8)
    parser.add_argument('--proposals',type=int,default=3)
    parser.add_argument('--budget-usd',type=float,default=50)
    parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--corpus',default='data/corpus')
    parser.add_argument('--plan-only',action='store_true',help='Freeze and inspect the source plan without making API calls')
    parser.add_argument('--exclude-report',type=Path,action='append',default=[])
    args=parser.parse_args()
    if not 1 <= args.sample <= 2000 or not math.isfinite(args.budget_usd) or args.budget_usd <= 0:
        parser.error('sample must be 1..2000 and budget-usd must be a finite positive amount')
    if not args.all and args.budget_usd > 1000:
        parser.error('Research samples are capped at a $1000 per-run allowance')
    if args.all and args.exclude_report:
        parser.error('exclude-report applies only to sample validation')
    args.run_dir.mkdir(parents=True,exist_ok=True)
    with (args.run_dir/'pilot.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        RATES[JUDGE]=(2.0,0.25,6.0)
        full=SalesQuestionsReliable(args.corpus,args.run_dir,workers=args.workers,proposals=args.proposals)
        full.transport.budget_usd=args.budget_usd
        full.recover_interrupted_requests()
        eligible=[u for u in full.plan() if not (u['domain']=='b2c' and u['question_class']=='multi_call')]
        excluded_ids=set()
        for path in args.exclude_report:
            prior=json.loads(path.read_text())
            for q in prior.get('questions',prior.get('units',[])):
                excluded_ids.update(q['supporting_call_ids'])
        excluded_groups={c.get('group_id') or c['call_id'] for calls in full.calls.values()
                         for c in calls.values() if c['call_id'] in excluded_ids}
        if excluded_groups:
            eligible=[u for u in eligible if not any(
                (full.calls[u['domain']][cid].get('group_id') or cid) in excluded_groups
                for cid in u['supporting_call_ids'])]
        if args.all:
            selected=eligible
        else:
            buckets={}
            for u in eligible:
                buckets.setdefault((u['domain'],u['question_class']),[]).append(u)
            rng=random.Random(args.seed)
            for bucket in buckets.values(): rng.shuffle(bucket)
            keys=[('b2c','single_call'),('b2b','single_call'),('b2c','single_call'),('b2b','multi_call')]
            needed=Counter(keys[i%4] for i in range(args.sample))
            for key,count in needed.items():
                if len(buckets.get(key,[])) < count:
                    parser.error(f'Insufficient unused units for {key}: need {count}, available {len(buckets.get(key,[]))}')
            selected=[buckets[keys[i%4]].pop() for i in range(args.sample)]
        plan={'scope':'all' if args.all else 'sample','seed':args.seed,'units':selected,
              'eligible_units':len(eligible),'generation_prompt':READY_PROMPT,'excluded_groups':sorted(excluded_groups)}
        plan_path=args.run_dir/'source-plan.json'
        if plan_path.exists() and json.loads(plan_path.read_text())!=plan:
            raise RuntimeError('Source plan changed; choose a new run directory')
        write_json(plan_path,plan)
        if args.plan_only:
            print(json.dumps({'units':len(selected),'counts':dict(Counter(u['domain']+'/'+u['question_class'] for u in selected)),'excluded_groups':len(excluded_groups),'api_calls':0}),flush=True)
            return
        completed=[]
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            iterator=iter(selected)
            pending={pool.submit(full.process_unit,u) for u in itertools.islice(iterator,args.workers)}
            while pending:
                done,pending=concurrent.futures.wait(pending,return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:
                    completed.append(future.result())
                    unit=next(iterator,None)
                    if unit is not None: pending.add(pool.submit(full.process_unit,unit))
                with full.transport.db() as db:
                    cost=db.execute('SELECT COALESCE(SUM(estimated_usd),0) FROM attempts').fetchone()[0]
                progress={'scope':plan['scope'],'total_units':len(selected),'completed_units':len(completed),
                          'outcomes':dict(Counter(u['status'] for u in completed)),'estimated_usd':cost,
                          'budget_usd':args.budget_usd,'complete':False}
                write_json(args.run_dir/'progress.json',progress)
                print(json.dumps(progress),flush=True)
        coverage=full.finalize(selected,completed)
        coverage['scope']=plan['scope']
        coverage['full_corpus_complete']=args.all
        coverage['accepted_questions']=coverage.pop('published_questions')
        coverage['published']=False
        write_json(args.run_dir/'coverage.json',coverage)
        selection=select_output(args.run_dir,full.transport,full.calls)
        with full.transport.db() as db:
            cost=db.execute('SELECT COALESCE(SUM(estimated_usd),0) FROM attempts').fetchone()[0]
        progress.update(complete=True,accepted_after_dedup=coverage['accepted_questions'],
                        selected_questions=selection['selected_questions'],estimated_usd=cost,
                        final_output=str(args.run_dir/'selected'))
        write_json(args.run_dir/'progress.json',progress)
        print(json.dumps(progress),flush=True)


if __name__=='__main__':
    main()
