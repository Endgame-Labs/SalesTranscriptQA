import json

import httpx

from salestranscriptqa.costs import breakdown
from salestranscriptqa.transport import PRIMARY, Transport, digest


def test_candidate_cost_attribution_matches_request_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("FIREWORKS_API_KEY", "test")
    config = {"version": "fixture-v1"}
    (tmp_path / "config.json").write_text(json.dumps(config))
    job = digest(dict(config=digest(config), domain="b2b", kind="single_call", calls=["b2b:call"]))
    t = Transport(tmp_path)

    def handler(request):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": '{"question":"What was the budget?"}'},
                    }
                ],
                "usage": {"prompt_tokens": 100, "completion_tokens": 20},
            },
        )

    t.client = httpx.Client(transport=httpx.MockTransport(handler))
    for stage, value in [
        ("generate", {"calls": [{"call_id": "b2b:call"}], "question_class": "single_call"}),
        ("no_context", {"question": "What was the budget?"}),
    ]:
        t.request(
            PRIMARY,
            "instruction\nINPUT JSON:\n" + json.dumps(value),
            stage,
            nonce="fixture-v1" + job,
        )
    result = breakdown(tmp_path, {job}, tmp_path / "costs.csv")
    assert {r["outcome"] for r in result["rows"]} == {"accepted"}
    assert sum(r["attempts"] for r in result["rows"]) == 2
    with t.db() as db:
        total = db.execute("select sum(estimated_usd) from attempts").fetchone()[0]
    assert abs(result["cost_by_candidate_outcome"]["accepted"] - total) < 1e-12
