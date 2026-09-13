"""Validated full-cohort packaging and pinned, atomic Hugging Face publication."""

import csv
import json
import os
import shlex
import shutil
import sqlite3
import statistics
import subprocess
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq
import yaml
from huggingface_hub import CommitOperationAdd, HfApi, hf_hub_download

from .corpus import sha, write_json
from .full import contract_valid, source_units
from .pilot import evidence_check

PILOT_REVISION = "d5eae88b4a725b697ab81dc720429477611f1a9c"
DEFAULT_REPO = "EndgameLabs/SalesTranscriptQA"


def metered_costs(run):
    with sqlite3.connect(Path(run) / "progress.sqlite") as db:
        db.row_factory = sqlite3.Row
        if db.execute("SELECT COUNT(*) FROM attempts WHERE status='running'").fetchone()[0]:
            raise ValueError("Unfinished API attempts prevent publication")
        return [
            dict(r)
            for r in db.execute("""SELECT stage,model,status,COUNT(*) attempts,
            SUM(input_tokens) input_tokens,SUM(cached_tokens) cached_tokens,
            SUM(output_tokens) output_tokens,SUM(estimated_usd) estimated_usd,
            SUM(CASE WHEN estimated_usd IS NULL THEN 1 ELSE 0 END) unknown_usage_attempts,
            SUM(elapsed) elapsed_seconds FROM attempts GROUP BY stage,model,status""")
        ]


def validate_complete(corpus, run):
    corpus, run = Path(corpus), Path(run)
    coverage = json.loads((run / "coverage.json").read_text())
    if coverage.get("complete") is not True:
        raise ValueError("Full generation is not complete")
    calls = {}
    expected = {}
    for domain in ["b2b", "b2c"]:
        cs = pq.read_table(corpus / f"{domain}-corpus.parquet").to_pylist()
        calls.update({c["call_id"]: c for c in cs})
        for kind, source in source_units(cs):
            expected[(domain, kind, tuple(c["call_id"] for c in source))] = True
    plan = json.loads((run / "source-plan.json").read_text())
    observed = {(u["domain"], u["question_class"], tuple(u["supporting_call_ids"])) for u in plan}
    if observed != set(expected) or len(plan) != len(expected):
        raise ValueError("Source plan does not cover every eligible unit exactly once")
    if coverage["total_units"] != len(plan):
        raise ValueError("Coverage count mismatch")
    unit_jobs = set()
    units = []
    for u in plan:
        done = json.loads((run / "units" / f"{u['unit_id']}.json").read_text())
        if any(done[k] != u[k] for k in u) or done["status"] not in ["accepted", "rejected"]:
            raise ValueError("Invalid terminal source unit")
        if done["accepted_job"]:
            unit_jobs.add(done["accepted_job"])
        units.append(done)
    rows = json.loads((run / "questions.json").read_text())
    if len(rows) != coverage["published_questions"] or len({q["question_id"] for q in rows}) != len(
        rows
    ):
        raise ValueError("Published question count/identity mismatch")
    for domain in ["b2b", "b2c"]:
        if pq.read_table(run / f"{domain}-test.parquet").to_pylist() != [
            q for q in rows if q["domain"] == domain
        ]:
            raise ValueError("Parquet and selected JSON disagree")
    for q in rows:
        source = [calls[cid] for cid in q["supporting_call_ids"]]
        if len(source) != (1 if q["question_class"] == "single_call" else 2):
            raise ValueError("Wrong source count")
        if any(c["domain"] != q["domain"] for c in source):
            raise ValueError("Cross-domain source")
        if len(source) == 2 and (
            not source[0]["group_id"] or source[0]["group_id"] != source[1]["group_id"]
        ):
            raise ValueError("Cross-group source")
        evidence_check(q, source)
        job = q["provenance"]["job_id"]
        r = json.loads((run / "candidates" / f"{job}.json").read_text())
        if job not in unit_jobs or r["status"] != "accepted" or not r.get("contract_checked"):
            raise ValueError("Question lacks accepted source unit and contract audit")
        if any(
            q[k] != r[k] for k in ["question", "gold_answer", "supporting_call_ids", "evidence"]
        ):
            raise ValueError("Question changed after validation")
        if r["stages"]["final_audit"].get("pass") is not True or not contract_valid(
            r["stages"]["question_contract"], r["stages"]["contract_audit"], q["question"], source
        ):
            raise ValueError("Question failed final quality gates")
    dropped = {r["question_id"] for r in coverage["duplicates"]}
    all_accepted = {
        json.loads((run / "candidates" / f"{job}.json").read_text())["question_id"]
        for job in unit_jobs
    }
    if all_accepted != {q["question_id"] for q in rows} | dropped:
        raise ValueError("Unaccounted accepted candidates")
    return rows, calls, coverage, units


