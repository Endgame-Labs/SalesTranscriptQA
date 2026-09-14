from copy import deepcopy
import json
import pytest
from salestranscriptqa.citation_audit import assess
from salestranscriptqa.pilot import evidence_check


class Transport:
    def __init__(self, verdict):
        self.verdict = verdict
        self.payload = None

    def request(self, model, prompt, stage, nonce):
        self.payload = json.loads(prompt.split('\nINPUT JSON:\n')[1])
        return self.verdict


def fixture():
    calls = [{'call_id': 'a', 'metadata': {'account_name': 'Acme'},
              'dialogue': 'Buyer: We need support.\nRep: Our dedicated team will help.\nUNCITED SENTINEL'}]
    q = {'question': 'What support did the rep offer?', 'gold_answer': 'A dedicated team.',
         'evidence': [{'call_id': 'a', 'kind': 'dialogue', 'answer_claim': 'A dedicated team will help.',
                       'line_start': 0, 'line_end': 1}]}
    return evidence_check(q, calls), calls


def test_uncited_dialogue_cannot_rescue_bad_citation_and_input_is_immutable():
    q, calls = fixture()
    original = deepcopy(q)
    t = Transport({'evidence_support': [{'index': 0, 'supported': False}], 'answer_supported': False})
    assert not assess(q, calls, t)['passed']
    assert 'dedicated team will help' not in t.payload['cited_evidence'][0]['quote']
    assert 'UNCITED SENTINEL' not in json.dumps(t.payload)
    assert q == original


def test_missing_duplicate_or_nonboolean_verdicts_fail_closed():
    q, calls = fixture()
    for support in [[], [{'index': True, 'supported': True}], [{'index': 1, 'supported': True}],
                    [{'index': 0, 'supported': 'true'}], [{'index': 0, 'supported': True}] * 2]:
        assert not assess(q, calls, Transport({'evidence_support': support, 'answer_supported': True}))['passed']
    t = Transport({'evidence_support': [{'index': 0, 'supported': True}], 'answer_supported': True})
    assert assess(q, calls, t)['passed']
    q['evidence'][0]['quote'] = 'Wrong stored quote'
    with pytest.raises(ValueError, match='Stored citations'):
        assess(q, calls, t)
