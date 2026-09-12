"""Verified, reproducible publication artifacts and atomized generation costs."""

import json
import shutil
import sqlite3
import zipfile
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq
from sklearn.feature_extraction.text import TfidfVectorizer

from .corpus import sha, write_json
from .pilot import evidence_check


def cost_report(run_parent):
    stages = []
    for database in sorted(Path(run_parent).glob("*/progress.sqlite")):
        with sqlite3.connect(database) as db:
            db.row_factory = sqlite3.Row
            for row in db.execute("""SELECT stage,model,status,COUNT(*) attempts,
                SUM(input_tokens) input_tokens,SUM(cached_tokens) cached_tokens,
                SUM(output_tokens) output_tokens,SUM(estimated_usd) estimated_usd,
                SUM(CASE WHEN estimated_usd IS NULL THEN 1 ELSE 0 END) unknown_usage_attempts,
                SUM(elapsed) elapsed_seconds FROM attempts GROUP BY stage,model,status"""):
                stages.append(dict(run=database.parent.name, **dict(row)))
    return dict(
        stages=stages,
        total_estimated_usd=sum(r["estimated_usd"] or 0 for r in stages),
        unknown_usage_attempts=sum(r["unknown_usage_attempts"] for r in stages),
        pricing_basis="Fireworks serverless input/cached-input/output USD per million tokens, checked 2026-09-12; not an invoice",
        pricing_sources=[
            "https://fireworks.ai/models/deepseek-ai/deepseek-v4-flash-0731",
            "https://fireworks.ai/models/fireworks/glm-5p3-flash",
        ],
    )


