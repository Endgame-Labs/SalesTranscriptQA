from salestranscriptqa.question_style import locator_flags


def test_real_model_date_locator_failures():
    assert locator_flags("What did Olivia Grant say she was leaning towards during the April 10 call?")
    assert locator_flags("What pricing did Mei Lin quote during the December 29 call with Samuel Peterson?")
    assert locator_flags("In the call on July 11, what did Mark agree to?")
    assert locator_flags('What happened in the call titled Foobar?')
    assert locator_flags('What support was promised in the January call?')


def test_natural_customer_names_and_business_dates_are_preserved():
    for q in [
        "What is Elizabeth Choi's budget cap for PCBProto Wizard and VerifySim Elite?",
        "What did Mark Johnson find unclear about Executive Rides' offerings?",
        "What did Mason want clarified before his July 11 purchase deadline?",
        "When did Lila agree to follow up?",
        "What did Ravi commit to sending before the demo on July 11?",
    ]:
        assert locator_flags(q) == []
