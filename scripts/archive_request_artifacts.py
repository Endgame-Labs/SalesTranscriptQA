"""Losslessly compress completed, non-shared generation request logs."""
import argparse
import json

from salestranscriptqa.artifacts import archive_requests

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run_dir")
    p.add_argument("--max-raw-bytes", type=int, required=True)
    a = p.parse_args()
    print(json.dumps(archive_requests(a.run_dir, a.max_raw_bytes)), flush=True)
