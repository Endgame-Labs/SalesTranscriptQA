# SalesTranscriptQA

A dialogue RAG benchmark built from Salesforce's synthetic CRMArena-Pro sales calls, with separate B2B and B2C question sets and a companion CLI in this repository.

**Current direction: revised sales/account QA.** The validated `sales-questions-v9-line-evidence` prompt and quality gates are the standard for new generation. A 2,000-source-unit expansion is underway, followed automatically by independent source review and full-corpus RAG evaluation. B2C is single-call only; B2B supports single- and two-call questions. [Generation guide](docs/GENERATION.md) · [Cohort registry](reports/cohort-registry.json).

The earlier 200-question Hugging Face pilot and stopped legacy full-generation run are retired for new research. They remain historical artifacts; they will not be mixed into the revised cohort. The published [Hugging Face dataset](https://huggingface.co/datasets/EndgameLabs/SalesTranscriptQA) still serves that legacy pilot pending replacement publication. The revised 37-question sample yielded 36 active seed questions after quarantining one ambiguous package question.

The CLI is implemented and tested. [Legacy CLI release](https://github.com/Endgame-Labs/SalesTranscriptQA/releases/tag/v0.1.0) · [Historical pilot report](reports/PILOT.md) · [Revised generator readiness report](reports/GENERATOR_READINESS.md).

- [CLI and generation usage](docs/USAGE.md): installation, exports, judging and reproducible builds.
- [Pilot implementation choices](docs/IMPLEMENTATION.md): models, rates, sampling and validation settings.
- [Corpus inventory](reports/corpus-inventory.json): verified counts, identity joins and eligible call pairs.
- [Specification](docs/SPEC.md): agreed scope, data contracts, generation and publication approach.
- [Decision record](docs/DECISIONS.md): source decisions and implementation defaults.
- [Attribution](NOTICE.md) and [upstream data license](LICENSE-DATA.txt).

The corpus preserves dialogue verbatim. Linked IDs are resolved into separate identifying metadata. Questions may use both dialogue and that metadata; advanced questions must require evidence from exactly two calls within one opportunity or lead.

Publication uses canonical Parquet plus Markdown transcript exports with YAML frontmatter. The `salestranscriptqa` CLI fetches pinned Hugging Face releases, exports corpora/questions, validates submissions, and supports answer judging in the style of [EnronQA-cli](https://github.com/dorkitude/EnronQA-cli).

## Attribution and licensing

Source data: [Salesforce/CRMArenaPro](https://huggingface.co/datasets/Salesforce/CRMArenaPro), accompanying [CRMArena-Pro: Holistic Assessment of LLM Agents on Diverse and Realistic Enterprise Tasks](https://arxiv.org/abs/2505.18878), from [Salesforce AI Research](https://github.com/SalesforceAIResearch/CRMArena).

This is an independent adaptation, not an official Salesforce benchmark or a reproduction of its CRM agent evaluation. Original code and documentation in this repository are MIT-licensed. Upstream data and transcript-derived releases retain CC BY-NC 4.0 terms; the MIT license does not relicense them. See [NOTICE.md](NOTICE.md).
