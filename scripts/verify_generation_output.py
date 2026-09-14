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
from salestranscriptqa.speaker_scope import VERSION, precheck_group, speaker_catalog


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
    scope_names=speaker_catalog(calls.values()) if plan.get("explicit_speaker_prefilter") else frozenset()
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
        for group in gate['groups']:
            if group.get('method')==VERSION:
                checked=precheck_group(q['question'],[calls[cid] for cid in group['call_ids']],scope_names)
                assert checked==group and checked['classification']=='insufficient'
                assert plan.get('explicit_speaker_prefilter')==VERSION
        assert candidate['stages']['final_audit']['pass'] is True
    selection=json.loads((root/'selected/selection.json').read_text())
    selected=json.loads((root/'selected/questions.json').read_text())
    selected_parquet=[q for domain in ['b2b','b2c'] for q in pq.read_table(root/'selected'/f'{domain}-test.parquet').to_pylist()]
    assert canonical(selected)==canonical(selected_parquet)
    expected={d['question_id'] for d in selection['decisions'] if d['accepted'] is True}
    assert {q['question_id'] for q in selected}==expected
    decisions={d['question_id']:d for d in selection['decisions']}
    for q in selected:
        if q['question_class']=='multi_call':
            review=decisions[q['question_id']]['multi_necessity']
            assert review['accepted'] is True and len(review['verdicts'])==2
            assert all(v['passed'] is True for v in review['verdicts'])
    assert len(selected)==selection['selected_questions']==progress['selected_questions']
    assert canonical(selected)==canonical([q for q in questions if q['question_id'] in expected])
    report={'verified':True,'scope':plan['scope'],'source_units':len(plan['units']),
            'raw_accepted_questions':len(questions),'accepted_questions':len(selected),'accepted_counts':dict(Counter(q['domain']+'/'+q['question_class'] for q in selected)),
            'excluded_groups':len(excluded),'checks':['source hashes','complete scope','group exclusions','no B2C multi-call',
            'JSON/Parquet parity','unique question IDs','exact evidence','accepted contract and consistency gates','locator checks','final coherence selection and Parquet parity','cross-model multi-call necessity'],
            'limitations':'Artifact integrity and recorded-gate verification, not an independent semantic quality estimate.'}
    write_json(Path('reports')/(root.name+'-verification.json'),report)
    print(json.dumps(report))


if __name__=='__main__':
    main()
