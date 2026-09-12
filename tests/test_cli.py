import json

import pytest
import typer
from typer.testing import CliRunner

from salestranscriptqa.cli import app, batch, preflight, public_question, score_batch

ROW = dict(
    question_id="q",
    domain="b2b",
    question_class="multi_call",
    question="What changed?",
    gold_answer="Budget rose from 10 to 20",
    alternate_answers=[],
    supporting_call_ids=["a", "b"],
    evidence=[],
)


def test_gold_and_sources_are_opt_in():
    assert set(public_question(ROW, False, False)) == {
        "question_id",
        "domain",
        "question_class",
        "question",
    }


def test_batch_rejects_duplicate_unknown_empty_and_wrong_domain(tmp_path):
    p = tmp_path / "answers.jsonl"
    for rows in (
        [{"question_id": "q", "answer": "ok"}] * 2,
        [{"question_id": "unknown", "answer": "ok"}],
        [{"question_id": "q", "answer": " "}],
        [{"question_id": "q", "answer": "ok", "domain": "b2c"}],
    ):
        p.write_text("\n".join(json.dumps(r) for r in rows))
        with pytest.raises(typer.BadParameter):
            batch(p, [ROW])


def test_multicall_recall_distinguishes_complete_set():
    a = [
        dict(
            question_id="q",
            answer=ROW["gold_answer"],
            retrieved_call_ids=["a", "x", "y", "z", "n", "b"],
        )
    ]
    r = score_batch(a, [ROW])["results"][0]
    assert r["exact_match"] == 1
    assert r["call_recall_at_5"] == 0.5
    assert r["all_calls_at_5"] == 0
    assert r["call_recall_at_10"] == 1
    assert r["all_calls_at_10"] == 1


def test_no_overwrite_without_force(tmp_path):
    path = tmp_path / "exists"
    path.write_text("original")
    with pytest.raises(typer.BadParameter):
        preflight(path)
    assert path.read_text() == "original"


def test_help_and_instructions():
    runner = CliRunner()
    assert runner.invoke(app, ["--help"]).exit_code == 0
    result = runner.invoke(app, ["instructions"])
    assert result.exit_code == 0
    assert "CRMArena-Pro" in result.stdout
