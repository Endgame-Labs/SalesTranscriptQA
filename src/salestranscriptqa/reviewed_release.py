"""Package the completed v9 cohort without admitting unreviewed generation output."""

import json
import shutil
import subprocess
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq
import yaml

from .corpus import sha, write_json
from .event_scope import select_reviewed
from .full import source_units
from .full_checkpoint import reviewed_selection
from .full_release import PILOT_REVISION


def read(path):
    return json.loads(Path(path).read_text())


def verify_rag(questions, report):
    """Require all four outcomes for every unchanged question, regardless of score."""
    report = Path(report)
    verification = read(report / "verification.json")
    rows = [json.loads(line) for line in (report / "results.jsonl").read_text().splitlines() if line]
    lookup = {q["question_id"]: q for q in questions}
    expected = {(qid, arm) for qid in lookup for arm in
                ("hybrid", "hybrid-rerank", "oracle", "no-context")}
    if (len(lookup) != len(questions) or len(rows) != len(expected)
            or {(r["question_id"], r["configuration"]) for r in rows} != expected
            or verification.get("exact_context_and_coverage_verified") is not True
            or verification.get("question_count") != len(questions)
            or verification.get("outcomes") != len(rows)):
        raise ValueError("Incomplete or unverified four-arm RAG cohort")
    for row in rows:
        if any(row[key] != lookup[row["question_id"]][key] for key in
               ("question", "gold_answer", "supporting_call_ids", "evidence")):
            raise ValueError("RAG question differs from frozen release")
    return verification


def replay_reviews(selected, exported, reviews, exclusions, pre_scope, scope, frozen):
    """Recompute selection; stored aggregate pass flags alone are insufficient."""
    by_item = {q["item"]: q for q in exported}
    by_id = {q["question_id"]: q for q in selected}
    fields = ("question", "gold_answer", "supporting_call_ids", "evidence")
    for q in exported:
        if q["question_id"] not in by_id or any(q[k] != by_id[q["question_id"]][k] for k in fields):
            raise ValueError("Review export differs from selected questions")
    for row in reviews:
        q = by_item.get(row["item"])
        if q is None or any(row[k] != q[k] for k in ("question", "gold_answer")):
            raise ValueError("Independent review text differs from export")
        if row.get("passed") is True:
            verdict = row.get("verdict", {})
            citation = row.get("citation_audit", {})
            required = ("realistic_sales_need", "natural_wording", "adequately_scoped",
                        "factual_answer", "exactly_requested_answer", "both_sources_required")
            if (not all(verdict.get(k) is True for k in required)
                    or verdict.get("locator_preamble") is not False
                    or citation.get("passed") is not True
                    or citation.get("schema_valid") is not True
                    or citation.get("verdict", {}).get("answer_supported") is not True
                    or len(citation.get("verdict", {}).get("evidence_support", [])) != len(q["evidence"])
                    or not all(e.get("supported") is True for e in
                               citation.get("verdict", {}).get("evidence_support", []))):
                raise ValueError("Independent review pass contradicts its gates")
    expected_pre, rejected = reviewed_selection(selected, exported, reviews, exclusions)
    if expected_pre != pre_scope:
        raise ValueError("Pre-scope questions differ from source review and quarantines")
    expected_final, scope_rejected = select_reviewed(pre_scope, scope)
    if expected_final != frozen:
        raise ValueError("Frozen questions differ from exhaustive customer-scope selection")
    return rejected + scope_rejected


