# Attribution and data terms

SalesTranscriptQA is an independent project by Endgame Labs, maintained by Kyle Wild. It is not endorsed by Salesforce.

The source transcripts and eligible source questions come from Salesforce AI Research's **CRMArena-Pro: Holistic Assessment of LLM Agents on Diverse and Realistic Enterprise Tasks**:

- Paper: https://arxiv.org/abs/2505.18878
- Dataset: https://huggingface.co/datasets/Salesforce/CRMArenaPro
- Repository: https://github.com/SalesforceAIResearch/CRMArena
- Upstream license: https://github.com/SalesforceAIResearch/CRMArena/blob/6d84f3d71305af0fd3d5ed3c1936b7887464455a/LICENSE.txt

The upstream data are licensed under Creative Commons Attribution–NonCommercial 4.0 International. The full supplied license is retained in LICENSE-DATA.txt. Preserve attribution and license notices and identify modifications in redistributed adaptations. MIT licensing of this project's original implementation does not apply to the source data or waive the noncommercial restriction. Transcript-derived dataset releases will carry CC BY-NC 4.0 notices and upstream attribution.

Planned modifications: select voice-call transcripts, denormalize identifying metadata through source IDs, generate dialogue-grounded QA and evidence annotations, adapt eligible source questions, and provide Parquet/Markdown exports. Dialogue remains verbatim. No derived release exists at this specification stage.

Methodological inspiration: **EnronQA: Towards Personalized RAG over Private Documents**, Michael J. Ryan, Chris Nivera, Danmei Xu, and Daniel Campos (2025), https://arxiv.org/abs/2505.00263. CLI interface inspiration: https://github.com/dorkitude/EnronQA-cli. Preserve applicable copyright/license notices for any future code reuse.
