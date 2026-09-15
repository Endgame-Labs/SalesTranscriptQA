# Citation requirements diagnostic — September 15, 2026

**Not promoted. Production citation protocol, generation prompt and cohort decisions
are unchanged.** The candidate still accepts unsupported agreement, ranking and
uncertainty claims, and rejects a previously accepted control for contextual details.

## Why this probe

Hourly manual checks repeatedly find that the citation judge accepts a question
about an agreed purchase when the quoted span contains interest and a price but
ends before agreement. The existing prompt already says to reject missing facts,
uncited replies, lost uncertainty and time qualifiers. This probe explicitly asks
Qwen to enumerate requirements implied by question plus gold answer, treat
answer_claim as an assertion rather than a source, and attach exact quote substrings.
It distinguishes contextual locators from requested commitments. No full uncited
dialogue, baseline outcome or manual label is supplied to the model.

## Reproduction and artifacts

Run from repository root:

```sh
uv run python scripts/probe_citation_requirements.py   reports/citation-requirements-probe-20260915-input.json   --run-dir runs/sales-full-v2-citation-requirements-probe-v1   --output reports/citation-requirements-probe-20260915-results.json
```

The input freezes twelve selected development cases from prior hourly audits:
eight manual failures and four accepted controls. Baselines are the saved original
citation-gate decisions, not rerun measurements. The results include exact prompt,
model, all verdicts and label comparisons. Immutable request receipts and SQLite
usage are in the run directory. Existing transport provides caching, bounded retries,
exponential rate-limit backoff and a $1 diagnostic ceiling. Actual configured-rate
API estimate **$0.061266**, included in the shared campaign ledger by run prefix.

## Results

| Decision compared to the twelve manual labels | Agreement |
|---|---:|
| Original citation gate | 6/12 |
| Candidate model's answer_supported (before output validation) | 7/12 |

This is a deliberately selected failure/control set, not a population accuracy
estimate. The difference is not enough to support production replacement.

- Newly catches Mohammad's missing purchase-confirmation anchor and Sophia's
  uncited model year. Continues rejecting Isabelle's missing agreement and
  Khalid's missing salesperson reply, which the original gate already rejected.
- Still semantically passes Noah's unsupported most-important ranking, Laura's
  question-only ranking, Emil's agreed-purchase premise despite only interest
  being quoted, and Mia's loss of might before the competitor allegation.
- Incorrectly rejects the Linda budget/total control under the existing labeling
  convention because the quoted spans omit product quantities used as question
  context. That contextual-versus-asserted boundary needs an explicit policy
  before broadening the production gate.
- Seven outputs fail exact-quote/schema validation. Some invent punctuation or
  paraphrase quote substrings; others introduce metadata-only requirements with
  absent or JSON-formatted quotes. Rejection from an invalid output is not evidence
  the semantic defect was detected. In particular, Emil and Laura are marked
  passed=false only because of validation, while their semantic verdicts are true.
- Of the four positive controls, the semantic candidate accepts the Kaito proposed
  timeline, Mohammed's requested meeting topic and Olivia's quote/follow-up; the
  exact-quote checker only accepts Olivia. This validator/output contract also
  needs work before production use.

The rationale for Noah explicitly excuses escalation because it mirrors the
question; Mia's rationale acknowledges might but still calls the answer faithful.
These are model adjudication failures despite explicit instructions, not missing
source spans being accidentally sent to the model. No semantic retries were used
and no labels or cohorts were changed to make the diagnostic look successful.

## Next action

Keep the existing production gate and the hourly manual exclusions. Preserve this
negative result for the final report; do not claim that more detailed instructions
solve the citation-review problem. Any replacement needs fresh controls and
consistent treatment of contextual locators, agreement premises and uncertainty.
