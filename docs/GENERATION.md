# Generate sales questions

The current standard is `sales-questions-v9-line-evidence`, with the same prompt and quality gates validated in the 100-unit sample. The next run expands to **2,000 source units**, excluding all 392 CRM groups covered by the prior validation/exclusion plans. Retired pilot/full-v1 questions must not be mixed into new releases. The [cohort registry](../reports/cohort-registry.json) records exclusions and active inputs.

## Expanded generation and RAG workflow

Operational status: [expansion issue #3](https://github.com/Endgame-Labs/SalesTranscriptQA/issues/3).

```bash
uv run python scripts/expanded_sample_workflow.py
```

This resumable workflow generates 1,000 B2C single-call units, 500 B2B single-call units, and 500 B2B two-call units, with up to three proposals per unit and 16 workers. It verifies artifacts, independently reviews all selected questions, freezes review-passing questions, and runs the sibling private RAG evaluator with the same hybrid/reranked/full-source/no-context protocol as the 37-question diagnostic. Review exclusions occur before RAG; retrieval failures never trigger question deletion.

The overall expanded-sample + conditional full-run experiment has a $5,000 ceiling. The current expansion retains its $850 generation guard, a $150 independent-review allowance, and a $500 RAG allowance. These are conservative sublimits, not separate additions to the overall ceiling. An active assistant goal reviews progress and random quality samples hourly; the scripted monitor is supplemental. After the expansion passes agent review, a full eligible run is authorized within the remaining shared budget.

An 08:00 UTC source inspection on September 14 found a supported answer with an
incorrectly narrow evidence span. Full-transcript reviewers could see the missing
line and passed the answer, overlooking the citation defect. Independent review
now additionally requires `quoted-evidence-audit-v1`: a separate Qwen request sees
only cited passages and identifying metadata, checks each evidence-to-claim link,
and checks complete answer support. Missing or malformed verdict coverage fails
closed. This strengthens the post-generation review; the v9 generator and original
artifacts remain unchanged. Both expanded and full workflows export evidence into
the review inputs and freeze only questions passing both reviews. No automatic
span repair or manual acceptance override is performed. The recorded regression
shows the erroneous citation rejected and an explicitly corrected example accepted.

Generation currently has an $850 operational cap. The earlier sample projects roughly $540 for generation plus tens of dollars for review/RAG, with substantial uncertainty. API estimates exclude turbopuffer/VM. No Hugging Face upload occurs. The legacy `generate_and_publish.py` entry point now refuses execution.

On the research VM, the complete sequence runs as `salestranscriptqa-expanded-2000.service`:

```bash
watch -n 10 'cat runs/sales-expanded-2000-v1/workflow.json; cat runs/sales-expanded-2000-v1/progress.json'
journalctl --user -u salestranscriptqa-expanded-2000.service -f
```

Stage logs are in the run directory. RAG progress later appears at `../2026-09-12-salestranscriptqa-rag-evaluation/runs/expanded-2000-v1/progress.json`. Errors stop the sequence and preserve checkpoints; rerun the workflow after resolving the cause.

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
operational allowance, not a provider invoice guarantee. The original bounded research campaign used a $1,000 limit; the newly authorized expansion has the explicit allowance above. Individual sample runs remain capped at $1,000. The sample command defaults to $50.

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

Final question-only GLM selection removes unrelated fact bundles and clearly mismatched domain language, such as unexplained installation of ordinary purchased vehicles. Two-call questions also require cross-model agreement on substantively distinct requested facts; valid negative judgments are not retried into positives. Names can supply
natural scope; document-date/title preambles and unbound first-person identity are
rejected. All judges remain fallible, and coherence has subjective boundaries.

The current model IDs, configured rates and per-attempt usage are stored in run
configuration and request records. `scripts/research_costs.py` reports campaign
estimates from unique SQLite databases; it does not sum overlapping report totals.

## Eventual full generation

For a full run, replace `--sample 100` with `--all` and use
a new directory and an explicit budget. The full eligible scope is 14,916 source
units: 10,829 single calls and 4,087 B2B pairs. This mode exists but has not been run
during the current research. It also writes local artifacts only; publication is a
separate task. The historical `generate_and_publish.py` workflow is not this runner.

See [experiment history](QUESTION_EXPERIMENTS.md) for comparisons and calibration
failures that motivated the current checks.

## Reuse the approved expansion in a full run

After the assistant has inspected the completed expansion and recorded its exact
reviewed-question SHA-256 in a checkpoint assessment with `approved_for_full: true`,
`scripts/seed_full_run.py --source EXPANDED_RUN --destination NEW_FULL_RUN --checkpoint-review ASSESSMENT.json`
can seed a new full-run directory without model calls. It requires a terminal source
workflow, preserves candidate/unit files separately, snapshots SQLite, and reuses
immutable provider responses. The full runner must use the same frozen configuration
(currently 16 workers and three proposals) or initialization rejects the cache.
The helper does not start the full run or change its question policy.

### Supervised full workflow

`scripts/full_sample_workflow.py` is prepared but has not been started. After the
assistant assesses the completed expansion's quality, random source samples, all
four RAG arms, and cost forecast, the assessment file
`reports/expanded-2000-full-checkpoint.json` must identify the exact reviewed
question SHA-256 and set `approved_for_full: true`. It also supplies
`budget_limits`: `generation_usd`, `review_usd`, `rag_usd`, and `reserve_usd`.
These are positive cumulative ceilings, not forecasts. Generation includes the
imported checkpoint spend; accounting deducts that inherited spend exactly once.
Retain at least $100 reserve for monitoring and unmetered infrastructure. This
reserve is not evidence of actual VM or Turbopuffer invoice charges.

Validate the assessment and combined allowance without starting work:

```bash
uv run python scripts/full_sample_workflow.py \
  --checkpoint-review reports/expanded-2000-full-checkpoint.json --check-only
```

The same command without `--check-only` seeds compatible generation caches,
freezes and validates all 14,916 source units before paid generation, runs the
existing gates, independently reviews every selected question, freezes the final
cohort, and evaluates every final question in all four RAG arms. The accompanying
`ops/salestranscriptqa-full-v2.service` is a deployment template, not an enabled
service. It must not be started before checkpoint approval.

Known historical quarantines and expanded independent-review rejections remain
excluded by question ID or normalized question text. RAG failures do not remove
questions. Before each paid stage, the workflow checks all remaining stage
ceilings together against the shared $5,000 campaign allowance. Each transport
also reserves the cost of in-flight calls against its own stage ceiling. The
assistant must continue hourly inspection, account for additional diagnostics
and infrastructure, and stop if the reserve is inadequate. Stage failures stop
the workflow and preserve artifacts; do not increase limits without rechecking
the shared allowance and recording the revised assessment.

The workflow leaves publication and the final secret-gist report as explicit
post-evaluation steps. Its `complete` state means generation/review/RAG completed,
not that the overall supervised task is finished.

Inherited attempt IDs and usage represent already-paid work. Count them once across
source/destination ledgers; the destination's generation allowance includes those
carried-forward costs. The new source plan must cover all eligible units, and the
final cohort still needs selection, independent review, quarantine checks, and RAG
verification before reporting.

## Packaging the reviewed full-v2 release

After the full workflow finishes, prepare the current cohort with the dedicated
v9 packager. The legacy `prepare-full-release` command targets the retired full-v1
format and must not be used for this run.

```bash
uv run salestranscriptqa prepare-reviewed-release \
  --run-dir runs/sales-full-v2 \
  --rag-report ../2026-09-12-salestranscriptqa-rag-evaluation/reports/full-v2 \
  --output data/full-v2-release
```

This makes no model calls and does not upload. It requires completed generation,
reviews and RAG; verifies every eligible source unit and recorded generation gate;
replays independent source/citation reviews, quarantines and customer-history
selection; checks the exact frozen JSON/Parquet; and requires all four RAG outcomes
for every unchanged question, including its evidence. Incorrect RAG answers remain
included. An unfinished run fails before creating a release directory.

The package preserves the original corpus and the historical pilot separately,
retains Salesforce attribution and CC BY-NC 4.0, and includes the exact frozen QA,
coverage, review evidence, verification receipts and checksums. The dataset card
describes the current GLM/DeepSeek/Qwen methodology and its automated-review and
construction-evaluation limitations. It makes no human-gold accuracy claim.

After inspecting that package, publish and verify its immutable revision:

```bash
uv run salestranscriptqa publish-full-release \
  --output data/full-v2-release \
  --receipt runs/sales-full-v2/publication.json \
  --repo EndgameLabs/SalesTranscriptQA
```

Publication validates checksums and the reviewed-release receipt, uses an atomic
Hugging Face commit with a pinned parent, then verifies anonymous downloads and
an anonymous CLI fetch. A saved receipt resumes verification of the same revision
without creating another publication commit. This upload is separate from the
generation service and must only occur after the frozen cohort is reviewed.
