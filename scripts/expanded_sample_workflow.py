"""Durable 2,000-unit generation → independent review → frozen-cohort RAG test.

Run from SalesTranscriptQA: uv run python scripts/expanded_sample_workflow.py
Never publishes to Hugging Face. Each stage is resumable; errors stop the workflow.
"""
import fcntl
import hashlib
import json
import subprocess
import time
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from salestranscriptqa.corpus import write_json

PROJECT=Path(__file__).resolve().parents[1]
ROOT=Path('runs/sales-expanded-2000-v1')
EVAL=PROJECT.parent/'2026-09-12-salestranscriptqa-rag-evaluation'
EVAL_ROOT='runs/expanded-2000-v1'
EVAL_REPORT='reports/expanded-2000-v1'
GEN=['uv','run','python','scripts/generate_sales_questions.py','--sample','2000','--seed','20260919',
     '--workers','16','--proposals','3','--budget-usd','850','--run-dir',str(ROOT)]
for exclusion in ['reports/sales-questions-v6-glm-seed20260915-n100.json',
                  'runs/sales-questions-v8-focused-seed20260916-n100/plan.json',
                  'runs/sales-ready-validation-20260917/source-plan.json',
                  'runs/sales-ready-validation-20260918/source-plan.json']:
    GEN += ['--exclude-report',exclusion]

def main():
    root=PROJECT/ROOT
    root.mkdir(parents=True,exist_ok=True)
    with (root/'workflow.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        def status(stage,**kw):
            record=dict(stage=stage,updated=time.time(),**kw)
            write_json(root/'workflow.json',record)
            print(json.dumps(record),flush=True)
        def run(stage,argv,cwd=PROJECT):
            status(stage)
            with (root/f'{stage}.log').open('a') as log:
                subprocess.run(argv,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,check=True)
        try:
            write_json(root/'validation-command.json',GEN)
            run('generation',GEN)
            run('generation-verify',['uv','run','python','scripts/verify_generation_output.py',str(ROOT)])
            run('generation-export',['uv','run','python','scripts/review_generation_output.py',str(ROOT)])
            report=f'reports/{ROOT.name}-accepted.json'
            run('independent-review',['uv','run','python','scripts/review_sales_sample.py',report])
            review=json.loads((PROJECT/f'reports/{ROOT.name}-accepted-qwen-review-v1.json').read_text())
            qs=json.loads((root/'selected/questions.json').read_text())
            exported=json.loads((PROJECT/report).read_text())['questions']
            by_item={q['item']:q for q in exported}
            assert len(review['results'])==len(qs)==len(by_item)
            allowed={by_item[r['item']]['question_id'] for r in review['results'] if r['passed'] is True and not r['mechanical_locator_flags']}
            final=[q for q in qs if q['question_id'] in allowed]
            assert final and all(any(q['domain']==d for q in final) for d in ['b2b','b2c'])
            active=root/'reviewed'
            active.mkdir(exist_ok=True)
            frozen=active/'questions.json'
            if frozen.exists():assert json.loads(frozen.read_text())==final
            write_json(frozen,final)
            for d in ['b2b','b2c']:
                table=pq.read_table(root/'selected'/f'{d}-test.parquet')
                pq.write_table(table.filter(pa.array([q['question_id'] in allowed for q in table.to_pylist()])),active/f'{d}-test.parquet')
            selection=dict(before_review=len(qs),accepted=len(final),rejected=[r for r in review['results'] if by_item[r['item']]['question_id'] not in allowed],
                           question_sha256=hashlib.sha256(frozen.read_bytes()).hexdigest(),
                           policy='Independent source review exclusions happen before RAG. RAG failures do not remove questions.')
            write_json(PROJECT/f'reports/{ROOT.name}-review-selection.json',selection)
            args=['--questions',str(frozen),'--run-dir',EVAL_ROOT,'--report-dir',EVAL_REPORT]
            run('rag-evaluation',['uv','run','python','sample_eval.py',*args],EVAL)
            run('rag-verification',['uv','run','python','sample_report.py','--run-dir',EVAL_ROOT,'--report-dir',EVAL_REPORT],EVAL)
            registry_path=PROJECT/'reports/cohort-registry.json'
            registry=json.loads(registry_path.read_text())
            registry['active_cohort']={'path':str(ROOT/'reviewed'),'questions':len(final),'sha256':selection['question_sha256']}
            registry['active_seed']['status']='superseded by expanded reviewed cohort'
            registry['expansion']['status']='generation, independent review, and RAG evaluation complete'
            write_json(registry_path,registry)
            status('complete',accepted_questions=len(final),generation_selected=len(qs),report=str(EVAL/EVAL_REPORT/'RESULTS.md'),published=False)
        except Exception as exc:
            status('failed',error_type=type(exc).__name__)
            raise

if __name__=='__main__':main()
