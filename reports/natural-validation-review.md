# Natural-question validation review

The natural-v2 review sample remains unchanged. A new `NaturalNext` validation revision (`natural-pilot-v3`) excludes the two-call-only quality flags from single-call acceptance. B2B multi-call candidates must still pass both flags. Legacy Pilot, Full, and Natural v2 preserve their original required flags and cached decisions. A regression test uses the observed false-two-call-flags failure pattern; 28 tests pass.

## Directly checked examples

- Review item 18 asks the extended warranty price. Original source `b2c:a05Ws000005SdWcIAK` states $1,299.99; alternate selected source `b2c:a05Ws000005STyqIAG` also states $1,299.99. The existing selector explicitly returned ambiguous=false, but code rejected the different source ID. This is an exact-source validation error, not evidence of an incorrect answer. Checking these two transcripts does not establish global price consistency.
- Review item 13 asks the Volvo XC60/Lexus RX 350 demonstration time without customer context. Original source `b2c:a05Ws000005SZOFIA4` confirms Saturday at noon; competing source `b2c:a05Ws000005SXxTIAW` confirms Friday afternoon. This is an actual conflicting-answer ambiguity.

## Required ambiguity redesign

Compare the answers supported by competing sources, not merely the selected source IDs. Require exact evidence for each proposed alternative or conflict. Retain original verified supporting evidence while representing alternative sufficient evidence separately. An independent judge must verify question scope and answer equivalence; different wording alone is not a conflict. Reject customer-specific questions whose omitted scope permits incompatible answers. Repeated company-wide facts can be valid but should not dominate the question distribution. Broader competitor retrieval is needed before claiming corpus-wide ambiguity resolution; the current top-ten TF-IDF pool is not sufficient proof.

No ambiguity gate has yet been relaxed or replaced. Publication and full evaluation remain paused. B2C multi-call questions are excluded from future generation; B2B may retain both classes. Initial-discussion/follow-up phrasing is allowed occasionally, not mandated.

## Answer-based audit experiment (September 14)

Implemented an experimental answer-based check with deterministic evidence validation and cross-family verification. The first version requested exact quotes and produced seven invalid-evidence assessments in the 20-question/30-competitor review. The second requests numbered source lines and copies quotes in code; it produced 13 pool-consistent, 4 ambiguous, 2 invalid-evidence, and 1 verification-failed assessments. These are experimental outputs, **not approved QA counts**.

Critical regression: item 13's second-version assessment incorrectly returned consistent_in_pool even though the known Friday-afternoon conflict (`b2c:a05Ws000005SXxTIAW`) was present in the pool. Both proposer and verifier missed it. The same method correctly detected the conflict in the isolated two-call live regression. This larger-pool miss invalidates adoption of the current design as a production gate; passing the small regression is insufficient. Preserve both reports so the failure is reproducible.

Next implementation: reference-blind answer extraction on individual sources/small batches, followed by explicit evidence-grounded answer comparison, with the known conflict tested amid the full distractor pool. Do not weaken conflict handling or accept the provisional pool-consistent results. Existing production acceptance has not changed.

Recorded experiment costs: quote-based regression $0.00261845, quote-based 20-item review $0.22427915, indexed-evidence regression $0.00271623, indexed-evidence 20-item review $0.28225254 (total $0.51186637). Thirty-three deterministic tests pass; this does not imply the live larger-pool semantic regression passed.

## Reference-blind per-transcript regression (September 14)

Implemented `blind_ambiguity.py`: GLM extracts an answer from each transcript individually without the reference; DeepSeek verifies support without the reference; only afterward does a separate DeepSeek request compare extracted and reference answers. Deterministic aggregation preserves any verified conflict and treats missing/failed source reviews as inconclusive rather than consistent.

The first implementation combined support verification and reference comparison and failed both live regressions with inconclusive results (retained in `blind-ambiguity-regression-v1.json`). Separating those stages fixed both full-pool cases (`blind-ambiguity-regression-v2.json`):

- Item 13, 30 transcripts: 3 conflicting, 1 equivalent, 26 insufficient. The known Friday-afternoon conflict is explicitly extracted and retained; overall ambiguous.
- Item 18, 31 transcripts: 11 equivalent warranty-price answers, 20 insufficient; overall consistent in this pool.

Total recorded cost across both per-transcript trial revisions: $0.068262454. Existing suite: 35 passing tests; an additional reference-isolation regression passed with the two other blind-audit tests (3 tests). No production acceptance changes; full pilot review and multi-call extension remain necessary. No corpus-wide ambiguity guarantee.
