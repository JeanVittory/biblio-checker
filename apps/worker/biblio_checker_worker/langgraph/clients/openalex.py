from __future__ import annotations

import re
import urllib.parse
from typing import Any

import httpx
import structlog

from biblio_checker_worker.langgraph.schemas import MatchCandidate

OPENALEX_BASE_URL = "https://api.openalex.org"

_DOI_PATTERN = re.compile(r"^10\.\d{4,}(/\S+)+$")

logger = structlog.stdlib.get_logger("biblio_checker_worker.langgraph.clients.openalex")


def _validate_doi(doi: str) -> bool:
    return bool(_DOI_PATTERN.match(doi))


def _sanitize_filter_value(value: str) -> str:
    """Remove characters that OpenAlex uses as filter delimiters."""
    return value.replace(",", " ").replace(":", " ")


def _extract_openalex_id(openalex_url: str) -> str:
    """Extract the W-prefixed ID from an OpenAlex URL."""
    return openalex_url.rstrip("/").split("/")[-1]


def _extract_doi(doi_url: str | None) -> str | None:
    """Strip 'https://doi.org/' prefix if present."""
    if doi_url is None:
        return None
    if doi_url.startswith("https://doi.org/"):
        return doi_url[len("https://doi.org/"):]
    return doi_url


def _parse_work(work: dict[str, Any], match_type: str, raw_score: float) -> MatchCandidate:
    openalex_url: str = work.get("id", "")
    external_id = _extract_openalex_id(openalex_url) if openalex_url else ""
    title: str | None = work.get("title") or None
    authorships: list[dict] = work.get("authorships", [])
    authors = [
        a["author"]["display_name"]
        for a in authorships
        if isinstance(a, dict) and isinstance(a.get("author"), dict) and a["author"].get("display_name")
    ]
    year: int | None = work.get("publication_year")
    doi = _extract_doi(work.get("doi"))
    url = openalex_url or None

    return MatchCandidate(
        source="openalex",
        external_id=external_id,
        title=title,
        authors=authors,
        year=year,
        doi=doi,
        url=url,
        match_type=match_type,
        raw_score=raw_score,
    )


