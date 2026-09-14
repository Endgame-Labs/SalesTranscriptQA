import json
from salestranscriptqa.event_scope import customer_history, assess

def test_history_includes_all_opportunities_for_account_without_name_join():
    def call(cid,account,group,domain='b2b'):
        return dict(call_id=cid,domain=domain,group_id=group,metadata={'account_id':account},dialogue='x')
    cs={c['call_id']:c for c in [call('a','A','g1'),call('b','A','g2'),call('c','B','g3'),call('d','A','g1','b2c')]}
    q={'supporting_call_ids':['a'],'domain':'b2b'}
    assert [c['call_id'] for c in customer_history(q,cs)]==['a','b']

def test_reference_blind_extraction_and_multiple_answers_fail_closed():
    q={'question':'What price?','gold_answer':'secret reference'}
    calls=[{'call_id':'a','metadata':{},'dialogue':'Price 1\nPrice 2'}]
    class T:
        def __init__(self):self.n=0
        def request(self,model,prompt,stage,nonce):
            self.n+=1
            if self.n==1:
                assert 'secret reference' not in prompt
                return {'scope':'multiple','answers':[{'answer':str(i),'evidence':[{'call_id':'a','line_start':i,'line_end':i+1}]} for i in range(2)]}
            return dict(scope_determinate=True,reference_complete_and_supported=True,alternatives_checked=True)
    result=assess(q,calls,T())
    assert result['schema_valid'] and not result['passed']
    assert result['extraction']['answers'][0]['evidence'][0]['quote']=='Price 1'

def test_equal_endpoint_normalization_preserves_raw_receipt():
    raw={'scope':'determinate','answers':[{'answer':'one','evidence':[{'call_id':'a','line_start':0,'line_end':0}]}]}
    class T:
        def request(self,model,prompt,stage,nonce):
            if stage.endswith('-extract'):return raw
            return dict(scope_determinate=True,reference_complete_and_supported=True,alternatives_checked=True)
    r=assess({'question':'Price?','gold_answer':'one'},[{'call_id':'a','metadata':{},'dialogue':'one'}],T())
    assert r['passed'] and r['evidence_index_repairs']
    assert raw['answers'][0]['evidence'][0]['line_end']==0
    assert r['extraction']['answers'][0]['evidence'][0]['quote']=='one'

def test_selection_requires_full_coverage_and_both_verdicts():
    import pytest
    from salestranscriptqa.event_scope import select_reviewed,VERSION
    q={'question_id':'q','question':'What?','gold_answer':'one'}
    row=dict(q,passed=True,schema_valid=True,extraction={'scope':'multiple'},verdict=dict(scope_determinate=True,reference_complete_and_supported=True,alternatives_checked=True))
    # A stale or inconsistent passed flag cannot bypass the underlying scope decision.
    assert select_reviewed([q],{'protocol':VERSION,'results':[row]})[0]==[]
    with pytest.raises(ValueError):select_reviewed([q],{'protocol':VERSION,'results':[]})
    row['extraction']['scope']='determinate'
    assert select_reviewed([q],{'protocol':VERSION,'results':[row]})[0]==[q]
