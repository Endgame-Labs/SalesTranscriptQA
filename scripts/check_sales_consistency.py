"""Audit every accepted sample question against lexical neighbors and complete CRM groups."""
import argparse
import concurrent.futures
import json
from collections import Counter
from pathlib import Path
from salestranscriptqa.sales_questions import SalesQuestionsGLM
from salestranscriptqa.answer_consistency import check_group, check_group_v2, aggregate, JUDGE
from salestranscriptqa.transport import RATES
from salestranscriptqa.corpus import write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    parser.add_argument('--version',choices=['1','2'],default='2')
    args=parser.parse_args()
    report=json.loads(args.report.read_text())
    root=Path('runs')/(args.report.stem+'-consistency-v'+args.version)
    if args.version=='2':
        RATES[JUDGE]=(2.0,0.25,6.0)
    checker=check_group_v2 if args.version=='2' else check_group
    full=SalesQuestionsGLM('data/corpus',root,workers=8)
    lookup={}
    for domain,calls in full.calls.items():
        lookup[domain]={}
        for call in calls.values():
            lookup[domain].setdefault(call.get('group_id') or call['call_id'],[]).append(call)
    def run(q):
        calls,vectorizer,matrix=full.index[q['domain']]
        scores=(matrix @ vectorizer.transform([q['question']]).T).toarray().ravel()
        selected=[calls[i] for i in scores.argsort()[-30:][::-1]]
        selected += [full.calls[q['domain']][cid] for cid in q['supporting_call_ids']]
        groups=sorted({c.get('group_id') or c['call_id'] for c in selected})
        rows=[]
        for group in groups:
            rows.append(checker(q['question'],q['gold_answer'],lookup[q['domain']][group],full.transport))
        result={'item':q['item'],'question':q['question'],'gold_answer':q['gold_answer'],
                'decision':aggregate(rows),'groups':rows}
        write_json(root/'questions'/f'{q["job_id"]}.json',result)
        print(json.dumps({'item':q['item'],'decision':result['decision']}),flush=True)
        return result
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        rows=list(pool.map(run,[q for q in report['questions'] if q['status']=='accepted']))
    with full.transport.db() as db:
        cost=db.execute('SELECT COALESCE(SUM(estimated_usd),0) FROM attempts').fetchone()[0]
    result={'results':rows,'counts':dict(Counter(r['decision'] for r in rows)),'estimated_usd':cost,
            'version':args.version,'limitations':'Top-30 lexical neighbors plus intended sources, expanded to whole explicit CRM groups. Reference-blind GLM extraction, evidence-aware Qwen adjudication. Not exhaustive corpus proof or human labels.'}
    write_json(Path('reports')/(root.name+'.json'),result)
    print(json.dumps({k:v for k,v in result.items() if k!='results'}),flush=True)


if __name__=='__main__':
    main()
