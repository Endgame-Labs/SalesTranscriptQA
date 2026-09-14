"""Retired legacy workflow; retained as a clear failure for old service commands."""

def main():
    raise RuntimeError(
        "Legacy full-v1 generation/publication is retired. "
        "Use scripts/generate_sales_questions.py with the validated sales-questions-v9-line-evidence protocol. "
        "See docs/GENERATION.md and reports/cohort-registry.json for the active cohort."
    )

if __name__ == "__main__":
    main()
