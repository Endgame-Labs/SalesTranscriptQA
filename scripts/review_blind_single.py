"""Review every single-call pilot item with per-transcript blind extraction."""
import concurrent.futures
import json
from collections import Counter
from pathlib import Path
import pyarrow.parquet as pq
from salestranscriptqa.blind_ambiguity import audit
from salestranscriptqa.transport import Transport
from salestranscriptqa.corpus import write_json

questions=json.loads(Path('reports/natural-pilot-v2.json').read_text())['questions']
previous=json.loads(Path('reports/natural-pilot-ambiguity-review-v2.json').read_text())['results']
calls={c['call_id']:c for d in ['b2b','b2c'] for c in pq.read_table(f'data/corpus/{d}-corpus.parquet').to_pylist()}
transport=Transport('runs/blind-ambiguity-regression-v1')

def check(item):
    i,q=item
    ids=previous[i]['pool_call_ids']
    result=audit(q['question'],q['gold_answer'],[calls[cid] for cid in ids],transport,workers=6)
    value={'item':i+1,'question':q['question'],'previous_status':q['status'],**result}
    write_json(Path('runs/blind-single-review')/(q['job_id']+'.json'),value)
    print(json.dumps({'item':i+1,'decision':result['decision']}),flush=True)
    return value

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    results=list(pool.map(check,[(i,q) for i,q in enumerate(questions) if q['question_class']=='single_call']))
with transport.db() as db:
    cost=db.execute('SELECT SUM(estimated_usd) FROM attempts').fetchone()[0]
write_json(Path('reports/blind-single-review.json'),{'results':results,
           'counts':dict(Counter(r['decision'] for r in results)), 'cumulative_trial_usd':cost,
           'limitations':'15 single-call questions, each against its frozen top-30 TF-IDF pool plus original sources. Does not replace other gates or establish corpus-wide uniqueness. Cost includes earlier regression trials.'})
