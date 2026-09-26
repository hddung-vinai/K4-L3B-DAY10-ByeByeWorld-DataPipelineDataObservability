from __future__ import annotations

from typing import Any

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import now_utc, write_json

MIN_ROWS = 5
MAX_ROWS = 5000
REQUIRED_COLUMNS = ("paper_id", "title", "text_for_embedding")
MIN_SUMMARY_CHARS = 30
MAX_STALE_RATIO = 0.25


def _build_expectations() -> list:
    expectations = [gx.expectations.ExpectTableRowCountToBeBetween(min_value=MIN_ROWS, max_value=MAX_ROWS)]
    expectations += [gx.expectations.ExpectColumnValuesToNotBeNull(column=column) for column in REQUIRED_COLUMNS]
    expectations.append(gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"))
    expectations.append(gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=MIN_SUMMARY_CHARS))
    return expectations

def evaluate_freshness_sla(df: pd.DataFrame, threshold_days: int, max_stale_ratio: float = MAX_STALE_RATIO) -> dict[str, Any]:
    total_rows = len(df)
    age_days = pd.to_numeric(df["age_days"], errors="coerce") if "age_days" in df else pd.Series(dtype=float)
    stale_rows = int((age_days > threshold_days).sum())
    stale_ratio = stale_rows / total_rows if total_rows else 1.0
    published = pd.to_datetime(df["published"], errors="coerce") if "published" in df else pd.Series(dtype="datetime64[ns]")
    return {
        "latest_published": published.max().strftime("%Y-%m-%d") if published.notna().any() else None,
        "oldest_published": published.min().strftime("%Y-%m-%d") if published.notna().any() else None,
        "threshold_days": threshold_days,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_ratio, 4),
        "max_stale_ratio": max_stale_ratio,
        "is_fresh": total_rows > 0 and stale_ratio <= max_stale_ratio,
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    suite = context.suites.add(gx.ExpectationSuite(name=f"papers_{report_name}_suite"))
    for expectation in _build_expectations():
        suite.add_expectation(expectation)
    validation = batch.validate(suite)

    checks = []
    for result in validation.results:
        config = result.expectation_config
        checks.append(
            {
                "expectation": config.type,
                "column": config.kwargs.get("column"),
                "success": bool(result.success),
                "observed_value": result.result.get("observed_value"),
                "unexpected_count": result.result.get("unexpected_count"),
            }
        )

    freshness = evaluate_freshness_sla(df, settings.freshness_threshold_days)
    gx_success = bool(validation.success)
    report = {
        "report_name": report_name,
        "checked_at": now_utc().isoformat(),
        "row_count": len(df),
        "success": gx_success and freshness["is_fresh"],
        "gx_success": gx_success,
        "gx_version": gx.__version__,
        "checks": checks,
        "freshness": freshness,
    }
    write_json(settings.paths.quality_dir / f"{report_name}_quality_report.json", report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    report = {"checked_at": now_utc().isoformat(), **evaluate_freshness_sla(df, settings.freshness_threshold_days)}
    write_json(report_path, report)
    return report