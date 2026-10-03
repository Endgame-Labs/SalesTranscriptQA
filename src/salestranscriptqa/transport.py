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

from .artifacts import read_json_artifact
from .budget_ledger import install as install_budget_ledger

# DeepSeek V4 Flash 0731 generated the published cohorts but Fireworks retired
# it on 2026-10-02 (404 "not deployed"). It stays here only so recorded
# attempts from those runs can still be priced.
DEEPSEEK_V4_FLASH_0731 = "accounts/fireworks/models/deepseek-v4-flash-0731"
GLM_5P3_FLASH = "accounts/fireworks/models/glm-5p3-flash"
DEEPSEEK_V4P1_FLASH = "accounts/fireworks/models/deepseek-v4p1-flash"
# Since 2026-10-03 DeepSeek V4.1 Flash takes the retired 0731's slot, keeping two
# model families. The constant names are historical, not role names: the
# current pipeline (v8/v9 sales arms, natural v5) generates questions with
# SECONDARY (GLM 5.3 Flash) and independently answers/cross-checks with PRIMARY
# (DeepSeek V4.1 Flash). See docs/IMPLEMENTATION.md.
PRIMARY = DEEPSEEK_V4P1_FLASH
SECONDARY = GLM_5P3_FLASH
# USD per 1M input / cached-input / output tokens, Fireworks serverless Standard.
# GLM and DeepSeek V4.1 Flash: https://docs.fireworks.ai/serverless/pricing, read 2026-10-03.
# DeepSeek 0731 (historical): https://fireworks.ai/models/deepseek-ai/deepseek-v4-flash-0731, read 2026-09-12.
RATES = {
    DEEPSEEK_V4_FLASH_0731: (0.22, 0.007, 0.66),
    GLM_5P3_FLASH: (0.15, 0.03, 0.50),
    DEEPSEEK_V4P1_FLASH: (0.30, 0.006, 1.20),
}
# GLM 5.3 Flash is thinking-only: "none" or disabled thinking is a 400. "low"
# keeps reasoning small; max_tokens below leaves room for it. DeepSeek V4.1
# Flash accepts "none" (verified 2026-10-03).
REASONING_EFFORT = {GLM_5P3_FLASH: "low", DEEPSEEK_V4P1_FLASH: "none"}


def reasoning_effort(model):
    return REASONING_EFFORT.get(model, "none")


def output_tokens(usage):
    """Billed output tokens. Fireworks completion_tokens already include
    completion_tokens_details.reasoning_tokens; never bill fewer than those."""
    out = usage.get("completion_tokens")
    reasoning = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
    return None if out is None else max(out, reasoning)


class BudgetExceededError(RuntimeError):
    """Configured conservative per-run API allowance has been exhausted."""


class InvalidModelOutputError(ValueError):
    """All bounded attempts returned successful HTTP responses with unusable model output."""


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
    def __init__(self, root, budget_usd=None):
        self.budget_usd = budget_usd
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
                CREATE TABLE IF NOT EXISTS budget_reservations(id TEXT PRIMARY KEY, worst_usd REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS attempts_cache ON attempts(request_key,status,started);
            """)

        with self.db() as db:
            install_budget_ledger(db)

    def db(self):
        db = sqlite3.connect(self.root / "progress.sqlite", timeout=60)
        db.row_factory = sqlite3.Row
        return db

    def start_attempt(self, aid, key, stage, model, started, payload):
        # Reserve one conservative attempt allowance atomically across workers.
        # One UTF-8 byte per input token plus framing allowance deliberately overestimates.
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            if self.budget_usd is not None:
                a, _, c = RATES[model]
                worst = ((len(json.dumps(payload,ensure_ascii=False).encode()) + 1024) * a
                         + payload['max_tokens'] * c) / 1e6
                used = db.execute("SELECT usd FROM budget_total WHERE id=1").fetchone()[0]
                if used + worst > self.budget_usd:
                    raise BudgetExceededError('Run API allowance exhausted; raise the explicit budget to resume')
                db.execute('INSERT INTO budget_reservations VALUES(?,?)',(aid,worst))
            db.execute("INSERT INTO attempts(id,request_key,stage,model,started,status) VALUES(?,?,?,?,?,?)",
                       (aid,key,stage,model,started,'running'))

    def request(self, model, prompt, stage, nonce=""):
        if model not in RATES:
            raise ValueError("Model pricing must be configured")
        payload = dict(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=4096,
            reasoning_effort=reasoning_effort(model),
            response_format={"type": "json_object"},
        )
        key = digest(dict(payload=payload, stage=stage, nonce=nonce))
        with self.db() as db:
            row = db.execute(
                "SELECT artifact FROM attempts WHERE request_key=? AND status='ok' ORDER BY started LIMIT 1",
                (key,),
            ).fetchone()
        if row:
            return read_json_artifact(self.root / row["artifact"])["parsed"]
        credentials()
        invalid_outputs = 0
        for attempt in range(8):
            while True:
                with self.lock:
                    delay = self.cooldown - time.time()
                if delay <= 0:
                    break
                time.sleep(min(delay, 30))
            aid = uuid.uuid4().hex
            started = time.time()
            self.start_attempt(aid, key, stage, model, started, payload)
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
                    # Includes "length": a thinking model can spend max_tokens on reasoning.
                    raise ValueError("Incomplete completion")
                # The answer is message.content only, never reasoning_content.
                content = data["choices"][0]["message"].get("content")
                if not isinstance(content, str) or not content.strip():
                    raise ValueError("Empty completion")
                parsed = json.loads(content)
                if not isinstance(parsed, dict):
                    raise ValueError("Expected JSON object")
            except Exception as exc:
                error = type(exc).__name__  # no server bodies, headers or credentials in errors
            if (
                response is not None
                and response.status_code == 200
                and error
                in ("ValueError", "JSONDecodeError", "KeyError", "IndexError", "TypeError")
            ):
                invalid_outputs += 1
            usage = (data or {}).get("usage") or {}
            inp, out = usage.get("prompt_tokens"), output_tokens(usage)
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
        if invalid_outputs == 8:
            raise InvalidModelOutputError("invalid_model_output_after_8_attempts")
        raise RuntimeError("Provider retries exhausted")
