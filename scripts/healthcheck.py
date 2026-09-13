"""One read-only health observation, scheduled every 20 minutes by systemd."""

import json
import sqlite3
import subprocess
import time
from pathlib import Path

root = Path("runs/full-v1")
service = subprocess.run(
    [
        "systemctl",
        "--user",
        "show",
        "salestranscriptqa-full-v1",
        "--property=ActiveState",
        "--property=SubState",
        "--property=MainPID",
    ],
    capture_output=True,
    text=True,
    check=True,
)
state = dict(line.split("=", 1) for line in service.stdout.splitlines() if "=" in line)
progress = json.loads((root / "progress.json").read_text())
with sqlite3.connect(root / "progress.sqlite", timeout=30) as db:
    attempts, latest, cost = db.execute(
        "SELECT COUNT(*),MAX(started),SUM(estimated_usd) FROM attempts"
    ).fetchone()
path = root / "healthchecks.jsonl"
previous = json.loads(path.read_text().splitlines()[-1]) if path.exists() else None
record = dict(
    observed_at=time.time(),
    service=state,
    completed_units=progress["completed_units"],
    total_units=progress["total_units"],
    attempts=attempts,
    latest_request_started=latest,
    estimated_usd=cost,
    workflow=json.loads((root / "workflow.json").read_text()),
)
record["units_since_previous"] = (
    None if previous is None else record["completed_units"] - previous["completed_units"]
)
record["requests_since_previous"] = None if previous is None else attempts - previous["attempts"]
record["moving"] = state["ActiveState"] == "active" and (
    previous is None or record["units_since_previous"] > 0 or record["requests_since_previous"] > 0
)
with path.open("a") as f:
    f.write(json.dumps(record) + "\n")
print(json.dumps(record))
