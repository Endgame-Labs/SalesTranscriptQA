"""Live regression audit of the two known defective pilot items; paid API calls."""

import json
from pathlib import Path

from salestranscriptqa.full import Full

full = Full("data/corpus", "runs/contract-regression-v2")
questions = json.loads(Path("runs/pilot-v2/questions.json").read_text())
results = []
for q in questions:
    if q["question_id"] not in [
        "b2b-single_call-44366532fbd14e03",
        "b2c-multi_call-44c21bc1b95c05df",
    ]:
        continue
    calls = [full.calls[q["domain"]][cid] for cid in q["supporting_call_ids"]]
    result = json.loads(
        (Path("runs/pilot-v2/candidates") / (q["provenance"]["job_id"] + ".json")).read_text()
    )
    audited = full.audit_candidate(result, calls)
    results.append(
        dict(
            question_id=q["question_id"],
            status=audited["status"],
            failure=audited.get("failure"),
            contract=audited["stages"]["question_contract"],
            verdict=audited["stages"]["contract_audit"],
        )
    )
Path("reports/full-contract-regression.json").write_text(json.dumps(results, indent=2) + "\n")
assert len(results) == 2 and all(r["status"] == "rejected" for r in results)
print({"known_bad_pilot_questions_rejected": len(results)})
