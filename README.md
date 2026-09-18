# SalesTranscriptQA

A dialogue RAG benchmark built from Salesforce's synthetic CRMArena-Pro sales calls, with separate B2B and B2C question sets and a companion CLI in this repository.

**Full v2 published September 18, 2026.** All 14,916 eligible source units were processed. The reviewed release contains **2,962 QA pairs**: 1,215 B2B single-call, 428 B2B multi-call, and 1,319 B2C single-call. [Pinned Hugging Face release](https://huggingface.co/datasets/EndgameLabs/SalesTranscriptQA/tree/183bd79178a3555351d25400225001a9b27ecc2f) · [Generation guide](docs/GENERATION.md) · [Cohort registry](reports/cohort-registry.json).

The earlier 200-question pilot and legacy generation run are retired from active use. Historical pilot files are preserved under `pilot/` in the dataset; they are not mixed into the revised cohort.

The CLI is implemented and tested. [Legacy CLI release](https://github.com/Endgame-Labs/SalesTranscriptQA/releases/tag/v0.1.0) · [Historical pilot report](reports/PILOT.md) · [Revised generator readiness report](reports/GENERATOR_READINESS.md).

- [CLI and generation usage](docs/USAGE.md): installation, exports, judging and reproducible builds.
- [Pilot implementation choices](docs/IMPLEMENTATION.md): models, rates, sampling and validation settings.
- [Corpus inventory](reports/corpus-inventory.json): verified counts, identity joins and eligible call pairs.
- [Specification](docs/SPEC.md): agreed scope, data contracts, generation and publication approach.
- [Decision record](docs/DECISIONS.md): source decisions and implementation defaults.
- [Attribution](NOTICE.md) and [upstream data license](LICENSE-DATA.txt).

The corpus preserves dialogue verbatim. Linked IDs are resolved into separate identifying metadata. Questions may use both dialogue and that metadata; advanced questions must require evidence from exactly two calls within one opportunity or lead.

Publication uses canonical Parquet plus Markdown transcript exports with YAML frontmatter. The `salestranscriptqa` CLI fetches pinned Hugging Face releases, exports corpora/questions, validates submissions, and supports answer judging in the style of [EnronQA-cli](https://github.com/dorkitude/EnronQA-cli).

## Full release and evaluation

Generation used the v9 prompt and independent source/citation and customer-history
reviews. Hourly source inspections added quality exclusions. No question was
removed because of its RAG score. Dialogue and identifying metadata remain
unchanged from the source corpus.

A four-configuration evaluation used the full 10,829-call corpus, 1,042-token
chunks with 260-token overlap, hybrid dense/BM25 retrieval, and 4,096-token
contexts. GLM 5.3 Flash answered; Qwen 3.8 Max judged.

| Configuration | Correct / questions | Judged accuracy |
| --- | ---: | ---: |
| hybrid | 2,593 / 2,962 | 87.5% |
| hybrid-rerank | 2,851 / 2,962 | 96.3% |
| oracle | 2,959 / 2,962 | 99.9% |
| no-context | 0 / 2,962 | 0.0% |

These are construction diagnostics on an automatically reviewed synthetic
cohort, not held-out results or human gold. Reranked multi-call accuracy is
348/428 (81.3%); questions can remain difficult despite passing source review.
All 11,848 retained outcomes passed exact-context and coverage verification.
The final quality reconciliation reused cached outcomes with zero new API calls.

Anonymous checksums and a pinned CLI download were verified after publication.
To fetch this exact release:

```sh
uv run salestranscriptqa fetch --repo EndgameLabs/SalesTranscriptQA --revision 183bd79178a3555351d25400225001a9b27ecc2f
```

See the [publication receipt](reports/full-v2-publication.json) and
[release verification](reports/full-v2-release-verification.json). The managed
full workflow is complete. Preserve local `runs/`, `data/`, SQLite files and API
artifacts for reproducibility; GitHub does not contain the entire resumable cache.
[Historical reboot checkpoint and recovery notes](docs/REBOOT-CHECKPOINT-20260918.md)
remain available. The project ran on `tango-middlegame` (exe.dev); the private
workspace README maintains the shared machine inventory.

## Attribution and licensing

Source data: [Salesforce/CRMArenaPro](https://huggingface.co/datasets/Salesforce/CRMArenaPro), accompanying [CRMArena-Pro: Holistic Assessment of LLM Agents on Diverse and Realistic Enterprise Tasks](https://arxiv.org/abs/2505.18878), from [Salesforce AI Research](https://github.com/SalesforceAIResearch/CRMArena).

This is an independent adaptation, not an official Salesforce benchmark or a reproduction of its CRM agent evaluation. Original code and documentation in this repository are MIT-licensed. Upstream data and transcript-derived releases retain CC BY-NC 4.0 terms; the MIT license does not relicense them. See [NOTICE.md](NOTICE.md).
