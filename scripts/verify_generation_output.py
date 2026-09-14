"""Verify complete sample/full output, source evidence, gates, coverage and Parquet parity."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pyarrow.parquet as pq
from salestranscriptqa.pilot import evidence_check
from salestranscriptqa.question_style import locator_flags
from salestranscriptqa.answer_consistency import aggregate
from salestranscriptqa.corpus import write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir',type=Path)
    parser.add_argument('--corpus',type=Path,default=Path('data/corpus'))
    args=parser.parse_args()
    root=args.run_dir
    read=lambda name:json.loads((root/name).read_text())
    progress,coverage,plan,config=[read(n) for n in ['progress.json','coverage.json','source-plan.json','config.json']]
    assert progress['complete'] is True and coverage['complete'] is True
    assert coverage['published'] is False
    assert coverage['full_corpus_complete']==(plan['scope']=='all')
    assert progress['completed_units']==progress['total_units']==len(plan['units'])==coverage['total_units']
    calls={}
    for domain in ['b2b','b2c']:
        path=args.corpus/f'{domain}-corpus.parquet'
        assert hashlib.sha256(path.read_bytes()).hexdigest()==config['corpus_hashes'][domain]
        calls.update({c['call_id']:c for c in pq.read_table(path).to_pylist()})
    excluded=set(plan.get('excluded_groups',[]))
    for unit in plan['units']:
        assert not (unit['domain']=='b2c' and unit['question_class']=='multi_call')
        for cid in unit['supporting_call_ids']:
            assert (calls[cid].get('group_id') or cid) not in excluded
    questions=read('questions.json')
    assert len(questions)==coverage['accepted_questions']==progress['accepted_after_dedup']
    assert len({q['question_id'] for q in questions})==len(questions)
    parquet=[q for domain in ['b2b','b2c'] for q in pq.read_table(root/f'{domain}-test.parquet').to_pylist()]
    canonical=lambda rows:json.dumps(sorted(rows,key=lambda q:q['question_id']),sort_keys=True)
    assert canonical(parquet)==canonical(questions)
    for q in questions:
        assert not locator_flags(q['question'])
        source=[calls[cid] for cid in q['supporting_call_ids']]
        evidence_check(deepcopy(q),source)
        candidate=read(f'candidates/{q["provenance"]["job_id"]}.json')
        assert candidate['status']=='accepted' and candidate['contract_checked'] is True
        for field in ['question','gold_answer','supporting_call_ids','evidence']:
            assert candidate[field]==q[field]
        gate=candidate['stages']['specificity']
        assert gate['method']=='reference-blind-group-consistency-v2'
        assert aggregate(gate['groups'])=='consistent_in_pool'
        assert candidate['stages']['final_audit']['pass'] is True
    report={'verified':True,'scope':plan['scope'],'source_units':len(plan['units']),
            'accepted_questions':len(questions),'accepted_counts':dict(Counter(q['domain']+'/'+q['question_class'] for q in questions)),
            'excluded_groups':len(excluded),'checks':['source hashes','complete scope','group exclusions','no B2C multi-call',
            'JSON/Parquet parity','unique question IDs','exact evidence','accepted contract and consistency gates','locator checks'],
            'limitations':'Artifact integrity and recorded-gate verification, not an independent semantic quality estimate.'}
    write_json(Path('reports')/(root.name+'-verification.json'),report)
    print(json.dumps(report))


if __name__=='__main__':
    main()
