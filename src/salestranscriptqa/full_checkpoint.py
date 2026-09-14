"""Checkpoint selection and cumulative budget checks for the supervised full run."""
import math
import re
import unicodedata
from pathlib import Path


def question_key(text):
    return ' '.join(re.findall(r'\w+', unicodedata.normalize('NFKC', text).casefold()))


def reviewed_selection(questions, exported, reviews, exclusions):
    by_item = {q['item']: q for q in exported}
    if len(by_item) != len(exported) or len(reviews) != len(exported):
        raise ValueError('Independent review coverage mismatch')
    if len({r['item'] for r in reviews}) != len(reviews) or set(by_item) != {r['item'] for r in reviews}:
        raise ValueError('Independent review IDs do not match export')
    ids = [q['question_id'] for q in questions]
    if len(set(ids)) != len(ids) or set(ids) != {q['question_id'] for q in exported}:
        raise ValueError('Export does not match selected question IDs')
    excluded_ids = {q.get('question_id') for q in exclusions}
    excluded_text = {question_key(q['question']) for q in exclusions if q.get('question')}
    rejected = []
    allowed = set()
    for review in reviews:
        q = by_item[review['item']]
        quarantined = q['question_id'] in excluded_ids or question_key(q['question']) in excluded_text
        if review.get('passed') is True and not review.get('mechanical_locator_flags') and not quarantined:
            allowed.add(q['question_id'])
        else:
            rejected.append({**review, 'question_id': q['question_id'], 'prior_quarantine': quarantined})
    return [q for q in questions if q['question_id'] in allowed], rejected


def budget_envelope(report, limits, inherited, full_root, review_root, rag_root):
    """Bound all full-stage ceilings together; inherited calls were already billed.

    Stage limits are cumulative in their own ledgers, including cached generation.
    The reserve covers later diagnostics and unmetered infrastructure; it is an
    allowance, not an invoice estimate. Parallel paid jobs must not consume it
    without a fresh supervision check.
    """
    required = {'generation_usd', 'review_usd', 'rag_usd', 'reserve_usd'}
    if set(limits) != required or any(not math.isfinite(v) or v <= 0 for v in limits.values()):
        raise ValueError('Four finite positive stage/reserve allowances required')
    if limits['reserve_usd'] < 100:
        raise ValueError('Retain at least $100 for monitoring and unmetered costs')
    if limits['generation_usd'] < inherited:
        raise ValueError('Generation ceiling must include inherited costs')
    own = 0
    current = {'generation_usd': inherited, 'review_usd': 0, 'rag_usd': 0}
    lookup = {str(Path(full_root).resolve()): 'generation_usd', str(Path(review_root).resolve()): 'review_usd'}
    for row in report['generation_and_review']:
        key = lookup.get(str(Path(row['run']).resolve()))
        if key:
            value = row['incremental_recorded_usd'] + row['unknown_or_inflight_reservations_usd']
            own += value
            current[key] += value
    for row in report['rag']:
        if Path(row['run']).resolve() == Path(rag_root).resolve():
            own += row['conservative_guard_usd']
            current['rag_usd'] += row['conservative_guard_usd']
    if any(current[k] > limits[k] for k in current):
        raise ValueError('A full-run ledger has already exceeded its stage allowance')
    outside = report['conservative_fireworks_usd'] - own
    upper = outside + sum(limits.values()) - inherited
    if upper > min(5000, report['ceiling_usd']):
        raise ValueError(f'Combined campaign allowance ${upper:.2f} exceeds shared ceiling')
    return {'outside_full_ledgers_usd': outside, 'inherited_usd': inherited,
            'current_full_ledgers_usd': current, 'campaign_envelope_usd': upper,
            'limits': limits, 'reserve_is_not_invoice_estimate': True}
