from __future__ import annotations

from dataclasses import asdict, dataclass
import html
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json

CROSSREF_URL = "https://api.crossref.org/works"
RETRY_STATUS = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    return normalize_whitespace(html.unescape(text))


def _date_from_parts(field: dict | None) -> str:
    parts = ((field or {}).get("date-parts") or [[]])[0]
    if not parts or parts[0] is None:
        return ""
    year, month, day = (list(parts) + [1, 1])[:3]
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    records: list[PaperRecord] = []
    seen: set[str] = set()
    for item in payload.get("message", {}).get("items", []):
        doi = (item.get("DOI") or "").strip().lower()
        title = _clean_text(" ".join(item.get("title") or []))
        summary = _clean_text(item.get("abstract", ""))
        if not doi or not title or not summary or doi in seen:
            continue
        seen.add(doi)

        authors = [
            normalize_whitespace(f"{a.get('given', '')} {a.get('family', '')}") or a.get("name", "")
            for a in item.get("author") or []
        ]
        authors = [a for a in authors if a]
        categories = [c for c in item.get("subject") or [] if c]

        published = (
            _date_from_parts(item.get("published"))
            or _date_from_parts(item.get("published-online"))
            or _date_from_parts(item.get("published-print"))
            or (item.get("created", {}).get("date-time") or "")[:10]
        )
        updated = (item.get("indexed", {}).get("date-time") or "")[:10] or published

        abs_url = item.get("URL") or f"https://doi.org/{doi}"
        pdf_url = next(
            (l["URL"] for l in item.get("link") or [] if l.get("content-type") == "application/pdf"),
            abs_url,
        )
        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=f"Crossref record {doi}",
            )
        )
    return records


def _request_crossref(settings: Settings, retries: int = 3) -> dict:
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "select": "DOI,title,abstract,author,subject,published,created,indexed,URL,link",
    }
    for attempt in range(retries):
        response = requests.get(CROSSREF_URL, params=params, timeout=30)
        if response.status_code in RETRY_STATUS and attempt < retries - 1:
            time.sleep(2**attempt)
            continue
        response.raise_for_status()
        return response.json()
    raise RuntimeError("Crossref request failed")


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    raw_path = settings.paths.raw_api_response
    try:
        payload = _request_crossref(settings)
        write_json(raw_path, payload)
    except (requests.RequestException, RuntimeError, ValueError) as exc:
        if not raw_path.exists():
            raise
        print(f"[crossref] API loi ({exc}); dung snapshot {raw_path}")
        payload = read_json(raw_path)

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(r) for r in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    return [PaperRecord(**row) for row in read_json(path)]
