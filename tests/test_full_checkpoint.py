import pytest
from salestranscriptqa.full_checkpoint import budget_envelope, reviewed_selection


def test_review_coverage_and_quarantine_survive_new_ids():
    questions = [{'question_id': 'new-id', 'question': "What is Sofia Kim’s package price?"},
                 {'question_id': 'keep', 'question': 'What discount did Liam offer?'}]
    exported = [dict(q, item=i) for i, q in enumerate(questions)]
    reviews = [{'item': i, 'passed': True, 'mechanical_locator_flags': []} for i in range(2)]
    final, rejected = reviewed_selection(questions, exported, reviews,
                                        [{'question_id': 'old-id', 'question': "what is Sofia Kim's package price"}])
    assert [q['question_id'] for q in final] == ['keep']
    assert rejected[0]['prior_quarantine']
    with pytest.raises(ValueError, match='coverage'):
        reviewed_selection(questions, exported, reviews[:1], [])
    with pytest.raises(ValueError, match='IDs'):
        reviewed_selection(questions, exported, [reviews[0], reviews[0]], [])


def test_campaign_ceiling_counts_inheritance_once_and_all_future_stages(tmp_path):
    full, review, rag = [tmp_path / p for p in ['full', 'review', 'rag']]
    report = {'ceiling_usd': 5000, 'conservative_fireworks_usd': 800,
              'generation_and_review': [{'run': str(full), 'incremental_recorded_usd': 190,
                                         'unknown_or_inflight_reservations_usd': 10},
                                        {'run': str(review), 'incremental_recorded_usd': 20,
                                         'unknown_or_inflight_reservations_usd': 0}],
              'rag': [{'run': str(rag), 'conservative_guard_usd': 30}]}
    limits = {'generation_usd': 4500, 'review_usd': 100, 'rag_usd': 200, 'reserve_usd': 100}
    # $550 outside full ledgers includes the inherited $500 checkpoint calls.
    result = budget_envelope(report, limits, 500, full, review, rag)
    assert result['campaign_envelope_usd'] == 4950
    assert result['current_full_ledgers_usd']['generation_usd'] == 700
    with pytest.raises(ValueError, match='shared ceiling'):
        budget_envelope(report, dict(limits, rag_usd=300), 500, full, review, rag)
    with pytest.raises(ValueError, match='already exceeded'):
        budget_envelope(report, dict(limits, generation_usd=650), 500, full, review, rag)
    with pytest.raises(ValueError, match='finite'):
        budget_envelope(report, dict(limits, generation_usd=float('nan')), 500, full, review, rag)