class OpenAlexClient:
    def __init__(
        self,
        timeout: int,
        email: str = "",
        base_url: str = OPENALEX_BASE_URL,
    ) -> None:
        headers: dict[str, str] = {"Accept": "application/json"}
        if email:
            headers["User-Agent"] = f"BiblioChecker/0.1 (mailto:{email})"
        self._client = httpx.Client(base_url=base_url, timeout=timeout, headers=headers)

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
                logger.debug("search_request", source="openalex", strategy="doi_lookup", skipped=True, reason="invalid_doi_format")
            else:
                logger.info("search_starting", source="openalex", strategy="doi_lookup", doi=doi)
                result = self._doi_lookup(doi)
                logger.info("search_complete", source="openalex", candidates_found=len(result))
                if result:
                    return result

        # Strategy 2: Title + Author + Year
        if title is not None and authors and year is not None:
            logger.info("search_starting", source="openalex", strategy="title_author_year_search", title=title, first_author=authors[0], year=year)
            result = self._title_author_year_search(title, authors[0], year)
            logger.info("search_complete", source="openalex", candidates_found=len(result))
            if result:
                return result

        # Strategy 3: ISSN + Volume
        if issn is not None and volume is not None:
            logger.info("search_starting", source="openalex", strategy="issn_volume_search", issn=issn, volume=volume)
            result = self._issn_volume_search(issn, volume)
            logger.info("search_complete", source="openalex", candidates_found=len(result))
            if result:
                return result

        # Strategy 4: Title + Year
        if title is not None and year is not None:
            logger.info("search_starting", source="openalex", strategy="title_year_search", title=title, year=year)
            result = self._title_year_search(title, year)
            logger.info("search_complete", source="openalex", candidates_found=len(result))
            if result:
                return result

        # Strategy 5: Author + Title search
        if title is not None and authors:
            logger.info("search_starting", source="openalex", strategy="author_title_search", title=title, first_author=authors[0])
            result = self._author_title_search(title, authors[0])
            logger.info("search_complete", source="openalex", candidates_found=len(result))
            if result:
                return result

        # Strategy 6: Title only
        if title is not None:
            logger.info("search_starting", source="openalex", strategy="title_search", title=title)
            result = self._title_search(title)
            logger.info("search_complete", source="openalex", candidates_found=len(result))
            if result:
                return result

        logger.info("search_complete", source="openalex", candidates_found=0)
        return []

    def _doi_lookup(self, doi: str) -> list[MatchCandidate]:
        encoded_doi = urllib.parse.quote(doi, safe="")
        path = f"/works/https://doi.org/{encoded_doi}"
        logger.debug("search_request", source="openalex", url=str(self._client.base_url) + path)
        try:
            response = self._client.get(path)
        except httpx.HTTPStatusError:
            raise
        if response.status_code == 404:
            return []
        response.raise_for_status()
        try:
            work = response.json()
        except Exception:
            logger.warning("search_parse_error", source="openalex", strategy="doi_lookup", detail="malformed JSON")
            return []
        if not isinstance(work, dict):
            logger.warning("search_parse_error", source="openalex", strategy="doi_lookup", detail="unexpected response shape")
            return []
        return [_parse_work(work, match_type="doi_exact", raw_score=1.0)]

    def _title_author_year_search(self, title: str, first_author: str, year: int) -> list[MatchCandidate]:
        """Search by title, first author name, and publication year combined."""
        safe_title = _sanitize_filter_value(title[:500])
        safe_author = _sanitize_filter_value(first_author[:128])
        filter_value = f"title.search:{safe_title},raw_author_name.search:{safe_author},publication_year:{year}"
        logger.debug("search_request", source="openalex", url=f"{self._client.base_url}/works", params={"filter": filter_value})
        response = self._client.get("/works", params={"filter": filter_value, "per_page": 5})
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return self._parse_results_page(response, match_type="metadata_partial", raw_score=0.0)

    def _issn_volume_search(self, issn: str, volume: str) -> list[MatchCandidate]:
        """Search by journal ISSN and volume number combined."""
        safe_issn = _sanitize_filter_value(issn)
        safe_volume = _sanitize_filter_value(volume[:20])
        filter_value = f"primary_location.source.issn:{safe_issn},biblio.volume:{safe_volume}"
        logger.debug("search_request", source="openalex", url=f"{self._client.base_url}/works", params={"filter": filter_value})
        response = self._client.get("/works", params={"filter": filter_value, "per_page": 5})
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return self._parse_results_page(response, match_type="metadata_partial", raw_score=0.0)

    def _title_year_search(self, title: str, year: int) -> list[MatchCandidate]:
        """Search by title and publication year combined."""
        safe_title = _sanitize_filter_value(title[:500])
        filter_value = f"title.search:{safe_title},publication_year:{year}"
        logger.debug("search_request", source="openalex", url=f"{self._client.base_url}/works", params={"filter": filter_value})
        response = self._client.get("/works", params={"filter": filter_value, "per_page": 5})
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return self._parse_results_page(response, match_type="title_fuzzy", raw_score=0.0)

    def _title_search(self, title: str) -> list[MatchCandidate]:
        safe_title = _sanitize_filter_value(title[:500])
        logger.debug("search_request", source="openalex", url=f"{self._client.base_url}/works", params={"filter": f"title.search:{safe_title}"})
        try:
            response = self._client.get("/works", params={"filter": f"title.search:{safe_title}", "per_page": 5})
        except httpx.HTTPStatusError:
            raise
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return self._parse_results_page(response, match_type="title_fuzzy", raw_score=0.0)

    def _author_title_search(self, title: str, first_author: str) -> list[MatchCandidate]:
        safe_title = _sanitize_filter_value(title[:500])
        safe_author = _sanitize_filter_value(first_author[:128])
        filter_value = f"title.search:{safe_title},raw_author_name.search:{safe_author}"
        logger.debug("search_request", source="openalex", url=f"{self._client.base_url}/works", params={"filter": filter_value})
        try:
            response = self._client.get("/works", params={"filter": filter_value, "per_page": 5})
        except httpx.HTTPStatusError:
            raise
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return self._parse_results_page(response, match_type="metadata_partial", raw_score=0.0)

    def _parse_results_page(
        self,
        response: httpx.Response,
        match_type: str,
        raw_score: float,
    ) -> list[MatchCandidate]:
        try:
            data = response.json()
        except Exception:
            logger.warning("search_parse_error", source="openalex", detail="malformed JSON")
            return []
        if not isinstance(data, dict):
            logger.warning("search_parse_error", source="openalex", detail="unexpected response shape")
            return []
        results: list[Any] = data.get("results", [])
        if not isinstance(results, list):
            logger.warning("search_parse_error", source="openalex", detail="results field not a list")
            return []
        candidates: list[MatchCandidate] = []
        for work in results:
            if not isinstance(work, dict):
                continue
            try:
                candidates.append(_parse_work(work, match_type=match_type, raw_score=raw_score))
            except Exception:
                logger.warning("search_parse_error", source="openalex", detail="could not parse work entry")
                continue
        return candidates

    def close(self) -> None:
        self._client.close()
