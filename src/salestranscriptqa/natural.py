"""Experimental content-led questions; isolated from the frozen full-v1 run."""
from .full import Full

OLD_ANCHORS = "Use identifying names and call dates in the question to make its subject unambiguous."
NATURAL_PROMPT = (
    "Write a realistic business question whose answer must be found by searching the dialogue content. "
    "Do NOT identify source calls in the question: no call dates, timestamps, record IDs, 'in the call', "
    "or numbered source-call framing. Do not use participant names as document lookup keys. "
    "Prefer substantive context such as the business problem, purchase requirement, objection, "
    "or proposed solution. Use a company or product name only when necessary to scope the business "
    "question; do not stack identifying names. Do not replace dates with a unique quote or leak "
    "the answer through an elaborate description. The question must still be self-contained and "
    "have a determinate supported answer; avoid generic questions applicable to many customers. "
    "For two sources, ask one coherent business question integrating their distinct facts, "
    "not two unrelated lookups joined with 'and'. Occasional initial-discussion or follow-up wording is allowed when it meaningfully scopes a business question, but prefer content-led wording and avoid using this as a template. You may ask about a supported change, tradeoff, "
    "requirement and response, or complementary aspects of the same decision. Do not invent causality. "
)


class Natural(Full):
    version = "natural-pilot-v2"

    def ask(self, model, instruction, value, stage, job):
        if stage == "generate":
            assert OLD_ANCHORS in instruction
            instruction = instruction.replace(OLD_ANCHORS, NATURAL_PROMPT)
        if stage in ("quality_audit", "final_audit"):
            instruction += (
                " Also reject questions with source-locator scaffolding: exact call dates/timestamps, "
                "participant names used as lookup keys, or numbered source-call framing. Initial-discussion or follow-up wording is allowed when it meaningfully scopes the business question. "
                "Require a natural content-led business question with enough context for a determinate "
                "answer. Company/product names are allowed only as meaningful business scope. "
                "For multiple sources require a coherent business relationship between the requested facts."
            )
        return super().ask(model, instruction, value, stage, job)
