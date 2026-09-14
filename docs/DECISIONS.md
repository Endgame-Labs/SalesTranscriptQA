# Decision record — September 12, 2026

The following relevant source statements by Kyle Wild establish the project scope. Follow-up confirmations are summarized to avoid reproducing unrelated conversation history. Implementation specifics beyond these agreements are marked as defaults in the specification.

> let's make a pure dialogue RAG question sets, one for the B2B sales calls and another for the B2C sales calls. we'll just use the transcripts from CRMArena-Pro.
>
> we can just call it SalesTranscriptQA and put the CLI in the same github repo.
>
> Endgame's github; we can borrow their questions too, just the subset that make sense for our the use case.

> actually how would we build the multi-call questions? i think those are a good idea too, just need to be their own more advanced class of question. yes questions can rely on the metadata..

> keep the dialogue verbatim

On metadata scope:

> yes just sort of use it to denormalize based on the ID

Confirmed individually:

- Single-call plus advanced multi-call classes; multi-call grouping within one opportunity or lead.
- Canonical Parquet and Markdown transcript exports with YAML frontmatter.
- Concise answers with explicit exact dialogue/metadata evidence.
- Answerable, factual questions only; two-call questions must actually require both calls.
- A balanced 200-question pilot, 50 per domain/class; exactly two calls for pilot multi-call questions.
- Full domain transcript corpus for retrieval, including calls not used to generate questions.
- New questions by default; upstream adaptations must pass the same validation.
- Python harness, SQLite progress/metadata, file artifacts and different model families for generation/validation.
- One Hugging Face dataset with B2B and B2C configurations.

After comparing exhaustive human review and sampled human audits, Kyle instructed:

> skip it

This supersedes the suggested human-review gate: use automated validation only and disclose that limitation.

Kyle then confirmed saving this specification in a public Endgame-Labs/SalesTranscriptQA repository and submoduling it into the research workspace. This milestone establishes a specification, not a completed pilot or CLI.

## Hugging Face organization selected

Kyle subsequently specified:

> okay we're gonna use this org: https://huggingface.co/EndgameLabs
>
> make a note of that and tell me the next step

Publish the dataset as **EndgameLabs/SalesTranscriptQA**. This supersedes the earlier tentative `endgame-labs` Hugging Face namespace. The GitHub organization remains **Endgame-Labs**. Publication awaits a write token with access to the selected Hugging Face organization.

## README presentation

Kyle requested that the GitHub README not link to GitHub issues. Keep the README focused on the dataset, CLI, usage, results and attribution; operational issue links belong in implementation/planning documentation.

## 2026-09-13 — Exhaustive expansion

Kyle selected “all of them” after being offered all eligible calls/call pairs versus a fixed QA count. Interpret this as every individual call and every distinct-dialogue pair within the same explicit opportunity or lead, not every possible question or cross-account combination. Attempt up to three proposals per source unit, keeping at most one passing QA; record exhausted units and global duplicate removals. Do not relax quality gates to reach a nominal count.

Use a fresh strengthened generation protocol and preserve the original pilot for reproducibility. Publishing the completed full cohort to the existing EndgameLabs/SalesTranscriptQA dataset is part of the authorized workflow. Main configurations expose the new cohort; separate pilot configurations and immutable history preserve the old one. No generation deadline or accepted yield is promised.

## September 14, 2026 — Adopt revised questions and expand validation

Kyle: “expand the generation sample size by 20x and then run another similar test against it” and “get rid of the bad ones from prior run, this new sample is better and we'll rely on this style of prompting and quality from now on for this project.”

Expand 100 source units to 2,000 using unchanged v9 generation and final quality gates. Exclude previously sampled CRM groups. Retire legacy pilot/full-v1 questions from active research; preserve historical artifacts and published pilot until a replacement release. Quarantine the ambiguous Sofia package question from the 37-question seed; retain SkyTech because its observed failure was retrieval-context truncation. Independently review and freeze expanded questions before RAG; do not remove difficult questions based on RAG scores. Track active inputs in reports/cohort-registry.json.

## September 14, 2026 — Agent supervision, shared $5,000 ceiling, conditional full run

Kyle requests that the assistant itself inspect progress and random quality samples hourly, fix issues, and monitor a $5,000 ceiling. If the 2,000-unit expansion and RAG test look good, proceed to the full eligible QA set under the same shared ceiling. Completion requires a secret-gist HTML report and HTML Preview link after the full workflow; a scripted health check or interim expanded-sample report alone is insufficient. Reuse compatible completed work, preserve frozen historical cohorts, and do not delete questions merely because retrieval fails.

## September 14, 2026, 08:00 UTC — Close the citation-validation gap

The assistant's random source audit found that candidate
`b2b-single_call-398ddef21e9e5869` cited only the customer's request for immediate
support while claiming the salesperson promised a dedicated team. The next line
supports the answer, but it was absent from the citation. Exact-span validation
and full-source model reviews therefore did not establish evidence entailment.
Add a separate quoted-evidence audit to independent review before freezing the
expanded/full cohorts. It receives no uncited dialogue, must cover every evidence
item, and must affirm support for the complete gold answer. Preserve the raw
candidate and exclude it if this new gate fails; do not silently repair historical
artifacts. This is an evidence-validation correction under the authorized hourly
quality supervision, not a change to question generation style.
