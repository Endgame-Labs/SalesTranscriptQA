"""Seed a fresh full-run directory from an approved, complete expansion checkpoint.

Copies terminal unit/candidate records and backs up SQLite; immutable response JSON
files are hard-linked when possible. It never calls a model or starts generation.
"""
import argparse
import fcntl
import hashlib
import json
import os
import shutil
import sqlite3
from pathlib import Path
from salestranscriptqa.corpus import write_json


def seed(source,destination,approval):
    source,destination=Path(source),Path(destination)
    review=json.loads(Path(approval).read_text())
    if destination.exists():raise ValueError('Destination must be new; preserve existing run directories')
    frozen=source/'reviewed/questions.json'
    if review.get('approved_for_full') is not True or review.get('question_sha256')!=hashlib.sha256(frozen.read_bytes()).hexdigest():
        raise ValueError('Explicit checkpoint assessment must approve these exact reviewed questions')
    with (source/'pilot.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        progress=json.loads((source/'progress.json').read_text())
        workflow=json.loads((source/'workflow.json').read_text())
        config=json.loads((source/'config.json').read_text())
        if not progress.get('complete') or workflow.get('stage')!='complete':raise ValueError('Source workflow must be complete')
        if config.get('version')!='sales-questions-v9-line-evidence':raise ValueError('Unexpected generation protocol')
        with sqlite3.connect(f'file:{source}/progress.sqlite?mode=ro',uri=True) as db:
            if db.execute("SELECT COUNT(*) FROM attempts WHERE status='running'").fetchone()[0]:raise ValueError('Source contains unfinished API attempts')
            if db.execute("SELECT COUNT(*) FROM jobs WHERE status='running'").fetchone()[0]:raise ValueError('Source contains unfinished candidate jobs')
            counts=dict(db.execute('SELECT status,COUNT(*) FROM attempts GROUP BY status').fetchall())
            cost=db.execute('SELECT COALESCE(SUM(estimated_usd),0) FROM attempts').fetchone()[0]
            for (artifact,) in db.execute('SELECT artifact FROM attempts WHERE artifact IS NOT NULL'):
                p=Path(artifact)
                if p.is_absolute() or '..' in p.parts or not (source/p).is_file():raise ValueError('Invalid cached response artifact')
            staging=destination.with_name(destination.name+'.importing')
            staging.mkdir(parents=True,exist_ok=False)
            # Each provider response has a unique attempt UUID and is immutable thereafter.
            linked=0;copied=0
            def immutable(src,dst):
                nonlocal linked,copied
                try:os.link(src,dst);linked+=1
                except OSError:shutil.copy2(src,dst);copied+=1
            if (source/'requests').exists():shutil.copytree(source/'requests',staging/'requests',copy_function=immutable)
            for name in ['candidates','units']:
                shutil.copytree(source/name,staging/name)
            shutil.copy2(source/'config.json',staging/'config.json')
            with sqlite3.connect(staging/'progress.sqlite') as target:
                db.backup(target)
                assert target.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            receipt=dict(source=str(source.resolve()),source_config_sha256=hashlib.sha256((source/'config.json').read_bytes()).hexdigest(),
                approved_questions_sha256=review['question_sha256'],checkpoint_review=review,
                copied_attempt_counts=counts,carried_forward_estimated_usd=cost,
                inherited_units=len(list((staging/'units').glob('*.json'))),linked_response_files=linked,copied_response_files=copied,
                accounting='Inherited attempt IDs and usage are the same spend, not new charges. Deduplicate by attempt ID when summing source and destination ledgers.',
                scope='Cache seed only; full source plan and execution not started')
            write_json(staging/'cache-import.json',receipt)
            staging.rename(destination)
            return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--checkpoint-review',type=Path,required=True)
    a=p.parse_args();print(json.dumps(seed(a.source,a.destination,a.checkpoint_review)))
