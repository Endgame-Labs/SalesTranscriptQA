import pytest

from salestranscriptqa.pilot import evidence_check
from salestranscriptqa.transport import retry_delay


def test_offsets_preserve_unicode_and_newlines():
    calls = [dict(call_id="c", dialogue="Zoë: café\nBuyer: €20.", metadata={})]
    q = dict(
        question="Price?",
        gold_answer="€20",
        evidence=[dict(call_id="c", answer_claim="price", kind="dialogue", quote="Buyer: €20.")],
    )
    item = evidence_check(q, calls)["evidence"][0]
    assert calls[0]["dialogue"][item["start"] : item["end"]] == "Buyer: €20."


def test_requires_dialogue_from_both_calls():
    calls = [dict(call_id=k, dialogue="Call " + k, metadata={}) for k in ("a", "b")]
    q = dict(
        question="Compare?",
        gold_answer="a and b",
        evidence=[dict(call_id="a", answer_claim="a", kind="dialogue", quote="Call a")],
    )
    with pytest.raises(ValueError, match="missing_dialogue"):
        evidence_check(q, calls)


def test_rejects_fabricated_quote_and_metadata():
    calls = [dict(call_id="c", dialogue="Actual", metadata={"name": "Sue"})]
    for e in [
        dict(kind="dialogue", quote="Fake"),
        dict(kind="metadata", pointer="/metadata/name", value="Bob"),
    ]:
        q = dict(
            question="Who?",
            gold_answer="Bob",
            evidence=[dict(call_id="c", answer_claim="identity", **e)],
        )
        with pytest.raises(ValueError):
            evidence_check(q, calls)


def test_retry_after_seconds_and_date():
    assert retry_delay(0, "120") >= 120
    assert retry_delay(0, "Thu, 01 Jan 1970 00:02:00 GMT", now=0) >= 120
    assert retry_delay(7) >= 30
