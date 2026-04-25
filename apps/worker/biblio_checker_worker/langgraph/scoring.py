from __future__ import annotations

import re
from difflib import SequenceMatcher

_PUNCT_RE = re.compile(r"[.,;:\"'()\[\]]")
_AUTHOR_PUNCT_RE = re.compile(r"[.,]")
_WHITESPACE_RE = re.compile(r"\s+")

_TITLE_WEIGHT = 0.55
_AUTHOR_WEIGHT = 0.30
_YEAR_WEIGHT = 0.15

_AUTHOR_BONUS_THRESHOLD = 0.8
_AUTHOR_FIRST_WEIGHT = 0.7
_AUTHOR_BONUS_MAX = 0.3


def _normalize_title(title: str) -> str:
    title = title.lower().strip()
    title = _PUNCT_RE.sub("", title)
    title = _WHITESPACE_RE.sub(" ", title).strip()
    return title


def _normalize_author(author: str) -> str:
    author = author.lower()
    author = _AUTHOR_PUNCT_RE.sub("", author)
    parts = sorted(author.split())
    return " ".join(parts)


def title_similarity(title_a: str | None, title_b: str | None) -> float:
    """Compute similarity between two titles. Returns 0.0-1.0.

    Returns 0.0 if either title is None or empty.
    Normalization: lowercase, strip, collapse whitespace, remove common punctuation.
    """
    if not title_a or not title_b:
        return 0.0
    norm_a = _normalize_title(title_a)
    norm_b = _normalize_title(title_b)
    if not norm_a or not norm_b:
        return 0.0
    return SequenceMatcher(None, norm_a, norm_b).ratio()


def author_similarity(authors_a: list[str], authors_b: list[str]) -> float:
    """Compute similarity between two author lists. Returns 0.0-1.0.

    First-author match carries 0.7 weight. Additional matches contribute a bonus
    of up to 0.3, weighted by what fraction of the longer list was matched.
    """
    if not authors_a or not authors_b:
        return 0.0

    norm_a = [_normalize_author(a) for a in authors_a]
    norm_b = [_normalize_author(b) for b in authors_b]

    first_author_sim = SequenceMatcher(None, norm_a[0], norm_b[0]).ratio()

    # Bonus: count how many authors in norm_a fuzzy-match any author in norm_b
    matched_count = 0
    for author in norm_a:
        for other in norm_b:
            if SequenceMatcher(None, author, other).ratio() >= _AUTHOR_BONUS_THRESHOLD:
                matched_count += 1
                break  # count each author in A at most once

    bonus = matched_count / max(len(norm_a), len(norm_b)) * _AUTHOR_BONUS_MAX

    return min(first_author_sim * _AUTHOR_FIRST_WEIGHT + bonus, 1.0)


def _year_similarity(ref_year: int | None, candidate_year: int | None) -> float:
    """Return year similarity with gradual degradation for different editions.

    Books often have multiple editions spanning decades (e.g. Kuhn 1962 vs 1986
    reprint). A strict ±1 tolerance penalizes legitimate re-editions.

    Returns: 1.0 exact, 0.8 ±1-2y, 0.5 ±3-5y, 0.0 beyond or if either is None.
    """
    if ref_year is None or candidate_year is None:
        return 0.0
    diff = abs(ref_year - candidate_year)
    if diff == 0:
        return 1.0
    if diff <= 2:
        return 0.8
    if diff <= 5:
        return 0.5
    return 0.0


def compute_match_score(
    *,
    ref_title: str | None,
    ref_authors: list[str],
    ref_year: int | None,
    candidate_title: str | None,
    candidate_authors: list[str],
    candidate_year: int | None,
) -> float:
    """Compute overall similarity score between a reference and a candidate.

    Returns a float in [0.0, 1.0] rounded to 4 decimal places.

    Weights: title=0.55, authors=0.30, year=0.15.
    """
    title_sim = title_similarity(ref_title, candidate_title)
    author_sim = author_similarity(ref_authors, candidate_authors)
    year_sim = _year_similarity(ref_year, candidate_year)

    score = (
        _TITLE_WEIGHT * title_sim
        + _AUTHOR_WEIGHT * author_sim
        + _YEAR_WEIGHT * year_sim
    )
    return round(min(score, 1.0), 4)
