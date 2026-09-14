# Agent quality inspection — September 14, 2026, 04:00 UTC hour

Live process verified: generator PID 436544 under `salestranscriptqa-expanded-2000.service`. At the first snapshot: 85/2000 completed, 21 preliminary accepted, $29.82 recorded. Later snapshot reached 100/2000, 32 preliminary accepted, $33.71; work is progressing. Counts are before final coherence and two-call necessity selection.

Sample: six seeded random contract-accepted candidates, two per permitted domain/class; seed 2026091404. Exact questions, answers, and citations are preserved in `expanded-20260914-04-sample.json`. Production final-gate spot checks are in `expanded-20260914-04-gates.json`. No generator prompt or label was changed.

Agent findings:

- GreenStar multi-call combines product mechanics with a volume quote. The production coherence check permits it, but the stricter cross-family necessity check rejects it (DeepSeek false, GLM true). This is a compound-query/coherence boundary, not missing factual support. Keep it out if the final production gate rejects it; do not override the negative.
- FutureTech multi-call mostly restates a 10% quantity discount; the first call supplies the only price. Cross-family necessity also rejects it. The model disagreement illustrates why both families must pass.
- InnoBuild budget/deployment and ClearSky discounted price breakdown are concise and directly supported by cited dialogue.
- Ava's promised proposal is a clear follow-up commitment, directly supported.
- Charlotte's meeting time is concrete, but “other alternatives” is a vague comparison target. Watch this in the final independent review; do not treat the preliminary acceptance as final quality approval.

Outcome: no evidence of a runtime stall or corrupted generation; existing final gates caught both questionable multi-call drafts in this spot check. Continue the frozen run. Do not launch full generation until expanded final review and RAG results have been inspected. This six-question inspection is not a population quality estimate or human gold certification.

Budget: $5,000 shared ceiling for expansion plus conditional full run. Current conservative guards remain $850 generation, $150 independent review, $500 RAG; these are sublimits within the ceiling. Unknown usage and turbopuffer/VM are not included in recorded Fireworks totals.
