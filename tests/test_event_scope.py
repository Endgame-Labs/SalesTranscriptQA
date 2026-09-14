from copy import deepcopy
import pytest
from salestranscriptqa.event_scope import customer_history,assess,normalize_extraction,select_reviewed,VERSION

def test_history_includes_all_opportunities_for_account_without_name_join():
    def call(cid,account,group,domain='b2b'):
        return dict(call_id=cid,domain=domain,group_id=group,metadata={'account_id':account},dialogue='x')
    cs={c['call_id']:c for c in [call('a','A','g1'),call('b','A','g2'),call('c','B','g3'),call('d','A','g1','b2c')]}
    assert [c['call_id'] for c in customer_history({'supporting_call_ids':['a'],'domain':'b2b'},cs)]==['a','b']

def test_both_scope_models_are_reference_blind_and_independent():
    q={'question':'What price?','gold_answer':'secret reference'}
    calls=[{'call_id':'a','metadata':{},'dialogue':'Price 1\nPrice 2'}]
    class T:
        def __init__(self):self.n=0
        def request(self,model,prompt,stage,nonce):
            self.n+=1
            assert 'secret reference' not in prompt and 'draft_extraction' not in prompt
            return {'scope':'multiple' if self.n==2 else 'determinate','answers':[{'answer':'private draft '+str(i),'evidence':[{'call_id':'a','line_start':i,'line_end':i+1}]} for i in range(self.n)]}
    t=T();r=assess(q,calls,t)
    assert r['schema_valid'] and not r['passed'] and t.n==2 and r['comparison'] is None

def test_equal_endpoint_normalization_preserves_raw_receipt():
    raw={'scope':'determinate','answers':[{'answer':'one','evidence':[{'call_id':'a','line_start':0,'line_end':0}]}]}
    r,valid,repairs=normalize_extraction(raw,[{'call_id':'a','dialogue':'one'}])
    assert valid and repairs and raw['answers'][0]['evidence'][0]['line_end']==0
    assert r['answers'][0]['evidence'][0]['quote']=='one'

def test_selection_requires_full_coverage_and_both_verdicts():
    q={'question_id':'q','question':'What?','gold_answer':'one'}
    row=dict(q,passed=True,schema_valid=True,extraction={'scope':'determinate'},verdict={'scope':'multiple'},comparison=dict(answers_agree=True,reference_covers_requested_facts=True))
    assert select_reviewed([q],{'protocol':VERSION,'results':[row]})[0]==[]
    with pytest.raises(ValueError):select_reviewed([q],{'protocol':VERSION,'results':[]})
    row['verdict']['scope']='determinate'
    assert select_reviewed([q],{'protocol':VERSION,'results':[row]})[0]==[q]
