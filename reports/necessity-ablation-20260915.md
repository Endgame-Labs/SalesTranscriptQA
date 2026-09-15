# Source-isolation necessity diagnostic — September 15, 2026

Production gate and cohort selection are unchanged. This diagnostic is not approved
as a replacement or a rescue path. Ledger: runs/sales-full-v2-necessity-ablation-diagnostic-v1.
Recorded API cost: $0.02338975, included in the shared campaign ceiling.

## Trigger and method

Hourly audits identified source-confirmed DeepSeek errors: SkyTech's one-week
integration timeline and TechWave's PulseSim comparison were attributed to the
wrong source; TrueNorth's separate answer parts were mistaken for single-source
sufficiency. Inspection of saved requests confirmed correct, separate source
payloads; this was not a harness source-mixing bug.

The diagnostic GLM extractor receives one call and the question, never gold or the
other call. It returns claims with exact contiguous quotations. Mechanical checks
require every quote to occur in its source. Qwen compares the independently
extracted claims with the reference, assessing each source's complete coverage,
union coverage, and coherence. Malformed/ungrounded output fails closed. No
semantic retries or production gate changes. Extraction omissions can falsely
suggest necessity; exact quotes alone do not prove claim entailment.

Six deliberately selected regression examples: three previous DeepSeek negatives
(SkyTech, TechWave, TrueNorth), one accepted comparison (Laila/Pedro), and two
manual weak-necessity holds (BioPulse, UrbanTech). This is not a random accuracy
sample. All six returned valid output and supports_necessity=true.

## Findings

Source isolation recovered the split facts for SkyTech and TechWave, but did not
solve attribution-driven false necessity. UrbanTech's later extractor independently
returned BOTH early-adoption feedback and Adaptive Design Solutions. Nevertheless,
Qwen called that source incomplete because it could not supply the acknowledgment
as an initial-call fact. This contradicts the diagnostic instruction to evaluate
substantive information rather than require first/later attribution. BioPulse's
later call recounts discovery positioning, but the judge again insists on separate
historical attribution. These are the same weaknesses manual inspection flagged.

TrueNorth's deployment/security combination was called coherent; that remains a
judgment question, separate from the logical error in the old necessity verdict.
All-positive output does not establish a reliable replacement. No quarantines
were lifted and no production decisions were re-run or overwritten.

A stronger future protocol would need independently validated factual requirements
and a paraphrase/attribution challenge set, tested on both redundant-call controls
and genuinely distinct-call positives. Do not tune acceptance using RAG outcomes.
The final construction report must disclose both false-negative reviewer errors
and weak-necessity false positives, plus conservative selection's effect on yield.

## Validation

Four tests pass: per-source/reference isolation, fabricated quote rejection,
one-source complete-answer rejection, and duplicate coverage rejection.
A first invocation stopped before its comparison because the new diagnostic's
Qwen price was not registered; fixed by registering the existing $2/$0.25/$6
rates. Resumption reused cached extraction requests. Raw receipts preserved.

Input: reports/necessity-ablation-20260915-input.json.
Results: reports/necessity-ablation-20260915-results.json.
Operational tracker: https://github.com/dorkitude/SalesTranscriptQA-rag-evaluation/issues/7.
