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
