import concurrent.futures
import pytest
from salestranscriptqa.transport import Transport, PRIMARY, BudgetExceededError


def test_concurrent_attempt_reservations_and_unknown_usage(tmp_path):
    transport=Transport(tmp_path,budget_usd=0.0035)
    payload={'max_tokens':4096,'messages':[{'content':'hello'}]}
    def reserve(i):
        try:
            transport.start_attempt(str(i),str(i),'test',PRIMARY,0,payload)
            return True
        except BudgetExceededError:
            return False
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(reserve,range(4)))
    assert sum(results)==1
    with transport.db() as db:
        # An interrupted request's unknown usage retains its reservation.
        db.execute("UPDATE attempts SET status='interrupted'")
    assert not reserve(5)
    with transport.db() as db:
        # Known usage replaces the conservative reservation, freeing unused allowance.
        db.execute('UPDATE attempts SET estimated_usd=0.0001')
    assert reserve(6)


def test_budget_failure_does_not_create_running_attempt(tmp_path):
    transport=Transport(tmp_path,budget_usd=0)
    with pytest.raises(BudgetExceededError):
        transport.start_attempt('a','k','test',PRIMARY,0,{'max_tokens':4096})
    with transport.db() as db:
        assert db.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]==0
