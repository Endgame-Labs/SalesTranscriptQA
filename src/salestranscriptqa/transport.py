"""Resumable JSON requests and per-attempt billing, with shared rate-limit cooldown."""

import email.utils
import hashlib
import json
import os
import random
import sqlite3
import threading
import time
import uuid
from pathlib import Path

import httpx

PRIMARY = "accounts/fireworks/models/deepseek-v4-flash-0731"
SECONDARY = "accounts/fireworks/models/glm-5p3-flash"
RATES = {PRIMARY: (0.22, 0.007, 0.66), SECONDARY: (0.15, 0.03, 0.50)}


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def credentials():
    if not os.environ.get("FIREWORKS_API_KEY"):
        # Load only this key. Never execute the secrets file as shell code.
        import shlex

        for line in (Path.home() / ".secrets/keys.env").read_text().splitlines():
            key, sep, value = line.removeprefix("export ").partition("=")
            if sep and key.strip() == "FIREWORKS_API_KEY":
                os.environ[key.strip()] = shlex.split(value)[0]
                break
    if not os.environ.get("FIREWORKS_API_KEY"):
        raise RuntimeError("FIREWORKS_API_KEY is unavailable")


def retry_delay(attempt, header=None, now=None):
    delay = random.uniform(0.5, 1.5) * min(60, 2 ** (attempt + 1))
    if header:
        try:
            value = float(header)
        except ValueError:
            try:
                value = email.utils.parsedate_to_datetime(header).timestamp() - (
                    time.time() if now is None else now
                )
            except (ValueError, TypeError, OverflowError):
                value = 0
        delay = max(delay, value)
    return max(0, delay)


class Transport:
    def __init__(self, root):
        self.root = Path(root)
        (self.root / "requests").mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.cooldown = 0
        self.client = httpx.Client(timeout=180, limits=httpx.Limits(max_connections=12))
        with self.db() as db:
            db.execute("pragma journal_mode=WAL")
            db.executescript("""CREATE TABLE IF NOT EXISTS attempts(
                id TEXT PRIMARY KEY, request_key TEXT, stage TEXT, model TEXT,
                started REAL, elapsed REAL, status TEXT, http_status INTEGER,
                input_tokens INTEGER, cached_tokens INTEGER, output_tokens INTEGER,
                estimated_usd REAL, artifact TEXT, error TEXT);
                CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, status TEXT, artifact TEXT, lease_until REAL);
                CREATE INDEX IF NOT EXISTS attempts_cache ON attempts(request_key,status,started);
            """)

    def db(self):
        db = sqlite3.connect(self.root / "progress.sqlite", timeout=60)
        db.row_factory = sqlite3.Row
        return db

    def request(self, model, prompt, stage, nonce=""):
        if model not in RATES:
            raise ValueError("Model pricing must be configured")
        payload = dict(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=4096,
            reasoning_effort="low" if model == SECONDARY else "none",
            response_format={"type": "json_object"},
        )
        key = digest(dict(payload=payload, stage=stage, nonce=nonce))
        with self.db() as db:
            row = db.execute(
                "SELECT artifact FROM attempts WHERE request_key=? AND status='ok' ORDER BY started LIMIT 1",
                (key,),
            ).fetchone()
        if row:
            return json.loads((self.root / row["artifact"]).read_text())["parsed"]
        credentials()
        for attempt in range(8):
            while True:
                with self.lock:
                    delay = self.cooldown - time.time()
                if delay <= 0:
                    break
                time.sleep(min(delay, 30))
            aid = uuid.uuid4().hex
            started = time.time()
            with self.db() as db:
                db.execute(
                    "INSERT INTO attempts(id,request_key,stage,model,started,status) VALUES(?,?,?,?,?,?)",
                    (aid, key, stage, model, started, "running"),
                )
            data, response, parsed, error = None, None, None, None
            try:
                response = self.client.post(
                    "https://api.fireworks.ai/inference/v1/chat/completions",
                    headers={"Authorization": "Bearer " + os.environ["FIREWORKS_API_KEY"]},
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                if data["choices"][0]["finish_reason"] != "stop":
                    raise ValueError("Incomplete completion")
                parsed = json.loads(data["choices"][0]["message"]["content"])
                if not isinstance(parsed, dict):
                    raise ValueError("Expected JSON object")
            except Exception as exc:
                error = type(exc).__name__  # no server bodies, headers or credentials in errors
            usage = (data or {}).get("usage") or {}
            inp, out = usage.get("prompt_tokens"), usage.get("completion_tokens")
            cached = (
                (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
                if usage
                else None
            )
            a, b, c = RATES[model]
            cost = (
                ((inp - cached) * a + cached * b + out * c) / 1e6
                if inp is not None and out is not None
                else None
            )
            artifact = f"requests/{aid}.json"
            # Persist visible output/usage only, never hidden reasoning or headers.
            value = dict(
                request=payload,
                parsed=parsed,
                usage=usage,
                error=error,
                provider_id=(data or {}).get("id"),
                attempt=attempt,
            )
            temp = (self.root / artifact).with_suffix(".tmp")
            temp.write_text(json.dumps(value, ensure_ascii=False))
            temp.replace(self.root / artifact)
            with self.db() as db:
                db.execute(
                    "UPDATE attempts SET elapsed=?,status=?,http_status=?,input_tokens=?,cached_tokens=?,output_tokens=?,estimated_usd=?,artifact=?,error=? WHERE id=?",
                    (
                        time.time() - started,
                        "ok" if error is None else "error",
                        response.status_code if response is not None else None,
                        inp,
                        cached,
                        out,
                        cost,
                        artifact,
                        error,
                        aid,
                    ),
                )
            if error is None:
                return parsed
            if response is not None and response.status_code in (400, 401, 403, 404, 422):
                raise RuntimeError(f"Nonretryable provider failure: HTTP {response.status_code}")
            if attempt < 7:
                delay = retry_delay(
                    attempt, response.headers.get("Retry-After") if response is not None else None
                )
                with self.lock:
                    self.cooldown = max(self.cooldown, time.time() + delay)
        raise RuntimeError("Provider retries exhausted")
