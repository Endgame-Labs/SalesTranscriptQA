"""Diagnostic real-output coherence cases; not a random accuracy estimate."""
import concurrent.futures
import json
from pathlib import Path
from salestranscriptqa.query_coherence import assess
from salestranscriptqa.transport import Transport
from salestranscriptqa.corpus import write_json

questions=json.loads(Path('reports/sales-questions-v8-focused-seed20260916-n100.json').read_text())['questions']
# Single price/requirement/objection-response requests versus unrelated fact bundles.
labels={3:True,25:True,47:True,74:True,79:True,94:False,76:False}
transport=Transport('runs/sales-query-coherence-calibration-v1')
def run(item):
    number,expected=item;q=questions[number-1]
    result=assess(q['question'],q['question_class'],transport,version=1)
    return {'item':number,'question':q['question'],'expected':expected,'passed':result['accepted']==expected,**result}
with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
    rows=list(pool.map(run,labels.items()))
with transport.db() as db:
    cost=db.execute('SELECT COALESCE(SUM(estimated_usd),0) FROM attempts').fetchone()[0]
report={'results':rows,'passed':all(r['passed'] for r in rows),'estimated_usd':cost,
        'limitations':'Seven intentionally selected calibration examples; independent holdout review remains required.'}
write_json(Path('reports/sales-query-coherence-calibration-v1.json'),report)
print(json.dumps(report),flush=True)
