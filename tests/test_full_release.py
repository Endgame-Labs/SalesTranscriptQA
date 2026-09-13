import json
import shutil
import zipfile

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from salestranscriptqa.corpus import sha, write_json
from salestranscriptqa.full import Full
from salestranscriptqa.full_release import prepare_full
from salestranscriptqa.pilot import evidence_check
from salestranscriptqa.transport import Transport, digest


def test_complete_release_preserves_pilot_and_validates_every_manifest_file(tmp_path):
    corpus, run, pilot, output = [tmp_path / s for s in ["corpus", "run", "pilot", "output"]]
    corpus.mkdir()
    pilot.mkdir()
    full = object.__new__(Full)
    full.root = run
    full.transport = Transport(run)
    full.calls = {}
    full.config_digest = "test-config"
    write_json(run / "config.json", {"version": "fixture"})
    for domain, name, answer in [("b2b", "Sue", "€20"), ("b2c", "Jim", "160-point")]:
        body = name + ": " + answer
        c = dict(
            call_id=domain + ":a",
            domain=domain,
            group_id=domain + ":g",
            dialogue=body,
            dialogue_sha256=sha(body.encode()),
            metadata={"name": name},
        )
        full.calls[domain] = {c["call_id"]: c}
        pq.write_table(pa.Table.from_pylist([c]), corpus / f"{domain}-corpus.parquet")
        shutil.copyfile(corpus / f"{domain}-corpus.parquet", pilot / f"{domain}-corpus.parquet")
        with zipfile.ZipFile(pilot / f"{domain}-markdown.zip", "w") as z:
            z.writestr("a.md", "---\n{}\n---\n" + body)
        pq.write_table(
            pa.Table.from_pylist([{"question": "old pilot " + domain}]),
            pilot / f"{domain}-test.parquet",
        )
    plan = full.plan()
    write_json(run / "source-plan.json", plan)
    terminal = []
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
    for unit in plan:
        c = full.calls[unit["domain"]][unit["supporting_call_ids"][0]]
        question = (
            "What price did Sue quote?"
            if c["domain"] == "b2b"
            else "Which inspection did Jim offer?"
        )
        answer = "€20" if c["domain"] == "b2b" else "160-point"
        job = digest(unit)
        candidate = dict(
            job_id=job,
            question_id=job,
            domain=c["domain"],
            question_class="single_call",
            question=question,
            gold_answer=answer,
            supporting_call_ids=[c["call_id"]],
            evidence=[
                dict(
                    call_id=c["call_id"], answer_claim=answer, kind="dialogue", quote=c["dialogue"]
                )
            ],
            status="accepted",
            contract_checked=True,
            stages=dict(
                final_audit={"pass": True},
                question_contract={
                    "obligations": [
                        dict(
                            question_span=question,
                            explicitly_requested=True,
                            required_fact=answer,
                            source_call_ids=[c["call_id"]],
                        )
                    ]
                },
                contract_audit=dict(
                    flags,
                    unasked_gold_claims=[],
                    gold_claim_checks=[
                        dict(claim=answer, question_span=question, required_by_question=True)
                    ],
                ),
            ),
        )
        evidence_check(candidate, [c])
        write_json(run / "candidates" / f"{job}.json", candidate)
        done = dict(unit, status="accepted", jobs=[job], accepted_job=job)
        terminal.append(done)
        write_json(run / "units" / f"{unit['unit_id']}.json", done)
    full.finalize(plan, terminal)
    with full.transport.db() as db:
        db.execute(
            "INSERT INTO attempts(id,stage,model,status,input_tokens,cached_tokens,output_tokens,estimated_usd,elapsed) VALUES('a','generate','fixture','ok',10,0,10,.01,1)"
        )
    for name in ["LICENSE-DATA.txt", "NOTICE.md", "upstream-manifest.json", "README.md"]:
        (pilot / name).write_text("fixture " + name)
    entries = []
    for p in pilot.iterdir():
        entries.append(dict(path=p.name, sha256=sha(p.read_bytes()), bytes=p.stat().st_size))
    write_json(pilot / "manifest.json", dict(files=entries))
    report = prepare_full(corpus, run, output, pilot)
    assert report["question_count"] == 2 and report["source_units"] == 2
    manifest = json.loads((output / "manifest.json").read_text())
    for entry in manifest["files"]:
        p = output / entry["path"]
        assert sha(p.read_bytes()) == entry["sha256"] and p.stat().st_size == entry["bytes"]
    for p in pilot.iterdir():
        assert (output / "pilot" / p.name).read_bytes() == p.read_bytes()
    for domain in ["b2b", "b2c"]:
        assert (output / f"{domain}-corpus.parquet").read_bytes() == (
            corpus / f"{domain}-corpus.parquet"
        ).read_bytes()
    with pytest.raises(ValueError, match="empty"):
        prepare_full(corpus, run, output, pilot)
