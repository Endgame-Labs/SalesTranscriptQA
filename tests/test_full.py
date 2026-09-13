import pytest

from salestranscriptqa.full import contract_valid, deduplicate, source_units


def call(cid, group, body=None):
    return dict(call_id=cid, group_id=group, dialogue_sha256=body or cid)


def test_exhaustive_pairs_do_not_cross_groups_or_repeat_dialogue():
    calls = [call("a", "x"), call("b", "x"), call("c", "x", "b"), call("d", "y"), call("e", None)]
    units = [(kind, [c["call_id"] for c in cs]) for kind, cs in source_units(calls)]
    assert len([u for u in units if u[0] == "single_call"]) == 5
    assert [ids for k, ids in units if k == "multi_call"] == [["a", "b"], ["a", "c"]]


def test_contract_requires_an_exclusive_requested_fact_from_each_call():
    flags = dict.fromkeys(
        [
            "question_answer_aligned",
            "no_unasked_required_facts",
            "complete_minimal_reference",
            "independent_answer_satisfies_question",
            "obligations_correct",
            "each_call_required_by_question",
        ],
        True,
    )
    flags.update(
        unasked_gold_claims=[],
        gold_claim_checks=[
            dict(claim="Lexus", question_span="What model", required_by_question=True),
            dict(claim="160-point", question_span="what inspection", required_by_question=True),
        ],
    )
    q = "What model on Monday and what inspection on Tuesday?"
    a = dict(
        question_span="What model",
        explicitly_requested=True,
        required_fact="Lexus",
        source_call_ids=["a"],
    )
    b = dict(
        question_span="what inspection",
        explicitly_requested=True,
        required_fact="160-point",
        source_call_ids=["b"],
    )
    calls = [call("a", "x"), call("b", "x")]
    assert contract_valid({"obligations": [a, b]}, flags, q, calls)
    assert not contract_valid({"obligations": [b]}, flags, q, calls)
    assert not contract_valid(
        {"obligations": [dict(a, source_call_ids=["a", "b"]), b]}, flags, q, calls
    )
    assert not contract_valid(
        {"obligations": [dict(a, question_span="unasked"), b]}, flags, q, calls
    )
    assert not contract_valid(
        {"obligations": [a, b]}, dict(flags, no_unasked_required_facts=False), q, calls
    )


def test_duplicate_filter_retains_distinct_questions_deterministically():
    rows = [
        dict(question_id="b", question="What price did Sue quote for Workflow Genius?"),
        dict(question_id="a", question="What price did Sue quote for Workflow Genius?"),
        dict(question_id="c", question="Which vehicle inspection checklist did Joe request?"),
    ]
    kept, rejected = deduplicate(rows)
    assert [q["question_id"] for q in kept] == ["a", "c"]
    assert rejected[0]["question_id"] == "b" and rejected[0]["duplicate_of"] == "a"
    assert deduplicate(list(reversed(rows))) == (kept, rejected)


def test_unit_resume_and_proposal_bound(tmp_path):
    from salestranscriptqa.full import Full

    full = object.__new__(Full)
    full.root = tmp_path
    full.calls = {"b2b": {"a": call("a", "x")}}
    full.settings = {"proposals_per_unit": 3}
    seen = []

    def candidate(domain, kind, calls, variant):
        seen.append(variant)
        return dict(job_id=str(variant), status="rejected")

    full.candidate = candidate
    u = dict(unit_id="u", domain="b2b", question_class="single_call", supporting_call_ids=["a"])
    assert full.process_unit(u)["jobs"] == ["0", "1", "2"]
    assert full.process_unit(u)["status"] == "rejected"
    assert seen == [0, 1, 2]


def test_transport_failure_is_not_finalized_as_quality_rejection(tmp_path):
    from salestranscriptqa.full import Full

    full = object.__new__(Full)
    full.root = tmp_path
    full.calls = {"b2b": {"a": call("a", "x")}}
    full.settings = {"proposals_per_unit": 3}

    def fail(*args):
        raise RuntimeError("Provider retries exhausted")

    full.candidate = fail
    u = dict(unit_id="u", domain="b2b", question_class="single_call", supporting_call_ids=["a"])
    with pytest.raises(RuntimeError):
        full.process_unit(u)
    assert not (tmp_path / "units/u.json").exists()


def test_publisher_refuses_incomplete_or_modified_artifacts_before_network(tmp_path, monkeypatch):
    import json

    import salestranscriptqa.full_release as release

    def forbidden(*args, **kwargs):
        raise AssertionError("Network must not be reached")

    monkeypatch.setattr(release, "HfApi", forbidden)
    (tmp_path / "manifest.json").write_text(json.dumps({"release": "full-v1", "files": []}))
    (tmp_path / "coverage.json").write_text(json.dumps({"complete": False}))
    with pytest.raises(ValueError, match="completed"):
        release.publish_full(tmp_path, tmp_path / "receipt.json")
    (tmp_path / "coverage.json").write_text(json.dumps({"complete": True}))
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "release": "full-v1",
                "files": [{"path": "coverage.json", "bytes": 1, "sha256": "wrong"}],
            }
        )
    )
    with pytest.raises(ValueError, match="checksum"):
        release.publish_full(tmp_path, tmp_path / "receipt.json")


def test_missing_source_unit_blocks_release(tmp_path):
    import json

    import pyarrow as pa
    import pyarrow.parquet as pq

    from salestranscriptqa.full_release import validate_complete

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    run = tmp_path / "run"
    run.mkdir()
    for domain in ["b2b", "b2c"]:
        pq.write_table(
            pa.Table.from_pylist([dict(call(domain + ":a", "g"), domain=domain)]),
            corpus / f"{domain}-corpus.parquet",
        )
    (run / "coverage.json").write_text(json.dumps({"complete": True, "total_units": 0}))
    (run / "source-plan.json").write_text("[]")
    with pytest.raises(ValueError, match="every eligible unit"):
        validate_complete(corpus, run)
