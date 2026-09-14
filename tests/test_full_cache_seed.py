import hashlib
import importlib.util
import json
import sqlite3
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('seed_full_run',Path(__file__).parents[1]/'scripts/seed_full_run.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def fixture(tmp_path):
    src=tmp_path/'source';src.mkdir()
    for d in ['reviewed','requests','units','candidates']:(src/d).mkdir()
    (src/'reviewed/questions.json').write_text('[]')
    for name,value in [('progress.json',{'complete':True}),('workflow.json',{'stage':'complete'}),('config.json',{'version':'sales-questions-v9-line-evidence'})]:
        (src/name).write_text(json.dumps(value))
    (src/'requests/a.json').write_text('{"parsed":true}')
    (src/'units/u.json').write_text('{"status":"accepted"}')
    (src/'candidates/c.json').write_text('{"status":"accepted"}')
    with sqlite3.connect(src/'progress.sqlite') as db:
        db.executescript('CREATE TABLE attempts(id TEXT, status TEXT, estimated_usd REAL, artifact TEXT); CREATE TABLE jobs(status TEXT);')
        db.execute('INSERT INTO attempts VALUES(?,?,?,?)',('a','ok',.25,'requests/a.json'))
    review=tmp_path/'review.json';review.write_text(json.dumps({'approved_for_full':True,'question_sha256':hashlib.sha256(b'[]').hexdigest()}))
    return src,review

def test_reuses_attempt_identity_and_cost_without_copying_source_plan(tmp_path):
    src,review=fixture(tmp_path);dest=tmp_path/'full'
    receipt=module.seed(src,dest,review)
    assert receipt['carried_forward_estimated_usd']==.25 and receipt['inherited_units']==1
    assert not (dest/'source-plan.json').exists()
    with sqlite3.connect(dest/'progress.sqlite') as db:assert db.execute('SELECT id FROM attempts').fetchone()[0]=='a'
    (dest/'candidates/c.json').write_text('changed')
    assert json.loads((src/'candidates/c.json').read_text())['status']=='accepted'

def test_refuses_unapproved_or_unfinished_source(tmp_path):
    src,review=fixture(tmp_path)
    (src/'workflow.json').write_text('{"stage":"generation"}')
    with pytest.raises(ValueError,match='complete'):module.seed(src,tmp_path/'full',review)
    assert not (tmp_path/'full').exists()
