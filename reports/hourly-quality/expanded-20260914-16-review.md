# Agent hourly inspection — September 14, 2026, 16:00 UTC

The expanded workflow completed at 15:27 UTC. All 548 frozen questions have all
four outcomes (2,192 total), with exact context/coverage verification. Hybrid:
475/548 (86.7%); reranked: 519/548 (94.7%), including 477/494 single-call and 42/54
multi-call. Oracle: 548/548; no-context: 0/548. RAG API estimate $32.584. Campaign
recorded API estimate before the new diagnostic: $635.47, conservative $642.37.
There are 124 RAG requests without usage, principally rate-limit retries; keep
reservations rather than treating them as free. VM/Turbopuffer bills are excluded.

Full expansion is held despite encouraging accuracy. Source inspection found a
within-customer ambiguity defect: extracting one answer per source group can miss
other complete answers within that group. Hidden annotated call IDs must not define
what an unqualified "the call" or "the two calls" means. Full-source oracle
performance cannot detect this defect because it receives only the annotated calls.

Source-confirmed cases:
- Marcus Nguyen/Quantum Designs has three same-opportunity calls on Oct 19–21,
  with review-materials, schedule-meeting, and coordinate-demo commitments. The
  question says "across the two calls" without identifying which pair.
- Samuel/Aiden Clark has same-opportunity calendar-invite and later information,
  dealership-visit, and follow-up commitments. The question names the Tesla
  opportunity but not which next-step event. The RAG answer's extra calendar invite
  is source-supported and deserves an ambiguity/incomplete-reference audit.

Six further frozen questions were sampled with seed 2026091416, excluding prior
hourly samples. This draw is independent of RAG correctness. All exact evidence
spans were checked and all six gold answers have support in their annotated calls:
Marcus's meeting/demo; Jamal's scalability development; Chidi's documentation and
next-week follow-up; Monique's first-quarter support reassessment/end-week contract;
Emily's two vehicle prices and maintenance price; Zara's competitor-process comment
and Friday demo. Marcus is the confirmed ambiguity case above; Chidi's unqualified
"after the call" also requires complete-history checking. No population error rate
is inferred from six samples.

A new diagnostic applies the same reference-blind alternative-answer extraction
and Qwen verification to every one of the 548 questions, expanding to all calls
with matching account/lead IDs. It uses no RAG outcomes, changes no cohort files,
and preserves malformed evidence separately from substantive ambiguity decisions.
It is live as salestranscriptqa-scope-audit.service (PID 473166), initially capped
at $30 and included in shared campaign accounting. Initial diagnostic receipts
include a source-grounded rejection of Marcus's question. Audit reliability and
cost still need inspection before making this a production acceptance gate.

Tracking: https://github.com/Endgame-Labs/SalesTranscriptQA/issues/6.
The full run remains unapproved. Next assistant inspection: 17:00 UTC; continue
bounded quality diagnosis before then. No original question/evidence was rewritten.

Follow-up during this inspection: the diagnostic reproduced GLM's existing
single-line equal-endpoint convention. Added and tested the same bounded
normalization used by v9 (start==end becomes one in-bounds line), retaining the raw
provider receipt and an explicit repair record. No other span is changed. The
service was intentionally stopped and resumed from cached requests as
salestranscriptqa-scope-audit-v2.service with a $75 cumulative allowance, because
complete account histories make Qwen review more expensive than gold-only review.
In-flight requests interrupted by the restart retain conservative reservations;
unknown usage must not be reported as free. Three targeted tests pass. This remains
a diagnostic; no accepted cohort or generation prompt has changed.
