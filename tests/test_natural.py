from salestranscriptqa.natural import Natural, NaturalNext


def test_single_call_does_not_fail_on_inapplicable_two_call_flags():
    # Actual v2 failure: correct single-call answer rejected because the model
    # set both two-call-only flags false despite instructions to set them true.
    v2 = object.__new__(Natural)
    v3 = object.__new__(NaturalNext)
    verdict = dict.fromkeys(v2.quality_required('single_call'), True)
    verdict.update(both_calls_necessary=False, single_call_answers_fail=False)
    assert not all(verdict[k] for k in v2.quality_required('single_call'))
    assert all(verdict[k] for k in v3.quality_required('single_call'))
    assert not all(verdict[k] for k in v3.quality_required('multi_call'))
    verdict['factual'] = False
    assert not all(verdict[k] for k in v3.quality_required('single_call'))
