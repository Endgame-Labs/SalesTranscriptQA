"""Assess all 20 existing questions against 30 lexical competitors plus source calls."""
import concurrent.futures
import json
import random
from pathlib import Path
from salestranscriptqa.natural import NaturalNext
from salestranscriptqa.ambiguity import audit
from salestranscriptqa.corpus import write_json

full = NaturalNext('data/corpus','runs/natural-pilot-v3-ambiguity-v2',workers=4)
rows = json.loads(Path('reports/natural-pilot-v2.json').read_text())['questions']

def check(q):
    calls,vectorizer,matrix = full.index[q['domain']]
    scores = (matrix @ vectorizer.transform([q['question']]).T).toarray().ravel()
    pool = {calls[i]['call_id']:calls[i] for i in scores.argsort()[-30:][::-1]}
    pool.update({cid:full.calls[q['domain']][cid] for cid in q['supporting_call_ids']})
    sources = list(pool.values())
    random.Random(q['job_id']).shuffle(sources)
    result = audit(full.transport,q['question'],q['gold_answer'],sources)
    value = {'job_id':q['job_id'],'question':q['question'],'previous_status':q['status'],
             'previous_failure':q['failure'],'pool_call_ids':[c['call_id'] for c in sources], **result}
    write_json(full.root/'reviews'/(q['job_id']+'.json'),value)
    print(json.dumps({'job':q['job_id'],'decision':result['decision']}),flush=True)
    return value

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(check,rows))
with full.transport.db() as db:
    cost = db.execute('SELECT SUM(estimated_usd) FROM attempts').fetchone()[0]
write_json(Path('reports/natural-pilot-ambiguity-review-v2.json'),
           {'results':results,'estimated_usd':cost,
            'limitations':'Thirty TF-IDF competitors plus original sources per question; not corpus-wide proof. Does not override any other quality, evidence, or multi-call necessity gate.'})
