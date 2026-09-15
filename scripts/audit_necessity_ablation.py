"""Diagnostic only: independent per-source answers; no production gate/cohort mutation."""
import argparse
import json
from pathlib import Path

import pyarrow.parquet as pq

from salestranscriptqa.corpus import write_json
from salestranscriptqa.necessity_ablation import VERSION, assess
from salestranscriptqa.transport import Transport


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('questions', type=Path)
    p.add_argument('--run-dir', type=Path, required=True)
    p.add_argument('--budget-usd', type=float, default=1)
    args = p.parse_args()
    questions = json.loads(args.questions.read_text())
    calls = {c['call_id']: c for d in ['b2b', 'b2c']
             for c in pq.read_table(f'data/corpus/{d}-corpus.parquet').to_pylist()}
    transport = Transport(args.run_dir, budget_usd=args.budget_usd)
    rows = []
    for q in questions:
        result = assess(q, [calls[c] for c in q['supporting_call_ids']], transport)
        row = {'question_id': q['question_id'], 'question': q['question'],
               'gold_answer': q['gold_answer'], **result}
        rows.append(row)
        write_json(args.run_dir / 'questions' / f"{q['question_id']}.json", row)
        print(json.dumps({k: row[k] for k in ['question_id', 'valid', 'supports_necessity']}),
              flush=True)
    with transport.db() as db:
        cost = db.execute('SELECT COALESCE(SUM(estimated_usd),0) FROM attempts').fetchone()[0]
    write_json(args.run_dir / 'report.json', {'protocol': VERSION, 'questions': len(rows),
               'estimated_usd': cost, 'results': rows,
               'policy': 'Diagnostic only; extraction omissions can cause false necessity. '
                         'No production gate changes, RAG outcomes or cohort mutation.'})


if __name__ == '__main__':
    main()
