from salestranscriptqa.speaker_scope import absent_speakers,required_speakers,speaker_catalog
NAMES=frozenset({('andres','perez'),('mei','chen'),('robert','smith')})

def test_absent_required_name_is_negative_but_partial_names_and_metadata_are_kept():
    q='What did Mei Chen promise?'
    assert absent_speakers(q,[{'dialogue':'Alex: I will send the quote.'}],NAMES)==['mei chen']
    assert not absent_speakers(q,[{'dialogue':'Mei: I will send the quote.'}],NAMES)
    assert not absent_speakers(q,[{'dialogue':'I will send the quote.','metadata':{'rep':'Mei Chen'}}],NAMES)

def test_unicode_accents_and_initial_aliases_are_preserved():
    assert not absent_speakers('What did Andrés Pérez request?',[{'dialogue':'Andrés Pérez: A demo.'}],NAMES)
    assert not absent_speakers('What did Robert Smith request?',[{'dialogue':'R. Smith: A demo.'}],NAMES)
    assert not absent_speakers('What did Robert Smith request?',[{'dialogue':'Bob (Robert): A demo.'}],NAMES)

def test_negations_alternatives_hypotheticals_and_incidental_mentions_fall_back():
    for q in ['What did anyone except Mei Chen offer?','What did Mei Chen or Robert Smith request?',
              'What would Mei Chen recommend?','Was Mei Chen on the call?',
              'How many times did Mei Chen speak?','Which calls did Mei Chen attend?','What was discussed in a book titled Mei Chen?']:
        assert not required_speakers(q,NAMES)

def test_catalog_excludes_generic_roles_and_single_names():
    names=speaker_catalog([{'dialogue':'[2020] Sales Agent: Hi\n[2020] Mei Chen: Hello\n[2020] Mei: Yes'}])
    assert names=={('mei','chen')}

def test_precheck_records_recomputable_insufficient_group_only():
    from salestranscriptqa.speaker_scope import precheck_group
    calls=[{'call_id':'x','dialogue':'[2020] Alex Jones: I will send it.'}]
    r=precheck_group('What did Mei Chen promise?',calls,NAMES)
    assert r['classification']=='insufficient' and r['absent_required_speakers']==['mei chen'] and r['call_ids']==['x']
    assert precheck_group('What did Mei promise?',calls,NAMES) is None
