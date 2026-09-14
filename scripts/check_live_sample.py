"""Run existing final gates and independent review on a frozen hourly QA sample."""
import argparse
import json
from pathlib import Path
import pyarrow.parquet as pq
from salestranscriptqa.transport import Transport,RATES,digest
from salestranscriptqa.query_coherence import assess
from salestranscriptqa.multi_necessity import assess as necessity
from salestranscriptqa.question_style import locator_flags
from review_sales_sample import MODEL,PROMPT,FIELDS


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('sample',type=Path);p.add_argument('--run-dir',type=Path,required=True)
    a=p.parse_args();qs=json.loads(a.sample.read_text())['questions']
    calls={c['call_id']:c for d in ['b2b','b2c'] for c in pq.read_table(f'data/corpus/{d}-corpus.parquet').to_pylist()}
    RATES[MODEL]=(2,.25,6);t=Transport(a.run_dir,budget_usd=5);results=[]
    for q in qs:
        row={'question_id':q['question_id'],'question':q['question'],'coherence':assess(q['question'],q['question_class'],t)}
        sources=[calls[cid] for cid in q['supporting_call_ids']]
        if q['question_class']=='multi_call' and row['coherence']['accepted']:row['necessity']=necessity(q,sources,t)
        payload={k:q[k] for k in ['question','gold_answer','question_class']}
        payload['calls']=[{k:c[k] for k in ['call_id','metadata','dialogue']} for c in sources]
        verdict=t.request(MODEL,PROMPT+'\nINPUT JSON:\n'+json.dumps(payload),'independent_sales_review',nonce=digest(payload))
        row['independent_review']={'passed':all(verdict.get(f) is True for f in FIELDS) and verdict.get('locator_preamble') is False and not locator_flags(q['question']),'verdict':verdict}
        results.append(row)
        print(json.dumps({'question_id':q['question_id'],'coherence':row['coherence']['accepted'],'necessity':row.get('necessity',{}).get('accepted'),'review':row['independent_review']['passed']}),flush=True)
    output=a.sample.with_name(a.sample.stem.replace('-sample','-gates')+'.json');output.write_text(json.dumps(results,indent=2)+'\n')

if __name__=='__main__':main()
