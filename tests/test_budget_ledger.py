import concurrent.futures
import sqlite3

import pytest

from salestranscriptqa.budget_ledger import install
from salestranscriptqa.transport import Transport, PRIMARY, BudgetExceededError


def assert_total(db):
    actual = db.execute('SELECT usd FROM budget_total').fetchone()[0]
    expected = db.execute('SELECT COALESCE(SUM(COALESCE(a.estimated_usd,r.worst_usd,0)),0) FROM attempts a LEFT JOIN budget_reservations r ON a.id=r.id').fetchone()[0]
    assert actual == pytest.approx(expected, abs=1e-9)


def test_legacy_migration_and_all_mutations(tmp_path):
    t = Transport(tmp_path)
    with t.db() as db:
        for row in db.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall():
            db.execute('DROP TRIGGER '+row[0])
        db.execute('DROP TABLE budget_total')
        db.execute("INSERT INTO attempts(id,estimated_usd) VALUES('known',2),('unknown',NULL)")
        db.execute("INSERT INTO budget_reservations VALUES('known',10),('unknown',3)")
    with t.db() as db:
        install(db)
        assert_total(db)
    with t.db() as db:
        install(db)  # reopening cannot duplicate the starting total
        assert_total(db)
        for sql in [
            "UPDATE attempts SET estimated_usd=1 WHERE id='unknown'",
            "UPDATE attempts SET estimated_usd=NULL WHERE id='known'",
            "UPDATE budget_reservations SET worst_usd=4 WHERE id='known'",
            "DELETE FROM budget_reservations WHERE id='known'",
            "INSERT INTO budget_reservations VALUES('known',5)",
            "DELETE FROM attempts WHERE id='unknown'",
            "INSERT INTO budget_reservations VALUES('late',7)",
            "INSERT INTO attempts(id) VALUES('late')",
            "INSERT INTO attempts(id) VALUES('first')",
            "INSERT INTO budget_reservations VALUES('first',8)",
        ]:
            db.execute(sql)
            assert_total(db)
    with t.db() as db:
        before=db.execute('SELECT usd FROM budget_total').fetchone()[0]
        db.execute("UPDATE attempts SET estimated_usd=999 WHERE id='late'")
        db.rollback()
        assert db.execute('SELECT usd FROM budget_total').fetchone()[0] == before


def test_concurrent_independent_transports_respect_shared_limit(tmp_path):
    a,b=Transport(tmp_path,budget_usd=.0035),Transport(tmp_path,budget_usd=.0035)
    def reserve(i):
        try:
            (a if i%2 else b).start_attempt(str(i),str(i),'test',PRIMARY,0,{'max_tokens':4096})
            return True
        except BudgetExceededError:
            return False
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        assert sum(pool.map(reserve,range(32))) == 1
    with a.db() as db:
        assert_total(db)
