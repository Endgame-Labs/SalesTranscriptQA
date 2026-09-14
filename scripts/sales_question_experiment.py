"""Bounded, reproducible sample experiment. Never launches full generation/publication."""
import argparse
import concurrent.futures
import fcntl
import json
import random
from collections import Counter
from pathlib import Path
from salestranscriptqa.corpus import write_json
from salestranscriptqa.sales_questions import SalesQuestions, SalesQuestionsGLM, SalesQuestionsEdited, SALES_PROMPT, STYLE_AUDIT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=['deepseek', 'glm', 'edited'], default='deepseek')
    parser.add_argument('--seed', type=int, default=20260915)
    parser.add_argument('--count', type=int, default=100)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    if not 1 <= args.count <= 100:
        parser.error('Experiments are limited to 1..100 source units per invocation')
    cls = {'deepseek':SalesQuestions,'glm':SalesQuestionsGLM,'edited':SalesQuestionsEdited}[args.model]
    root = Path('runs') / f'{cls.version}-seed{args.seed}-n{args.count}'
    root.mkdir(parents=True, exist_ok=True)
    with (root/'experiment.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        full = cls('data/corpus', root, workers=args.workers)
        buckets = {}
        for unit in full.plan():
            if unit['domain'] == 'b2c' and unit['question_class'] == 'multi_call':
                continue
            buckets.setdefault((unit['domain'], unit['question_class']), []).append(unit)
        rng = random.Random(args.seed)
        for units in buckets.values():
            rng.shuffle(units)
        # Half B2C single, quarter each B2B single/multi, including rounding.
        keys = [('b2c','single_call'), ('b2b','single_call'), ('b2c','single_call'), ('b2b','multi_call')]
        sample = [buckets[keys[i % 4]].pop() for i in range(args.count)]
        write_json(root/'plan.json', {'seed':args.seed,'units':sample,'generation_prompt':SALES_PROMPT,
                                     'style_audit':STYLE_AUDIT,'generator':full.generator})
        def propose(unit):
            calls = [full.calls[unit['domain']][cid] for cid in unit['supporting_call_ids']]
            result = full.candidate(unit['domain'],unit['question_class'],calls)
            print(json.dumps({k:result.get(k) for k in ['job_id','status','failure']}),flush=True)
            return result
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            results = list(pool.map(propose,sample))
        with full.transport.db() as db:
            cost = db.execute('SELECT COALESCE(SUM(estimated_usd),0) FROM attempts').fetchone()[0]
            artifacts = [root/p for p, in db.execute("SELECT artifact FROM attempts WHERE stage='generate' AND status='ok' ORDER BY started")]
        raw = {}
        for path in artifacts:
            artifact = json.loads(path.read_text())
            value = json.loads(artifact['request']['messages'][0]['content'].split('INPUT JSON:\n',1)[1])
            raw.setdefault(tuple(c['call_id'] for c in value['calls']),artifact['parsed'])
        rows = []
        for i,result in enumerate(results,1):
            q = result.get('candidate',result)
            if not q.get('question'):
                q = raw.get(tuple(result['supporting_call_ids']),{})
            rows.append({'item':i,**{k:result.get(k) for k in ['job_id','domain','question_class','supporting_call_ids','status','failure']},
                         'question':q.get('question'),'gold_answer':q.get('gold_answer')})
        report = {'questions':rows,'counts':dict(Counter(r['status'] for r in rows)),
                  'failures':dict(Counter(r['failure'] for r in rows if r['status']!='accepted')),
                  'estimated_usd':cost,'run_root':str(root),'seed':args.seed,
                  'limitations':'First proposals with no replacement. Legacy exact-source specificity gate retained; acceptance is provisional pending independent sample review and ambiguity checks.'}
        report_path = Path('reports')/f'{root.name}.json'
        write_json(report_path,report)
        markdown = ['# Sales question experiment',f'\nGenerator: {full.generator}. Seed: {args.seed}.',
                    f'\nOutcomes: {report["counts"]}. Estimated API cost: ${cost:.4f}.',f'\n{report["limitations"]}\n']
        for row in rows:
            markdown += [f'## {row["item"]}. {row["domain"]} {row["question_class"]} — {row["status"]}',
                         f'\n**Q:** {row["question"]}\n\n**A:** {row["gold_answer"]}\n']
            if row['failure']:
                markdown += [f'Gate: `{row["failure"]}`\n']
        report_path.with_suffix('.md').write_text('\n'.join(markdown))
        print(json.dumps({k:v for k,v in report.items() if k!='questions'}),flush=True)


if __name__ == '__main__':
    main()
