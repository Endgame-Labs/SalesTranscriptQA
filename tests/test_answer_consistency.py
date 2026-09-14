import json
from salestranscriptqa.answer_consistency import check_group, aggregate


def test_reference_blind_extraction_and_evidence_aware_adjudication():
    class Transport:
        def request(self,model,prompt,stage,nonce):
            value=json.loads(prompt.split('INPUT JSON:\n',1)[1])
            if stage=='group_blind_extraction':
                assert 'reference_answer' not in value
                return {'answerable':True,'answer':'Friday','evidence':[{'call_id':'a','line_start':0,'line_end':1}]}
            assert value['reference_answer']=='Saturday'
            assert value['extracted']['evidence'][0]['quote']=='Friday'
            return {'classification':'conflicting','reason':'Different appointment days'}
    result=check_group('When is the demo?','Saturday',[{'call_id':'a','metadata':{},'dialogue':'Friday'}],Transport())
    assert result['classification']=='conflicting'


def test_duplicate_answers_are_not_conflicts_and_unknown_fails_closed():
    groups=[{'classification':'equivalent'},{'classification':'equivalent'},{'classification':'insufficient'}]
    assert aggregate(groups)=='consistent_in_pool'
    assert aggregate(groups+[{'classification':'conflicting'}])=='ambiguous'
    assert aggregate(groups+[{'classification':'uncertain'}])=='inconclusive'
    assert aggregate([])=='inconclusive'


def test_wrong_entity_stops_before_reference_comparison():
    from salestranscriptqa.answer_consistency import check_group_v2
    stages=[]
    class Transport:
        def request(self,model,prompt,stage,nonce):
            stages.append(stage)
            value=json.loads(prompt.split('INPUT JSON:\n',1)[1])
            assert 'reference_answer' not in value and 'answer_b' not in value
            if stage=='group_blind_extraction':
                return {'answerable':False,'answer':'No Elena','evidence':[]}
            assert stage=='group_blind_verification_v2'
            return {'complete':False,'answer':'No Elena','evidence':[],'reason':'Wrong salesperson'}
    result=check_group_v2('What did Elena promise?','A quote tomorrow',
        [{'call_id':'a','metadata':{},'dialogue':'Tariq: I will send a demo.'}],Transport())
    assert result['classification']=='insufficient'
    assert stages==['group_blind_extraction','group_blind_verification_v2']
