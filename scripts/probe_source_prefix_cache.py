"""Bounded diagnostic of source-first JSON ordering + documented Fireworks affinity.

Does not change production prompts, jobs, or accepted questions.
"""
import collections
import json
import random
import sqlite3
from pathlib import Path
from salestranscriptqa.transport import Transport,RATES,digest
from salestranscriptqa.answer_consistency import JUDGE,VERIFY_BLIND,COMPARE_ONLY
from salestranscriptqa.ambiguity import materialize_evidence

ROOT=Path('runs/sales-expanded-cache-probe-v1')
SOURCE=Path('runs/sales-expanded-2000-v1')


def main():
    RATES[JUDGE]=(2,.25,6)
    ROOT.mkdir(exist_ok=True)
    manifest=ROOT/'plan.json'
    if manifest.exists():plan=json.loads(manifest.read_text())
    else:
        buckets=collections.defaultdict(dict);windows=collections.Counter();totals=collections.Counter();last={}
        with sqlite3.connect(f'file:{SOURCE}/progress.sqlite?mode=ro',uri=True) as db:
            records=db.execute("SELECT artifact,started,input_tokens FROM attempts WHERE stage='group_blind_verification_v2' AND status='ok' ORDER BY started").fetchall()
        for path,started,tokens in records:
            value=json.loads((SOURCE/path).read_text());prompt=value['request']['messages'][0]['content']
            instruction,blob=prompt.split('\nINPUT JSON:\n',1);payload=json.loads(blob)
            assert instruction==VERIFY_BLIND
            key=digest(payload['calls']);qkey=digest(payload['question'])
            buckets[key].setdefault(qkey,{'payload':payload,'original_verdict':value['parsed'],'artifact':path})
            totals['requests']+=1;totals['input_tokens']+=tokens or 0
            if key in last:
                for seconds in [300,900,3600]:
                    if started-last[key]<=seconds:windows[str(seconds)]+=tokens or 0
            last[key]=started
        eligible=[(key,list(values.values())) for key,values in sorted(buckets.items()) if len(values)>=4 and any(r['original_verdict'].get('complete') is True for r in values.values()) and any(r['original_verdict'].get('complete') is False for r in values.values())]
        rng=random.Random(20260914);rng.shuffle(eligible);groups=[]
        for key,values in eligible[:3]:
            positive=next(r for r in values if r['original_verdict'].get('complete') is True)
            others=[r for r in values if r is not positive];rng.shuffle(others)
            groups.append({'group_key':key,'cases':[positive,*others[:3]]})
        assert len(groups)==3
        plan={'groups':groups,'source_requests':dict(totals),'potential_repeated_group_input_within_seconds':dict(windows),'seed':20260914,
              'limitations':'Selected frequent source groups with positive and negative decisions; cache gains are a warm-reuse diagnostic, not an end-to-end cost forecast. TTL estimates assume identical group prefix and replica routing, ignoring eviction; they are upper bounds.'}
        manifest.write_text(json.dumps(plan,indent=2)+'\n')
    transport=Transport(ROOT,budget_usd=5)
    rows=[]
    for group in plan['groups']:
        for mode in ['question-first','source-first']:
            # Each arm gets separate cache isolation; cases inside an arm share a replica hint.
            routing='stqa-prefix-v1-'+mode+'-'+group['group_key'][:16]
            transport.client.headers.update({'x-session-affinity':routing,'x-prompt-cache-isolation-key':routing})
            for i,case in enumerate(group['cases']):
                payload=case['payload']
                reordered={'calls':payload['calls'],'question':payload['question'],'draft_extraction':payload['draft_extraction']}
                blob=json.dumps(payload if mode=='question-first' else reordered)
                assert json.loads(blob)==payload
                verdict=transport.request(JUDGE,VERIFY_BLIND+'\nINPUT JSON:\n'+blob,'prefix_probe/'+mode,nonce=group['group_key']+str(i))
                row=dict(group=group['group_key'],mode=mode,position=i,question=payload['question'],complete=verdict.get('complete'),verdict=verdict,
                         original_complete=case['original_verdict'].get('complete'),routing=routing)
                rows.append(row);print(json.dumps({k:row[k] for k in ['mode','position','complete','original_complete']}),flush=True)
    checks=[]
    for i in range(12):
        group=plan['groups'][i//4];position=i%4
        left=next(r for r in rows if r['group']==group['group_key'] and r['position']==position and r['mode']=='question-first')
        right=next(r for r in rows if r['group']==group['group_key'] and r['position']==position and r['mode']=='source-first')
        check=dict(group=group['group_key'],position=position,complete_agrees=left['complete']==right['complete'])
        if left['complete'] and right['complete']:
            compare={'question':left['question'],'answer_a':left['verdict'].get('answer'),'answer_b':right['verdict'].get('answer')}
            check['answer_comparison']=transport.request(JUDGE,COMPARE_ONLY+'\nINPUT JSON:\n'+json.dumps(compare),'prefix_probe/comparison',nonce=digest(compare))
        checks.append(check)
    usage=[]
    with transport.db() as db:
        for stage,n,input_tokens,cached,output,cost in db.execute('SELECT stage,COUNT(*),SUM(input_tokens),SUM(cached_tokens),SUM(output_tokens),SUM(estimated_usd) FROM attempts GROUP BY stage'):
            usage.append(dict(stage=stage,attempts=n,input_tokens=input_tokens,cached_tokens=cached,output_tokens=output,estimated_usd=cost))
    result={'plan':{k:v for k,v in plan.items() if k != 'groups'},'group_keys':[g['group_key'] for g in plan['groups']],'outcomes':rows,'paired_checks':checks,'usage':usage,'production_changed':False,'local_plan':str(manifest)}
    Path('reports/source-prefix-cache-probe-v1.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'usage':usage,'complete_agreement':sum(c['complete_agrees'] for c in checks),'pairs':len(checks)}),flush=True)

if __name__=='__main__':main()