def prepare_reviewed(project, run, rag_report, output, pilot=None):
    project, run, rag_report, output = map(lambda p: Path(p).resolve(),
                                         (project, run, rag_report, output))
    pilot = Path(pilot).resolve() if pilot else project / "data/release"
    if output.exists() and any(output.iterdir()):
        raise ValueError("Use an empty release output directory")
    progress, workflow, plan, config = [read(run / name) for name in
                                      ("progress.json", "workflow.json", "source-plan.json", "config.json")]
    if (progress.get("complete") is not True or workflow.get("stage") != "complete"
            or plan.get("scope") != "all" or plan.get("excluded_groups")
            or progress["total_units"] != 14916 or progress["completed_units"] != 14916
            or config.get("version") != "sales-questions-v9-line-evidence"):
        raise ValueError("Completed full v9 generation, reviews, and RAG required")
    # Independently re-run recorded gate, corpus hash, quote and Parquet validation.
    subprocess.run(["uv", "run", "python", "scripts/verify_generation_output.py", str(run)],
                   cwd=project, check=True)
    calls, expected = {}, set()
    for domain in ("b2b", "b2c"):
        rows = pq.read_table(project / "data/corpus" / f"{domain}-corpus.parquet").to_pylist()
        calls.update({c["call_id"]: c for c in rows})
        expected.update((domain, kind, tuple(c["call_id"] for c in source))
                        for kind, source in source_units(rows)
                        if not (domain == "b2c" and kind == "multi_call"))
    observed = {(u["domain"], u["question_class"], tuple(u["supporting_call_ids"]))
                for u in plan["units"]}
    if observed != expected or len(plan["units"]) != len(expected) or len(expected) != 14916:
        raise ValueError("Source plan does not cover every eligible unit exactly once")
    units = []
    for unit in plan["units"]:
        done = read(run / "units" / f"{unit['unit_id']}.json")
        if any(done[k] != v for k, v in unit.items()) or done["status"] not in ("accepted", "rejected"):
            raise ValueError("Invalid terminal source unit")
        units.append(done)
    reports = project / "reports"
    prefix = run.name
    selected = read(run / "selected/questions.json")
    exported = read(reports / f"{prefix}-accepted.json")["questions"]
    reviews = read(reports / f"{prefix}-accepted-qwen-review-v1.json")["results"]
    registry = read(reports / "cohort-registry.json")
    exclusions = registry["excluded_questions"] + read(
        reports / "sales-expanded-2000-v1-review-selection.json")["rejected"]
    pre_scope = read(run / "pre-scope/questions.json")
    scope = read(reports / f"{prefix}-customer-scope-review.json")
    frozen_path = run / "reviewed/questions.json"
    frozen = read(frozen_path)
    accepted_jobs = {u["accepted_job"] for u in units if u["status"] == "accepted"}
    if any(q["provenance"]["job_id"] not in accepted_jobs for q in frozen):
        raise ValueError("Frozen question lacks an accepted source unit")
    if scope["question_sha256"] != sha((run / "pre-scope/questions.json").read_bytes()):
        raise ValueError("Scope audit input checksum mismatch")
    rejected = replay_reviews(selected, exported, reviews, exclusions, pre_scope, scope, frozen)
    selection = read(reports / f"{prefix}-review-selection.json")
    if (selection["question_sha256"] != sha(frozen_path.read_bytes())
            or selection["accepted"] != len(frozen) or selection["rejected"] != rejected
            or not frozen or {q["domain"] for q in frozen} != {"b2b", "b2c"}):
        raise ValueError("Final selection receipt mismatch")
    verification = verify_rag(frozen, rag_report)
    for domain in ("b2b", "b2c"):
        if pq.read_table(run / "reviewed" / f"{domain}-test.parquet").to_pylist() != [
                q for q in frozen if q["domain"] == domain]:
            raise ValueError("Reviewed Parquet differs from frozen questions")
    old = read(pilot / "manifest.json")
    for entry in old["files"]:
        path = Path(entry["path"])
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Unsafe pilot manifest path")
        body = (pilot / path).read_bytes()
        if len(body) != entry["bytes"] or sha(body) != entry["sha256"]:
            raise ValueError("Pilot checksum mismatch")
    for domain in ("b2b", "b2c"):
        if (pilot / f"{domain}-corpus.parquet").read_bytes() != (
                project / "data/corpus" / f"{domain}-corpus.parquet").read_bytes():
            raise ValueError("Published corpus changed")
    output.mkdir(parents=True, exist_ok=True)
    for name in {e["path"] for e in old["files"]} | {"manifest.json", "README.md"}:
        dest = output / "pilot" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pilot / name, dest)
    for domain in ("b2b", "b2c"):
        for suffix in ("corpus.parquet", "markdown.zip"):
            shutil.copyfile(pilot / f"{domain}-{suffix}", output / f"{domain}-{suffix}")
        shutil.copyfile(run / "reviewed" / f"{domain}-test.parquet", output / f"{domain}-test.parquet")
    for name in ("LICENSE-DATA.txt", "NOTICE.md", "upstream-manifest.json"):
        shutil.copyfile(pilot / name, output / name)
    shutil.copyfile(frozen_path, output / "questions.json")
    shutil.copyfile(run / "config.json", output / "generation-config.json")
    write_json(output / "source-coverage.json", units)
    coverage = dict(complete=True, source_units=len(units), question_count=len(frozen),
                    counts=dict(Counter(q["domain"] + "/" + q["question_class"] for q in frozen)),
                    before_independent_review=len(selected), excluded_after_review=len(rejected))
    write_json(output / "coverage.json", coverage)
    write_json(output / "review-selection.json", selection)
    write_json(output / "validation-audits.json", dict(source_and_citation=reviews, customer_scope=scope))
    write_json(output / "release-verification.json", dict(
        release="full-v2", question_sha256=selection["question_sha256"],
        question_count=len(frozen), full_source_coverage=True, review_selection_replayed=True,
        frozen_parquet_verified=True, rag=verification,
        limitations="Recorded gates and artifact integrity; not a human correctness estimate. RAG scores never select questions."))
    configs = [dict(config_name=d + suffix, data_files=[dict(split="test", path=path + f"{d}-test.parquet")])
               for d in ("b2b", "b2c") for suffix, path in (("", ""), ("_pilot", "pilot/"))]
    card = dict(license="cc-by-nc-4.0", language=["en"], task_categories=["question-answering"],
                tags=["rag", "synthetic", "sales", "multi-hop"], configs=configs)
    table = "\n".join(f"| {d.upper()} | {sum(c['domain'] == d for c in calls.values())} | "
                      f"{coverage['counts'].get(d + '/single_call', 0)} | {coverage['counts'].get(d + '/multi_call', 0)} |"
                      for d in ("b2b", "b2c"))
    text = f"""# SalesTranscriptQA

{len(frozen):,} reviewed questions over {len(calls):,} verbatim synthetic CRMArena-Pro sales-call transcripts. All {len(units):,} eligible source units were processed: single calls in both domains and distinct-dialogue pairs within one B2B opportunity. No B2C multi-call questions. Rejected proposals and review failures do not become benchmark questions.

| Domain | Corpus calls | Single-call QA | Two-call QA |
|---|---:|---:|---:|
{table}

## Methodology and limitations

GLM 5.3 Flash generates candidate questions through Fireworks, with DeepSeek V4 Flash 0731 as the other model family for independent checks. The v9 pipeline checks source-conditioned answers, no-context answers, single-source ablations, question/answer contracts, exact evidence, group consistency, coherence, and two-model source necessity. Qwen 3.8 Max separately reviews full sources and cited passages. GLM and Qwen independently search the customer's complete account/lead-ID history for competing answers without seeing the reference answer; a further comparison checks agreement and reference coverage. Prior quality quarantines remain excluded.

Quality judgments are automated. Assistant inspections sampled candidates, but this is not a human-annotated gold set or a measured human correctness rate. Reviewers can make errors or reject valid questions. Final RAG evaluation covers every frozen question under hybrid, hybrid plus reranking, oracle, and no-context conditions. RAG results never remove questions. These are construction diagnostics, not independent held-out accuracy: generator/evaluation model families and some source groups overlap earlier experiments.

Dialogue remains verbatim. Questions may use published metadata, whose names are joined by IDs and do not establish who spoke. Search the full domain corpus; never give retrieval or answering systems reference answers, evidence labels, or supporting call IDs. Full source coverage does not mean coverage of every possible question or fact.

## Files and CLI

`b2b` and `b2c` configs expose reviewed QA Parquet; `*-corpus.parquet` and `*-markdown.zip` provide the complete corpus. `questions.json` is the exact frozen QA input used for RAG. `manifest.json` records file checksums. Coverage, selection and validation artifacts document the retained cohort; raw provider traces and credentials are excluded. Costs are reported separately in the campaign experiment report and are configured-rate estimates, not provider invoices.

Each QA includes domain/class, a concise reference answer, supporting call IDs, evidence and provenance. Evidence character offsets are zero-based Unicode code points, end-exclusive. Download using an immutable revision:

```sh
salestranscriptqa fetch --repo EndgameLabs/SalesTranscriptQA --revision COMMIT_SHA --data-dir salestranscriptqa-data
```

[Implementation and CLI](https://github.com/Endgame-Labs/SalesTranscriptQA) · [Usage](https://github.com/Endgame-Labs/SalesTranscriptQA/blob/main/docs/USAGE.md)

The original 200-question pilot is archived under `pilot/`, configs `b2b_pilot` and `b2c_pilot`, and revision `{PILOT_REVISION}`. It contains known wording/reference and multi-call defects and is retained for reproducibility, not mixed into the current cohort. No independent train/test split is claimed.

## Attribution and license

Derived from [Salesforce/CRMArenaPro](https://huggingface.co/datasets/Salesforce/CRMArenaPro), accompanying [CRMArena-Pro](https://arxiv.org/abs/2505.18878), Salesforce AI Research. Independent adaptation by Kyle Wild / Endgame Labs; not endorsed by Salesforce. Data and derived QA use CC BY-NC 4.0. The CLI's MIT license does not relicense the data. See `NOTICE.md`, `LICENSE-DATA.txt`, and `upstream-manifest.json` for attribution and pinned sources.
"""
    (output / "README.md").write_text("---\n" + yaml.safe_dump(card, sort_keys=False) + "---\n\n" + text)
    manifest = dict(schema_version=1, release="full-v2", question_count=len(frozen),
                    question_sha256=selection["question_sha256"], corpus_count=len(calls),
                    license="cc-by-nc-4.0", files=[])
    for path in sorted(output.rglob("*")):
        if path.is_file():
            manifest["files"].append(dict(path=str(path.relative_to(output)), bytes=path.stat().st_size,
                                          sha256=sha(path.read_bytes())))
    write_json(output / "manifest.json", manifest)
    verify_package(output, manifest)
    return coverage


