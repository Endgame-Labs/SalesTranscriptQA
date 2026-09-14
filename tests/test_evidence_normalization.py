from salestranscriptqa.sales_questions import normalize_single_line_evidence
from salestranscriptqa.pilot import evidence_check
import pytest


def test_observed_equal_endpoints_copy_exact_source_line_without_mutating_raw():
    raw={'question':'What did Aiden say?','gold_answer':'Enticing upfront promotions.',
         'evidence':[{'call_id':'a','kind':'dialogue','answer_claim':'Promotions','line_start':1,'line_end':1}]}
    result=normalize_single_line_evidence(raw,[{'call_id':'a','numbered_lines':[(0,'Hello'),(1,'Enticing upfront promotions.')]}])
    checked=evidence_check(result,[{'call_id':'a','dialogue':'Hello\nEnticing upfront promotions.','metadata':{}}])
    assert checked['evidence'][0]['quote']=='Enticing upfront promotions.'
    assert raw['evidence'][0]['line_end']==1
    assert checked['evidence_index_repairs'][0]['normalized_end']==2


@pytest.mark.parametrize('start,end',[(2,2),(-1,-1),(True,True),(1,0),(0,3)])
def test_invalid_ranges_are_not_guessed(start,end):
    raw={'evidence':[{'call_id':'a','kind':'dialogue','line_start':start,'line_end':end}]}
    assert normalize_single_line_evidence(raw,[{'call_id':'a','numbered_lines':[(0,'hello'),(1,'bye')]}])==raw
