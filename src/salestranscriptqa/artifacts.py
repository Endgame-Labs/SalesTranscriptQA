"""Lossless storage for completed request artifacts; cache semantics stay unchanged."""
import fcntl
import gzip
import hashlib
import json
import os
import sqlite3
from pathlib import Path


def read_json_artifact(path):
    path = Path(path)
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            return json.load(stream)
    return json.loads(path.read_text())


def archive_requests(root, max_raw_bytes):
    root = Path(root).resolve()
    if max_raw_bytes <= 0:
        raise ValueError("Positive byte limit required")
    with (root / "pilot.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if json.loads((root / "progress.json").read_text()).get("complete") is not True:
            raise ValueError("Only completed generation can be archived")
        with sqlite3.connect(root / "progress.sqlite", timeout=60) as db:
            rows = db.execute("SELECT id,artifact FROM attempts WHERE status='ok' AND artifact IS NOT NULL ORDER BY id").fetchall()
            count = raw_bytes = compressed_bytes = 0
            manifest = root / "request-compression.jsonl"
            with manifest.open("a") as log:
                for aid, relative in rows:
                    if raw_bytes >= max_raw_bytes:
                        break
                    path = root / relative
                    if path.suffix != ".json":
                        continue
                    if path.resolve().parent != root / "requests":
                        raise ValueError("Unexpected artifact path")
                    if path.stat().st_nlink != 1:
                        continue  # Preserve shared inherited checkpoint artifacts.
                    target = path.with_suffix(".json.gz")
                    if target.exists():
                        raise ValueError("Existing compressed artifact requires inspection")
                    original = path.read_bytes()
                    json.loads(original)
                    packed = gzip.compress(original, compresslevel=6, mtime=0)
                    if gzip.decompress(packed) != original:
                        raise ValueError("Compression round-trip mismatch")
                    temporary = target.with_suffix(".gz.tmp")
                    with temporary.open("xb") as out:
                        out.write(packed)
                        out.flush()
                        os.fsync(out.fileno())
                    temporary.rename(target)
                    # Verify bytes read from disk, not only the in-memory compression.
                    if gzip.decompress(target.read_bytes()) != original:
                        raise ValueError("Written archive verification failed")
                    changed = db.execute("UPDATE attempts SET artifact=? WHERE id=? AND artifact=?", (str(target.relative_to(root)), aid, relative)).rowcount
                    if changed != 1:
                        raise ValueError("Artifact ledger changed concurrently")
                    db.commit()
                    record = dict(attempt_id=aid, original_path=relative, artifact=str(target.relative_to(root)), sha256=hashlib.sha256(original).hexdigest(), compressed_sha256=hashlib.sha256(packed).hexdigest(), raw_bytes=len(original), compressed_bytes=len(packed))
                    log.write(json.dumps(record) + "\n")
                    log.flush()
                    os.fsync(log.fileno())
                    path.unlink()  # Only after disk round-trip, ledger commit and durable receipt.
                    count += 1
                    raw_bytes += len(original)
                    compressed_bytes += len(packed)
            return dict(artifacts=count, raw_bytes=raw_bytes, compressed_bytes=compressed_bytes, freed_bytes=raw_bytes-compressed_bytes, manifest=str(manifest))
