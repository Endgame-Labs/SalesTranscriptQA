"""Check domain-language selection without rewriting source facts."""
import concurrent.futures
import json
from pathlib import Path
from salestranscriptqa.query_coherence import assess
from salestranscriptqa.transport import Transport
from salestranscriptqa.corpus import write_json

cases=[
 ("What vehicles is Isaac Turner considering and what installation timeline did he require?",False),
 ("What is Ava Singh's budget and desired installation timeline for the Jeep Grand Cherokee and protection film purchase?",True),
 ("What is Zaid Hassan's budget and installation timeline for the Lahore Digital Experts purchase?",True),
 ("What is the total quoted price for Fatima Ali's order of 2 PulseSim Pro and 4 NextGen IDE units, and what installation timeline did she require?",True),
 ("What discovery meeting did Aarav schedule with Nina Rossi of Innovative Robotics, and what did she say data protection was for their operations?",False),
 ("What quote did Miguel give Rajveer Singh for AI Cirku-Tech, including the discount and total price?",True),
]
transport=Transport('runs/sales-query-plausibility-calibration-v2')
def run(case):
 q,expected=case;r=assess(q,'single_call',transport)
 return {'question':q,'expected':expected,'passed':r['accepted']==expected,**r}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
 rows=list(pool.map(run,cases))
with transport.db() as db:
 cost=db.execute('SELECT COALESCE(SUM(estimated_usd),0) FROM attempts').fetchone()[0]
report={'results':rows,'passed':all(r['passed'] for r in rows),'estimated_usd':cost,
        'limitations':'Targeted language/coherence controls, not a random accuracy estimate. Source facts are not rewritten.'}
write_json(Path('reports/sales-query-plausibility-calibration-v2.json'),report)
print(json.dumps(report),flush=True)
