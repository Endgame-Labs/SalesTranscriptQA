# Sales question redesign experiments

The target is a question a sales rep or account manager would ask about a customer,
account or opportunity. Natural participant names are allowed. Avoid repetitive
source-location scaffolding such as “in the July 11 call titled … with …”. Business
appointment/deadline dates are legitimate content. Initial/follow-up wording can
appear occasionally. B2C uses single-call questions only; B2B also has same-group
multi-call questions. Transcript dialogue remains verbatim.

These are bounded experiments, not the replacement production generator yet.
Full generation and automatic publication remain stopped. The current research
budget ceiling is $1,000; recorded Fireworks costs are estimates, not invoices.

Run from the repository root with the corpus already available:

```bash
uv run python scripts/sales_question_experiment.py --model deepseek --count 100
uv run python scripts/sales_question_experiment.py --model glm --count 100
uv run python scripts/review_sales_sample.py reports/sales-questions-v6-deepseek-seed20260915-n100.json
uv run python scripts/review_sales_sample.py reports/sales-questions-v6-glm-seed20260915-n100.json
```

Each experiment is capped at 100 source units. The seed fixes the same random
source units for both generators: half B2C single, quarter B2B single, quarter B2B
multi. Each unit gets one proposal; failures are reported rather than replaced.
Changing the prompt requires a new version/run directory. Run locks prevent two
processes writing the same experiment. SQLite stores progress and metered request
attempts; JSON files preserve prompts, sources, generated artifacts and decisions.
A repeated command reuses the frozen request/candidate cache. The existing shared
Fireworks transport handles rate limits with exponential backoff, jitter and
Retry-After. No command here publishes data or starts full generation.

Current checks include exact evidence spans, an independently answered question
using the other model family, no-context controls, one-call ablations for multi-call
questions, factual/answer-completeness audits, source specificity, and the existing
question-first atomic answer contract. Single-call candidates do not depend on
inapplicable two-call flags. A separate Qwen reviewer inspects all accepted items
and ten seeded rejected items for sales usefulness, natural language, source
support and exact question/answer alignment.

Known limitations under investigation:

- The legacy specificity check still demands the original source set among ten
  lexical distractors. It can reject alternative evidence supporting the same
  answer; it does not prove corpus-wide uniqueness.
- A prompt instruction alone has not reliably stopped date/call preambles.
  Independent review results must be inspected before choosing final gates.
- Multi-call questions may look natural yet merely concatenate unrelated facts.
  Both the factual ablations and the account-level coherence check matter.
- Automated judgments are fallible. Prior blinded extraction experiments found
  actual alternate answers but also partial-answer false positives; those findings
  must guide a calibrated replacement specificity check, not an untested waiver.

The v4/v5 reports preserve earlier scope/wording experiments. Their participant-name
restrictions were an overcorrection and are superseded by v6; their results should
not be treated as the desired style specification.
