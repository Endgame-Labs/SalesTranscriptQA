# Generator readiness

The revised generator is ready for a user-run generation job. **No full-corpus run
or new Hugging Face publication was performed.** The published dataset remains the
historical 200-question pilot.

## Validation result

A completed sample of **100 source units** produced **234 proposals**, of which 41
passed generation/source/contract gates. Final selection retained **37 questions**:
17 B2B single-call, 14 B2C single-call, and 6 B2B multi-call. All 37 questions and
answers were inspected during development, and all 37 passed the final independent
Qwen source review. Answers range from **7 to 29 words**, median **19**.

The sample excludes 293 CRM groups used by earlier experiments. It is source-group
disjoint generation validation, but final selection was refined after inspecting
outputs. **The 37/37 reviewer result is not an unbiased accuracy estimate**, and
model judgments are not human gold labels.

[Read all 37 questions and answers](sales-ready-validation-20260918-accepted.md) ·
[JSON](sales-ready-validation-20260918-accepted.json) ·
[Independent review](sales-ready-validation-20260918-accepted-qwen-review-v1.json)

## Experiments and resulting choices

| Approach | Units | Proposals per unit | Accepted by that version | Recorded generation/gate API estimate |
|---|---:|---:|---:|---:|
| Natural names, DeepSeek generator (v6) | 100 | 1 | 29 | $0.3067 |
| Same sources, GLM generator (v6) | 100 | 1 | 33 | $0.3519 |
| GLM draft + DeepSeek edit (v7) | 100 | 1 | 28 | $0.4098 |
| Focused GLM + group consistency (v8) | 100 | 1 | 21 | $12.0586 |
| Focused GLM + evidence normalization + final selection (v9) | 100 | Up to 3 | 37 final / 41 before selection | $27.1164 |

These are development comparisons, not a controlled ranking: validators and proposal
budgets changed. Earlier 20-question trials and targeted ambiguity audits are in the
[experiment history](../docs/QUESTION_EXPERIMENTS.md).

The selected approach keeps natural participant/account context, removes repetitive
source-locator phrasing, and favors practical questions about requirements, terms,
objections and commitments. Blind extraction and blind source-completeness verification
precede answer comparison. This caught genuine competing quotes and commitments
that exact-source selection missed, while accepting equivalent evidence.

Generation uses GLM Flash; independent answering and contracts use DeepSeek Flash
and GLM. Qwen performs blind completeness verification and answer comparison over
retrieved CRM groups. The exact IDs/rates are recorded in configurations and costs.
Final question-only GLM selection checks coherence and plausible sales language.
Advanced questions additionally need agreement from both DeepSeek and GLM that
each call contributes substantively distinct requested information.

Four generated acceptances were removed by final selection: an unrelated competitor
fact bundle, unexplained vehicle-installation wording, a repeated delay complaint
presented as two-call reasoning, and a multi-call item with judge disagreement.
No selected question was manually rewritten. Raw outputs, failed proposals, exact
evidence and every automatic selection decision remain preserved.

## Execution and integrity evidence

- All 100 units completed; all eligible strata are represented; no B2C multi-call unit was generated.
- Corpus hashes and exact evidence verified against the frozen verbatim source corpus.
- Final JSON and both Parquet files match, IDs are unique, and recorded contract, consistency and final-selection gates were verified.
- A completed replay made **zero new API attempts** and preserved dataset artifact hashes.
- **53 tests pass**, including budget concurrency/unknown usage, reference isolation, evidence normalization and bounded schema repair.

[Artifact verification](sales-ready-validation-20260918-verification.json) ·
[Replay receipt](sales-ready-validation-20260918-replay.json) ·
[Final selection decisions](sales-ready-validation-20260918-selection.json)

## Costs and practical limits

Recorded research campaign API estimate: **$52.2455** against the $1,000 research ceiling.
The final 100-unit run, including final selection, cost **$27.1164**; its independent review cost **$0.20573** (including the earlier 39-question review). These are configured-rate estimates, not invoices. Unknown interrupted usage may be omitted.

The expensive stage is Qwen blind source-completeness verification: **$24.5908** of
the final run. GLM generation itself cost **$0.1064**. Stronger ambiguity checking is
therefore much more expensive than the original generation-only pipeline. A simple
linear extrapolation to 14,916 units is about **$4,045** at this sample's rate; it is
a planning approximation, not a quote, and coverage/proposal mix can change costs.
The runner's explicit budget makes an incremental rollout possible.

[Atomic costs by stage/model](sales-ready-validation-20260918-costs.csv) ·
[Campaign ledger](question-research-costs.json)

The consistency check covers 30 lexical neighbors plus intended sources, expanded
to full explicit CRM groups. It is not exhaustive corpus-wide ambiguity proof.
Strict consensus can reject good questions; acceptance yield is not an accuracy
score. Semantic judges remain fallible, and the upstream calls contain synthetic
business facts. The generator preserves those facts rather than correcting them.

## Run it

Follow the [generation guide](../docs/GENERATION.md). One command handles generation,
resumption, final selection and local JSON/Parquet output. The final files are under
`RUN_DIR/selected/`. Full generation requires explicit `--all`; publication is separate.
