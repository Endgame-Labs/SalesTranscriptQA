"""Replay observed false conflicts plus known duplicate/conflict controls."""
import concurrent.futures
import json
from pathlib import Path
import pyarrow.parquet as pq
from salestranscriptqa.answer_consistency import check_group_v2
from salestranscriptqa.transport import Transport
from salestranscriptqa.corpus import write_json

calls={c['call_id']:c for d in ['b2b','b2c'] for c in pq.read_table(f'data/corpus/{d}-corpus.parquet').to_pylist()}
old=json.loads(Path('reports/natural-pilot-v2.json').read_text())['questions']
new=json.loads(Path('reports/sales-questions-v6-glm-seed20260915-n100.json').read_text())['questions']
tasks=[{'label':'appointment_conflict','q':old[12],'ids':['b2c:a05Ws000005SXxTIAW'],'expected':'conflicting'},
       {'label':'duplicate_warranty','q':old[17],'ids':['b2c:a05Ws000005STyqIAG'],'expected':'equivalent'}]
for path in Path('runs/sales-questions-v6-glm-seed20260915-n100-consistency-v1/questions').glob('*.json'):
    row=json.loads(path.read_text())
    if row['item']==19:
        for group in row['groups']:
            if group['classification']=='conflicting':
                tasks.append({'label':'wrong_salesperson_'+group['call_ids'][0],'q':new[18],
                              'ids':group['call_ids'],'expected':'insufficient'})
    if row['item']==10:
        for group in row['groups']:
            if group['classification']=='conflicting':
                expected='conflicting' if 'b2b:a05Wt000003Sv6XIAS' in group['call_ids'] else 'insufficient'
                tasks.append({'label':'quote_scope_'+group['call_ids'][0],'q':new[9],
                              'ids':group['call_ids'],'expected':expected})
transport=Transport('runs/group-consistency-calibration-v2')
def run(task):
    q=task['q'];result=check_group_v2(q['question'],q['gold_answer'],[calls[i] for i in task['ids']],transport)
    return {'label':task['label'],'expected':task['expected'],'passed':result['classification']==task['expected'],'result':result}
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    rows=list(pool.map(run,tasks))
with transport.db() as db:
    cost=db.execute('SELECT COALESCE(SUM(estimated_usd),0) FROM attempts').fetchone()[0]
report={'results':rows,'passed':all(r['passed'] for r in rows),'estimated_usd':cost,
        'limitations':'Targeted observed failure regressions, not a random quality estimate.'}
write_json(Path('reports/group-consistency-calibration-v2.json'),report)
print(json.dumps(report),flush=True)
