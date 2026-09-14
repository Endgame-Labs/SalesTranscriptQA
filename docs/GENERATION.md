# Generate sales questions

The revised generator is undergoing a 100-unit validation run. Full generation
and publication are paused. These instructions describe the implementation being
validated; the final results report will record readiness and sample quality.

## Prepare

From this repository:

```bash
uv sync --frozen
uv run salestranscriptqa build-corpus --fetch-source
```

Provide `FIREWORKS_API_KEY` in your environment. On the development VM the helper
can load that key alone from `~/.secrets/keys.env`. No Hugging Face token is required
for generation. Source transcripts remain verbatim; Salesforce attribution and
CC BY-NC 4.0 data terms remain in effect.

## Run a sample

```bash
uv run python scripts/generate_sales_questions.py \
  --sample 100 --seed 20260918 --workers 8 --proposals 3 \
  --budget-usd 50 --run-dir runs/my-sales-qa-sample
```

The sample is half B2C single-call, one quarter B2B single-call and one quarter B2B
two-call. Two-call units share an explicit opportunity. B2C multi-call units are
excluded. Up to three proposals are attempted per source unit; rejected units are
retained. Selection and deduplication may further reduce the output count.

To validate on unused CRM groups, add `--exclude-report PATH` for each previous
question report or source plan. This excludes entire groups, not merely question
strings. A fresh seed alone does not guarantee disjoint source groups.

## Observe and resume

```bash
watch -n 10 cat runs/my-sales-qa-sample/progress.json
```

Repeat the original command to resume. Keep its source plan and generation settings
the same; use a new directory when changing them. Successful requests and finished
units are cached. A process lock prevents concurrent writers. Infrastructure failures
stop the run; they do not become quality rejections. In-flight requests interrupted
before billing is recorded retain conservative budget reservations.

The spend limit accounts for recorded usage and reserves an overestimate for active
requests. You can raise `--budget-usd` when resuming after a budget stop. This is an
operational allowance, not a provider invoice guarantee. The research campaign is
limited to $1,000 across experiments. The sample command defaults to $50.

## Outputs

The final dataset is in `RUN_DIR/selected/`:

- `b2b-test.parquet` and `b2c-test.parquet`: final selected question/answer rows.
- `questions.json`: the same rows in JSON.
- `selection.json`: coherence decisions and prompt/input fingerprints.

The run root retains the frozen corpus/configuration/source plan, SQLite request
progress and costs, request/candidate/unit artifacts, raw pre-selection questions
and Parquet, deduplication/coverage reports, and progress. Generation never uploads
or modifies the published Hugging Face dataset.

```bash
uv run python scripts/verify_generation_output.py runs/my-sales-qa-sample
uv run python scripts/review_generation_output.py runs/my-sales-qa-sample
```

The first command verifies artifacts and recorded gates. The second writes readable
accepted questions and a JSON report under `reports/`. The optional independent
review uses `scripts/review_sales_sample.py REPORT.json` and incurs additional API cost.

## Models and checks

GLM Flash generates questions; DeepSeek Flash independently answers them. Mechanical
checks copy exact dialogue evidence and normalize only the observed equal-endpoint,
one-line citation case. No-context controls, single-call ablations for two-call QAs,
factual audits and an atomic question/answer contract enforce grounded answers.

For answer consistency, 30 lexical neighbors plus the intended sources are expanded
to complete explicit CRM groups. GLM extracts answers without the reference; Qwen
independently verifies complete source support without the reference, then compares
verified answers. Equivalent evidence is allowed; conflicting complete answers and
inconclusive checks reject the proposal. This is a checked source pool, not a proof
of uniqueness over the whole corpus.

Final question-only GLM selection removes unrelated fact bundles. Names can supply
natural scope; document-date/title preambles and unbound first-person identity are
rejected. All judges remain fallible, and coherence has subjective boundaries.

The current model IDs, configured rates and per-attempt usage are stored in run
configuration and request records. `scripts/research_costs.py` reports campaign
estimates from unique SQLite databases; it does not sum overlapping report totals.

## Eventual full generation

After accepting the validated approach, replace `--sample 100` with `--all` and use
a new directory and an explicit budget. The full eligible scope is 14,916 source
units: 10,829 single calls and 4,087 B2B pairs. This mode exists but has not been run
during the current research. It also writes local artifacts only; publication is a
separate task. The historical `generate_and_publish.py` workflow is not this runner.

See [experiment history](QUESTION_EXPERIMENTS.md) for comparisons and calibration
failures that motivated the current checks.
