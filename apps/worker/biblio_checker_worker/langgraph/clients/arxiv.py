from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from typing import Any

import httpx
import structlog

from biblio_checker_worker.langgraph.schemas import MatchCandidate

ARXIV_BASE_URL = "https://export.arxiv.org/api"

_DOI_PATTERN = re.compile(r"^10\.\d{4,}(/\S+)+$")
_ARXIV_ID_NEW = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")
_ARXIV_ID_OLD = re.compile(r"^[a-z-]+/\d{7}$")

# XML namespaces used by arXiv Atom responses
_ATOM_NS = "http://www.w3.org/2005/Atom"
_ARXIV_NS = "http://arxiv.org/schemas/atom"

logger = structlog.stdlib.get_logger("biblio_checker_worker.langgraph.clients.arxiv")

_ARXIV_QUERY_SPECIAL = re.compile(r'["\(\)]')
_ARXIV_BOOLEAN_PATTERN = re.compile(r'\b(AND|OR|ANDNOT)\b', re.IGNORECASE)


def _sanitize_arxiv_term(value: str) -> str:
    """Remove arXiv boolean operators and syntax characters from a search term."""
    cleaned = _ARXIV_BOOLEAN_PATTERN.sub("", value)
    cleaned = _ARXIV_QUERY_SPECIAL.sub("", cleaned)
    return cleaned.strip()


def _validate_doi(doi: str) -> bool:
    return bool(_DOI_PATTERN.match(doi))


def _validate_arxiv_id(arxiv_id: str) -> bool:
    return bool(_ARXIV_ID_NEW.match(arxiv_id) or _ARXIV_ID_OLD.match(arxiv_id))


def _extract_arxiv_id_from_url(url: str) -> str:
    """Extract bare arXiv ID (without version) from an abs URL like http://arxiv.org/abs/2301.12345v1."""
    bare = url.rstrip("/").split("/")[-1]
    # Strip version suffix like 'v1'
    bare = re.sub(r"v\d+$", "", bare)
    return bare


def _parse_entry(entry: ET.Element, match_type: str, raw_score: float) -> MatchCandidate | None:
    """Parse a single Atom <entry> element into a MatchCandidate."""
    # <id>
    id_el = entry.find(f"{{{_ATOM_NS}}}id")
    if id_el is None or not id_el.text:
        return None
    abs_url: str = id_el.text.strip()
    external_id = _extract_arxiv_id_from_url(abs_url)

    # <title>
    title_el = entry.find(f"{{{_ATOM_NS}}}title")
    title: str | None = None
    if title_el is not None and title_el.text:
        title = " ".join(title_el.text.split())  # collapse whitespace

    # <author><name>
    authors: list[str] = []
    for author_el in entry.findall(f"{{{_ATOM_NS}}}author"):
        name_el = author_el.find(f"{{{_ATOM_NS}}}name")
        if name_el is not None and name_el.text:
            authors.append(name_el.text.strip())

    # <published> year portion
    published_el = entry.find(f"{{{_ATOM_NS}}}published")
    year: int | None = None
    if published_el is not None and published_el.text:
        year_str = published_el.text.strip()[:4]
        if year_str.isdigit():
            year = int(year_str)

    # <arxiv:doi>
    doi_el = entry.find(f"{{{_ARXIV_NS}}}doi")
    doi: str | None = None
    if doi_el is not None and doi_el.text:
        doi = doi_el.text.strip() or None

    return MatchCandidate(
        source="arxiv",
        external_id=external_id,
        title=title,
        authors=authors,
        year=year,
        doi=doi,
        url=abs_url,
        match_type=match_type,
        raw_score=raw_score,
    )


