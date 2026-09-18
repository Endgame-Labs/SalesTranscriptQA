# SalesTranscriptQA

A dialogue RAG benchmark built from Salesforce's synthetic CRMArena-Pro sales calls, with separate B2B and B2C question sets and a companion CLI in this repository.

**Resumed after disk expansion (September 18, 2026, 06:29 UTC).** Full v9 generation and automated review have finished; RAG evaluation is partially complete. See the checkpoint and resume instructions below. B2C is single-call only; B2B supports single- and two-call questions. [Generation guide](docs/GENERATION.md) · [Cohort registry](reports/cohort-registry.json).

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

## Current run and saved reboot checkpoint

The user has resumed the work. The service and hourly timer are active again;
2,967 unchanged QA pairs remain after the three quality holds were reconciled.
The private evaluator now has a tested `reconcile_partial.py` migration that maps
cached embeddings by original question ID and preserves API receipts and costs.
Migration made no model calls. Disk space is now about 405 GB free. The managed
workflow replays cached reviews before resuming RAG. Next assistant inspection:
07:00 UTC. The notes below preserve the pause checkpoint and recovery procedure;
the previously outstanding partial-cache reconciliation is now implemented.

### Historical pause checkpoint and resumption

All 14,916 eligible source units have been processed. Generation selected 4,932
questions; source/citation and customer-history reviews reduced these to 2,970
frozen QA pairs (1,217 B2B single, 1,323 B2C single, 430 B2B multi). The latest
assistant sample added three evidence-context holds, leaving **2,967 eligible**
questions pending reconciliation. See the [latest quality inspection](reports/hourly-quality/full-20260918-04-review.md).
The 04 UTC inspection was performed early, before the user-requested pause.

The private sibling `../2026-09-12-salestranscriptqa-rag-evaluation/` owns RAG
execution. It has completed all 93 query-embedding batches and 845 successful
reranker requests against the frozen 2,970-question input; answering/judging has
not started. Its README contains the detailed resume requirements. Historical
results and dashboard links are earlier experiments, not this unfinished run.

Campaign API estimates at pause: **$4,541.95 recorded / $4,561.26 conservative**,
including unknown/in-flight reservations, against the shared **$5,000 ceiling**.
These are configured-rate Fireworks estimates, not an invoice; VM/storage,
Turbopuffer and assistant costs, and earlier pre-campaign work are excluded.
No revised full dataset has been published; Hugging Face still serves the legacy
200-question pilot. Final RAG verification, publication and secret-gist report
remain unfinished.

The generation/RAG service and hourly timer were stopped and disabled so reboot
will not restart paid work. Request-log compression was also stopped: 124,655
artifacts compressed losslessly, approximately 962 MB recovered. JSON and JSON.gz
artifacts are both supported. Preserve this repository's ignored `runs/`, `data/`,
SQLite databases and any WAL/SHM files, plus the private evaluator's ignored
`runs/`, `data/` and unfinished reports. **GitHub is not a backup of those caches.**
Resize the existing persistent disk; do not replace these directories with a
fresh clone. Credentials remain local in `~/.secrets/keys.env`.

After disk expansion and reboot:

1. Check disk space and that both repositories, local caches and credentials
   survived. Run `uv sync --frozen` in each Python repository.
2. Reconcile the three new ID holds before restarting the full workflow. The
   existing frozen file and RAG configuration still describe 2,970 questions;
   blindly starting the service will hit intentional quarantine/hash guards.
   Preserve the old cohort and query-to-vector/cache mapping. A safe cached
   subset-resume path is **not yet implemented**; implement and verify it first,
   retaining unchanged QA content and all historical costs. Do not remove holds,
   bypass guards, delete caches or regenerate the dataset to make it resume.
3. Once the cohort/cache reconciliation is verified, check the budget and resume
   from this repository:

   ```sh
   uv run python scripts/full_sample_workflow.py --checkpoint-review reports/expanded-2000-full-checkpoint.json --check-only
   systemctl --user reset-failed salestranscriptqa-full-v2.service
   systemctl --user start salestranscriptqa-full-v2.service
   systemctl --user enable --now salestranscriptqa-full-hourly.timer
   tail -f runs/sales-full-v2/rag-evaluation.log
   ```

   The service remains disabled for boot unless explicitly enabled later. The
   timer is a supplemental budget/health check, not a substitute for the requested
   assistant's hourly source-quality inspection. Resume those inspections too.
4. Complete all four RAG arms for the reconciled cohort, verify actual results,
   publish the reviewed release to `EndgameLabs/SalesTranscriptQA`, verify an
   anonymous CLI fetch, and create the final secret gist with an HTMLPreview link.
   Never select questions based on their RAG score.

## Attribution and licensing

Source data: [Salesforce/CRMArenaPro](https://huggingface.co/datasets/Salesforce/CRMArenaPro), accompanying [CRMArena-Pro: Holistic Assessment of LLM Agents on Diverse and Realistic Enterprise Tasks](https://arxiv.org/abs/2505.18878), from [Salesforce AI Research](https://github.com/SalesforceAIResearch/CRMArena).

This is an independent adaptation, not an official Salesforce benchmark or a reproduction of its CRM agent evaluation. Original code and documentation in this repository are MIT-licensed. Upstream data and transcript-derived releases retain CC BY-NC 4.0 terms; the MIT license does not relicense them. See [NOTICE.md](NOTICE.md).
