"""Run all eligible v9 source units after an explicitly approved expanded checkpoint.

This does not create an approval, relax quality gates, or publish to Hugging Face.
The assessment must contain approved_for_full, question_sha256, and budget_limits.
Budget limits are cumulative generation/review/RAG ceilings plus a reserve. All
four are checked against the shared $5,000 campaign ceiling before paid stages.
"""
import argparse
import fcntl
import hashlib
import json
import subprocess
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from salestranscriptqa.corpus import write_json
from salestranscriptqa.full_checkpoint import budget_envelope, reviewed_selection
from seed_full_run import seed

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT / 'runs/sales-expanded-2000-v1'
ROOT = PROJECT / 'runs/sales-full-v2'
EVAL = PROJECT.parent / '2026-09-12-salestranscriptqa-rag-evaluation'
EVAL_ROOT = EVAL / 'runs/full-v2'
EVAL_REPORT = EVAL / 'reports/full-v2'
REPORT = PROJECT / 'reports/sales-full-v2-accepted.json'
REVIEW_ROOT = PROJECT / 'runs/sales-full-v2-accepted-qwen-review-v1'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint-review', type=Path, required=True)
    parser.add_argument('--check-only', action='store_true', help='Validate approval and budget without seeding or calling models')
    args = parser.parse_args()
    approval = json.loads(args.checkpoint_review.read_text())
    source_hash = hashlib.sha256((SOURCE / 'reviewed/questions.json').read_bytes()).hexdigest()
    if approval.get('approved_for_full') is not True or approval.get('question_sha256') != source_hash:
        raise ValueError('Full run requires approval of this exact completed checkpoint')
    if json.loads((SOURCE / 'workflow.json').read_text()).get('stage') != 'complete':
        raise ValueError('Expanded generation, independent review, and RAG must finish first')
    config = json.loads((SOURCE / 'config.json').read_text())
    if config['version'] != 'sales-questions-v9-line-evidence' or config['workers'] != 16 or config['proposals_per_unit'] != 3:
        raise ValueError('Full run must preserve the approved v9 generation configuration')
    limits = approval['budget_limits']
    # Before seeding, all source costs are already included in campaign accounting.
    import sqlite3
    with sqlite3.connect(f'file:{SOURCE}/progress.sqlite?mode=ro', uri=True) as db:
        if db.execute("SELECT COUNT(*) FROM attempts WHERE estimated_usd IS NULL").fetchone()[0]:
            raise ValueError('Resolve unknown checkpoint API costs before full expansion')
        inherited = db.execute('SELECT COALESCE(SUM(estimated_usd),0) FROM attempts').fetchone()[0]

    def check_budget():
        report = json.loads(subprocess.check_output(['uv', 'run', 'python', 'campaign_costs.py'], cwd=EVAL, text=True))
        return budget_envelope(report, limits, inherited, ROOT, REVIEW_ROOT, EVAL_ROOT)

    envelope = check_budget()
    if args.check_only:
        print(json.dumps(envelope, indent=2))
        return
    if not ROOT.exists():
        seed(SOURCE, ROOT, args.checkpoint_review)
    receipt = json.loads((ROOT / 'cache-import.json').read_text())
    if receipt['approved_questions_sha256'] != source_hash or receipt['checkpoint_review'] != approval:
        raise ValueError('Existing full cache was seeded from a different checkpoint assessment')
    if receipt['carried_forward_estimated_usd'] != inherited:
        raise ValueError('Completed checkpoint cost changed after cache import')
    with (ROOT / 'workflow.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)

        def status(stage, **extra):
            record = dict(stage=stage, updated=time.time(), **extra)
            write_json(ROOT / 'workflow.json', record)
            print(json.dumps(record), flush=True)

        def run(stage, command, cwd=PROJECT, paid=False):
            if paid:
                write_json(ROOT / f'{stage}-budget-envelope.json', check_budget())
            status(stage)
            with (ROOT / f'{stage}.log').open('a') as log:
                subprocess.run(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, check=True)

        try:
            generation = ['uv', 'run', 'python', 'scripts/generate_sales_questions.py', '--all',
                          '--seed', '20260919', '--workers', '16', '--proposals', '3',
                          '--budget-usd', str(limits['generation_usd']), '--run-dir', str(ROOT)]
            write_json(ROOT / 'validation-command.json', generation)
            run('source-plan', [*generation, '--plan-only'])
            plan = json.loads((ROOT / 'source-plan.json').read_text())
            if plan['scope'] != 'all' or len(plan['units']) != 14916 or any(
                u['domain'] == 'b2c' and u['question_class'] == 'multi_call' for u in plan['units']
            ):
                raise ValueError('Full source scope does not match approved corpus')
            run('generation', generation, paid=True)
            run('generation-verify', ['uv', 'run', 'python', 'scripts/verify_generation_output.py', str(ROOT)])
            run('generation-export', ['uv', 'run', 'python', 'scripts/review_generation_output.py', str(ROOT)])
            run('independent-review', ['uv', 'run', 'python', 'scripts/review_sales_sample.py', str(REPORT),
                                      '--budget-usd', str(limits['review_usd'])], paid=True)
            reviews = json.loads((PROJECT / 'reports/sales-full-v2-accepted-qwen-review-v1.json').read_text())['results']
            questions = json.loads((ROOT / 'selected/questions.json').read_text())
            exported = json.loads(REPORT.read_text())['questions']
            registry_path = PROJECT / 'reports/cohort-registry.json'
            registry = json.loads(registry_path.read_text())
            # Preserve both the named historical quarantine and expanded review rejections.
            checkpoint_rejections = json.loads((PROJECT / 'reports/sales-expanded-2000-v1-review-selection.json').read_text())['rejected']
            final, rejected = reviewed_selection(questions, exported, reviews,
                                                 registry['excluded_questions'] + checkpoint_rejections)
            if not final or not all(any(q['domain'] == d for q in final) for d in ['b2b', 'b2c']):
                raise ValueError('Reviewed cohort must be nonempty and cover both domains')
            active = ROOT / 'reviewed'
            active.mkdir(exist_ok=True)
            frozen = active / 'questions.json'
            if frozen.exists() and json.loads(frozen.read_text()) != final:
                raise ValueError('Frozen full cohort changed on resume')
            write_json(frozen, final)
            allowed = {q['question_id'] for q in final}
            for domain in ['b2b', 'b2c']:
                table = pq.read_table(ROOT / 'selected' / f'{domain}-test.parquet')
                pq.write_table(table.filter(pa.array([q['question_id'] in allowed for q in table.to_pylist()])), active / f'{domain}-test.parquet')
            selection = dict(before_review=len(questions), accepted=len(final), rejected=rejected,
                             question_sha256=hashlib.sha256(frozen.read_bytes()).hexdigest(),
                             policy='Independent quality review and prior quarantines only; RAG failures never remove questions.')
            write_json(PROJECT / 'reports/sales-full-v2-review-selection.json', selection)
            run('rag-evaluation', ['uv', 'run', 'python', 'sample_eval.py', '--questions', str(frozen),
                                  '--run-dir', str(EVAL_ROOT), '--report-dir', str(EVAL_REPORT),
                                  '--budget-usd', str(limits['rag_usd'])], EVAL, paid=True)
            run('rag-verification', ['uv', 'run', 'python', 'sample_report.py', '--run-dir', str(EVAL_ROOT),
                                    '--report-dir', str(EVAL_REPORT)], EVAL)
            registry['active_cohort'] = {'path': str(active.relative_to(PROJECT)), 'questions': len(final), 'sha256': selection['question_sha256']}
            registry['full_run'] = {'path': str(ROOT.relative_to(PROJECT)), 'source_units': 14916,
                                    'status': 'generation, independent review, and four-arm RAG complete', 'published': False}
            write_json(registry_path, registry)
            status('complete', accepted_questions=len(final), generation_selected=len(questions),
                   report=str(EVAL_REPORT / 'RESULTS.md'), published=False)
        except Exception as exc:
            status('failed', error_type=type(exc).__name__)
            raise


if __name__ == '__main__':
    main()
