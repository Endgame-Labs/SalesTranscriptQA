# SalesTranscriptQA

A dialogue RAG benchmark built from Salesforce's synthetic CRMArena-Pro sales calls, with separate B2B and B2C question sets and a companion CLI in this repository.

**Status: 200-question pilot complete.** All 200 questions passed automated validation: 50 single-call and 50 two-call questions per domain, with the full 10,829-call corpus. No human review or calibration was performed. The CLI is implemented and tested. Hugging Face publication targets **EndgameLabs/SalesTranscriptQA** and is pending a write token with access to the [EndgameLabs organization](https://huggingface.co/EndgameLabs).

[Download the pilot and CLI release](https://github.com/Endgame-Labs/SalesTranscriptQA/releases/tag/v0.1.0) · [Pilot report and costs](reports/PILOT.md)

The final run accepted 200 of 256 candidates. Median answer length: 13 words. Estimated API spend: **$0.89 for the pilot; $0.92 including all development and smoke checks**. These are usage-based estimates, not invoices.

- [CLI and generation usage](docs/USAGE.md): installation, exports, judging and reproducible builds.
- [Pilot implementation choices](docs/IMPLEMENTATION.md): models, rates, sampling and validation settings.
- [Corpus inventory](reports/corpus-inventory.json): verified counts, identity joins and eligible call pairs.
- [Specification](docs/SPEC.md): agreed scope, data contracts, generation and publication approach.
- [Decision record](docs/DECISIONS.md): source decisions and implementation defaults.
- [Implementation and pilot issue #1](https://github.com/Endgame-Labs/SalesTranscriptQA/issues/1): operational source of truth.
- [Attribution](NOTICE.md) and [upstream data license](LICENSE-DATA.txt).

The corpus preserves dialogue verbatim. Linked IDs are resolved into separate identifying metadata. Questions may use both dialogue and that metadata; advanced questions must require evidence from exactly two calls within one opportunity or lead.

Publication uses canonical Parquet plus Markdown transcript exports with YAML frontmatter. The `salestranscriptqa` CLI fetches pinned Hugging Face releases, exports corpora/questions, validates submissions, and supports answer judging in the style of [EnronQA-cli](https://github.com/dorkitude/EnronQA-cli).

## Attribution and licensing

Source data: [Salesforce/CRMArenaPro](https://huggingface.co/datasets/Salesforce/CRMArenaPro), accompanying [CRMArena-Pro: Holistic Assessment of LLM Agents on Diverse and Realistic Enterprise Tasks](https://arxiv.org/abs/2505.18878), from [Salesforce AI Research](https://github.com/SalesforceAIResearch/CRMArena).

This is an independent adaptation, not an official Salesforce benchmark or a reproduction of its CRM agent evaluation. Original code and documentation in this repository are MIT-licensed. Upstream data and transcript-derived releases retain CC BY-NC 4.0 terms; the MIT license does not relicense them. See [NOTICE.md](NOTICE.md).
