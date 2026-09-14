# Cost diagnostics during expanded generation

These probes do not change the running v9 generation protocol or its quality gates.

## Prompt-prefix caching

We replayed four distinct questions against each of three frequently reused source
groups using Qwen verification. Each group included positive and negative baseline
decisions. The two arms used identical JSON content with either question-first or
source-first key ordering, separate cache isolation keys, and session-affinity hints
following the [Fireworks prompt-caching documentation](https://docs.fireworks.ai/guides/prompt-caching).

Both arms reported **zero cached tokens** across 12 requests and 68,205 input tokens
per arm. Costs were $0.159696 and $0.159804 respectively. All 12 completeness
decisions agreed; the eight positive answer pairs were judged equivalent, costing
another $0.012292. Total diagnostic cost: **$0.331792**. This selected replay provides
no evidence of savings, so we did not adopt the ordering change. It does not explain
why cache hits were absent or establish behavior for other workloads.

The compact [probe results](source-prefix-cache-probe-v1.json) contain usage,
verdicts, and comparisons. Full source payloads remain in the local run manifest.

## Explicit speaker absence prototype

The offline prototype considers only exact known full speaker names in selected
grammatical positions. It falls back to model review for ambiguous, negated,
conditional, alternative, attendance, counting, and boolean questions. Any name
token occurring anywhere in the complete source metadata or dialogue also keeps
model review. Unicode normalization preserves accented-name matches.

The latest [saved-decision replay](absent-speaker-probe-v2.json) covers 9,086 Qwen
verifications, including 1,715 positive completeness decisions. The prototype
would skip 1,256 checks representing $11.9385905 of $93.10615 in verification costs
(12.8%). Every proposed skip had an original negative verdict; none of the positive
decisions would be removed. Four targeted tests cover partial names, metadata,
Unicode, aliases, generic speaker labels, and syntax fallbacks.

This is agreement with existing model decisions, **not proof of semantic safety**.
Unrecognized aliases, implicit references, or unhandled syntax could still make an
absence rule unsound. It is not enabled in production. Any adoption requires a
separate checkpoint assessment and protocol record; these savings are not included
in the current run's budget forecast. Earlier v1 results used a broader rule and
are retained only as diagnostic history.


## Complete-checkpoint speaker-absence review

The completed ledger contains 53,566 group verifier calls costing $540.53.
The conservative full-name absence rule would bypass 8,657 of those checks,
accounting for $83.46 of verifier spend (15.4% of this stage, 14.0% of all $597.10
generation spend; extraction savings are not included). Unlike the earlier partial
probe, there are 17 `complete=true` disagreements. Inspection shows the model
substituting another named person—e.g. Andreas for Mai Nguyen, Anwar for Chen Wei,
Jamal for Liu Wei, and Jorge for Pierre Fontaine—even though every token of the
required name is absent from the source group's metadata and dialogue. These are
not evidence that the requested person made the claim. The full raw disagreements
are retained in `absent-speaker-complete-checkpoint.json`.

An opt-in `--explicit-speaker-prefilter` is prepared, not enabled on the historical
checkpoint. It records deterministic insufficient groups with absent names,
preserves all partial-name/metadata matches, falls back on ambiguous syntax, and
records the policy in the immutable source plan. Output verification recomputes
each bypass from the original corpus. Cached completed units retain their original
gates; future full generation can opt in through its explicit checkpoint assessment.
This is a conservative source-availability rule, not proof of universal alias
resolution. No existing candidate or model receipt was changed by this diagnostic.
