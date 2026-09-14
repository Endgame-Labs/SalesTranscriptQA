"""Narrow checks for source-locator phrasing, not a ban on names or dates."""
import re

MONTH = r'(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?'
DATE = rf'(?:{MONTH}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?|\d{{4}}-\d{{2}}-\d{{2}})'
PATTERNS = {
    'dated_call_locator': re.compile(rf'\b(?:the\s+)?{DATE}\s+(?:sales\s+)?(?:call|conversation|discussion|meeting)\b|\b(?:call|conversation|discussion|meeting)\s+(?:on|dated|from)\s+{DATE}\b', re.I),
    'month_call_locator': re.compile(rf'\b{MONTH}\s+(?:call|conversation|discussion|meeting)\b', re.I),
    'year_call_locator': re.compile(r'\b(?:19|20)\d{2}\s+(?:call|conversation|discussion|meeting)\b', re.I),
    'unbound_first_person': re.compile(r'\b(?:I|me|my)\b'),
    'titled_call_locator': re.compile(r'\b(?:call|transcript|meeting)\s+(?:titled|entitled|named)\b', re.I),
    'numbered_source_locator': re.compile(r'\b(?:source|transcript|call)\s*#\s*\d+\b', re.I),
}


def locator_flags(question):
    return [name for name, pattern in PATTERNS.items() if pattern.search(question)]
