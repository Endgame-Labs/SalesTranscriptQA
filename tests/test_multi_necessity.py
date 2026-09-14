from salestranscriptqa.multi_necessity import assess


def test_schema_reply_gets_bounded_format_repair_not_automatic_acceptance():
    class Transport:
        def __init__(self):self.stages=[]
        def request(self,model,prompt,stage,nonce):
            self.stages.append(stage)
            if stage=='final_multi_necessity':return {'type':'object','properties':{}}
            return {'necessary':True,'exclusive_facts':[
                {'call_id':'a','fact':'Requirement','why_other_call_cannot_supply_it':'Only initial call'},
                {'call_id':'b','fact':'Resolution','why_other_call_cannot_supply_it':'Only final call'}], 'reason':'Distinct requested facts'}
    t=Transport()
    r=assess({'question':'Concern and resolution?','gold_answer':'A and B'},
             [{'call_id':i,'metadata':{},'dialogue':i} for i in ['a','b']],t)
    assert r['accepted']
    assert t.stages.count('final_multi_necessity_schema_repair')==2


def test_valid_negative_is_not_retried_into_positive():
    class Transport:
        def request(self,model,prompt,stage,nonce):
            assert stage=='final_multi_necessity'
            return {'necessary':False,'exclusive_facts':[],'reason':'Repeated fact'}
    r=assess({'question':'What did each say?','gold_answer':'Same delay'},
             [{'call_id':i,'metadata':{},'dialogue':i} for i in ['a','b']],Transport())
    assert r['accepted'] is False
