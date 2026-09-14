# Paired sales-question prompt experiment (v6)

Same seeded 100 source units per arm: 50 B2C single, 25 B2B single, 25 B2B multi.
No replacement of failed proposals. These are provisional gate outcomes, not validated
accuracy or release acceptance.

| Generator | Accepted by existing gates | Rejected | Estimated generation + gate API cost |
|---|---:|---:|---:|
| DeepSeek Flash | 29 | 71 | $0.306735002 |
| GLM Flash | 33 | 67 | $0.351881910 |

All 29 DeepSeek and 33 GLM accepted outputs were inspected during this iteration.
Natural customer names substantially improve readability and allow concise scoped
questions, such as Elizabeth Choi's purchase budget or Linda Olsson's lease preference.
The results are not yet sufficient to choose the production architecture.

Observed problems:

- Four accepted DeepSeek questions still locate a source by date/month and call;
  one GLM question does likewise. Narrow deterministic locator checks catch these.
- The independent Qwen review passed all 29 DeepSeek accepted questions, including
  the dated-call locators. Thus a general wording rubric alone is not a reliable
  style gate. It also passed 8 of 10 sampled rejected questions; those deserve
  failure-stage examination rather than automatic reinstatement.
- GLM tends to bundle several requested facts into a single-call question and write
  longer answers. Some combinations are useful (budget and purchase timeline),
  while others are less coherent (follow-up scheduling and two vehicle models).
  A stronger coherent-information-need constraint is needed, without banning all
  compound questions or natural customer names.
- DeepSeek has mechanical/schema failures in addition to content failures; the
  exact-source specificity and atomic-contract gates also reject many proposals.
  These reasons cannot be collapsed into a single model-quality failure rate.

Next work: examine independent GLM review and rejected-stage evidence, compare a
normalization/rewrite pass with fresh generation, incorporate explicit locator
checks and account-level coherence, and calibrate answer ambiguity on accepted
items. Re-run a fresh 100 after choosing the revised pipeline. Do not run the full
corpus or publish during this research phase.

Sources: the paired `sales-questions-v6-*-seed20260915-n100.json` reports and
independent `*-qwen-review-v1.json` reports in this directory. Full request/candidate
artifacts and per-attempt costs are in the corresponding ignored `runs/` directories.
Qwen review is an automated diagnostic, not a human gold label.

Independent GLM-arm review: `{'accepted/pass': 33, 'rejected/pass': 10}`, estimated Qwen cost $0.219510.
