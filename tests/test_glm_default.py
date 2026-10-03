import json

import httpx
import pytest

from salestranscriptqa import transport
from salestranscriptqa.sales_questions import SalesQuestions
from salestranscriptqa.transport import (
    DEEPSEEK_V4_FLASH_0731,
    GLM_5P3_FLASH,
    PRIMARY,
    RATES,
    SECONDARY,
    InvalidModelOutputError,
    Transport,
    output_tokens,
)


def ok(content='{"ok":true}', **usage):
    return {
        "choices": [{"finish_reason": "stop", "message": {"content": content}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, **usage},
    }


def test_defaults_are_glm_with_low_reasoning(tmp_path, monkeypatch):
    monkeypatch.setenv("FIREWORKS_API_KEY", "test")
    assert PRIMARY == SECONDARY == GLM_5P3_FLASH
    # The retired model keeps its rate so recorded attempts can still be priced.
    assert RATES[DEEPSEEK_V4_FLASH_0731] == (0.22, 0.007, 0.66)
    assert RATES[GLM_5P3_FLASH] == (0.15, 0.03, 0.50)
    sent = []
    t = Transport(tmp_path)
    t.client = httpx.Client(
        transport=httpx.MockTransport(
            lambda r: sent.append(json.loads(r.content)) or httpx.Response(200, json=ok())
        )
    )
    t.request(PRIMARY, "JSON", "glm")
    t.request(DEEPSEEK_V4_FLASH_0731, "JSON", "historical")
    assert sent[0]["reasoning_effort"] == "low" and sent[0]["max_tokens"] == 4096
    assert sent[1]["reasoning_effort"] == "none"


def test_historical_deepseek_arm_is_not_relabelled():
    assert SalesQuestions.generator == DEEPSEEK_V4_FLASH_0731


@pytest.mark.parametrize(
    "choice",
    [
        # Thinking spent the whole budget: empty answer, reasoning only.
        {"finish_reason": "length", "message": {"content": "", "reasoning_content": '{"ok":1}'}},
        # Stop with blank content must not be read from reasoning either.
        {"finish_reason": "stop", "message": {"content": "  ", "reasoning_content": '{"ok":1}'}},
        {"finish_reason": "stop", "message": {"content": None, "reasoning_content": '{"ok":1}'}},
    ],
)
def test_empty_or_truncated_content_is_retried_then_visible(tmp_path, monkeypatch, choice):
    monkeypatch.setenv("FIREWORKS_API_KEY", "test")
    monkeypatch.setattr(transport, "retry_delay", lambda *args: 0)
    t = Transport(tmp_path)
    body = {"choices": [choice], "usage": {"prompt_tokens": 2, "completion_tokens": 20,
            "completion_tokens_details": {"reasoning_tokens": 20}}}
    t.client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body)))
    with pytest.raises(InvalidModelOutputError):
        t.request(PRIMARY, "JSON", "empty")
    with t.db() as db:
        rows = db.execute("SELECT status,error,output_tokens FROM attempts").fetchall()
    assert len(rows) == 8
    assert all(r["status"] == "error" and r["error"] == "ValueError" for r in rows)
    assert all(r["output_tokens"] == 20 for r in rows)


def test_empty_then_answer_recovers(tmp_path, monkeypatch):
    monkeypatch.setenv("FIREWORKS_API_KEY", "test")
    monkeypatch.setattr(transport, "retry_delay", lambda *args: 0)
    replies = iter([ok(""), ok('{"answer":"OK"}')])
    t = Transport(tmp_path)
    t.client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=next(replies))))
    assert t.request(PRIMARY, "JSON", "recover") == {"answer": "OK"}


def test_reasoning_tokens_are_billed_as_output(tmp_path, monkeypatch):
    # Fireworks reports reasoning inside completion_tokens.
    assert output_tokens({"completion_tokens": 20, "completion_tokens_details": {"reasoning_tokens": 20}}) == 20
    # Never bill fewer output tokens than the reported reasoning.
    assert output_tokens({"completion_tokens": 3, "completion_tokens_details": {"reasoning_tokens": 40}}) == 40
    assert output_tokens({}) is None
    monkeypatch.setenv("FIREWORKS_API_KEY", "test")
    t = Transport(tmp_path)
    body = ok(completion_tokens=120, completion_tokens_details={"reasoning_tokens": 100})
    t.client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body)))
    t.request(PRIMARY, "JSON", "cost")
    with t.db() as db:
        row = db.execute("SELECT output_tokens,estimated_usd FROM attempts").fetchone()
    assert row["output_tokens"] == 120
    assert row["estimated_usd"] == pytest.approx((10 * 0.15 + 120 * 0.50) / 1e6)
