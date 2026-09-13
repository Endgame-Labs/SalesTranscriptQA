"""Durable full-generation workflow. Run with uv run python scripts/generate_and_publish.py."""

import fcntl
import json
import time
from pathlib import Path

from salestranscriptqa.corpus import write_json
from salestranscriptqa.full import Full
from salestranscriptqa.full_release import prepare_full, publish_full


def main():
    root = Path("runs/full-v1")
    root.mkdir(parents=True, exist_ok=True)
    output = Path("data/full-v1-release")
    with (root / "workflow.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)

        def status(stage, **extra):
            value = dict(stage=stage, updated=time.time(), **extra)
            write_json(root / "workflow.json", value)
            print(json.dumps(value), flush=True)

        try:
            status("generating")
            full = Full("data/corpus", root)
            full.run_all()
            full.transport.client.close()
            status("packaging")
            if not (output / "manifest.json").exists():
                # Incomplete packaging directories are preserved for diagnosis, never uploaded.
                if output.exists():
                    output.rename(output.with_name(output.name + f"-incomplete-{int(time.time())}"))
                prepare_full("data/corpus", root, output)
            status("publishing")
            publication = publish_full(output, root / "publication.json")
            status("complete", publication=publication)
        except Exception as exc:
            # No response bodies or credentials in durable status/logs.
            status("failed", error_type=type(exc).__name__)
            raise


if __name__ == "__main__":
    main()
