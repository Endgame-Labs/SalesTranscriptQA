# SalesTranscriptQA specification

Agreed scope: September 12, 2026. Status: agreed design baseline; see [implementation choices](IMPLEMENTATION.md) and the [pilot report](../reports/PILOT.md) for completed implementation and results. Implementation defaults below can be revised based on pilot evidence. Work is tracked in GitHub issues, not a separate task checklist here.

## Objective and pilot

Build a pure dialogue retrieval-augmented QA benchmark and companion CLI in one public Endgame-Labs/SalesTranscriptQA repository. The source is CRMArena-Pro's synthetic sales-call transcripts. It is not a CRM workflow benchmark: no hidden database queries, record mutation, policy enforcement, or access-control tasks are required of evaluated systems.

| Domain | Single-call | Two-call | Total |
|---|---:|---:|---:|
| B2B | 50 | 50 | 100 |
| B2C | 50 | 50 | 100 |
| Total | 100 | 100 | 200 |

These are accepted-question targets, not candidate counts. Generate replacements until targets pass, subject to finite retry limits and source eligibility. Report any shortage; never silently relax quality gates. Pilot cost and rejection rates inform later scaling. No full-generation size, deadline, or spend estimate is established.

Search/evaluation uses the full published corpus for the selected domain, not just calls supporting pilot questions. The pinned source contains 4,033 B2B and 6,796 B2C voice-call records. Validate those counts during extraction. Do not add email or live-chat records. Report malformed/missing transcripts rather than silently omit them or alter the dialogue.

## Corpus and denormalization

Read VoiceCallTranscript__c.Body__c from the pinned SQLite snapshots. Preserve its decoded text exactly, including whitespace and speaker labels; store a SHA-256 of its UTF-8 encoding. Markdown frontmatter and export separators are outside the verbatim body. Do not rewrite dialogue to insert names or fix apparent mistakes.

Resolve source IDs through documented foreign-key joins into separate identifying context: lead/opportunity IDs and names, account identity, linked contact identity, and call timestamps where available. Preserve original IDs and record field-level join provenance. A linked contact or record owner is not automatically a speaker: only label participants when the source supports that role. Missing or ambiguous joins remain null or explicitly ambiguous; never fill them with model guesses.

Use an explicit metadata allowlist. Exclude outcome and analytical fields such as qualification status, deal disposition, lead scores, and business-rule answers. The purpose is readable identity resolution, not exposing CRM labels that bypass the calls. Distinguish database snapshot metadata from information known at call time; do not invent historical values or temporal claims from a current snapshot.

Single-call questions rely on one call plus its published metadata. Two-call questions use exactly two distinct calls sharing one explicit opportunity or lead. Do not group solely by account. Require an unambiguous common grouping key; unresolved or conflicting links are ineligible for two-call generation. Dates may order calls only where the source actually provides that ordering.

## Question policy

- Answerable questions only; no unanswerable or refusal class.
- Answers must follow from explicit dialogue/metadata facts. Comparisons, combining complementary facts, and supported changes over time are allowed. Subjective sales judgments are excluded.
- Short reference answers; supporting evidence is stored separately. Prefer a phrase or concise sentence; do not omit facts needed for correctness to meet a rigid word cap.
- Every answer claim must have exact dialogue evidence or a published metadata-field pointer.
- Two-call questions must require both calls. Evidence must include dialogue from each call; shared identity metadata alone does not establish multi-call reasoning.
- Questions must identify their subject sufficiently for retrieval across the full domain corpus without relying on invisible CRM state.
- Generate new questions by default. Adapt upstream questions only when they meet every policy and validation gate; retain upstream task IDs, original text, source revision, and modification history in provenance. Upstream answers are candidates, not unquestioned gold labels.

## Publication data contract