def prepare(corpus, run, output, report_dir):
    corpus, run, output, report_dir = map(Path, (corpus, run, output, report_dir))
    output.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    all_calls = {}
    for domain in ("b2b", "b2c"):
        rows = pq.read_table(corpus / f"{domain}-corpus.parquet").to_pylist()
        for row in rows:
            assert sha(row["dialogue"].encode()) == row["dialogue_sha256"]
            md = (corpus / "markdown" / domain / f"{row['upstream_id']}.md").read_text()
            assert md.split("---\n", 2)[2] == row["dialogue"]
            all_calls[row["call_id"]] = row
        shutil.copyfile(corpus / f"{domain}-corpus.parquet", output / f"{domain}-corpus.parquet")
        shutil.copyfile(run / f"{domain}-test.parquet", output / f"{domain}-test.parquet")
        with zipfile.ZipFile(
            output / f"{domain}-markdown.zip", "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            for path in sorted((corpus / "markdown" / domain).glob("*.md")):
                info = zipfile.ZipInfo(f"{domain}/{path.name}", date_time=(2026, 9, 12, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes())
    questions = []
    for domain in ("b2b", "b2c"):
        questions.extend(pq.read_table(output / f"{domain}-test.parquet").to_pylist())
    assert len(questions) == 200
    assert len({q["question_id"] for q in questions}) == 200
    counts = Counter((q["domain"], q["question_class"]) for q in questions)
    assert set(counts.values()) == {50} and len(counts) == 4
    for q in questions:
        source = [all_calls[k] for k in q["supporting_call_ids"]]
        assert all(c["domain"] == q["domain"] for c in source)
        assert len(source) == (1 if q["question_class"] == "single_call" else 2)
        if len(source) == 2:
            assert source[0]["group_id"] and source[0]["group_id"] == source[1]["group_id"]
        evidence_check(q, source)
        artifact = json.loads(
            (run / "candidates" / f"{q['provenance']['job_id']}.json").read_text()
        )
        assert (
            artifact["status"] == "accepted" and artifact["stages"]["final_audit"]["pass"] is True
        )
        assert artifact["question"] == q["question"] and artifact["gold_answer"] == q["gold_answer"]
    texts = [q["question"] for q in questions]
    assert len({s.casefold().strip() for s in texts}) == 200
    vectors = TfidfVectorizer(ngram_range=(1, 2)).fit_transform(texts)
    similarity = (vectors @ vectors.T).toarray()
    duplicate_pairs = [
        dict(
            left=questions[i]["question_id"],
            right=questions[j]["question_id"],
            similarity=float(similarity[i, j]),
        )
        for i in range(len(questions))
        for j in range(i)
        if similarity[i, j] > 0.9
    ]
    # A conservative automatic release gate; replacements require rerunning selection.
    if duplicate_pairs:
        write_json(report_dir / "duplicate-candidates.json", duplicate_pairs)
        raise ValueError("Near-duplicate question candidates require replacement before release")
    costs = cost_report(run.parent)
    candidates = [json.loads(p.read_text()) for p in (run / "candidates").glob("*.json")]
    import statistics

    report = dict(
        questions=200,
        counts={f"{d}/{k}": v for (d, k), v in counts.items()},
        corpus_calls=len(all_calls),
        generated_candidates=len(candidates),
        accepted_candidates=sum(r["status"] == "accepted" for r in candidates),
        rejections=dict(Counter(r.get("failure") for r in candidates if r["status"] != "accepted")),
        median_answer_words=statistics.median(len(q["gold_answer"].split()) for q in questions),
        median_question_words=statistics.median(len(q["question"].split()) for q in questions),
        answer_over_30_words=sum(len(q["gold_answer"].split()) > 30 for q in questions),
        human_reviewed=False,
        near_duplicate_pairs=duplicate_pairs,
        costs=costs,
    )
    pilot_cost = sum(r["estimated_usd"] or 0 for r in costs["stages"] if r["run"] == run.name)
    report["pilot_estimated_usd"] = pilot_cost
    report["estimated_usd_per_accepted_question"] = pilot_cost / 200
    report["linear_projection_1000_questions_usd"] = pilot_cost * 5
    report["linear_projection_10000_questions_usd"] = pilot_cost * 50
    write_json(report_dir / "pilot.json", report)
    write_json(output / "pilot-report.json", report)
    write_json(output / "generation-config.json", json.loads((run / "config.json").read_text()))
    # Release concise audit outputs, not raw prompts/responses or model reasoning.
    audits = [
        dict(
            question_id=q["question_id"],
            **json.loads((run / "candidates" / f"{q['provenance']['job_id']}.json").read_text())[
                "stages"
            ],
        )
        for q in questions
    ]
    write_json(output / "validation-audits.json", audits)
    for name in ("LICENSE-DATA.txt", "NOTICE.md"):
        shutil.copyfile(name, output / name)
    shutil.copyfile("provenance/upstream-manifest.json", output / "upstream-manifest.json")
    manifest = dict(
        schema_version=1,
        release="pilot-v0.1.0",
        question_count=200,
        corpus_count=len(all_calls),
        license="cc-by-nc-4.0",
        files=[],
    )
    for path in sorted(output.iterdir()):
        if path.is_file() and path.name not in ("manifest.json", "README.md"):
            data = path.read_bytes()
            manifest["files"].append(dict(path=path.name, bytes=len(data), sha256=sha(data)))
    write_json(output / "manifest.json", manifest)
    shutil.copyfile("docs/DATASET_CARD.md", output / "README.md")
    (report_dir / "PILOT.md").write_text(f"""# SalesTranscriptQA pilot

Automatically generated and automatically validated; no human review or calibration.

- Accepted: **200 questions**, 50 per domain/class.
- Retrieval corpus: **10,829 calls**, all extracted verbatim.
- Candidate attempts in final run: **{len(candidates)}**.
- Median question/answer length: **{report["median_question_words"]} / {report["median_answer_words"]} words**.
- Pilot API cost estimate: **${pilot_cost:.4f}**.
- All development API cost estimate, including replaced runs and smoke checks: **${costs["total_estimated_usd"]:.4f}**.
- Attempts with unknown usage: **{costs["unknown_usage_attempts"]}**; these may incur unaccounted charges.
- Linear estimate: **${pilot_cost * 5:.2f} per 1,000 accepted questions**, **${pilot_cost * 50:.2f} per 10,000**, at the observed domain/class mix and rejection rate. These are token-priced estimates, not invoices or corpus-wide generation commitments. Yield may change as eligible source groups are exhausted.

See [machine-readable report](pilot.json) for per-stage/model/run quantities and costs. Local extraction and lexical retrieval used this VM; no separate GPU, embedding API or vector database charge was incurred. VM overhead is not priced in these API totals. Hugging Face storage charges, if any, are not included.

The first run rejected many retyped evidence quotes. The final run asks the generator to select line numbers; code copies the original dialogue and computes Unicode offsets. No source text is normalized. All retained questions passed independent answering, no-context checks, source selection against full-domain TF-IDF hard negatives, quality and fresh final audits. Two-call questions also passed each single-call ablation and a factual necessity check.

These model checks do not establish human-verified accuracy, exhaustive evidence uniqueness, or rigorous logical necessity. Calls are synthetic and short; questions are generated from known sources. This pilot was used to develop the pipeline and is not an untouched test set. A .9 TF-IDF cosine duplicate gate and exact duplicate checks passed. Source-pair eligibility is not proof that a useful two-call question exists.

[Implementation and follow-up issue](https://github.com/Endgame-Labs/SalesTranscriptQA/issues/1).
""")
    return report
