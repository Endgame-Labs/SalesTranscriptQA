# Sales question redesign experiments

The target is a question a sales rep or account manager would ask about a customer,
account or opportunity. Natural participant names are allowed. Avoid repetitive
source-location scaffolding such as “in the July 11 call titled … with …”. Business
appointment/deadline dates are legitimate content. Initial/follow-up wording can
appear occasionally. B2C uses single-call questions only; B2B also has same-group
multi-call questions. Transcript dialogue remains verbatim.

These are bounded experiments, not the replacement production generator yet.
Full generation and automatic publication remain stopped. The current research
budget ceiling is $1,000; recorded Fireworks costs are estimates, not invoices.

Run from the repository root with the corpus already available:

```bash
uv run python scripts/sales_question_experiment.py --model deepseek --count 100
uv run python scripts/sales_question_experiment.py --model glm --count 100
uv run python scripts/review_sales_sample.py reports/sales-questions-v6-deepseek-seed20260915-n100.json
uv run python scripts/review_sales_sample.py reports/sales-questions-v6-glm-seed20260915-n100.json
```

Each experiment is capped at 100 source units. The seed fixes the same random
source units for both generators: half B2C single, quarter B2B single, quarter B2B
multi. Each unit gets one proposal; failures are reported rather than replaced.
Changing the prompt requires a new version/run directory. Run locks prevent two
processes writing the same experiment. SQLite stores progress and metered request
attempts; JSON files preserve prompts, sources, generated artifacts and decisions.
A repeated command reuses the frozen request/candidate cache. The existing shared
Fireworks transport handles rate limits with exponential backoff, jitter and
Retry-After. No command here publishes data or starts full generation.

Current checks include exact evidence spans, an independently answered question
using the other model family, no-context controls, one-call ablations for multi-call
questions, factual/answer-completeness audits, source specificity, and the existing
question-first atomic answer contract. Single-call candidates do not depend on
inapplicable two-call flags. A separate Qwen reviewer inspects all accepted items
and ten seeded rejected items for sales usefulness, natural language, source
support and exact question/answer alignment.

Known limitations under investigation:

- The legacy specificity check still demands the original source set among ten
  lexical distractors. It can reject alternative evidence supporting the same
  answer; it does not prove corpus-wide uniqueness.
- A prompt instruction alone has not reliably stopped date/call preambles.
  Independent review results must be inspected before choosing final gates.
- Multi-call questions may look natural yet merely concatenate unrelated facts.
  Both the factual ablations and the account-level coherence check matter.
- Automated judgments are fallible. Prior blinded extraction experiments found
  actual alternate answers but also partial-answer false positives; those findings
  must guide a calibrated replacement specificity check, not an untested waiver.

The v4/v5 reports preserve earlier scope/wording experiments. Their participant-name
restrictions were an overcorrection and are superseded by v6; their results should
not be treated as the desired style specification.

## Draft/edit and answer-consistency experiments

```bash
uv run python scripts/sales_question_experiment.py --model edited --count 100
uv run python scripts/calibrate_consistency_v2.py
uv run python scripts/check_sales_consistency.py reports/sales-questions-v6-glm-seed20260915-n100.json --version 2
```

The edited arm uses GLM drafting and DeepSeek revision, followed by the same evidence,
independent answering, ablation and contract checks. Explicit locator patterns reject
dated/month-named call references while allowing participant names and business dates.
The initial 100-unit comparison reuses the prior source seed to isolate the effect of
editing; a fresh seed is still required before production selection.

The consistency experiment retrieves 30 lexical neighbors plus intended sources and
expands these to complete explicit CRM groups. Its first judge design was stopped:
seeing the reference caused false conflicts for wrong entities and partial answers.
Version 2 separates blind extraction, blind complete-answer verification, and only
then reference comparison. Nine observed-failure/control cases passed live calibration.
This is not yet the production specificity gate; broader sample results remain pending.

## Standalone runner under validation

The v8 focused-GLM arm integrates reference-blind group consistency into acceptance,
replacing exact original-source selection. Evidence spans, independent answers,
no-context controls, multi-call ablations and atomic question/answer contract checks
remain. The broader v6 audit has already found genuine competing quotes and customer
commitments that the earlier specificity selector missed.

The reusable runner is implemented but still undergoing live sample validation:

```bash
uv run python scripts/generate_sales_questions.py \
  --sample 100 --seed 20260917 --workers 8 --proposals 3 \
  --budget-usd 50 --run-dir runs/sales-ready-sample-20260917 \
  --exclude-report reports/sales-questions-v6-glm-seed20260915-n100.json
```

