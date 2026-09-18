# Historical pause and recovery — September 18, 2026

These notes preserve the intermediate state; the full release is now complete.
Commands and filesystem paths assume the repository root.

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
questions pending reconciliation. See the [latest quality inspection](../reports/hourly-quality/full-20260918-04-review.md).
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

