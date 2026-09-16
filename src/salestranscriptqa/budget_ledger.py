"""Incremental conservative allowance, kept atomic with the underlying receipts."""


def install(db):
    # One migration transaction: no worker can reserve against a partial rollup.
    db.execute('BEGIN IMMEDIATE')
    db.execute('CREATE TABLE IF NOT EXISTS budget_total(id INTEGER PRIMARY KEY CHECK(id=1), usd REAL NOT NULL)')
    if db.execute('SELECT 1 FROM budget_total WHERE id=1').fetchone():
        return
    db.execute('INSERT INTO budget_total SELECT 1, COALESCE(SUM(COALESCE(a.estimated_usd,r.worst_usd,0)),0) FROM attempts a LEFT JOIN budget_reservations r ON a.id=r.id')
    for event, expression in [
        ('INSERT', 'COALESCE(NEW.estimated_usd,(SELECT worst_usd FROM budget_reservations WHERE id=NEW.id),0)'),
        ('DELETE', '-COALESCE(OLD.estimated_usd,(SELECT worst_usd FROM budget_reservations WHERE id=OLD.id),0)'),
        ('UPDATE OF estimated_usd', 'COALESCE(NEW.estimated_usd,(SELECT worst_usd FROM budget_reservations WHERE id=NEW.id),0)-COALESCE(OLD.estimated_usd,(SELECT worst_usd FROM budget_reservations WHERE id=OLD.id),0)'),
    ]:
        name = event.split()[0].lower()
        db.execute(f'CREATE TRIGGER budget_attempt_{name} AFTER {event} ON attempts BEGIN UPDATE budget_total SET usd=usd+({expression}) WHERE id=1; END')
    # Reservations may be inserted before or after their attempts; known usage wins.
    for event, expression, alias in [
        ('INSERT', 'NEW.worst_usd', 'NEW'),
        ('DELETE', '-OLD.worst_usd', 'OLD'),
        ('UPDATE OF worst_usd', 'NEW.worst_usd-OLD.worst_usd', 'NEW'),
    ]:
        name = event.split()[0].lower()
        db.execute(f'CREATE TRIGGER budget_reservation_{name} AFTER {event} ON budget_reservations WHEN EXISTS(SELECT 1 FROM attempts WHERE id={alias}.id AND estimated_usd IS NULL) BEGIN UPDATE budget_total SET usd=usd+({expression}) WHERE id=1; END')
