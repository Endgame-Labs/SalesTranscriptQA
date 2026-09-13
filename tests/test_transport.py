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


def test_rate_limit_honors_retry_after_and_keeps_both_attempts(tmp_path, monkeypatch):
    from salestranscriptqa import transport

    monkeypatch.setenv("FIREWORKS_API_KEY", "test")
    clock = [1000.0]
    monkeypatch.setattr(transport.time, "time", lambda: clock[0])
    monkeypatch.setattr(
        transport.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds)
    )
    t = Transport(tmp_path)
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "5"}, json={"error": "limited"})
        return httpx.Response(
            200,
            json={
                "choices": [{"finish_reason": "stop", "message": {"content": '{"ok":true}'}}],
                "usage": {"prompt_tokens": 2, "completion_tokens": 3},
            },
        )

    t.client = httpx.Client(transport=httpx.MockTransport(handler))
    assert t.request(PRIMARY, "JSON", "rate-limit") == {"ok": True}
    assert clock[0] >= 1005
    with t.db() as db:
        assert [
            row["http_status"] for row in db.execute("select * from attempts order by started")
        ] == [429, 200]


def test_invalid_completions_are_distinct_from_unavailable_provider(tmp_path, monkeypatch):
    import pytest

    from salestranscriptqa import transport

    monkeypatch.setenv("FIREWORKS_API_KEY", "test")
    monkeypatch.setattr(transport, "retry_delay", lambda *args: 0)
    for status, error in [(200, transport.InvalidModelOutputError), (503, RuntimeError)]:
        t = Transport(tmp_path / str(status))
        t.client = httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    status,
                    json={
                        "choices": [
                            {"finish_reason": "length", "message": {"content": "unfinished"}}
                        ],
                        "usage": {"prompt_tokens": 2, "completion_tokens": 4096},
                    },
                )
            )
        )
        with pytest.raises(error) as caught:
            t.request(PRIMARY, "JSON", "audit")
        assert type(caught.value) is error
        with t.db() as db:
            assert db.execute("SELECT count(*) FROM attempts").fetchone()[0] == 8
