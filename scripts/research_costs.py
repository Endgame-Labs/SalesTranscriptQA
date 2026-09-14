"""Report metered prompt-research usage from unique run databases, never summed reports."""
import json
import sqlite3
from pathlib import Path

prefixes=('natural-','ambiguity','answer-ambiguity','blind-','conflict-','group-consistency','sales-')
rows=[]
seen=set()
for path in sorted(Path('runs').glob('*/progress.sqlite')):
    if not path.parent.name.startswith(prefixes) or path.resolve() in seen:
        continue
    seen.add(path.resolve())
    with sqlite3.connect(path) as db:
        cost,unknown,running=db.execute("SELECT COALESCE(SUM(estimated_usd),0),SUM(estimated_usd IS NULL AND status!='running'),SUM(status='running') FROM attempts").fetchone()
    rows.append({'run':path.parent.name,'estimated_usd':cost,'unmetered_terminal_attempts':unknown or 0,'running_or_stale_attempts':running or 0})
result={'runs':rows,'estimated_usd_total':sum(r['estimated_usd'] for r in rows),'research_budget_usd':1000,
        'limitations':'Recorded Fireworks estimates only, not invoice; unknown/interrupted usage may be omitted. Excludes pre-research full generation and RAG evaluation. Reservations are conservative spending controls, not API charges.'}
print(json.dumps(result,indent=2))
