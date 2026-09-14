"""Wait on one live Linux process handle, then verify a completed bounded sample."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import sqlite3
import subprocess
from salestranscriptqa.corpus import write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid',type=int,required=True)
    parser.add_argument('--run-dir',type=Path,required=True)
    args=parser.parse_args()
    root=args.run_dir
    # A pidfd pins this exact process; PID reuse cannot trigger a different job.
    handle=os.pidfd_open(args.pid)
    try:
        while not select.select([handle],[],[],5)[0]:
            pass
    finally:
        os.close(handle)
    progress=json.loads((root/'progress.json').read_text())
    if progress.get('complete') is not True or progress.get('scope')!='sample' or progress.get('total_units')!=100:
        raise RuntimeError('The original process ended without completing the intended 100-unit sample')
    command=json.loads((root/'validation-command.json').read_text())
    if command[:4]!=['uv','run','python','scripts/generate_sales_questions.py'] or '--all' in command:
        raise RuntimeError('Expected the recorded bounded generation command')
    if command[command.index('--sample')+1]!='100' or command[command.index('--run-dir')+1]!=str(root):
        raise RuntimeError('Recorded command scope/root mismatch')
    def counts():
        with sqlite3.connect(root/'progress.sqlite') as db:
            return dict(db.execute('SELECT stage,COUNT(*) FROM attempts GROUP BY stage').fetchall())
    def snapshot():
        files=[root/'questions.json',root/'b2b-test.parquet',root/'b2c-test.parquet',
               root/'selected/questions.json',root/'selected/b2b-test.parquet',root/'selected/b2c-test.parquet',root/'selected/selection.json']
        return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    log=(root/'completion-validation.log').open('a')
    def run(argv):
        print(json.dumps({'step':argv}),flush=True)
        subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,check=True)
    before=counts()
    run(command) # cached generation plus newly added final selection
    after_selection=counts()
    assert {k:v for k,v in before.items() if k!='query_coherence'}=={k:v for k,v in after_selection.items() if k!='query_coherence'}
    run(['uv','run','python','scripts/verify_generation_output.py',str(root)])
    run(['uv','run','python','scripts/review_generation_output.py',str(root)])
    report=Path('reports')/(root.name+'-accepted.json')
    run(['uv','run','python','scripts/review_sales_sample.py',str(report)])
    before_replay=counts();hashes=snapshot()
    run(command)
    assert counts()==before_replay, 'Completed replay made new API attempts'
    assert snapshot()==hashes, 'Completed replay changed dataset artifacts'
    run(['uv','run','python','scripts/verify_generation_output.py',str(root)])
    receipt={'automation_complete':True,'first_replay_added_only_selection':True,
             'second_replay_new_attempts':0,'artifact_hashes':hashes,'attempts_by_stage':counts(),
             'independent_review_report':str(report.with_name(report.stem+'-qwen-review-v1.json')),
             'limitations':'Proves completed bounded execution, artifact verification and cache replay. Final semantic review and readiness decision still require inspecting the resulting questions/reviews.'}
    write_json(Path('reports')/(root.name+'-replay.json'),receipt)
    print(json.dumps(receipt),flush=True)


if __name__=='__main__':
    main()
