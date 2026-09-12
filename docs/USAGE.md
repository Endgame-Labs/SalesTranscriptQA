# Using SalesTranscriptQA

Install from the repository with `uv sync --frozen`, or install the CLI with:

```sh
uv tool install git+https://github.com/Endgame-Labs/SalesTranscriptQA.git
salestranscriptqa --help
```

## Get a dataset release

The pilot is available on [Hugging Face](https://huggingface.co/datasets/EndgameLabs/SalesTranscriptQA) and as a GitHub prerelease:

```sh
gh release download v0.1.0 --repo Endgame-Labs/SalesTranscriptQA --pattern salestranscriptqa-pilot-v0.1.0.zip
unzip salestranscriptqa-pilot-v0.1.0.zip
```

This creates `salestranscriptqa-data/`, the default directory used by the examples below.

Fetch the published Hugging Face pilot at its immutable revision:

```sh
salestranscriptqa fetch --repo EndgameLabs/SalesTranscriptQA --revision d5eae88b4a725b697ab81dc720429477611f1a9c --data-dir salestranscriptqa-data
```

The CLI requires an immutable revision and verifies all manifest checksums. The dataset includes full B2B/B2C corpora, question Parquet files, and Markdown transcript archives. A locally prepared release directory can also be supplied using `--data-dir`.

## Export questions and documents

```sh
salestranscriptqa questions export --domain b2b --output questions.jsonl
salestranscriptqa questions export --domain b2c --question-class multi_call --output multicall.jsonl
salestranscriptqa documents export --domain b2b --output calls.jsonl
salestranscriptqa documents export --domain b2b --shards 8 --output call-shards
salestranscriptqa documents export --domain b2c --format markdown --output transcripts
salestranscriptqa questions sample --domain b2b --count 4 --seed 42 --include-answer
salestranscriptqa questions get QUESTION_ID --domain b2b --include-answer --include-source
salestranscriptqa documents get CALL_ID --domain b2b
```

Gold answers and source evidence are excluded from question exports unless requested with `--include-answer` and `--include-source`. Corpus exports contain every call in the chosen domain. Do not restrict retrieval to the source calls associated with sampled questions. Markdown/YAML copies are in each release's `b2b-markdown.zip` and `b2c-markdown.zip` archives; dialogue is verbatim.

## Submit and evaluate answers

Produce one JSON object per line:

```json
{"question_id":"QUESTION_ID","answer":"A concise answer","retrieved_call_ids":["CALL_ID_1","CALL_ID_2"]}
```

`retrieved_call_ids` is optional and preserves retrieval order. Required fields are `question_id` and a nonblank `answer`. Questions must belong to the selected domain and IDs must be unique. Partial submissions are supported; reports include coverage and score only submitted questions.

```sh
salestranscriptqa validate answers.jsonl --domain b2b
salestranscriptqa score answers.jsonl --domain b2b --output lexical-scores.json
salestranscriptqa judge-input answers.jsonl --domain b2b --output judge-input.jsonl
```

Lexical scores are normalized exact match and token F1, not semantic correctness. Retrieval reporting distinguishes required-call recall from retrieving the entire required call set at 5 and 10. Results are reported overall and by question class.

External judges can produce JSONL records with `question_id` and boolean `correct`:

```sh
salestranscriptqa score answers.jsonl --domain b2b --judgments judgments.jsonl --output scores.json
```

For direct LLM judging, export your provider key into an environment variable and choose a model explicitly:

```sh
salestranscriptqa check answers.jsonl --domain b2b --model PROVIDER_MODEL_ID --api-key-env FIREWORKS_API_KEY --output judgments.jsonl
```

Use `--base-url` for another HTTPS OpenAI-compatible JSON endpoint. `--reasoning-effort` and `--max-tokens` configure provider reasoning/output limits; for GLM Flash, use `--reasoning-effort low`. The full submission and output destination are validated before paid requests. Judgments checkpoint after each question and include per-attempt timing and provider usage where supplied. Failures have an `error` field, never a fabricated correctness value; `check` exits nonzero if any fail. `score` rejects incomplete/duplicate judgment sets. A new `check` invocation currently rejudges the supplied batch; supply only unanswered items when recovering a partial judging run.

Outputs refuse overwrite unless `--force` is supplied. Answers, judge results and API keys are not uploaded by these commands.

## Build the corpus and pilot

From a source checkout:

```sh
uv sync --frozen
uv run salestranscriptqa build-corpus --fetch-source
uv run salestranscriptqa generate-pilot --per-class 50
```

Source downloads are pinned by `provenance/upstream-manifest.json`. To use an existing verified source download, pass `--source-dir PATH` to `build-corpus`. Default generated files are ignored by Git: `data/` for corpora and release artifacts, `runs/` for SQLite progress and model request artifacts.

Generation uses DeepSeek V4 Flash 0731 and GLM 5.3 Flash through Fireworks. Supply `FIREWORKS_API_KEY` in the environment. On the development VM, the harness can load only that key from `~/.secrets/keys.env` if it is not already set. No other keys are read into the environment.

The harness uses one process lock per run with six concurrent candidate workers, transactional SQLite stage records, request caching, bounded exponential backoff with jitter, and shared rate-limit cooldown. Each source group contributes at most one candidate per class in a run. Rejected candidates are retained and replaced with candidates from other groups; there is no refinement/optimization loop in this first implementation. Resume with the same run directory and configuration. Use a new directory/version when changing the generation protocol.

This version implements the modular stages directly in Python. It does not require DSPy or spaCy. Prompts are versioned in `src/salestranscriptqa/pilot.py`; no DSPy optimization or human calibration is claimed.

## Data terms

The data are **CC BY-NC 4.0**, with Salesforce attribution. The CLI and original implementation are **MIT**. The CLI license does not grant commercial rights to the dataset. See [NOTICE](../NOTICE.md) and the [specification](SPEC.md).