Use one Hugging Face dataset repository with B2B and B2C QA configurations. Within each domain, question_class is single_call or multi_call. Pilot QA belongs to an evaluation/test split; no training split is implied. Publish separately addressed corpus Parquet files alongside those QA configurations, plus generated Markdown exports and a checksum manifest. The selected Hugging Face organization is [EndgameLabs](https://huggingface.co/EndgameLabs); publish as `EndgameLabs/SalesTranscriptQA`. This differs from the GitHub organization `Endgame-Labs`.

Canonical logical records:

| Record | Required content |
|---|---|
| Transcript | schema_version, call_id, domain, upstream_id, dialogue, dialogue_sha256, identifying metadata, source revision and field provenance |
| QA | schema_version, question_id, domain, question_class, question, gold_answer, alternate_answers, supporting_call_ids, evidence, generation/adaptation provenance |
| Evidence | call_id, answer_claim, kind; for dialogue: exact quote and zero-based Unicode-code-point start/end offsets, end exclusive; for metadata: JSON Pointer and exact typed value |
| Release manifest | release/schema versions, upstream pins, artifact paths/checksums/counts, generation configuration digest, validation summary, license and citation references |

Implementation defaults: use stable domain-namespaced source IDs for calls, persistent IDs for question records, sorted canonical serialization for hashes, and native Arrow nested types for evidence. Record answer edits/revisions explicitly. Verify quote == dialogue[start:end] and pointer/value resolution mechanically. Alternate answers must be independently supported semantic equivalents, not partial required-answer components.

Generate Markdown and YAML metadata from canonical transcript records; test that removing the export envelope reproduces dialogue exactly. Evidence offsets always refer to canonical dialogue, never Markdown offsets. Store generation/evaluation-only provenance separately from searchable identifying metadata so it cannot leak answers into retrieval.

Do not publish private credentials, raw provider headers, hidden reasoning, or unrelated CRM tables. Publish concise evidence-based validation reasons, prompt templates, model IDs, configuration and aggregate costs sufficient to audit the method.

## Python generation harness

Use Python with uv. Reuse the established MediaSumQA harness architecture where suitable: SQLite for progress/metadata, immutable files for artifacts, and Parquet for publication. DSPy may orchestrate modular generation/refinement and later prompt optimization; do not assume optimization has already run. spaCy is optional and only added for a demonstrated NLP need.

Models are configurable and use different families for candidate generation and independent answering/validation. Prior project choices motivate DeepSeek Flash and GLM Flash on Fireworks, but exact currently available endpoint/model IDs, rates, and roles must be verified and pinned before execution. No model price or automatic judge accuracy is assumed here.

Stages:

1. Verify pinned downloads and hashes; extract corpus and metadata provenance; measure eligible pairs and corpus ambiguity.
2. Seed deterministic candidate sampling across domain and question class; cap repeated use of a call/group to improve diversity. Record the actual sampling policy and seed.
3. Generate a candidate question, short answer, and evidence from the supplied call(s). Prior questions for that source discourage duplicates.
4. Validate schema, exact quotes/offsets, metadata pointers, domain/group consistency, and evidence coverage mechanically.
5. Have a fresh model from a different family answer from the source without seeing the proposed answer. Compare answers with a structured semantic judge; disagreements fail or trigger bounded refinement.
6. Check specificity against retrieved hard negatives from the full domain corpus, following EnronQA's source-selection approach. Record the retriever/index/version and competitors. A minimal implementation default is a fixed lexical retriever selecting up to ten competing calls, adding gold calls when absent. For two-call questions the selector must identify both sources. Passing this check is not a claim of exhaustive uniqueness.
7. Check no-context answerability with generation and independent model families: reject questions they can answer correctly without call content or identifying metadata. This checks guessability, not proven absence from model training.
8. For two-call candidates, run independent answering with each call separately, including that call's metadata. Reject/reclassify candidates answerable from either alone. Require a separate evidence-based judgment that both calls contribute necessary facts; model failure alone is not proof of logical necessity.
9. Apply a structured factuality/clarity/completeness/conciseness quality check. Reject unsupported temporal inferences, subjective judgments, answer leakage, and near-duplicate questions. Refine only a bounded number of times, then replace failed candidates.
10. Run a fresh final automated audit on the selected cohort, freeze accepted records, export, and produce cost/quality reports.

Human review and human calibration are explicitly excluded by project decision. Label the release automatically generated and automatically validated; model agreement is not human-verified accuracy. Do not import EnronQA's reported judge agreement as evidence about this harness.

SQLite tracks runs, source units, candidates/revisions, stage jobs, attempts, validations, artifacts and usage. Job identity includes source/config/prompt digests. Use transactional claims with leases, resumable states and unique job keys; commit completion only after artifact integrity checks. Recovery reuses completed artifacts. Retrying uncertain network outcomes may incur extra provider charges; record these separately where knowable.

For Fireworks 429/rate-limit and retryable transient failures, use bounded exponential backoff with jitter, honor Retry-After, and coordinate bounded concurrency across workers. Authentication and invalid-input failures stop rather than retry indefinitely. Record request IDs when available, status, attempt count, timing and usage without secrets. Store per-attempt input/output/cache token counts, explicit unknown usage, dated price snapshots, calculated cost, and any provider-reported charges. Report rejected/refined/failed/retried attempts in total spend, plus cost per accepted QA and stage. Do not claim token-priced estimates are invoices.

## CLI contract

Implement the CLI in this same repository; provisional executable salestranscriptqa. Follow EnronQA-cli conventions for explicit fetch, local caching, question and document get/export, question sampling, submission validation, judge-input export, configurable judging and scoring. Final command spelling should be checked against the reference CLI during implementation. These are planned interfaces, not runnable examples.

Fetch a pinned HF revision with checksum validation. Export questions without gold answers/evidence by default; explicit flags expose those for research. Export the full selected domain corpus independently of the question subset. Support Markdown and machine-readable corpus exports/sharding. Validate complete JSONL batches before paid judging, including IDs, domain, duplicates, required fields and nonblank answers. Keep user submissions and judge results local unless explicitly exported.

Answer accuracy is evaluated separately from retrieval evidence. Report per-domain/per-class counts and errors. For multi-call retrieval report both fraction of required calls retrieved and whether both required calls appear at k (including k=5 and k=10); do not silently conflate these. Supporting-call annotations may omit valid alternative evidence, so acknowledge that limitation. The CLI provides dataset/evaluation interfaces; evaluated systems may bring their own search/retrieval harness.

Use configurable model endpoints and clear scoring provenance; no built-in claim of reproducing CRMArena-Pro's official workflow rewards. Package/install documentation, compatibility tests and release artifacts belong alongside the CLI implementation.

## Release acceptance and limitations

Release requires mechanical corpus fidelity and provenance checks, accepted counts per pilot cell, passing automated QA/evidence gates, successful cross-format validation, deterministic export hashes, and a dataset card documenting method, synthetic origin, licensing, model configurations, costs and limitations. No human signoff gate is required.

Before a future train/dev/test expansion, split by connected opportunity/lead groups (and duplicate calls) to avoid source leakage. Pilot tuning records must be identified; do not later describe this development pilot as an untouched test set. Full-scale size, split ratios, model endpoints, and concrete retry/sampling limits remain implementation choices to record before running.

## Methodological references

- [EnronQA](https://arxiv.org/abs/2505.00263): modular generation, specificity, cross-family answer agreement, no-context checks, feedback/refinement. Exact evidence annotations and two-call necessity checks are extensions here. Unlike EnronQA's small human calibration studies, this project omits human validation.
- [HotpotQA](https://hotpotqa.github.io/): supporting-fact supervision and separate answer/evidence evaluation.
- [CRMArena-Pro](https://arxiv.org/abs/2505.18878): original synthetic corpus and eligible task material; this adaptation changes the task into dialogue QA.
