"""Conservative explicit-speaker absence precheck (not enabled by default).

Only known full speaker names in clear subject/recipient/possessive positions are
considered. Any literal name token anywhere in the source group keeps model review.
Negated, alternative, conditional, and hypothetical questions always fall back.
"""
import json
import re
import unicodedata

VERSION='explicit-speaker-absence-v1'
FALLBACK=re.compile(r"\b(no|not|never|except|excluding|without|unless|either|or|versus|vs|unlike|if|would|could|might|assuming|but|whether|any|ever|none|zero|times|many|count|number|absent|present|attend|attended|participate|participated|join|joined)\b|n['’]t|other than|rather than|instead of",re.I)
ROLES={'agent','customer','representative','support','sales','manager','team','department','unknown','speaker','assistant'}


def words(text):
    text=''.join(c for c in unicodedata.normalize('NFKD',text.casefold()) if not unicodedata.combining(c))
    return re.findall(r'[^\W\d_]+',text)


def speaker_catalog(calls):
    names=set()
    for call in calls:
        for name in re.findall(r'^\[[^\]]+\]\s+([^:\n]{2,90}):',call['dialogue'],re.M):
            parts=tuple(words(name))
            if len(parts)>=2 and all(len(w)>=2 for w in parts) and not set(parts)&ROLES:names.add(parts)
    return frozenset(names)


def required_speakers(question,names):
    if FALLBACK.search(question) or re.search(r'(^|,\s*)(did|does|is|was|were|are|has|have|can|will)\b',question,re.I):return []
    text=' '+' '.join(words(question))+' ';found=[]
    for name in names:
        phrase=' '+' '.join(name)+' '
        offset=text.find(phrase)
        if offset<0:continue
        before=text[:offset].split();after=text[offset+len(phrase):].split()
        if (before and before[-1] in {'did','does','do','has','had','to','for','from','with','by'}) or (after and after[0]=='s'):
            found.append(name)
    return sorted(found)


def absent_speakers(question,calls,names):
    required=required_speakers(question,names)
    source_tokens=set(words(json.dumps(calls,ensure_ascii=False)))
    return [' '.join(name) for name in required if not set(name)&source_tokens]
