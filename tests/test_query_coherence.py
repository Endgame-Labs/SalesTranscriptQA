import json
from salestranscriptqa.query_coherence import assess


def test_coherence_gate_is_question_only_and_fails_closed():
    class Transport:
        def request(self,model,prompt,stage,nonce):
            value=json.loads(prompt.split('INPUT JSON:\n',1)[1])
            assert set(value)=={'question','question_class'}
            return {'accept':True} # An unreasoned/malformed approval is insufficient.
    assert assess('What did Nina require?','single_call',Transport())['accepted'] is False
