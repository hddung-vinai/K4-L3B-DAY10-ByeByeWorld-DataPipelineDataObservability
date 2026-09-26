from __future__ import annotations

from datetime import UTC, datetime
import re

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord

TAG_RE = re.compile(r"<[^>]+>")
MIN_SUMMARY_CHARS = 50


def _clean_text(value: str | None) -> str:
    return normalize_whitespace(TAG_RE.sub(" ", value or ""))


def _clean_list(values: list[str] | None) -> list[str]:
    cleaned = [_clean_text(value) for value in values or []]
    return list(dict.fromkeys(value for value in cleaned if value))


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    rows = []
    for record in records:
        authors = _clean_list(record.authors)
        categories = _clean_list(record.categories)
        rows.append(
            {
                "paper_id": _clean_text(record.paper_id).lower(),
                "title": _clean_text(record.title),
                "summary": _clean_text(record.summary),
                "authors": authors,
                "categories": categories,
                "primary_category": _clean_text(record.primary_category) or (categories[0] if categories else ""),
                "published": record.published,
                "updated": record.updated,
                "abs_url": record.abs_url.strip(),
                "pdf_url": record.pdf_url.strip(),
                "comment": _clean_text(record.comment),
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    published = pd.to_datetime(df["published"], errors="coerce", utc=True)
    updated = pd.to_datetime(df["updated"], errors="coerce", utc=True).fillna(published)
    run_ts = pd.Timestamp(run_date if run_date.tzinfo else run_date.replace(tzinfo=UTC))

    df["published"] = published.dt.strftime("%Y-%m-%d")
    df["updated"] = updated.dt.strftime("%Y-%m-%d")
    df["age_days"] = (run_ts - published).dt.days

    df["authors_joined"] = df["authors"].apply(", ".join)
    df["categories_joined"] = df["categories"].apply(", ".join)
    df["summary_chars"] = df["summary"].str.len()
    df["text_for_embedding"] = (
        "Title: " + df["title"]
        + "\nAuthors: " + df["authors_joined"]
        + "\nPublished: " + df["published"].fillna("")
        + "\nCategories: " + df["categories_joined"]
        + "\nSummary: " + df["summary"]
    )

    valid = (
        (df["paper_id"] != "")
        & (df["title"] != "")
        & (df["summary_chars"] >= MIN_SUMMARY_CHARS)
        & published.notna()
    )
    df = df[valid].drop_duplicates(subset="paper_id", keep="first")
    df["age_days"] = df["age_days"].astype(int)
    return df.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
