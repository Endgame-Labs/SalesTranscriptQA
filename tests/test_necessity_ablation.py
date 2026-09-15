import json

import pytest

from salestranscriptqa.necessity_ablation import assess, valid_extraction


def test_extractors_are_isolated_from_other_source_and_reference():
    class Transport:
        def request(self, model, prompt, stage, nonce):
            payload = json.loads(prompt.split('\nINPUT JSON:\n')[1])
            if stage == 'necessity_ablation_extract':
                assert set(payload) == {'question', 'call'}
                call = payload['call']
                assert set(call) == {'call_id', 'metadata', 'dialogue'}
                return {'claims': [{'answer': call['dialogue'], 'quote': call['dialogue']}],
                        'missing': 'Other requirement'}
            return {'source_coverage': [{'call_id': c, 'complete': False, 'reason': 'Partial'}
                                        for c in ['a', 'b']], 'union_complete': True,
                    'coherent': True, 'reason': 'Distinct required commercial terms'}
    calls = [{'call_id': c, 'metadata': {}, 'dialogue': c} for c in ['a', 'b']]
    assert assess({'question': 'Terms?', 'gold_answer': 'SECRET_REFERENCE'}, calls,
                  Transport())['supports_necessity']


def test_fabricated_quote_blocks_judgment():
    class Transport:
        def request(self, model, prompt, stage, nonce):
            assert stage == 'necessity_ablation_extract'
            return {'claims': [{'answer': 'Invented', 'quote': 'Not in source'}], 'missing': ''}
    calls = [{'call_id': c, 'metadata': {}, 'dialogue': c} for c in ['a', 'b']]
    result = assess({'question': 'Terms?', 'gold_answer': 'a and b'}, calls, Transport())
    assert not result['valid'] and result['verdict'] is None
    assert not valid_extraction({'claims': [{'answer': 'x', 'quote': ''}], 'missing': ''}, 'x')


@pytest.mark.parametrize('duplicate', [False, True])
def test_complete_source_or_duplicate_coverage_cannot_establish_necessity(duplicate):
    class Transport:
        def request(self, model, prompt, stage, nonce):
            if stage == 'necessity_ablation_extract':
                return {'claims': [{'answer': 'Terms', 'quote': 'Terms'}], 'missing': ''}
            return {'source_coverage': [
                {'call_id': 'a', 'complete': not duplicate, 'reason': 'All terms'},
                {'call_id': 'a' if duplicate else 'b', 'complete': False, 'reason': 'Partial'}],
                'union_complete': True, 'coherent': True, 'reason': 'Assessment'}
    calls = [{'call_id': c, 'metadata': {}, 'dialogue': 'Terms'} for c in ['a', 'b']]
    result = assess({'question': 'Terms?', 'gold_answer': 'Terms'}, calls, Transport())
    assert not result['supports_necessity']
    assert result['valid'] is (not duplicate)
