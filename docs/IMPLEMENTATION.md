# Pilot implementation choices

The [specification](SPEC.md) records the agreed product scope. [Issue #1](https://github.com/Endgame-Labs/SalesTranscriptQA/issues/1) tracks remaining work. The first implementation makes the following concrete choices:

- Direct Python modules, without DSPy optimization or spaCy. Generator: `accounts/fireworks/models/deepseek-v4-flash-0731`; independent answerer/validator: `accounts/fireworks/models/glm-5p3-flash`.
- Fireworks serverless pricing checked September 12, 2026: DeepSeek $0.22/$0.007/$0.66 and GLM $0.15/$0.03/$0.50 per million input/cached-input/output tokens. [DeepSeek source](https://fireworks.ai/models/deepseek-ai/deepseek-v4-flash-0731), [GLM source](https://fireworks.ai/models/fireworks/glm-5p3-flash).
- Temperature zero, 4,096 completion-token ceiling, DeepSeek reasoning `none`, GLM reasoning `low`, JSON-object responses. Provider sampling is not guaranteed deterministic.
- Six candidate workers in one process, with one exclusive process lock per run. SQLite records job status/lease metadata and per-request attempts. The process lock, not distributed lease claiming, enforces a single writer process; multiple machines must not share a run directory.
- Maximum eight transport attempts. Exponential backoff starts with a two-second base, caps the exponential base at 60 seconds, applies 0.5–1.5 jitter, and honors a longer `Retry-After`. Workers share the resulting cooldown. Authentication/invalid-request failures are not retried indefinitely.
- Seed 20260912; shuffle source groups independently for each domain/class. Choose one call or one eligible pair from each group. At most 1,000 candidate groups per class; a shortage fails visibly.
- Rejected candidates are replaced from other groups. This version does not refine questions or optimize prompts. Cache stage requests to resume completed work.
- Questions request 5–30-word answers; a 60-word ceiling rejects long answers mechanically. Completeness and concision are also checked by a model.
- The generator supplies zero-based line ranges, end exclusive. Code copies original text and calculates Unicode-code-point offsets. This replaced an initial experiment in which the model retyped quoted passages and frequently failed the verbatim gate.
- TF-IDF unigram/bigram retrieval over full call text plus identifying metadata, minimum document frequency 2, maximum 180,000 features per domain. Select ten competing calls; add gold calls if absent, shuffle the resulting pool, and require a model to select the intended minimal set without being shown which calls are gold. This tests specificity against hard negatives, not exhaustive corpus uniqueness.
- Each candidate receives independent source-conditioned answering; both model families also attempt it without context. For two-call candidates, the independent model answers from each call separately. A structured audit compares answers and independently checks factual necessity from the source. A separate fresh final audit rechecks question, answer and evidence.
- Human review/calibration is deliberately omitted. No published judge-agreement metric is inherited from another project.
- Exact duplicate rejection during selection and a final .9 TF-IDF unigram/bigram cosine gate before release. This is a lexical near-duplicate filter, not a semantic uniqueness guarantee.
- Canonical corpus Parquet regenerated twice with identical bytes. Markdown body round trips preserve every original dialogue character. Markdown archives use fixed ZIP entry timestamps for reproducible bytes.

The pilot test split is a development artifact, not a claim of independence from pipeline tuning. Future train/dev/test splits should separate connected source groups and duplicate content.
