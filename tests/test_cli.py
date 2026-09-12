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


def test_local_release_exports_and_detects_corruption(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq

    from salestranscriptqa.corpus import sha

    p = tmp_path / "b2b-test.parquet"
    pq.write_table(pa.Table.from_pylist([ROW]), p)
    (tmp_path / "manifest.json").write_text(
        json.dumps({"files": [{"path": p.name, "sha256": sha(p.read_bytes())}]})
    )
    runner = CliRunner()
    result = runner.invoke(
        app, ["questions", "export", "--domain", "b2b", "--data-dir", str(tmp_path)]
    )
    assert result.exit_code == 0
    assert "gold_answer" not in result.stdout and "supporting_call_ids" not in result.stdout
    assert json.loads(result.stdout)["question_id"] == "q"
    p.write_bytes(p.read_bytes() + b"corrupt")
    result = runner.invoke(
        app, ["questions", "export", "--domain", "b2b", "--data-dir", str(tmp_path)]
    )
    assert result.exit_code != 0
    assert "checksum" in result.output


def test_corpus_shards_and_markdown_preserve_dialogue(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq

    from salestranscriptqa.corpus import sha

    rows = [
        dict(
            call_id=f"b2b:c{i}",
            domain="b2b",
            metadata={"lead_name": "Zoë"},
            dialogue=f"Zoë: €{i}\nBuyer: Thanks.\n",
        )
        for i in range(3)
    ]
    p = tmp_path / "b2b-corpus.parquet"
    pq.write_table(pa.Table.from_pylist(rows), p)
    (tmp_path / "manifest.json").write_text(
        json.dumps({"files": [{"path": p.name, "sha256": sha(p.read_bytes())}]})
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "documents",
            "export",
            "--domain",
            "b2b",
            "--data-dir",
            str(tmp_path),
            "--shards",
            "2",
            "--output",
            str(tmp_path / "shards"),
        ],
    )
    assert result.exit_code == 0
    exported = [
        json.loads(line)
        for path in (tmp_path / "shards").glob("*.jsonl")
        for line in path.read_text().splitlines()
    ]
    assert sorted(r["call_id"] for r in exported) == ["b2b:c0", "b2b:c1", "b2b:c2"]
    result = runner.invoke(
        app,
        [
            "documents",
            "export",
            "--domain",
            "b2b",
            "--data-dir",
            str(tmp_path),
            "--format",
            "markdown",
            "--output",
            str(tmp_path / "markdown"),
        ],
    )
    assert result.exit_code == 0
    for i, row in enumerate(rows):
        assert (tmp_path / "markdown" / f"c{i}.md").read_text().split("---\n", 2)[2] == row[
            "dialogue"
        ]
