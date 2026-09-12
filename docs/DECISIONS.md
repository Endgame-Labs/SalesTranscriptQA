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
