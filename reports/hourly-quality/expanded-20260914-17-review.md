# Agent hourly inspection — September 14, 2026, 17:00 UTC

The revised complete-customer-history audit completed all 548 questions: 410 pass,
138 fail closed, including eight malformed evidence cases. Retained counts: 163
B2B single-call, 207 B2C single-call, 40 B2B multi-call. The 138 are not all manually
confirmed ambiguous; raw model disagreements and failure reasons remain available.
The original 548-question cohort and its RAG outcomes are preserved.

Recomputed and verified all 1,640 retained RAG outcomes with no new API calls.
Hybrid: 362/410 (88.3%); reranked: 401/410 (97.8%), including 367/370 single-call
and 34/40 multi-call. Oracle: 410/410; no-context: 0/410. The nine remaining reranked
errors were inspected: missing sources, truncated evidence, and answer selection/
attribution errors remain. No question was excluded for RAG correctness. Report
both the original and revised checkpoint: the revision was motivated by error
inspection and these are conditional construction diagnostics, not held-out accuracy.

Six fresh retained questions were sampled with seed 2026091417, two per stratum.
Exact source spans and same-opportunity grouping were verified. I inspected the
answers, evidence and both scope judgments: Nadya's CircuitWave partnership framing;
Ivan's proposal-versus-contract testimonial assessment; Jacqueline's budget and
four-day installation; Maya's TCO comparison; Emma Foster's warranty comparison;
Emma Harris's Porsche running costs versus Audi. Their stated facts are supported.
Substantive product/event qualifiers distinguish the relevant exchanges; no date/
title preambles were added. This sample does not prove corpus-wide unambiguity.

Recorded campaign API estimate: $729.02; conservative accounting: $739.45. The v2
scope audit cost $55.64; stopped v1 receipts and unknown usage reservations remain
included. VM/Turbopuffer invoices are not measured in these ledgers. Disk has about
30 GiB free; the 2,000-unit generation run uses 2.3 GiB, and immutable cache seeding
will hard-link responses rather than duplicate those bytes.

Approved full eligible scope: 14,916 units (4,033 B2B singles, 6,796 B2C singles,
4,087 B2B pairs). A zero-API full-plan smoke confirms those counts. The full run
retains v9 prompts/cache, adds the tested conservative speaker-absence precheck,
and requires source/citation plus dual reference-blind customer-scope review before
RAG. Historical scope failures are quarantined by ID/text. Full source and scope
review share one cumulative review allowance.

Allowances: cumulative generation $4,000 (including inherited $597.10), independent
review including scope $480, full RAG $230, reserve $100. The preflight campaign
upper envelope is $4,952.35, counting previous campaign costs once and retaining
unknown-request reservations. Forecasts remain uncertain; the caps do not promise
that every stage will fit. Hourly agent checks can diagnose/adjust within the shared
ceiling, but there is no automatic cap increase. Full workflow and supplemental
hourly timer will now be launched from the recorded assessment.

Next assistant inspection: 18:00 UTC, with live progress, costs, disk, and a fresh
quality sample. Tracking: public full-run issue #4 and private supervision issue #7.
