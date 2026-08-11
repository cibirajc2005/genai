"""Bounded, deterministic query expansion used before retrying retrieval."""

import re

SYNONYMS = {
    "leave": ["vacation", "absence", "paid leave", "unpaid leave"],
    "notice": ["resignation", "termination", "employment notice period"],
    "risk": ["compliance", "penalty", "obligation", "business impact"],
    "deadline": ["due date", "expiry", "renewal date"],
}


def expand_query(query: str, limit: int = 5) -> list[str]:
    additions: list[str] = []
    words = set(re.findall(r"[a-z]+", query.lower()))
    for word, related in SYNONYMS.items():
        if word in words:
            additions.extend(related)
    generic = "policy requirement responsibility deadline compliance"
    candidates = [query, f"{query} {' '.join(additions)}".strip(), f"{query} {generic}"]
    return list(dict.fromkeys(candidates))[: min(limit, 5)]
