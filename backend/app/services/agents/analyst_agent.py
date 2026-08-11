"""Evidence-only analyst helper."""


def summarize_evidence(evidence: list[dict], limit: int = 8) -> str:
    return "\n".join(
        f"[Source {index}] {item['text'][:400]}"
        for index, item in enumerate(evidence[:limit], 1)
    )
