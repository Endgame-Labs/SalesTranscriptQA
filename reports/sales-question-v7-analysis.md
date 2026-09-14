# Draft/edit experiment (v7)

100 first proposals on the same source units as v6: 28 accepted by existing gates,
72 rejected. Recorded generation/validation API estimate: $0.409811945. All 28
accepted outputs were inspected. Independent Qwen review is a separate diagnostic.

Editing usually shortens answers, but is not yet reliable as a production repair:

- Some revised questions lose useful name scope (Sara, Linda, or a generic Volvo
  price question). Rewriting must preserve sufficient entity context.
- One question introduces unbound first-person wording: “how did I address it?”
  A standalone benchmark has no authenticated salesperson identity to resolve “I”.
- Year-only call references slipped past the narrow date/month locator patterns.
- Some useful compound questions remain (budget/timeline, objection/response),
  along with less coherent pairings. Do not fix this with a blanket ban on “and”.
- The account-level Vertex quote remains ambiguous across different opportunities
  at the same company; the broader consistency audit found a directly supported
  alternative quote (5% and $2,849.95 versus 10% and $5,399.91). A customer/contact
  or substantive purchase scope may distinguish this naturally, without call dates.

The rewrite arm has not demonstrated enough benefit to select it over focused
fresh GLM generation. Remaining work: finish the reference-blind group-consistency
audit, apply a calibrated final acceptance gate, retain natural entity scope, and
evaluate a fresh seed before claiming the reusable generator is ready.
