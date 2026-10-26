"""Normalization helpers for editor-managed lesson metadata."""

import unicodedata


def normalize_search_keywords(value: str | None) -> str:
    """Normalize phrase-per-line metadata and remove case-insensitive duplicates."""
    if not value:
        return ""

    phrases = []
    seen = set()
    for line in unicodedata.normalize("NFKC", value).splitlines():
        phrase = " ".join(line.split())
        key = phrase.casefold()
        if phrase and key not in seen:
            seen.add(key)
            phrases.append(phrase)

    return "\n".join(phrases)
