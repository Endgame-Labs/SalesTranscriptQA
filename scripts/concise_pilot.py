"""Compare a scoped prompt on the same 20 randomly selected pilot source units."""
import concurrent.futures
import json
from pathlib import Path
from collections import Counter
from salestranscriptqa.natural import ConciseNatural, CONCISE_PROMPT
from salestranscriptqa.corpus import write_json

root=Path('runs/natural-pilot-v5-concise-glm')
full=ConciseNatural('data/corpus',root,workers=8)
original=json.loads(Path('reports/natural-pilot-v2.json').read_text())['questions']
write_json(root/'prompt.json',{'generation':CONCISE_PROMPT,'generator':'GLM','independent_answer':'DeepSeek'})
write_json(root/'source-plan.json',original)

def generate(q):
    calls=[full.calls[q['domain']][cid] for cid in q['supporting_call_ids']]
    result=full.candidate(q['domain'],q['question_class'],calls)
    print(json.dumps({'job':result['job_id'],'status':result['status'],'failure':result.get('failure')}),flush=True)
    return result

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    results=list(pool.map(generate,original))
with full.transport.db() as db:
    artifacts=[root/p for p, in db.execute("SELECT artifact FROM attempts WHERE stage='generate' AND status='ok' ORDER BY started")]
    cost=db.execute('SELECT SUM(estimated_usd) FROM attempts').fetchone()[0]
rows=[]
for i,r in enumerate(results,1):
    q=r.get('candidate',r)
    if not q.get('question'):
        for p in artifacts:
            a=json.loads(p.read_text());v=json.loads(a['request']['messages'][0]['content'].split('INPUT JSON:\n',1)[1])
            if [c['call_id'] for c in v['calls']]==r['supporting_call_ids']:
                q=a['parsed'];break
    rows.append({'item':i,**{k:r.get(k) for k in ['job_id','domain','question_class','supporting_call_ids','status','failure']},
                 'question':q.get('question'),'gold_answer':q.get('gold_answer')})
assert len(rows)==20 and all(r['question'] and r['gold_answer'] for r in rows)
write_json(Path('reports/natural-pilot-v5-concise-glm.json'),{'questions':rows,'estimated_usd':cost,
    'counts':dict(Counter(r['status'] for r in rows)),
    'limitations':'First proposal for the same 20 seeded source units as v2. Old exact-source specificity gate retained for comparability; statuses do not establish answer ambiguity or final approval.'})