def verify_package(output, manifest):
    """Check the release's frozen QA, both Parquet files, and completion receipt."""
    output = Path(output)
    required = {"questions.json", "release-verification.json", "coverage.json",
                "b2b-test.parquet", "b2c-test.parquet", "README.md", "LICENSE-DATA.txt",
                "NOTICE.md", "upstream-manifest.json", "review-selection.json",
                "validation-audits.json", "source-coverage.json", "generation-config.json",
                "b2b-corpus.parquet", "b2c-corpus.parquet", "b2b-markdown.zip", "b2c-markdown.zip"}
    names = [e["path"] for e in manifest["files"]]
    if not required <= set(names) or len(set(names)) != len(names):
        raise ValueError("Reviewed release manifest is incomplete or duplicated")
    body = (output / "questions.json").read_bytes()
    questions = json.loads(body)
    receipt = read(output / "release-verification.json")
    coverage = read(output / "coverage.json")
    n = len(questions)
    if (manifest.get("release") != "full-v2" or receipt.get("release") != "full-v2"
            or sha(body) != manifest.get("question_sha256")
            or sha(body) != receipt.get("question_sha256")
            or manifest.get("question_count") != n or receipt.get("question_count") != n
            or coverage.get("question_count") != n or coverage.get("source_units") != 14916
            or coverage.get("complete") is not True or not n
            or len({q["question_id"] for q in questions}) != n
            or not all(receipt.get(k) is True for k in
                       ("full_source_coverage", "review_selection_replayed", "frozen_parquet_verified"))
            or receipt.get("rag", {}).get("question_count") != n
            or receipt.get("rag", {}).get("outcomes") != n * 4
            or receipt.get("rag", {}).get("exact_context_and_coverage_verified") is not True):
        raise ValueError("Reviewed release completion receipt mismatch")
    for domain in ("b2b", "b2c"):
        expected = [q for q in questions if q["domain"] == domain]
        if not expected or pq.read_table(output / f"{domain}-test.parquet").to_pylist() != expected:
            raise ValueError("Reviewed release Parquet mismatch")