def prepare_full(corpus, run, output, pilot="data/release"):
    corpus, run, output, pilot = map(Path, [corpus, run, output, pilot])
    rows, calls, coverage, units = validate_complete(corpus, run)
    costs = metered_costs(run)
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError("Use an empty release output directory")
    # Verify archived pilot files against its frozen manifest before preserving them.
    old = json.loads((pilot / "manifest.json").read_text())
    for entry in old["files"]:
        body = (pilot / entry["path"]).read_bytes()
        if sha(body) != entry["sha256"] or len(body) != entry["bytes"]:
            raise ValueError("Pilot artifact checksum mismatch")
    for domain in ["b2b", "b2c"]:
        for c in [c for c in calls.values() if c["domain"] == domain]:
            if sha(c["dialogue"].encode()) != c["dialogue_sha256"]:
                raise ValueError("Dialogue checksum mismatch")
        if (corpus / f"{domain}-corpus.parquet").read_bytes() != (
            pilot / f"{domain}-corpus.parquet"
        ).read_bytes():
            raise ValueError("Full corpus differs from original published corpus")
        for suffix in ["corpus.parquet", "markdown.zip"]:
            shutil.copyfile(pilot / f"{domain}-{suffix}", output / f"{domain}-{suffix}")
        shutil.copyfile(run / f"{domain}-test.parquet", output / f"{domain}-test.parquet")
    # Preserve original development QA and its audits as an explicitly separate cohort.
    archive_paths = {entry["path"] for entry in old["files"]} | {"manifest.json", "README.md"}
    for name in sorted(archive_paths):
        destination = output / "pilot" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pilot / name, destination)
    for name in ["LICENSE-DATA.txt", "NOTICE.md", "upstream-manifest.json"]:
        shutil.copyfile(pilot / name, output / name)
    for name in ["coverage.json", "config.json"]:
        shutil.copyfile(
            run / name, output / ("generation-config.json" if name == "config.json" else name)
        )
    # Unit disposition includes only source IDs, candidate IDs and status, no raw provider traces.
    write_json(output / "source-coverage.json", units)
    audits = []
    for q in rows:
        r = json.loads((run / "candidates" / f"{q['provenance']['job_id']}.json").read_text())
        audits.append(dict(question_id=q["question_id"], **r["stages"]))
    write_json(output / "validation-audits.json", audits)
    with (output / "generation-costs.csv").open("w") as f:
        writer = csv.DictWriter(f, fieldnames=list(costs[0]))
        writer.writeheader()
        writer.writerows(costs)
    candidates = [json.loads(p.read_text()) for p in (run / "candidates").glob("*.json")]
    report = dict(
        question_count=len(rows),
        corpus_count=len(calls),
        source_units=len(units),
        accepted_counts=coverage["accepted_counts"],
        generated_candidates=len(candidates),
        rejected_candidates=dict(
            Counter(r.get("failure") for r in candidates if r["status"] == "rejected")
        ),
        exhausted_source_units=len(coverage["exhausted_units"]),
        near_duplicates_removed=len(coverage["duplicates"]),
        median_answer_words=statistics.median(len(q["gold_answer"].split()) for q in rows),
        estimated_usd=sum(r["estimated_usd"] or 0 for r in costs),
        unknown_usage_attempts=sum(r["unknown_usage_attempts"] for r in costs),
        costs=costs,
        human_reviewed=False,
        prior_pilot_revision=PILOT_REVISION,
    )
    write_json(output / "generation-report.json", report)
    configs = []
    for domain in ["b2b", "b2c"]:
        configs.append(
            dict(config_name=domain, data_files=[dict(split="test", path=f"{domain}-test.parquet")])
        )
        configs.append(
            dict(
                config_name=domain + "_pilot",
                data_files=[dict(split="test", path=f"pilot/{domain}-test.parquet")],
            )
        )
    card = dict(
        license="cc-by-nc-4.0",
        language=["en"],
        task_categories=["question-answering"],
        tags=["rag", "synthetic", "sales", "multi-hop"],
        configs=configs,
    )
    table = "\n".join(
        f"| {d.upper()} | {sum(c['domain'] == d for c in calls.values())} | {coverage['accepted_counts'].get(d + '/single_call', 0)} | {coverage['accepted_counts'].get(d + '/multi_call', 0)} |"
        for d in ["b2b", "b2c"]
    )
    (output / "README.md").write_text(
        "---\n"
        + yaml.safe_dump(card, sort_keys=False)
        + "---\n\n"
        + f"""# SalesTranscriptQA — full source coverage

{len(rows):,} automatically generated and validated questions over all {len(calls):,} verbatim synthetic CRMArena-Pro sales calls. Every one of {len(units):,} eligible single-call or same-opportunity/lead pair units was processed, with up to three proposals and at most one accepted QA per unit. Eligibility does not guarantee a useful question: {report["exhausted_source_units"]:,} units exhausted quality attempts and {report["near_duplicates_removed"]:,} accepted questions were removed as lexical near-duplicates.

| Domain | Corpus calls | Single-call QA | Two-call QA |
|---|---:|---:|---:|
{table}

No human review or calibration. Questions use transcript dialogue plus published identifying metadata. Dialogue remains verbatim; gold answers and source IDs must not be given to evaluated retrieval systems. Always search the full domain corpus.

## Generation and quality

DeepSeek V4 Flash 0731 generates concise questions and answers; GLM 5.3 Flash independently answers and validates through Fireworks. Source-conditioned answering, two no-context checks, both single-call ablations for two-call QA, exact evidence validation, TF-IDF hard negatives, and fresh final audits precede a new question-first obligation extraction and cross-family reference-alignment audit. The question-first extractor never sees the proposed reference. Required facts must actually be requested; every two-call question must require a distinct source-exclusive fact from each call. No DSPy optimization or human correctness rate is claimed. Final global lexical near-duplicates above .9 unigram/bigram TF-IDF cosine are removed deterministically.

The original 200-question pilot is preserved under `pilot/`, configs `b2b_pilot` and `b2c_pilot`, and immutable revision `{PILOT_REVISION}`. It contains known wording/reference and two-call-necessity defects and is retained for reproducing earlier experiments. The full cohort is freshly generated using the stronger protocol rather than silently changing those pilot annotations. Pilot and full cohorts overlap source groups; neither is an independent train/test split. Full source coverage is not coverage of every possible fact or question.

## Files and CLI

Configs `b2b` and `b2c` expose the new QA Parquet. Separate `*-corpus.parquet` and `*-markdown.zip` contain every source call. `manifest.json` records checksums; `source-coverage.json` records every source unit's terminal disposition; `coverage.json` includes exhausted units and duplicate removals. `generation-report.json`, `generation-costs.csv`, `generation-config.json`, and `validation-audits.json` document yield, metered costs and automated checks. Provider traces and credentials are excluded. Estimated generation API cost: ${report["estimated_usd"]:.2f}, not an invoice; {report["unknown_usage_attempts"]} attempts have unknown usage. VM/storage charges are excluded.

[Implementation and CLI](https://github.com/Endgame-Labs/SalesTranscriptQA) · [CLI usage](https://github.com/Endgame-Labs/SalesTranscriptQA/blob/main/docs/USAGE.md). Fetch with `salestranscriptqa fetch --repo EndgameLabs/SalesTranscriptQA --revision COMMIT_SHA --data-dir salestranscriptqa-data`, using this release's full immutable commit hash.

Each question has an ID, domain/class, question, concise gold answer, alternate-answer list, supporting call IDs, exact dialogue or metadata evidence, and provenance. Dialogue evidence offsets are zero-based Unicode code points, end-exclusive. Canonical dialogue has not been normalized. Linked identity metadata is resolved from IDs and does not imply that a linked contact is the speaker.

## Attribution and license

Derived from [Salesforce/CRMArenaPro](https://huggingface.co/datasets/Salesforce/CRMArenaPro), accompanying [CRMArena-Pro](https://arxiv.org/abs/2505.18878), Salesforce AI Research. This independent adaptation by Kyle Wild / Endgame Labs is not endorsed by Salesforce. Data and derived QA retain CC BY-NC 4.0; the companion CLI's MIT license does not relicense data. See NOTICE.md, LICENSE-DATA.txt and upstream-manifest.json for attribution and pinned source revisions.
"""
    )
    manifest = dict(
        schema_version=1,
        release="full-v1",
        question_count=len(rows),
        corpus_count=len(calls),
        license="cc-by-nc-4.0",
        files=[],
    )
    for path in sorted(output.rglob("*")):
        if path.is_file() and path != output / "manifest.json":
            body = path.read_bytes()
            manifest["files"].append(
                dict(path=str(path.relative_to(output)), bytes=len(body), sha256=sha(body))
            )
    write_json(output / "manifest.json", manifest)
    return report