Sample exclusions remove entire CRM groups appearing in earlier reports. The v8
initial fresh-seed experiment has two source-call overlaps with v6; it is a new
random sample, not a completely disjoint holdout. Use exclusions for the final
validation sample.

Repeat the identical command to resume. The source plan and configuration are frozen;
changing prompts requires a new version and directory. Observe the run with:

```bash
watch -n 10 cat runs/sales-ready-sample-20260917/progress.json
uv run python scripts/research_costs.py
```

SQLite meters each request attempt. The optional transport budget reserves a
conservative estimate for in-flight requests atomically across workers and retains
reservations for unknown usage. Known token usage replaces reservations. The cap is
an operational allowance, not a provider invoice guarantee. A budget stop preserves
checkpoints; raise the explicit allowance to resume if desired. The research-wide
ceiling remains $1,000 across all runs.

On completion the runner writes `questions.json`, B2B/B2C question Parquet files,
coverage/deduplication reports and progress. Sample coverage is explicitly marked;
no files are uploaded. B2C multi-call units are excluded. An explicit `--all` option
exists for eventual full generation, but has NOT been run during this research.
Do not confuse this new runner with the stopped historical generate-and-publish
workflow. Production readiness is still pending live sample results and review.

### One-line evidence normalization (v9)

Direct request inspection showed frequent `line_start == line_end` outputs for
one-line quotes. Version 9 interprets only equal integer endpoints within the
source as a one-line selection (`line_end = line_start + 1`). Raw provider JSON
is retained; the candidate records every repair. All subsequent source, evidence,
answer and contract checks still run. Out-of-bounds, reversed and noninteger
ranges remain invalid. Six regression cases cover this behavior.

The initial standalone v8 sample was intentionally stopped and preserved after
this diagnosis. A new v9 standalone sample uses seed 20260918 and excludes CRM
groups from v6, the v8 fresh-seed plan, and the interrupted standalone plan. It is
running under a $50 allowance, with 100 source units and up to three proposals
each. No full-corpus generation was started. Readiness remains pending completion,
output review and replay checks.

After a standalone run completes, verify its artifacts and export accepted questions
for review (substitute the actual run directory):

```bash
uv run python scripts/verify_generation_output.py runs/sales-ready-validation-20260918
uv run python scripts/review_generation_output.py runs/sales-ready-validation-20260918
uv run python scripts/review_sales_sample.py reports/sales-ready-validation-20260918-accepted.json
```

The artifact verifier checks the frozen corpus hashes, source-plan scope, complete
unit counts, excluded groups, absence of B2C multi-call units, JSON/Parquet equality,
question-ID uniqueness, exact evidence, recorded contract/consistency acceptance,
and locator checks. It deliberately does not label these integrity checks an
independent semantic quality estimate. Re-running the original generation command
after completion should replay checkpoints without new API attempts; this is part
of the pending end-to-end validation.

### Final coherence selection

The runner now preserves factual-gate output at the run root and writes the final
coherence-selected dataset under `selected/`. Its question-only GLM check rejects
unrelated fact bundles that passed factual audits. Five clear positive examples and
one clear negative were classified as intended; a seventh timing/deployment example
was accepted despite an initially negative manual label, a documented subjective
boundary. This is not claimed as a perfect or independently measured classifier.

`selected/selection.json` records every decision and the prompt/input digests.
All raw candidates and discarded questions remain reviewable. The output verifier
and review exporter use the final selected dataset. The active generation process
was launched before this final selection stage was added; replaying its completed
command will run cached generation and then this new stage, without restarting the
source-generation experiment. Final validation must include that replay and review.

Final selection v2 adds a plausibility check for mismatched source-template language
(e.g. unexplained installation of ordinary purchased vehicles). It does not rewrite
source facts; it rejects the question. Six targeted controls passed, including valid
software and protection-film installation. The v1 calibration remains replayable.
Because this final selection was refined after inspecting development outputs, the
source-group-disjoint generation sample is development validation, not an unbiased
held-out accuracy estimate for the entire final pipeline.

`scripts/finish_sample_validation.py` can wait on one exact live Linux process handle
and, only after successful completion of the recorded 100-unit sample, run selection,
artifact verification, question export, independent review, and a second replay. Its
receipt distinguishes execution/replay verification from the final semantic readiness
decision. It never starts a full-corpus run.
