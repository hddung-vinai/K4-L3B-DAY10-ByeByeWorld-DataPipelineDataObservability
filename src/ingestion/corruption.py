from __future__ import annotations

import math
import random
from typing import Any

import pandas as pd

from core.utils import now_utc, write_json

SEED = 42
DROP_LATEST_RATIO = 0.20
BLANK_SUMMARY_ROWS = 3
NOISE_ROWS = 3
TRUNCATE_TITLE_ROWS = 3
TRUNCATED_TITLE_CHARS = 7  # < 8 ky tu
STALE_RATIO = 0.40  # > 25% de vuot Freshness SLA
STALE_SHIFT_DAYS = 365
DUPLICATE_ROWS = 3
NOISE_TOKENS = ["#@!$", "lorem", "%%ERR%%", "\ufffd\ufffd", "NaN", "<<null>>", "0xDEADBEEF", "~~~~"]


def _pick(rng: random.Random, candidates: list[int], count: int) -> list[int]:
    return sorted(rng.sample(candidates, min(count, len(candidates))))


def _preview(value: Any, limit: int = 120) -> Any:
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + "..."
    return value


def _inject_noise(rng: random.Random, text: str) -> str:
    words = text.split()
    for _ in range(max(3, len(words) // 4)):
        words.insert(rng.randrange(len(words) + 1), rng.choice(NOISE_TOKENS))
    return " ".join(words)


def _rebuild_text_for_embedding(df: pd.DataFrame) -> pd.Series:
    return (
        "Title: " + df["title"].fillna("")
        + "\nAuthors: " + df["authors_joined"].fillna("")
        + "\nPublished: " + df["published"].fillna("")
        + "\nCategories: " + df["categories_joined"].fillna("")
        + "\nSummary: " + df["summary"].fillna("")
    )


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    rng = random.Random(SEED)
    corrupted = df.copy()
    corrupted["published"] = pd.to_datetime(corrupted["published"], errors="coerce").dt.strftime("%Y-%m-%d")
    corrupted = corrupted.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    input_rows = len(corrupted)
    events: list[dict[str, Any]] = []

    def log(kind: str, index: int, field: str | None, before: Any, after: Any) -> None:
        events.append(
            {
                "corruption": kind,
                "paper_id": corrupted.at[index, "paper_id"],
                "field": field,
                "before": _preview(before),
                "after": _preview(after),
            }
        )

    # 1. Drop latest records: bo 20% bai moi nhat (df da sort published giam dan)
    drop_count = math.ceil(input_rows * DROP_LATEST_RATIO)
    for index in range(drop_count):
        log("drop_latest_records", index, None, corrupted.at[index, "published"], "<dropped>")
    corrupted = corrupted.iloc[drop_count:].reset_index(drop=True)

    # Moi dong chi bi 1 loai loi noi dung de log ro rang; stale date co the chong len
    available = list(range(len(corrupted)))

    def take(count: int) -> list[int]:
        chosen = _pick(rng, available, count)
        for index in chosen:
            available.remove(index)
        return chosen

    # 2. Blank summary
    for index in take(BLANK_SUMMARY_ROWS):
        log("blank_summary", index, "summary", corrupted.at[index, "summary"], "")
        corrupted.at[index, "summary"] = ""

    # 3. Inject noise vao summary
    for index in take(NOISE_ROWS):
        before = corrupted.at[index, "summary"]
        after = _inject_noise(rng, before)
        log("inject_noise", index, "summary", before, after)
        corrupted.at[index, "summary"] = after

    # 4. Truncate title xuong < 8 ky tu
    for index in take(TRUNCATE_TITLE_ROWS):
        before = corrupted.at[index, "title"]
        after = before[:TRUNCATED_TITLE_CHARS]
        log("truncate_title", index, "title", before, after)
        corrupted.at[index, "title"] = after

    # 5. Stale date: lui published ve 365 ngay truoc
    stale_count = math.ceil(len(corrupted) * STALE_RATIO)
    for index in _pick(rng, list(range(len(corrupted))), stale_count):
        before = corrupted.at[index, "published"]
        after = (pd.Timestamp(before) - pd.Timedelta(days=STALE_SHIFT_DAYS)).strftime("%Y-%m-%d")
        log("stale_date", index, "published", before, after)
        corrupted.at[index, "published"] = after
        corrupted.at[index, "age_days"] = int(corrupted.at[index, "age_days"]) + STALE_SHIFT_DAYS

    # 7. Rebuild cac cot phu thuoc (truoc khi duplicate de ban sao giong het ban goc)
    corrupted["summary_chars"] = corrupted["summary"].str.len()
    corrupted["text_for_embedding"] = _rebuild_text_for_embedding(corrupted)

    # 6. Duplicate rows
    duplicate_indexes = _pick(rng, list(range(len(corrupted))), DUPLICATE_ROWS)
    for index in duplicate_indexes:
        log("duplicate_rows", index, "paper_id", None, corrupted.at[index, "paper_id"])
    corrupted = pd.concat([corrupted, corrupted.iloc[duplicate_indexes]], ignore_index=True)

    counts: dict[str, int] = {}
    for event in events:
        counts[event["corruption"]] = counts.get(event["corruption"], 0) + 1

    write_json(
        output_log_path,
        {
            "created_at": now_utc().isoformat(),
            "seed": SEED,
            "input_rows": input_rows,
            "output_rows": len(corrupted),
            "corruption_counts": counts,
            "events": events,
        },
    )
    return corrupted