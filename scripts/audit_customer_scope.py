"""Diagnostic only: audit every frozen question, without RAG results or cohort mutation."""
import argparse,concurrent.futures,hashlib,json
from collections import Counter
from pathlib import Path
import pyarrow.parquet as pq
from salestranscriptqa.corpus import write_json
from salestranscriptqa.event_scope import assess,customer_history,VERSION
from salestranscriptqa.transport import Transport

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('questions',type=Path);p.add_argument('--run-dir',type=Path,required=True)
    p.add_argument('--budget-usd',type=float,default=30);p.add_argument('--workers',type=int,default=8)
    a=p.parse_args();qs=json.loads(a.questions.read_text());t=Transport(a.run_dir,budget_usd=a.budget_usd)
    calls={c['call_id']:c for d in ['b2b','b2c'] for c in pq.read_table(f'data/corpus/{d}-corpus.parquet').to_pylist()}
    def check(q):
        sources=customer_history(q,calls);r=dict(question_id=q['question_id'],question=q['question'],gold_answer=q['gold_answer'],domain=q['domain'],question_class=q['question_class'],pool_call_ids=[c['call_id'] for c in sources],**assess(q,sources,t))
        write_json(a.run_dir/'questions'/f"{q['question_id']}.json",r)
        print(json.dumps({'question_id':q['question_id'],'passed':r['passed'],'scope':r['extraction'].get('scope'),'reason':(r.get('verdict') or {}).get('reason')}),flush=True)
        return r
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:rows=list(pool.map(check,qs))
    with t.db() as db:cost=db.execute('SELECT COALESCE(SUM(estimated_usd),0) FROM attempts').fetchone()[0]
    report={'protocol':VERSION,'question_sha256':hashlib.sha256(a.questions.read_bytes()).hexdigest(),'questions':len(qs),'counts':dict(Counter('pass' if r['passed'] else 'fail' for r in rows)),'estimated_usd':cost,'results':rows,'policy':'Diagnostic, all frozen questions; no RAG outcomes used; no cohort mutation. Full account/lead-ID histories, not a full-corpus proof.'}
    write_json(a.run_dir/'report.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='results'}),flush=True)

if __name__=='__main__':main()
