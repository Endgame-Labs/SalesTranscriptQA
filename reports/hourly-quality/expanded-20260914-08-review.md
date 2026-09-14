# Agent hourly inspection — September 14, 2026, 08:00 UTC

The generation service is active/running under PID 436535. At inspection,
805/2000 source units were complete: 291 preliminary accepted and 514 rejected.
Campaign Fireworks spend was $245.31 recorded, or $245.78 including in-flight
reservations. The hourly source/gate/citation checks and corrected-citation probe
added $0.06032644. VM/Turbopuffer invoices and older pre-campaign experiments are
excluded from these API estimates. The $850 generation guard remains unchanged
within the shared $5,000 ceiling.

The ledger had 62,339 successful attempts, 29 malformed-output retries (HTTP 200),
and 16 running requests. 1,194 requests started in the preceding five minutes;
the oldest active request was 16.4 seconds old. No HTTP 429/server errors were
recorded. Disk had 31.9 GiB free. Generation is healthy; no restart was needed.

Six new preliminary candidates were sampled with seed 2026091408, two per
permitted stratum and excluding prior hourly samples. I inspected their source
passages, neighboring dialogue and identifying metadata. Every stored character
span matched the transcript, but one span did not support its assigned claim.

- Circuit Dynamics multi-call: initial scalability/integration challenges and
  later onboarding products are supported within the same opportunity. Both
  necessity judges, coherence, source review, and the new citation audit pass.
- Pioneer Envisions multi-call: source/citation support and coherence pass;
  necessity rejects on model disagreement. DeepSeek incorrectly says the second
  call also states the customer's past competitor-support problem. Inspection
  of the full second call shows it does not. GLM identifies the exclusive facts
  correctly. Retain the conservative rejection and record this false-negative
  limitation for the checkpoint; do not override the model verdict.
- Ismail/Sarah single-call: the gold answer is present in the transcript, but
  evidence [11,12) contains only Ismail requesting mission-critical assistance.
  Sarah's dedicated-team promise is on the next, uncited line. All existing
  full-source gates pass, demonstrating a citation-validation gap. The new
  quoted-evidence audit rejects it.
- InnoSphere single-call: eight CryptSecure Core units, 5% discount, around $4,788
  is supported and preserves the approximate-price qualification. All gates pass.
- Ella B2C: accurately reports the negotiation question and Nadia's response
  about trust and market-priced packages, without inventing a yes/no negotiation
  policy. All gates pass.
- Luisa B2C: $323,196 budget and nine-day installation/delivery requirement are
  explicitly supported and scoped to the specified package. All gates pass.

## Intervention: validate the cited passages separately

The citation defect is tracked in [issue 5](https://github.com/Endgame-Labs/SalesTranscriptQA/issues/5).
Independent review now requires a separate `quoted-evidence-audit-v1` Qwen check
that sees cited passages and metadata but no uncited dialogue. It must cover
every evidence item and affirm support for the complete gold answer. Generation
exports now include evidence, so both expanded and full workflows apply this
check before freezing their reviewed cohort. Original candidates/transcripts
remain unchanged. This is a post-generation evidence-validation correction, not
a change to the v9 question-generation prompt.

The six-candidate replay rejected only the erroneous citation. A controlled
example extending that citation to include Sarah's response passed; the raw
candidate was not edited. The [regression artifact](../citation-audit-regression-20260914.json)
preserves both verdicts and spans. The test suite passed 63 tests.

Four of six sampled candidates pass all final gates after the citation fix,
including one multi-call question. This is a small diagnostic sample, not a
cohort-wide yield estimate. Full expansion remains conditional on completed
generation, review, RAG, and budget assessment. Next assistant inspection: 09:00 UTC.