def _parse_feed(xml_text: str, match_type: str, raw_score: float) -> list[MatchCandidate]:
    """Parse Atom XML feed returned by arXiv API."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError(f"XML parse error: {exc}") from exc

    entries = root.findall(f"{{{_ATOM_NS}}}entry")
    candidates: list[MatchCandidate] = []
    for entry in entries:
        try:
            candidate = _parse_entry(entry, match_type=match_type, raw_score=raw_score)
            if candidate is not None:
                candidates.append(candidate)
        except Exception:
            logger.warning("search_parse_error", source="arxiv", detail="could not parse entry")
            continue
    return candidates


class ArxivClient:
    def __init__(
        self,
        timeout: int,
        base_url: str = ARXIV_BASE_URL,
    ) -> None:
        self._client = httpx.Client(base_url=base_url, timeout=timeout)
        self._request_count = 0

    def _throttle(self) -> None:
        """Apply a 3-second delay between consecutive requests within one search invocation."""
        if self._request_count > 0:
            time.sleep(3)
        self._request_count += 1

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
        self._request_count = 0

        # Strategy 1: arXiv ID lookup
        if arxiv_id is not None:
            if not _validate_arxiv_id(arxiv_id):
                logger.debug("search_request", source="arxiv", strategy="id_lookup", skipped=True, reason="invalid_arxiv_id_format")
            else:
                self._throttle()
                logger.info("search_starting", source="arxiv", strategy="id_lookup", arxiv_id=arxiv_id)
                result = self._id_lookup(arxiv_id)
                logger.info("search_complete", source="arxiv", candidates_found=len(result))
                if result:
                    return result

        # Strategy 2: DOI search
        if doi is not None:
            if not _validate_doi(doi):
                logger.debug("search_request", source="arxiv", strategy="doi_search", skipped=True, reason="invalid_doi_format")
            else:
                self._throttle()
                logger.info("search_starting", source="arxiv", strategy="doi_search", doi=doi)
                result = self._doi_search(doi)
                logger.info("search_complete", source="arxiv", candidates_found=len(result))
                if result:
                    return result

        # Strategy 3: Title + Author search
        if title is not None and authors:
            self._throttle()
            logger.info("search_starting", source="arxiv", strategy="title_author_search", title=title, first_author=authors[0])
            result = self._title_author_search(title, authors[0])
            logger.info("search_complete", source="arxiv", candidates_found=len(result))
            if result:
                return result

        # Strategy 4: Title only search
        if title is not None:
            self._throttle()
            logger.info("search_starting", source="arxiv", strategy="title_search", title=title)
            result = self._title_search(title)
            logger.info("search_complete", source="arxiv", candidates_found=len(result))
            return result

        logger.info("search_complete", source="arxiv", candidates_found=0)
        return []

    def _id_lookup(self, arxiv_id: str) -> list[MatchCandidate]:
        logger.debug("search_request", source="arxiv", url=f"{self._client.base_url}/query", params={"id_list": arxiv_id})
        response = self._client.get("/query", params={"id_list": arxiv_id})
        if response.status_code == 404:
            return []
        response.raise_for_status()
        try:
            return _parse_feed(response.text, match_type="identifier_exact", raw_score=1.0)
        except ValueError:
            logger.warning("search_parse_error", source="arxiv", strategy="id_lookup", detail="XML parse error")
            return []

    def _doi_search(self, doi: str) -> list[MatchCandidate]:
        logger.debug("search_request", source="arxiv", url=f"{self._client.base_url}/query", params={"search_query": f"doi:{doi}", "max_results": 1})
        response = self._client.get("/query", params={"search_query": f"doi:{doi}", "max_results": 1})
        if response.status_code == 404:
            return []
        response.raise_for_status()
        try:
            return _parse_feed(response.text, match_type="doi_exact", raw_score=1.0)
        except ValueError:
            logger.warning("search_parse_error", source="arxiv", strategy="doi_search", detail="XML parse error")
            return []

    def _title_author_search(self, title: str, first_author: str) -> list[MatchCandidate]:
        """Search by combined title and first author surname."""
        surname = self._extract_surname(first_author[:128])
        safe_title = _sanitize_arxiv_term(title[:500])
        safe_surname = _sanitize_arxiv_term(surname)
        search_query = f'ti:"{safe_title}" AND au:{safe_surname}'
        logger.debug("search_request", source="arxiv", url=f"{self._client.base_url}/query", params={"search_query": search_query, "max_results": 5})
        response = self._client.get("/query", params={"search_query": search_query, "max_results": 5})
        if response.status_code == 404:
            return []
        response.raise_for_status()
        try:
            return _parse_feed(response.text, match_type="metadata_partial", raw_score=0.0)
        except ValueError:
            logger.warning("search_parse_error", source="arxiv", strategy="title_author_search", detail="XML parse error")
            return []

    def _title_search(self, title: str) -> list[MatchCandidate]:
        safe_title = _sanitize_arxiv_term(title[:500])
        logger.debug("search_request", source="arxiv", url=f"{self._client.base_url}/query", params={"search_query": f'ti:"{safe_title}"', "max_results": 5})
        response = self._client.get("/query", params={"search_query": f'ti:"{safe_title}"', "max_results": 5})
        if response.status_code == 404:
            return []
        response.raise_for_status()
        try:
            return _parse_feed(response.text, match_type="title_fuzzy", raw_score=0.0)
        except ValueError:
            logger.warning("search_parse_error", source="arxiv", strategy="title_search", detail="XML parse error")
            return []

    @staticmethod
    def _extract_surname(author_name: str) -> str:
        """Extract the surname from an author name for arXiv search.

        Handles common formats:
        - 'Smith, J.' -> 'Smith'
        - 'John Smith' -> 'Smith'
        - 'L. Martínez' -> 'Martínez'
        - 'Aristotle' -> 'Aristotle'
        """
        author_name = author_name.strip()
        if "," in author_name:
            # Format: "Surname, Given" -> take everything before the first comma
            return author_name.split(",")[0].strip()
        # Format: "Given Surname" -> take the last word
        parts = author_name.split()
        return parts[-1] if parts else author_name

    def close(self) -> None:
        self._client.close()
