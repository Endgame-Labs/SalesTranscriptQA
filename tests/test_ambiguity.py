from copy import deepcopy
from salestranscriptqa.ambiguity import decision, validate_evidence

CALLS = [dict(call_id='a', dialogue='The warranty costs $1299.', group_id='x'),
         dict(call_id='b', dialogue='The warranty costs $1299.', group_id='y')]
CHECKS = dict.fromkeys(['quotes_support_complete_answers','relations_correct',
                       'scope_assessment_correct','no_plausible_conflicts_omitted'], True)


def verdict():
    return {'scope_sufficient':True, 'reason':'Same answer, different sources.',
            'answers':[{'call_ids':[i], 'answer':'$1299', 'relation':'equivalent',
                        'evidence':[{'call_id':i,'quote':'The warranty costs $1299.'}]} for i in ['a','b']]}


def test_equivalent_alternative_source_is_not_ambiguity():
    assert decision(verdict(), CHECKS, CALLS) == 'consistent_in_pool'


def test_conflict_and_underspecified_scope_fail():
    v = verdict()
    v['answers'][1]['relation'] = 'conflicting'
    assert decision(v, CHECKS, CALLS) == 'ambiguous'
    v = verdict()
    v['scope_sufficient'] = False
    assert decision(v, CHECKS, CALLS) == 'ambiguous'


def test_fabricated_quotes_and_unrelated_source_combinations_fail():
    v = verdict()
    v['answers'][0]['evidence'][0]['quote'] = 'A fabricated price.'
    assert not validate_evidence(v, CALLS)
    v = verdict()
    v['answers'][0]['call_ids'] = ['a','b']
    v['answers'][0]['evidence'] += v['answers'][1]['evidence']
    assert not validate_evidence(v, CALLS)


def test_independent_verification_must_pass():
    checks = deepcopy(CHECKS)
    checks['no_plausible_conflicts_omitted'] = False
    assert decision(verdict(), checks, CALLS) == 'verification_failed'


def test_line_evidence_preserves_verbatim_and_rejects_bad_indices():
    from salestranscriptqa.ambiguity import materialize_evidence
    calls = [dict(call_id='a', dialogue='A: It’s $1299.\nB: Thanks.', group_id='x')]
    v = {'answers':[{'evidence':[{'call_id':'a','line_start':0,'line_end':1}]}]}
    assert materialize_evidence(v,calls)['answers'][0]['evidence'][0]['quote'] == 'A: It’s $1299.'
    v['answers'][0]['evidence'][0]['line_end'] = 3
    assert materialize_evidence(v,calls) is None
