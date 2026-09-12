import httpx

from salestranscriptqa.transport import PRIMARY, Transport


def test_cache_and_usage_are_recorded(tmp_path, monkeypatch):
    monkeypatch.setenv("FIREWORKS_API_KEY", "test-secret-never-log")
    t = Transport(tmp_path)
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "id": "response-id",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": '{"ok":true}',
                            "reasoning_content": "private reasoning",
                        },
                    }
                ],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 20,
                    "prompt_tokens_details": {"cached_tokens": 50},
                },
            },
        )

    t.client = httpx.Client(transport=httpx.MockTransport(handler))
    assert t.request(PRIMARY, "JSON please", "test") == {"ok": True}
    assert t.request(PRIMARY, "JSON please", "test") == {"ok": True}
    assert len(calls) == 1
    with t.db() as db:
        row = db.execute("select * from attempts").fetchone()
        assert row["input_tokens"] == 100
        assert row["estimated_usd"] > 0
    artifact = next((tmp_path / "requests").glob("*.json")).read_text()
    assert "test-secret-never-log" not in artifact
    assert "private reasoning" not in artifact


def test_auth_failure_is_not_retried(tmp_path, monkeypatch):
    import pytest

    monkeypatch.setenv("FIREWORKS_API_KEY", "test")
    t = Transport(tmp_path)
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(401, json={"error": "no"})

    t.client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(RuntimeError, match="Nonretryable"):
        t.request(PRIMARY, "x", "test")
    assert len(calls) == 1
    with t.db() as db:
        assert db.execute("select estimated_usd from attempts").fetchone()[0] is None
