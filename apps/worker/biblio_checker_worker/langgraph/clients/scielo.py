from __future__ import annotations

import re
from typing import Any

import httpx
import structlog

from biblio_checker_worker.langgraph.schemas import MatchCandidate

SCIELO_BASE_URL = "https://articlemeta.scielo.org/api/v1"

_DOI_PATTERN = re.compile(r"^10\.\d{4,}(/\S+)+$")

logger = structlog.stdlib.get_logger("biblio_checker_worker.langgraph.clients.scielo")


def _validate_doi(doi: str) -> bool:
    return bool(_DOI_PATTERN.match(doi))


def _parse_article(article_data: dict[str, Any], match_type: str, raw_score: float) -> MatchCandidate | None:
    """Parse an article response dict into a MatchCandidate.

    The response has a top-level 'code' and an 'article' dict with ISIS field codes.
    """
    code: str = article_data.get("code", "") or ""
    article: dict[str, Any] = article_data.get("article", {})
    if not isinstance(article, dict):
        return None

    # external_id: prefer v880[0]._, fall back to top-level code
    v880 = article.get("v880", [])
    external_id = code
    if isinstance(v880, list) and v880 and isinstance(v880[0], dict):
        external_id = v880[0].get("_", code) or code

    # title: v12[0]._
    v12 = article.get("v12", [])
    title: str | None = None
    if isinstance(v12, list) and v12 and isinstance(v12[0], dict):
        title = v12[0].get("_") or None

    # authors: v10[*] -> join n (given) + s (surname)
    v10 = article.get("v10", [])
    authors: list[str] = []
    if isinstance(v10, list):
        for author_entry in v10:
            if not isinstance(author_entry, dict):
                continue
            given = author_entry.get("n", "").strip()
            surname = author_entry.get("s", "").strip()
            parts = [p for p in [given, surname] if p]
            if parts:
                authors.append(" ".join(parts))

    # year: v65[0]._ first 4 characters
    v65 = article.get("v65", [])
    year: int | None = None
    if isinstance(v65, list) and v65 and isinstance(v65[0], dict):
        date_str = v65[0].get("_", "") or ""
        year_str = date_str[:4]
        if year_str.isdigit():
            year = int(year_str)

    # doi: v237[0]._
    v237 = article.get("v237", [])
    doi: str | None = None
    if isinstance(v237, list) and v237 and isinstance(v237[0], dict):
        doi = v237[0].get("_") or None

    # url: constructed from code
    url = f"https://www.scielo.br/scielo.php?pid={external_id}&script=sci_arttext" if external_id else None

    return MatchCandidate(
        source="scielo",
        external_id=external_id,
        title=title,
        authors=authors,
        year=year,
        doi=doi,
        url=url,
        match_type=match_type,
        raw_score=raw_score,
    )


class ScieloClient:
    def __init__(
        self,
        timeout: int,
        base_url: str = SCIELO_BASE_URL,
    ) -> None:
        self._client = httpx.Client(base_url=base_url, timeout=timeout)

    def search(
        self,
        *,
        title: str | None,
        authors: list[str],
        year: int | None,
        doi: str | None,
        arxiv_id: str | None,
        issn: str | None = None,
        volume: str | None = None,
        issue: str | None = None,
        pages: str | None = None,
        publisher: str | None = None,
    ) -> list[MatchCandidate]:
        # Strategy 1: DOI lookup
        if doi is not None:
            if not _validate_doi(doi):
                logger.debug("search_request", source="scielo", strategy="doi_lookup", skipped=True, reason="invalid_doi_format")
            else:
                logger.info("search_starting", source="scielo", strategy="doi_lookup", doi=doi)
                result = self._doi_lookup(doi)
                logger.info("search_complete", source="scielo", candidates_found=len(result))
                if result:
                    return result

        # Strategy 2: ISSN search
        if issn is not None:
            logger.info("search_starting", source="scielo", strategy="issn_search", issn=issn)
            result = self._issn_search(issn)
            logger.info("search_complete", source="scielo", candidates_found=len(result))
            return result

        logger.info("search_complete", source="scielo", candidates_found=0)
        return []

    def _doi_lookup(self, doi: str) -> list[MatchCandidate]:
        logger.debug("search_request", source="scielo", url=f"{self._client.base_url}/article/", params={"doi": doi})
        response = self._client.get("/article/", params={"doi": doi})
        if response.status_code == 404:
            return []
        response.raise_for_status()
        try:
            data = response.json()
        except Exception:
            logger.warning("search_parse_error", source="scielo", strategy="doi_lookup", detail="malformed JSON")
            return []
        if not isinstance(data, dict):
            logger.warning("search_parse_error", source="scielo", strategy="doi_lookup", detail="unexpected response shape")
            return []
        try:
            candidate = _parse_article(data, match_type="doi_exact", raw_score=1.0)
        except Exception:
            logger.warning("search_parse_error", source="scielo", strategy="doi_lookup", detail="could not parse article")
            return []
        if candidate is None:
            return []
        return [candidate]

    def _issn_search(self, issn: str) -> list[MatchCandidate]:
        """Two-step ISSN search: fetch article identifiers, then fetch each article by PID."""
        logger.debug("search_request", source="scielo", url=f"{self._client.base_url}/article/identifiers/", params={"issn": issn, "limit": 5})
        response = self._client.get("/article/identifiers/", params={"issn": issn, "limit": 5})
        if response.status_code == 404:
            return []
        response.raise_for_status()
        try:
            data = response.json()
        except Exception:
            logger.warning("search_parse_error", source="scielo", strategy="issn_search", detail="malformed JSON")
            return []
        if not isinstance(data, dict):
            logger.warning("search_parse_error", source="scielo", strategy="issn_search", detail="unexpected response shape")
            return []
        objects: list[Any] = data.get("objects", [])
        if not isinstance(objects, list):
            logger.warning("search_parse_error", source="scielo", strategy="issn_search", detail="objects field not a list")
            return []

        candidates: list[MatchCandidate] = []
        for obj in objects:
            if not isinstance(obj, dict):
                continue
            pid = obj.get("code", "")
            collection = obj.get("collection", "")
            if not pid:
                continue
            candidate = self._fetch_article_by_pid(pid, collection, match_type="issn_filter")
            if candidate is not None:
                candidates.append(candidate)

        return candidates

    def _fetch_article_by_pid(self, pid: str, collection: str, match_type: str = "title_fuzzy") -> MatchCandidate | None:
        params: dict[str, Any] = {"code": pid}
        if collection:
            params["collection"] = collection
        logger.debug("search_request", source="scielo", url=f"{self._client.base_url}/article/", params=params)
        response = self._client.get("/article/", params=params)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        try:
            data = response.json()
        except Exception:
            logger.warning("search_parse_error", source="scielo", strategy="pid_fetch", pid=pid, detail="malformed JSON")
            return None
        if not isinstance(data, dict):
            logger.warning("search_parse_error", source="scielo", strategy="pid_fetch", pid=pid, detail="unexpected response shape")
            return None
        try:
            return _parse_article(data, match_type=match_type, raw_score=0.0)
        except Exception:
            logger.warning("search_parse_error", source="scielo", strategy="pid_fetch", pid=pid, detail="could not parse article")
            return None

    def close(self) -> None:
        self._client.close()
