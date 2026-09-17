import json
from copy import deepcopy

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from salestranscriptqa.corpus import sha, write_json
from salestranscriptqa.event_scope import VERSION
from salestranscriptqa.reviewed_release import (
    prepare_reviewed,
    replay_reviews,
    verify_package,
    verify_rag,
)


def question(qid="q", domain="b2b"):
    return dict(question_id=qid, domain=domain, question_class="single_call",
                question="What price did Mei quote?", gold_answer="$10",
                supporting_call_ids=[domain + ":call"], evidence=[{"quote": "Mei: $10"}])


def review_inputs():
    q = question()
    exported = [dict(q, item=1)]
    reviews = [dict(item=1, question=q["question"], gold_answer=q["gold_answer"], passed=True,
                    mechanical_locator_flags=[], verdict=dict(
                        realistic_sales_need=True, natural_wording=True, adequately_scoped=True,
                        factual_answer=True, exactly_requested_answer=True, both_sources_required=True,
                        locator_preamble=False), citation_audit=dict(
                            passed=True, schema_valid=True, verdict=dict(answer_supported=True,
                                                                       evidence_support=[dict(supported=True)])))]
    scope = dict(protocol=VERSION, results=[dict(q, passed=True, schema_valid=True,
                 extraction=dict(scope="determinate"), verdict=dict(scope="determinate"),
                 comparison=dict(answers_agree=True, reference_covers_requested_facts=True))])
    return [q], exported, reviews, [], [q], scope, [q]


def test_review_replay_rejects_changed_text_and_hidden_failures():
    inputs = review_inputs()
    assert replay_reviews(*inputs) == []
    bad = deepcopy(inputs)
    bad[1][0]["gold_answer"] = "$20"
    with pytest.raises(ValueError, match="export differs"):
        replay_reviews(*bad)
    bad = deepcopy(inputs)
    bad[2][0]["citation_audit"]["verdict"]["answer_supported"] = False
    with pytest.raises(ValueError, match="contradicts"):
        replay_reviews(*bad)
    bad = deepcopy(inputs)
    bad[2][0]["citation_audit"]["verdict"]["evidence_support"] = []
    with pytest.raises(ValueError, match="contradicts"):
        replay_reviews(*bad)


def test_quarantine_and_scope_rejections_cannot_be_reintroduced():
    inputs = list(review_inputs())
    inputs[3] = [{"question_id": "q"}]
    with pytest.raises(ValueError, match="quarantines"):
        replay_reviews(*inputs)
    inputs = list(review_inputs())
    inputs[5]["results"][0]["verdict"]["scope"] = "multiple"
    with pytest.raises(ValueError, match="customer-scope"):
        replay_reviews(*inputs)


def test_rag_requires_all_arms_and_exact_evidence_but_not_correct_answers(tmp_path):
    q = question()
    rows = [dict(q, configuration=arm, judgment={"correct": False}) for arm in
            ("hybrid", "hybrid-rerank", "oracle", "no-context")]
    write_json(tmp_path / "verification.json", dict(question_count=1, outcomes=4,
                                                    exact_context_and_coverage_verified=True))
    def save(value):
        (tmp_path / "results.jsonl").write_text("\n".join(json.dumps(r) for r in value))
    save(rows)
    assert verify_rag([q], tmp_path)["outcomes"] == 4
    save(rows[:3] + [rows[0]])
    with pytest.raises(ValueError, match="four-arm"):
        verify_rag([q], tmp_path)
    bad = deepcopy(rows)
    bad[0]["evidence"][0]["quote"] = "Mei: $20"
    save(bad)
    with pytest.raises(ValueError, match="differs"):
        verify_rag([q], tmp_path)


def package(tmp_path):
    qs = [question(), question("r", "b2c")]
    write_json(tmp_path / "questions.json", qs)
    checksum = sha((tmp_path / "questions.json").read_bytes())
    receipt = dict(release="full-v2", question_sha256=checksum, question_count=2,
                   full_source_coverage=True, review_selection_replayed=True,
                   frozen_parquet_verified=True, rag=dict(question_count=2, outcomes=8,
                                                          exact_context_and_coverage_verified=True))
    write_json(tmp_path / "release-verification.json", receipt)
    write_json(tmp_path / "coverage.json", dict(complete=True, source_units=14916, question_count=2))
    for d in ("b2b", "b2c"):
        pq.write_table(pa.Table.from_pylist([q for q in qs if q["domain"] == d]), tmp_path / f"{d}-test.parquet")
    names = ("questions.json", "release-verification.json", "coverage.json", "b2b-test.parquet",
             "b2c-test.parquet", "README.md", "LICENSE-DATA.txt", "NOTICE.md", "upstream-manifest.json",
             "review-selection.json", "validation-audits.json", "source-coverage.json",
             "generation-config.json", "b2b-corpus.parquet", "b2c-corpus.parquet",
             "b2b-markdown.zip", "b2c-markdown.zip")
    return dict(release="full-v2", question_count=2, question_sha256=checksum,
                files=[dict(path=name) for name in names])


def test_publication_guard_rejects_changed_parquet_or_missing_receipt(tmp_path):
    manifest = package(tmp_path)
    verify_package(tmp_path, manifest)
    pq.write_table(pa.Table.from_pylist([question("unreviewed")]), tmp_path / "b2b-test.parquet")
    with pytest.raises(ValueError, match="Parquet"):
        verify_package(tmp_path, manifest)
    manifest["files"] = [e for e in manifest["files"] if e["path"] != "release-verification.json"]
    with pytest.raises(ValueError, match="manifest"):
        verify_package(tmp_path, manifest)


def test_incomplete_run_cannot_package_or_start_validation(tmp_path, monkeypatch):
    run = tmp_path / "run"
    for name, value in {
        "progress.json": {"complete": False}, "workflow.json": {"stage": "generation"},
        "source-plan.json": {"scope": "all"}, "config.json": {"version": "sales-questions-v9-line-evidence"}
    }.items():
        write_json(run / name, value)
    def forbidden(*args, **kwargs):
        pytest.fail("Incomplete packaging must fail before subprocess validation")
    monkeypatch.setattr("salestranscriptqa.reviewed_release.subprocess.run", forbidden)
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="Completed full"):
        prepare_reviewed(tmp_path, run, tmp_path / "rag", output)
    assert not output.exists()
