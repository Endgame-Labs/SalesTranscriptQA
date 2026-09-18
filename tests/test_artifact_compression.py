import json
import os
import sqlite3

import pytest

from salestranscriptqa.artifacts import archive_requests, read_json_artifact


def test_archive_preserves_exact_bytes_and_shared_checkpoint(tmp_path):
    (tmp_path / "requests").mkdir()
    (tmp_path / "progress.json").write_text('{"complete": true}')
    original = b'{"parsed": {"answer": "hello"}, "padding": "' + b'x'*10000 + b'"}\n'
    one = tmp_path / 'requests/one.json'
    one.write_bytes(original)
    shared = tmp_path / 'requests/shared.json'
    shared.write_bytes(original)
    os.link(shared, tmp_path / 'checkpoint.json')
    with sqlite3.connect(tmp_path/'progress.sqlite') as db:
        db.execute('CREATE TABLE attempts(id TEXT,artifact TEXT,status TEXT)')
        db.executemany('INSERT INTO attempts VALUES(?,?,?)',[('one','requests/one.json','ok'),('shared','requests/shared.json','ok')])
    receipt = archive_requests(tmp_path, 1000000)
    assert receipt['artifacts'] == 1 and receipt['freed_bytes'] > 9000
    assert not one.exists() and shared.read_bytes() == original
    with sqlite3.connect(tmp_path/'progress.sqlite') as db:
        path = db.execute("SELECT artifact FROM attempts WHERE id='one'").fetchone()[0]
    assert read_json_artifact(tmp_path/path) == json.loads(original)
    assert len((tmp_path/'request-compression.jsonl').read_text().splitlines()) == 1
    assert archive_requests(tmp_path, 1000000)['artifacts'] == 0


def test_incomplete_generation_is_not_modified(tmp_path):
    (tmp_path/'progress.json').write_text('{"complete": false}')
    with pytest.raises(ValueError, match='completed'):
        archive_requests(tmp_path, 10000)
