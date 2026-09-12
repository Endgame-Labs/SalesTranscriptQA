# SalesTranscriptQA pilot

Automatically generated and automatically validated; no human review or calibration.

- Accepted: **200 questions**, 50 per domain/class.
- Retrieval corpus: **10,829 calls**, all extracted verbatim.
- Candidate attempts in final run: **256**.
- Median question/answer length: **22.5 / 13.0 words**.
- Pilot API cost estimate: **$0.8859**.
- All development API cost estimate, including replaced runs and smoke checks: **$0.9196**.
- Attempts with unknown usage: **0**; these may incur unaccounted charges.
- Linear estimate: **$4.43 per 1,000 accepted questions**, **$44.30 per 10,000**, at the observed domain/class mix and rejection rate. These are token-priced estimates, not invoices or corpus-wide generation commitments. Yield may change as eligible source groups are exhausted.

See [machine-readable report](pilot.json) for per-stage/model/run quantities and costs. Local extraction and lexical retrieval used this VM; no separate GPU, embedding API or vector database charge was incurred. VM overhead is not priced in these API totals. Hugging Face storage charges, if any, are not included.

The first run rejected many retyped evidence quotes. The final run asks the generator to select line numbers; code copies the original dialogue and computes Unicode offsets. No source text is normalized. All retained questions passed independent answering, no-context checks, source selection against full-domain TF-IDF hard negatives, quality and fresh final audits. Two-call questions also passed each single-call ablation and a factual necessity check.

These model checks do not establish human-verified accuracy, exhaustive evidence uniqueness, or rigorous logical necessity. Calls are synthetic and short; questions are generated from known sources. This pilot was used to develop the pipeline and is not an untouched test set. A .9 TF-IDF cosine duplicate gate and exact duplicate checks passed. Source-pair eligibility is not proof that a useful two-call question exists.

[Implementation and follow-up issue](https://github.com/Endgame-Labs/SalesTranscriptQA/issues/1).
