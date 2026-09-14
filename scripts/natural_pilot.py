"""Review first proposals for 20 seeded random units; retain failures without resampling."""
import concurrent.futures
import json
import random
from collections import Counter
from pathlib import Path

from salestranscriptqa.corpus import write_json
from salestranscriptqa.natural import Natural, NATURAL_PROMPT

ROOT = Path('runs/natural-pilot-v2')
SEED = 20260914
full = Natural('data/corpus', ROOT, workers=12, proposals=3)
write_json(ROOT / 'prompt.json', {'prompt': NATURAL_PROMPT, 'seed': SEED})
buckets = {}
for u in full.plan():
    if u['domain'] == 'b2c' and u['question_class'] == 'multi_call':
        continue
    buckets.setdefault((u['domain'], u['question_class']), []).append(u)
rng = random.Random(SEED)
for units in buckets.values():
    rng.shuffle(units)
sample = [u for key, units in buckets.items() for u in units[:10 if key == ('b2c', 'single_call') else 5]]
write_json(ROOT / 'review-plan.json', {'seed': SEED, 'units': sample})


def propose(unit):
    calls = [full.calls[unit['domain']][cid] for cid in unit['supporting_call_ids']]
    return full.candidate(unit['domain'], unit['question_class'], calls, variant=0)


with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
    results = list(pool.map(propose, sample))
# Mechanical rejection can precede candidate persistence; recover the exact first
# generated text from its metered request artifact, never substitute a later retry.
with full.transport.db() as db:
    artifacts = [ROOT / p for p, in db.execute("SELECT artifact FROM attempts WHERE stage='generate' AND status='ok' ORDER BY started")]
    cost = db.execute('SELECT SUM(estimated_usd) FROM attempts').fetchone()[0]
rows = []
for result in results:
    candidate = result.get('candidate', result)
    if not candidate.get('question'):
        for p in artifacts:
            artifact = json.loads(p.read_text())
            payload = json.loads(artifact['request']['messages'][0]['content'].split('INPUT JSON:\n', 1)[1])
            if [c['call_id'] for c in payload['calls']] == result['supporting_call_ids']:
                candidate = artifact['parsed']
                break
    rows.append({**{k: result.get(k) for k in ['job_id', 'domain', 'question_class', 'status', 'failure', 'supporting_call_ids']},
                 'question': candidate.get('question'), 'gold_answer': candidate.get('gold_answer')})
assert len(rows) == 20 and all(r['question'] and r['gold_answer'] for r in rows)
report = {'seed': SEED, 'questions': rows, 'outcomes': dict(Counter(r['status'] for r in rows)),
          'estimated_usd_entire_trial': cost,
          'sampling': 'First proposal for each of 20 seeded random units: 10 B2C single, 5 B2B single, 5 B2B multi. No replacement of failures.',
          'cost_scope': 'Includes earlier accepted-target attempts from this run; not the cost of only these 20 first proposals.',
          'limitations': 'Automated gates only; specificity requires exact original source-set selection among TF-IDF distractors, which can reject alternative sources supporting the same answer. Passing does not establish corpus-wide unambiguity.'}
write_json(Path('reports/natural-pilot-v2.json'), report)
print(json.dumps({k:v for k,v in report.items() if k != 'questions'}), flush=True)
