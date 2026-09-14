"""Live-model regressions for known conflicting appointment and duplicate warranty answers."""
import concurrent.futures
import json
from pathlib import Path
import pyarrow.parquet as pq
from salestranscriptqa.answer_consistency import check_group
from salestranscriptqa.transport import Transport
from salestranscriptqa.corpus import write_json


def main():
    questions=json.loads(Path('reports/natural-pilot-v2.json').read_text())['questions']
    calls={c['call_id']:c for c in pq.read_table('data/corpus/b2c-corpus.parquet').to_pylist()}
    transport=Transport('runs/group-consistency-regressions-v1')
    tasks=[(12,'b2c:a05Ws000005SXxTIAW','conflicting'),
           (17,'b2c:a05Ws000005STyqIAG','equivalent')]
    def run(task):
        index,cid,expected=task
        q=questions[index]
        verdict=check_group(q['question'],q['gold_answer'],[calls[cid]],transport)
        return {'item':index+1,'expected':expected,'passed':verdict['classification']==expected,'result':verdict}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        rows=list(pool.map(run,tasks))
    with transport.db() as db:
        cost=db.execute('SELECT COALESCE(SUM(estimated_usd),0) FROM attempts').fetchone()[0]
    report={'results':rows,'passed':all(r['passed'] for r in rows),'estimated_usd':cost}
    write_json(Path('reports/group-consistency-regressions-v1.json'),report)
    print(json.dumps(report),flush=True)
    if not report['passed']:
        raise SystemExit(1)


if __name__=='__main__':
    main()
