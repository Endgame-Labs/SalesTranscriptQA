# Agent hourly inspection — September 14, 2026, 06:00 UTC

The generation service is active/running under PID 436535. At the inspection,
439/2000 units were complete: 155 preliminary accepted and 284 rejected.
Recorded campaign Fireworks spend was $139.76; including pending reservations,
the conservative estimate was $140.18. These are API usage estimates, excluding
VM/Turbopuffer invoices and older pre-campaign experiments. The $850 generation
guard remains within the shared $5,000 campaign ceiling.

The ledger had 35,287 successful attempts, 20 malformed-output retries (HTTP 200),
and 16 running requests. 1,147 requests started in the preceding five minutes;
the oldest active request was 6.2 seconds old. No HTTP 429 or server errors were
recorded. Disk had 32.3 GiB free. No restart or intervention was warranted.

Six new seeded preliminary candidates were sampled, two per permitted stratum,
excluding both earlier hourly samples (seed 2026091406). I inspected the quoted
source passages with neighboring dialogue and identifying metadata, and checked
every evidence character span against the original transcript. All spans matched.
The accompanying sample and gates files preserve exact results.

- EcoTech multi-call: prices and deployment timeline are grounded in separate
  calls within the same opportunity. Coherence and independent source review
  pass; the unanimous necessity gate rejects. DeepSeek's structured verdict is
  false, but its explanation reverses itself and concludes that both sources
  are necessary. GLM returns true with exclusive facts. This is a likely
  conservative verifier false negative, not evidence of an unsupported answer.
  Preserve the fail-closed result; do not override it from the explanation.
- TechFusion multi-call: competitor shortcomings plus current discounts are
  grounded, but the coherence gate rejects the combined lookups. Independent
  source review passes. This candidate should not become final through factual
  review alone.
- InnoBuild single-call: a focused competitor-flexibility question with a concise
  source-supported answer. Both gates pass.
- Nova Healthcare single-call: combines customer priorities and vendor update
  positioning. Coherence rejects; source review passes. The coherence rationale
  incorrectly calls these different customer accounts (TechPulse is the vendor),
  so its explanation is unreliable even though the combined request merits
  scrutiny. Also, “top priority” is slightly stronger than the transcript's “big
  priorities.” Keep the rejection; no manual rewrite or acceptance.
- Emma B2C: the explicitly scoped four-item package total is $159,299.96, matching
  both the transcript and arithmetic. The product list identifies the requested
  quote rather than a mechanical call-date/title preamble. Both gates pass.
- Jack B2C: interest in the Model S and a next-day discovery meeting are supported;
  the adjacent customer agreement and rep confirmation establish scheduling.
  Both gates pass.

All six independent source reviews pass, but only three pass all applicable
final gates in this diagnostic. This is a small stratified sample, not a cohort
acceptance-rate estimate. Verifier false negatives and contradictory explanations
remain limitations to assess at the completed checkpoint; they do not justify
loosening the frozen protocol mid-run. No production prompts, gates, or labels
were changed. The prepared full workflow remains unapproved and unstarted.

Next actual assistant inspection: September 14, 2026, 07:00 UTC.
