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


def test_schema_like_decision_fields_are_retried_and_preserved():
    class Transport:
        def __init__(self):self.stages=[]
        def request(self,model,prompt,stage,nonce):
            self.stages.append(stage)
            if stage=='final_multi_necessity':
                return {'type':'object','necessary':False,'exclusive_facts':[],
                        'reason':'Both calls are necessary.'}
            return {'necessary':True,'exclusive_facts':[
                {'call_id':i,'fact':'Distinct '+i,'why_other_call_cannot_supply_it':'Only in '+i}
                for i in ['a','b']], 'reason':'Each source supplies one requested fact'}
    t=Transport()
    r=assess({'question':'Terms in both calls?','gold_answer':'A and B'},
             [{'call_id':i,'metadata':{},'dialogue':i} for i in ['a','b']],t)
    assert r['accepted']
    assert t.stages.count('final_multi_necessity_schema_repair')==2
    assert all(v['schema_attempts'][0]['type']=='object' for v in r['verdicts'])


def test_exhausted_invalid_schema_cannot_pass_with_true_field():
    class Transport:
        def __init__(self):self.calls=0
        def request(self,*args,**kwargs):
            self.calls+=1
            return {'type':'object','necessary':True,'exclusive_facts':[
                {'call_id':i,'fact':'Distinct '+i,'why_other_call_cannot_supply_it':'Only in '+i}
                for i in ['a','b']], 'reason':'Both needed'}
    t=Transport()
    r=assess({'question':'Terms?','gold_answer':'A and B'},
             [{'call_id':i,'metadata':{},'dialogue':i} for i in ['a','b']],t)
    assert not r['accepted']
    assert t.calls==6
