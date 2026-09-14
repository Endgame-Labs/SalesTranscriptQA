# Natural-question validation review

The natural-v2 review sample remains unchanged. A new `NaturalNext` validation revision (`natural-pilot-v3`) excludes the two-call-only quality flags from single-call acceptance. B2B multi-call candidates must still pass both flags. Legacy Pilot, Full, and Natural v2 preserve their original required flags and cached decisions. A regression test uses the observed false-two-call-flags failure pattern; 28 tests pass.

## Directly checked examples

- Review item 18 asks the extended warranty price. Original source `b2c:a05Ws000005SdWcIAK` states $1,299.99; alternate selected source `b2c:a05Ws000005STyqIAG` also states $1,299.99. The existing selector explicitly returned ambiguous=false, but code rejected the different source ID. This is an exact-source validation error, not evidence of an incorrect answer. Checking these two transcripts does not establish global price consistency.
- Review item 13 asks the Volvo XC60/Lexus RX 350 demonstration time without customer context. Original source `b2c:a05Ws000005SZOFIA4` confirms Saturday at noon; competing source `b2c:a05Ws000005SXxTIAW` confirms Friday afternoon. This is an actual conflicting-answer ambiguity.

## Required ambiguity redesign

Compare the answers supported by competing sources, not merely the selected source IDs. Require exact evidence for each proposed alternative or conflict. Retain original verified supporting evidence while representing alternative sufficient evidence separately. An independent judge must verify question scope and answer equivalence; different wording alone is not a conflict. Reject customer-specific questions whose omitted scope permits incompatible answers. Repeated company-wide facts can be valid but should not dominate the question distribution. Broader competitor retrieval is needed before claiming corpus-wide ambiguity resolution; the current top-ten TF-IDF pool is not sufficient proof.

No ambiguity gate has yet been relaxed or replaced. Publication and full evaluation remain paused. B2C multi-call questions are excluded from future generation; B2B may retain both classes. Initial-discussion/follow-up phrasing is allowed occasionally, not mandated.
