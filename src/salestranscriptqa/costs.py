"""Link billed request attempts to accepted/rejected candidates using verified cache keys."""

import csv
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

from .transport import RATES, digest


def breakdown(run, accepted_ids, output):
    run, output = Path(run), Path(output)
    config = json.loads((run / "config.json").read_text())
    config_digest = digest(config)
    version = config["version"]
    with sqlite3.connect(run / "progress.sqlite") as db:
        db.row_factory = sqlite3.Row
        attempts = [dict(r) for r in db.execute("select * from attempts order by started")]
    parsed = {}
    question_jobs = defaultdict(set)
    generator_jobs = {}
    for row in attempts:
        if not row["artifact"]:
            continue
        artifact = json.loads((run / row["artifact"]).read_text())
        payload = artifact["request"]
        value = json.loads(payload["messages"][0]["content"].rsplit("\nINPUT JSON:\n", 1)[1])
        parsed[row["id"]] = (payload, value)
        if row["stage"] == "generate":
            ids = [c["call_id"] for c in value["calls"]]
            job = digest(
                dict(
                    config=config_digest,
                    domain=ids[0].split(":")[0],
                    kind=value["question_class"],
                    calls=ids,
                )
            )
            assert (
                digest(dict(payload=payload, stage=row["stage"], nonce=version + job))
                == row["request_key"]
            )
            generator_jobs[row["id"]] = job
            question = (artifact.get("parsed") or {}).get("question")
            if isinstance(question, str):
                question_jobs[question].add(job)
    groups = defaultdict(
        lambda: dict(
            attempts=0,
            input_tokens=0,
            cached_tokens=0,
            output_tokens=0,
            estimated_usd=0.0,
            unknown_usage_attempts=0,
        )
    )
    for row in attempts:
        job = generator_jobs.get(row["id"])
        if job is None and row["id"] in parsed:
            payload, value = parsed[row["id"]]
            question = value.get("question") or value.get("candidate", {}).get("question")
            for candidate_job in question_jobs.get(question, []):
                nonce = version + candidate_job
                if row["stage"] == "single_call_ablation":
                    nonce += value["calls"][0]["call_id"]
                if (
                    digest(dict(payload=payload, stage=row["stage"], nonce=nonce))
                    == row["request_key"]
                ):
                    job = candidate_job
                    break
        outcome = (
            "unattributed" if job is None else ("accepted" if job in accepted_ids else "rejected")
        )
        group = groups[outcome, row["stage"], row["model"]]
        group["attempts"] += 1
        for key in ("input_tokens", "cached_tokens", "output_tokens", "estimated_usd"):
            group[key] += row[key] or 0
        group["unknown_usage_attempts"] += row["estimated_usd"] is None
    rows = []
    for (outcome, stage, model), counts in sorted(groups.items()):
        rates = RATES[model]
        counts["uncached_input_tokens"] = counts["input_tokens"] - counts["cached_tokens"]
        rows.append(
            dict(
                outcome=outcome,
                stage=stage,
                model=model,
                **counts,
                input_usd_per_million=rates[0],
                cached_usd_per_million=rates[1],
                output_usd_per_million=rates[2],
            )
        )
    with output.open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    totals = defaultdict(float)
    for r in rows:
        totals[r["outcome"]] += r["estimated_usd"]
    return dict(rows=rows, cost_by_candidate_outcome=dict(totals))
