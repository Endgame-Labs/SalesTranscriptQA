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
