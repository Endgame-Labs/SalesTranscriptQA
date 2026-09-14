"""Offline high-recall entity absence diagnostic; never changes production gates."""
import argparse
import collections
import json
import sqlite3
from pathlib import Path
import pyarrow.parquet as pq


from salestranscriptqa.speaker_scope import words,speaker_catalog,required_speakers


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=Path('reports/absent-speaker-probe-v2.json'));args=parser.parse_args()
    corpus=[c for d in ['b2b','b2c'] for c in pq.read_table(f'data/corpus/{d}-corpus.parquet').to_pylist()]
    names=speaker_catalog(corpus)
    # Full known speaker names only. Retain a group if ANY name token occurs anywhere.
    # This deliberately keeps aliases/partial-name cases for model review.
    qcache={};gcache={};stats=collections.Counter();blocked=[];contradictions=[]
    root=Path('runs/sales-expanded-2000-v1')
    with sqlite3.connect(f'file:{root}/progress.sqlite?mode=ro',uri=True) as db:
        records=db.execute("SELECT artifact,estimated_usd FROM attempts WHERE stage='group_blind_verification_v2' AND status='ok' ORDER BY started").fetchall()
    for artifact,cost in records:
        v=json.loads((root/artifact).read_text());p=json.loads(v['request']['messages'][0]['content'].split('\nINPUT JSON:\n',1)[1])
        question=p['question']
        if question not in qcache:
            qcache[question]=required_speakers(question,names)
        key=json.dumps(p['calls'],sort_keys=True,ensure_ascii=False)
        if key not in gcache:gcache[key]=set(words(key))
        absent=[name for name in qcache[question] if not (set(name)&gcache[key])]
        complete=v['parsed'].get('complete')
        stats['checked']+=1;stats['original_complete_true']+=int(complete is True);stats['known_cost']+=cost or 0
        if absent:
            row={'question':question,'absent_names':[' '.join(n) for n in absent],'call_ids':[c['call_id'] for c in p['calls']],
                 'original_complete':complete,'artifact':artifact,'cost':cost}
            blocked.append(row);stats['would_skip']+=1;stats['would_skip_cost']+=cost or 0
            if complete is not False:contradictions.append({**row,'original_verdict':v['parsed']})
    result={'stats':dict(stats),'known_speaker_names':len(names),'unique_questions':len(qcache),'contradictions':contradictions,'skipped_examples':blocked[:30],
            'production_changed':False,'rule':'Only exact normalized full speaker names in clear subject/recipient/possessive positions; ambiguous syntax falls back. Reject a source group only if every token of at least one such name is absent from its complete metadata/dialogue. Any partial-name occurrence keeps model verification.',
            'limitations':'Agreement with saved model decisions is not proof of universal recall. Query mentions can be incidental; semantic scope and alias regressions must be assessed before adoption.'}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['skipped_examples','contradictions']}));print('Contradictions',len(contradictions))

if __name__=='__main__':main()
