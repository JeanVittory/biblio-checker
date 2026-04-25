from __future__ import annotations

from typing import Any

import httpx
import structlog

from biblio_checker_worker.langgraph.schemas import MatchCandidate

OPENLIBRARY_BASE_URL = "https://openlibrary.org"

logger = structlog.stdlib.get_logger(
    "biblio_checker_worker.langgraph.clients.openlibrary"
)


def _parse_doc(doc: dict[str, Any], match_type: str) -> MatchCandidate:
    key: str = doc.get("key", "")
    title: str | None = doc.get("title") or None
    authors: list[str] = doc.get("author_name", [])
    if not isinstance(authors, list):
        authors = []
    year: int | None = doc.get("first_publish_year")
    if not isinstance(year, int):
        year = None
    url = f"{OPENLIBRARY_BASE_URL}{key}" if key else None

    return MatchCandidate(
        source="openlibrary",
        external_id=key,
        title=title,
        authors=authors,
        year=year,
        doi=None,
        url=url,
        match_type=match_type,
        raw_score=0.0,
    )


class OpenLibraryClient:
    def __init__(self, timeout: int, base_url: str = OPENLIBRARY_BASE_URL) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

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
        # Strategy 1: Title + Author (structured fields)
        if title and authors:
            logger.info(
                "search_starting",
                source="openlibrary",
                strategy="title_author_search",
                title=title,
                first_author=authors[0],
            )
            result = self._title_author_search(title, authors[0])
            logger.info(
                "search_complete", source="openlibrary", candidates_found=len(result)
            )
            if result:
                return result

        # Strategy 2: General query (searches across all fields including translations)
        if title and authors:
            query = f"{authors[0]} {title}"
            logger.info(
                "search_starting",
                source="openlibrary",
                strategy="general_query",
                query=query,
            )
            result = self._general_search(query)
            logger.info(
                "search_complete", source="openlibrary", candidates_found=len(result)
            )
            if result:
                return result

        # Strategy 3: Title only (general query)
        if title:
            logger.info(
                "search_starting",
                source="openlibrary",
                strategy="title_search",
                title=title,
            )
            result = self._general_search(title)
            logger.info(
                "search_complete", source="openlibrary", candidates_found=len(result)
            )
            if result:
                return result

        logger.info("search_complete", source="openlibrary", candidates_found=0)
        return []

    def _title_author_search(self, title: str, author: str) -> list[MatchCandidate]:
        params = {"title": title[:500], "author": author[:128], "limit": "5"}
        logger.debug(
            "search_request",
            source="openlibrary",
            url=f"{self._client.base_url}/search.json",
            params=params,
        )
        response = self._client.get("/search.json", params=params)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return self._parse_response(response, match_type="title_author")

    def _general_search(self, query: str) -> list[MatchCandidate]:
        params = {"q": query[:500], "limit": "5"}
        logger.debug(
            "search_request",
            source="openlibrary",
            url=f"{self._client.base_url}/search.json",
            params=params,
        )
        response = self._client.get("/search.json", params=params)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return self._parse_response(response, match_type="title_fuzzy")

    def _parse_response(
        self, response: httpx.Response, match_type: str
    ) -> list[MatchCandidate]:
        try:
            data = response.json()
        except Exception:
            logger.warning(
                "search_parse_error", source="openlibrary", detail="malformed JSON"
            )
            return []
        if not isinstance(data, dict):
            logger.warning(
                "search_parse_error",
                source="openlibrary",
                detail="unexpected response shape",
            )
            return []
        docs: list[Any] = data.get("docs", [])
        if not isinstance(docs, list):
            return []
        candidates: list[MatchCandidate] = []
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            try:
                candidates.append(_parse_doc(doc, match_type=match_type))
            except Exception:
                logger.warning(
                    "search_parse_error",
                    source="openlibrary",
                    detail="could not parse doc entry",
                )
                continue
        return candidates

    def close(self) -> None:
        self._client.close()
