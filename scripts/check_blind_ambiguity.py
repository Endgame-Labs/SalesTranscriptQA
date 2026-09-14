"""Live regressions use the same full distractor pools as the previous failed audit."""
import json
from pathlib import Path
import pyarrow.parquet as pq
from salestranscriptqa.blind_ambiguity import audit
from salestranscriptqa.transport import Transport
from salestranscriptqa.corpus import write_json

rows = json.loads(Path('reports/natural-pilot-v2.json').read_text())['questions']
old = json.loads(Path('reports/natural-pilot-ambiguity-review-v2.json').read_text())['results']
calls = {c['call_id']:c for c in pq.read_table('data/corpus/b2c-corpus.parquet').to_pylist()}
transport = Transport('runs/blind-ambiguity-regression-v1')
results=[]
for i, expected in [(12,'ambiguous'),(17,'consistent_in_pool')]:
    q=rows[i]
    result=audit(q['question'],q['gold_answer'],[calls[cid] for cid in old[i]['pool_call_ids']],transport)
    results.append({'item':i+1,'question':q['question'],'expected':expected,**result})
    print(json.dumps({'item':i+1,'decision':result['decision']}),flush=True)
with transport.db() as db:
    cost=db.execute('SELECT SUM(estimated_usd) FROM attempts').fetchone()[0]
write_json(Path('reports/blind-ambiguity-regression-v2.json'),{'results':results,'estimated_usd':cost,
           'limitations':'Fixed distractor pools; single-source complete answers only. Not a multi-call production gate.'})
assert all(r['decision']==r['expected'] for r in results)
