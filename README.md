# SalesTranscriptQA

A dialogue RAG benchmark built from Salesforce's synthetic CRMArena-Pro sales calls. This repository contains the dataset-generation implementation and the `salestranscriptqa` CLI for fetching transcripts, exporting questions, and evaluating answers.

**Full v2: 2,962 reviewed QA pairs over 10,829 verbatim call transcripts.** Published September 18, 2026.

[Hugging Face dataset](https://huggingface.co/datasets/EndgameLabs/SalesTranscriptQA) · [Pinned release](https://huggingface.co/datasets/EndgameLabs/SalesTranscriptQA/tree/183bd79178a3555351d25400225001a9b27ecc2f) · [CLI usage](docs/USAGE.md) · [Generation guide](docs/GENERATION.md)

## Dataset

Questions use the dialogue and identifying metadata resolved from explicit CRM IDs. Single-call questions are answerable from one call; advanced B2B questions require evidence from exactly two calls within one opportunity. B2C questions are single-call only.

| Question set | QA pairs | Corpus calls |
| --- | ---: | ---: |
| B2B single-call | 1,215 | 4,033 |
| B2B multi-call | 428 | Same B2B corpus |
| B2C single-call | 1,319 | 6,796 |
| **Total** | **2,962** | **10,829** |

The corpus preserves dialogue verbatim. Metadata is separate from the dialogue and can include account, contact, lead, opportunity and timestamp fields. Questions can use participant names and substantive event descriptions without requiring repetitive call-title/date preambles.

Each QA record includes a stable `question_id`, domain, question class, question, reference answer, supporting call IDs, exact evidence spans, and generation provenance. Corpus and question files are canonical Parquet; Markdown transcript exports use YAML frontmatter for metadata. The release also includes frozen question JSON, coverage and validation records, and a checksum manifest. See the [specification](docs/SPEC.md) and [corpus inventory](reports/corpus-inventory.json).

### Example questions

These are unchanged questions and reference answers from the published cohort.

**B2B single-call**

> What future product updates did Chidi tell EcoWave's Olivia Williams are in development?

Enhancements to AI Cirku-Tech and OptiPower Manager to increase efficiency and accuracy in power optimization, rolled out with minimal disruption.

**B2C single-call**

> What two vehicle models did Ravi suggest to Linda Olsson during her discovery call, and what did he say each offers?

The 2023 Nissan Leaf (advanced driver-assistance, e-Pedal) and the 2024 Volkswagen ID.4 (spacious interior, intuitive interface, panoramic sunroof).

**B2B multi-call**

> Across the Innovatech Group EDA opportunity, what flexibility-related requirement did Sophia Zhang emphasize in the initial discussion, and what customization concern did she raise after the demo?

Initially she wanted solutions flexible enough to adapt to Innovatech's own security policies; after the demo she worried TechPulse's standardized offerings were less customizable than competitors' for their unique needs.

## Quick start

Install the CLI and fetch the immutable full-v2 release:

```sh
uv tool install git+https://github.com/Endgame-Labs/SalesTranscriptQA.git
salestranscriptqa fetch --repo EndgameLabs/SalesTranscriptQA --revision 183bd79178a3555351d25400225001a9b27ecc2f --data-dir salestranscriptqa-data
salestranscriptqa documents export --domain b2b --output calls.jsonl
salestranscriptqa questions export --domain b2b --output questions.jsonl
salestranscriptqa questions sample --domain b2b --count 4 --seed 42 --include-answer
```

Question exports omit reference answers and source evidence unless explicitly requested. Index the complete corpus for the selected domain; restricting retrieval to annotated supporting calls leaks benchmark labels. The CLI verifies release checksums and supports Markdown exports, submission validation, lexical scoring, external judgments, and direct model judging in the style of [EnronQA-cli](https://github.com/dorkitude/EnronQA-cli). See [usage and answer-submission format](docs/USAGE.md).

## How the questions were built

The full run processed **14,916 eligible source units**: 4,033 B2B calls, 6,796 B2C calls, and 4,087 B2B call pairs within one opportunity. Processing every unit does not guarantee an accepted question for every unit. Compatible decisions from the earlier 2,000-unit checkpoint were reused.

1. **Generate and independently answer.** The v9 prompt uses GLM 5.3 Flash to propose questions and DeepSeek v4 Flash to independently answer them through Fireworks.
2. **Check the proposed question and evidence.** Recorded gates check exact evidence, answer requirements, consistency, coherence, and no-context answerability. Multi-call questions must need both source calls.
3. **Review sources and citations independently.** Qwen reviews full source calls and separately checks whether the selected quotations support the answer's claims.
4. **Check the customer's full history.** Explicit account/lead IDs expand the source pool. GLM and Qwen independently answer without seeing the reference answer or designated gold-call IDs. Both must find a determinate answer; a separate comparison checks agreement and reference completeness.
5. **Inspect random source samples.** Assistant inspections compare questions, answers and evidence with the underlying transcripts. Holds include ambiguous event scope, unsupported commitments or rankings, and quotations missing necessary context. A true answer can still have defective evidence.
6. **Freeze and evaluate.** The published cohort has 2,962 questions after review. No question was removed because of its RAG score. Later source-quality holds were applied to unchanged cached outcomes before publication.

The Python harness uses SQLite for progress and metadata, files for artifacts, and Parquet for publication. Requests are cached; bounded exponential backoff, jitter, Retry-After and shared cooldown handle rate limits. The implementation does not require DSPy or spaCy. [Generation and reproducibility details](docs/GENERATION.md) · [Decision record](docs/DECISIONS.md) · [Cohort registry](reports/cohort-registry.json).

## Retrieval evaluation

All four configurations answer the same 2,962 questions against the complete domain-specific corpus. The answerer is **GLM 5.3 Flash** through Fireworks; **Qwen 3.8 Max** judges correctness, reference validity and support from the delivered context.

| Component | Setting |
| --- | --- |
| Chunking | 1,042 `cl100k_base` tokens; 260-token overlap |
| Embeddings | Fireworks Qwen3 Embedding 8B; 1,024 dimensions |
| Search | Native turbopuffer dense top 50 + BM25 top 50 |
| Fusion | Equal-weight reciprocal rank fusion, RRF(60) |
| Reranking comparison | Qwen3 Reranker 8B over the unique candidate union versus fusion order alone |
| Context | Pack the first 50 ranked chunks into 4,096 tokens; truncate the final chunk; no neighbor expansion |
| Oracle control | Complete annotated gold calls, including metadata |
| No-context control | Question without retrieved dialogue |

Gold answers and annotated source IDs do not enter retrieval, reranking or RAG answering. All **11,848 retained outcomes** passed exact-context and coverage verification.

### Answer accuracy

| Configuration | Overall | Single-call | Multi-call |
| --- | ---: | ---: | ---: |
| Hybrid | 87.5% (2,593/2,962) | 91.6% (2,322/2,534) | 63.3% (271/428) |
| Hybrid + reranker | 96.3% (2,851/2,962) | 98.8% (2,503/2,534) | 81.3% (348/428) |
| Oracle | 99.9% (2,959/2,962) | 99.9% (2,531/2,534) | 100.0% (428/428) |
| No context | 0.0% (0/2,962) | 0.0% (0/2,534) | 0.0% (0/428) |

Reranking improves overall judged accuracy by 8.7 percentage points. Multi-call questions remain more difficult, improving from 63.3% to 81.3%.

### Retrieval quality

| Configuration | Call recall @5 | Call recall @10 | All source calls in context | All cited evidence in context |
| --- | ---: | ---: | ---: | ---: |
| Hybrid | 90.1% | 96.7% | 88.6% | 83.3% |
| Hybrid + reranker | 98.1% | 99.0% | 96.9% | 94.7% |

Top-k counts **chunks**. Call recall averages the fraction of annotated source calls retrieved; all-source coverage requires every supporting call. Evidence coverage requires the full cited spans and can be stricter than having enough information to answer. Supporting-call annotations are not exhaustive relevance judgments.

## Interpretation and limitations

This is an automatically reviewed synthetic cohort, not human gold or a held-out estimate of general RAG performance. The answerer and source-review models participated in construction checks, which biases the oracle control. Source groups can recur across questions, and full generation includes previously sampled groups.

Compare reranked and non-reranked results within this cohort. Differences from earlier pilots can reflect changes in question composition and source-review filtering. Automated judges can confuse full sources with the delivered context; a failed answer can arise from retrieval, context truncation, answering, judging, or unresolved question ambiguity. Source-level inspection remains necessary. Oracle failures were retained.

The earlier 200-question pilot and legacy generation run are retired from active use. Historical pilot files remain under `pilot/` in the dataset and are not mixed into full v2.

## Release verification and reproduction

The published release passed anonymous file checksums and an immutable-revision CLI fetch. [Publication receipt](reports/full-v2-publication.json) · [Release verification](reports/full-v2-release-verification.json).

The managed full workflow is complete. Preserve local `runs/`, `data/`, SQLite databases and request artifacts for a full cached replay; GitHub does not contain the entire resumable cache. [Historical reboot checkpoint and recovery notes](docs/REBOOT-CHECKPOINT-20260918.md) remain available. The project ran on exe.dev `tango-middlegame`; the private workspace README maintains the shared machine inventory.

## Attribution and licensing

Source data: [Salesforce/CRMArenaPro](https://huggingface.co/datasets/Salesforce/CRMArenaPro), accompanying [CRMArena-Pro: Holistic Assessment of LLM Agents on Diverse and Realistic Enterprise Tasks](https://arxiv.org/abs/2505.18878), from [Salesforce AI Research](https://github.com/SalesforceAIResearch/CRMArena).

This is an independent adaptation by **Kyle Wild / Endgame Labs**, not an official Salesforce benchmark or a reproduction of its CRM agent evaluation. Original code and documentation are **MIT-licensed**. Upstream data and transcript-derived releases retain **CC BY-NC 4.0** terms; the MIT license does not relicense them. See [NOTICE.md](NOTICE.md) and [data license](LICENSE-DATA.txt).
