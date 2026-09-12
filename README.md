# SalesTranscriptQA

A planned dialogue RAG benchmark built from Salesforce's synthetic CRMArena-Pro sales calls, with separate B2B and B2C question sets and a companion CLI in this repository.

**Status: specification only.** The generation harness, CLI, pilot questions, and Hugging Face release are not implemented or published yet. The first target is 200 automatically validated questions: 50 single-call and 50 two-call questions per domain. Human review is not part of the planned validation process.

- [Specification](docs/SPEC.md): agreed scope, data contracts, generation and publication approach.
- [Decision record](docs/DECISIONS.md): source decisions and implementation defaults.
- [Tracking issues](https://github.com/Endgame-Labs/SalesTranscriptQA/issues): operational source of truth.
- [Attribution](NOTICE.md) and [upstream data license](LICENSE-DATA.txt).

The corpus preserves dialogue verbatim. Linked IDs are resolved into separate identifying metadata. Questions may use both dialogue and that metadata; advanced questions must require evidence from exactly two calls within one opportunity or lead.

Publication will use canonical Parquet plus Markdown transcript exports with YAML frontmatter. The planned `salestranscriptqa` CLI will fetch pinned Hugging Face releases, export corpora/questions, validate submissions, and support answer judging in the style of [EnronQA-cli](https://github.com/dorkitude/EnronQA-cli).

## Attribution and licensing

Source data: [Salesforce/CRMArenaPro](https://huggingface.co/datasets/Salesforce/CRMArenaPro), accompanying [CRMArena-Pro: Holistic Assessment of LLM Agents on Diverse and Realistic Enterprise Tasks](https://arxiv.org/abs/2505.18878), from [Salesforce AI Research](https://github.com/SalesforceAIResearch/CRMArena).

This is an independent adaptation, not an official Salesforce benchmark or a reproduction of its CRM agent evaluation. Original code and documentation in this repository are MIT-licensed. Upstream data and transcript-derived releases retain CC BY-NC 4.0 terms; the MIT license does not relicense them. See [NOTICE.md](NOTICE.md).
