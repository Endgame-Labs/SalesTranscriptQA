from salestranscriptqa.blind_ambiguity import extraction_payload, aggregate


def test_extraction_input_has_no_reference():
    p=extraction_payload('When is the demo?',{'call_id':'a','metadata':{},'dialogue':'Friday.'})
    assert set(p)=={'question','call'}
    assert p['call']['numbered_lines']==[(0,'Friday.')]


def test_any_verified_conflict_survives_distractors():
    rows=[{'call_id':str(i),'decision':'insufficient'} for i in range(30)]
    rows[3]['decision']='equivalent'
    rows[27]['decision']='conflicting'
    assert aggregate(rows,[str(i) for i in range(30)])=='ambiguous'
    rows[27]['decision']='equivalent'
    assert aggregate(rows,[str(i) for i in range(30)])=='consistent_in_pool'
    rows[27]['decision']='verification_failed'
    assert aggregate(rows,[str(i) for i in range(30)])=='inconclusive'
    assert aggregate(rows[:-1],[str(i) for i in range(30)])=='incomplete_pool'


def test_reference_is_withheld_until_answer_comparison():
    import json
    from salestranscriptqa.blind_ambiguity import classify

    class RecordedTransport:
        def request(self, model, instruction, stage, nonce):
            data = json.loads(instruction.split('INPUT JSON:\n', 1)[1])
            if stage == 'blind_extraction':
                assert 'reference_answer' not in data
                return {'answerable':True,'answer':'Friday.',
                        'evidence':[{'call_id':'a','line_start':0,'line_end':1}]}
            if stage == 'blind_support_verification_v2':
                assert 'reference_answer' not in data
                assert data['extracted']['evidence'][0]['quote']=='Friday.'
                return {'valid':True}
            assert stage=='blind_answer_comparison_v2'
            assert data['reference_answer']=='Saturday.'
            return {'relation':'conflicting'}

    result=classify('When is the demo?','Saturday.',
                    {'call_id':'a','metadata':{},'dialogue':'Friday.'},RecordedTransport())
    assert result['decision']=='conflicting'
