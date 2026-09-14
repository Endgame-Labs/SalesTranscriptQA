"""Paid live regression: repeated warranty price versus conflicting demo times."""
import json
from pathlib import Path
import pyarrow.parquet as pq
from salestranscriptqa.ambiguity import audit
from salestranscriptqa.transport import Transport
from salestranscriptqa.corpus import write_json

calls = {c['call_id']:c for c in pq.read_table('data/corpus/b2c-corpus.parquet').to_pylist()}
transport = Transport('runs/answer-ambiguity-regression-v2')
cases = [
    ('equivalent_sources', 'What is the price of the extended warranty offered by AutoElite Motors?',
     '$1,299.99', ['b2c:a05Ws000005SdWcIAK','b2c:a05Ws000005STyqIAG'], 'consistent_in_pool'),
    ('conflicting_appointments', 'What is the scheduled time for the product demonstration of the Volvo XC60 and Lexus RX 350?',
     'Saturday at noon.', ['b2c:a05Ws000005SZOFIA4','b2c:a05Ws000005SXxTIAW'], 'ambiguous'),
]
results=[]
for name,q,a,ids,expected in cases:
    result = audit(transport,q,a,[calls[i] for i in ids])
    results.append({'case':name,'question':q,'call_ids':ids,'expected':expected,**result})
with transport.db() as db:
    cost = db.execute('SELECT SUM(estimated_usd) FROM attempts').fetchone()[0]
write_json(Path('reports/answer-ambiguity-regression-v2.json'), {'results':results,'estimated_usd':cost})
print(json.dumps({'results':[(r['case'],r['decision']) for r in results], 'estimated_usd':cost}))
assert all(r['decision']==r['expected'] for r in results)