def hf_token():
    token = os.environ.get("HF_TOKEN")
    if not token:
        path = Path.home() / ".secrets/keys.env"
        if path.exists():
            for line in path.read_text().splitlines():
                key, sep, value = line.removeprefix("export ").partition("=")
                if sep and key.strip() == "HF_TOKEN":
                    token = shlex.split(value)[0]
                    break
    if not token:
        raise RuntimeError("HF_TOKEN unavailable")
    return token


def publish_full(output, receipt, repo=DEFAULT_REPO):
    output, receipt = Path(output), Path(receipt)
    manifest = json.loads((output / "manifest.json").read_text())
    coverage = json.loads((output / "coverage.json").read_text())
    if coverage.get("complete") is not True or manifest["release"] != "full-v1":
        raise ValueError("Only a completed full release can be published")
    for entry in manifest["files"]:
        p = Path(entry["path"])
        if p.is_absolute() or ".." in p.parts:
            raise ValueError("Unsafe manifest path")
        body = (output / p).read_bytes()
        if len(body) != entry["bytes"] or sha(body) != entry["sha256"]:
            raise ValueError("Release checksum mismatch")
    api = HfApi(token=hf_token())
    if receipt.exists():
        info = json.loads(receipt.read_text())
        if (
            info["manifest_sha256"] != sha((output / "manifest.json").read_bytes())
            or info["repo_id"] != repo
        ):
            raise ValueError("Publication receipt does not match this release")
        revision = info["revision"]
    else:
        parent = api.repo_info(repo, repo_type="dataset").sha
        paths = [output / entry["path"] for entry in manifest["files"]] + [output / "manifest.json"]
        commit = api.create_commit(
            repo_id=repo,
            repo_type="dataset",
            parent_commit=parent,
            commit_message=f"Publish full source coverage: {manifest['question_count']} validated QA",
            operations=[
                CommitOperationAdd(path_in_repo=str(p.relative_to(output)), path_or_fileobj=str(p))
                for p in paths
            ],
        )
        revision = commit.oid
        info = dict(
            repo_id=repo,
            revision=revision,
            parent_revision=parent,
            manifest_sha256=sha((output / "manifest.json").read_bytes()),
            verified=False,
        )
        write_json(receipt, info)
    # Public, pinned file checks: no token used for downloads.
    for entry in manifest["files"] + [
        dict(
            path="manifest.json",
            sha256=sha((output / "manifest.json").read_bytes()),
            bytes=(output / "manifest.json").stat().st_size,
        )
    ]:
        p = Path(
            hf_hub_download(
                repo_id=repo,
                repo_type="dataset",
                revision=revision,
                filename=entry["path"],
                token=False,
            )
        )
        if sha(p.read_bytes()) != entry["sha256"] or p.stat().st_size != entry["bytes"]:
            raise ValueError("Anonymous download verification failed")
    env = dict(os.environ, HF_HUB_DISABLE_IMPLICIT_TOKEN="1")
    env.pop("HF_TOKEN", None)
    target = receipt.parent / "anonymous-cli-verification"
    subprocess.run(
        [
            "uv",
            "run",
            "salestranscriptqa",
            "fetch",
            "--repo",
            repo,
            "--revision",
            revision,
            "--data-dir",
            str(target),
        ],
        env=env,
        check=True,
    )
    info.update(
        verified=True,
        anonymous_checksums=True,
        anonymous_cli_fetch=True,
        question_count=manifest["question_count"],
        url=f"https://huggingface.co/datasets/{repo}/tree/{revision}",
    )
    write_json(receipt, info)
    return info
