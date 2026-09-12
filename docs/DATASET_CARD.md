---
license: cc-by-nc-4.0
language:
- en
task_categories:
- question-answering
tags:
- rag
- synthetic
- sales
- multi-hop
size_categories:
- n<1K
configs:
- config_name: b2b
  data_files:
  - split: test
    path: b2b-test.parquet
- config_name: b2c
  data_files:
  - split: test
    path: b2c-test.parquet
---

# SalesTranscriptQA — 200-question pilot

SalesTranscriptQA is an automatically generated and automatically validated dialogue RAG benchmark based on Salesforce's **synthetic CRMArena-Pro sales-call transcripts**. It contains 200 questions: 50 single-call and 50 two-call questions each for B2B and B2C.

**No human review or human calibration was performed.** This pilot was used to develop the generation pipeline; it is not an untouched test set. Automated agreement is not a measured human correctness rate.

## Contents

| Domain | Full corpus | Single-call QA | Two-call QA |
|---|---:|---:|---:|
| B2B | 4,033 calls | 50 | 50 |
| B2C | 6,796 calls | 50 | 50 |

Use the full corpus for the chosen domain when evaluating retrieval. The HF configurations `b2b` and `b2c` expose QA records. Corpus records are available separately in `b2b-corpus.parquet` and `b2c-corpus.parquet`. Markdown/YAML transcript exports are in the corresponding `*-markdown.zip` archives. `manifest.json` provides file counts/checksums and `upstream-manifest.json` pins original sources.

Each QA record contains question ID, domain, question class, question, concise gold answer, alternate answers, supporting call IDs, evidence and provenance. Each evidence annotation identifies a call and answer claim, plus either a verbatim dialogue quote with zero-based Unicode character offsets (end exclusive) or a metadata pointer/value. Supporting sources and gold answers must not be supplied to evaluated retrieval systems.

Transcript dialogue is preserved verbatim. Identifying metadata is denormalized through original IDs, with explicit field provenance. This is snapshot metadata, not a reconstruction of CRM state at call time. No CRM qualification labels, outcome fields or hidden business rules are supplied. A linked contact is not automatically labeled as a speaker.

## Construction

The initial corpus was extracted from the pinned public CRMArena-Pro B2B/B2C SQLite snapshots. All 10,829 voice-call bodies passed checksum/fidelity validation. Exact dialogue-body hashes were unique within each domain. Questions were generated with DeepSeek V4 Flash 0731 and independently answered/validated with GLM 5.3 Flash on Fireworks.

The generator selects evidence line ranges; code copies original passages and computes offsets. Validation includes schema/evidence integrity, independent answer agreement, no-context answerability checks with both model families, source selection among full-domain TF-IDF hard negatives, quality checks and a fresh final audit. Two-call questions are restricted to one shared opportunity or lead and must pass both single-call ablations and a source-based necessity check.

Each source group supplies at most one candidate per question class in a run. The final cohort is balanced by domain/class; rejected candidates are replaced without human intervention. No upstream task questions were adapted for this pilot. This implementation uses direct Python modules; it does not claim DSPy prompt optimization. See `generation-config.json`, `validation-audits.json` and `pilot-report.json` for settings, audit results, yields and costs.

## Evaluation

[The companion CLI and implementation](https://github.com/Endgame-Labs/SalesTranscriptQA) support pinned downloads, exports, submission validation, lexical and LLM judging, and retrieval reporting. Report results separately by B2B/B2C and single-/two-call class.

Required-call recall@k measures the fraction of annotated supporting calls retrieved. All-calls@k measures whether the entire annotated required set was retrieved. Both are useful for two-call questions; do not conflate them. Alternative valid evidence elsewhere in the corpus may not be annotated.

## Limitations

The source calls are synthetic, relatively short, and may contain artificial patterns or inconsistencies. Questions are generated with knowledge of their intended sources. They often use names and dates for retrieval specificity. No-context model failures do not prove absence from training data; single-call model failures do not prove logical necessity. The additional evidence-based checks reduce these risks without eliminating them. Human agreement and benchmark ranking stability are unmeasured.

The pilot contains no unanswerable questions, no subjective sales judgments, and no cross-opportunity/account-wide questions. Single-call and two-call examples may share source groups; there are no training/development splits and no claim of cross-split independence. Full-scale costs are projections from a small development pilot, not invoices.

## Attribution and license

Source: Salesforce AI Research, [CRMArena-Pro: Holistic Assessment of LLM Agents on Diverse and Realistic Enterprise Tasks](https://arxiv.org/abs/2505.18878), [original dataset](https://huggingface.co/datasets/Salesforce/CRMArenaPro), [source repository](https://github.com/SalesforceAIResearch/CRMArena).

Adaptation: SalesTranscriptQA, Kyle Wild / Endgame Labs. Modifications include transcript selection, identifying-metadata joins, generated QA/evidence, validation and publication formats. Dialogue remains verbatim. This project is independent and is not endorsed by Salesforce; it does not reproduce CRMArena-Pro's interactive workflow tasks or official rewards.

The **dataset is CC BY-NC 4.0**. Preserve attribution and notices, and identify adaptations. The separate implementation/CLI is MIT; that license does not grant commercial rights to the dataset. See `LICENSE-DATA.txt` and `NOTICE.md`.

Methodological inspiration: [EnronQA](https://arxiv.org/abs/2505.00263) and [HotpotQA](https://hotpotqa.github.io/). Exact evidence spans and two-call necessity checks extend EnronQA's construction methodology; human calibration is omitted here.
