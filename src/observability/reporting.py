from __future__ import annotations

from typing import Any

from core.utils import write_text


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    if value is None or value == "":
        return "-"
    return str(value)


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(_fmt(cell) for cell in row) + " |" for row in rows]
    return "\n".join(lines)


def _status(success: bool) -> str:
    return "PASS" if success else "FAIL"


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    metric_rows = [
        ["Samples", metrics.get("samples")],
        ["Retrieval hit rate", metrics.get("retrieval_hit_rate")],
        ["Mean token F1", metrics.get("mean_token_f1")],
        ["Judge accuracy", metrics.get("judge_accuracy")],
        ["Mean judge score (1-5)", metrics.get("mean_judge_score")],
    ]
    check_rows = [
        [check["expectation"], check.get("column"), _status(check["success"]), check.get("unexpected_count")]
        for check in quality.get("checks", [])
    ]
    freshness_rows = [
        ["Latest published", freshness.get("latest_published")],
        ["Oldest published", freshness.get("oldest_published")],
        ["Stale rows", f"{freshness.get('stale_rows')} / {freshness.get('total_rows')}"],
        ["Stale ratio", freshness.get("stale_ratio")],
        ["Max stale ratio (SLA)", freshness.get("max_stale_ratio")],
        ["Threshold days", freshness.get("threshold_days")],
        ["is_fresh", freshness.get("is_fresh")],
    ]
    ragas = metrics.get("ragas", {})
    ragas_text = ragas.get("skipped") or ragas.get("error") or ", ".join(f"{k}={_fmt(v)}" for k, v in ragas.items())
    source_rows = [[key, value] for key, value in source_summary.items() if key != "run_at"]

    text = f"""# Phase 1 Report - Baseline RAG Pipeline

Generated at: {source_summary.get("run_at")}

## 1. Source

{_table(["Field", "Value"], source_rows)}

## 2. Baseline Evaluation

{_table(["Metric", "Value"], metric_rows)}

Ragas: {ragas_text}

## 3. Data Quality Gate (Great Expectations {quality.get("gx_version", "")})

Overall: **{_status(quality.get("success", False))}** (GX expectations: {_status(quality.get("gx_success", False))}, freshness: {_status(freshness.get("is_fresh", False))})

{_table(["Expectation", "Column", "Status", "Unexpected count"], check_rows)}

## 4. Freshness SLA

{_table(["Field", "Value"], freshness_rows)}
"""
    write_text(report_path, text)


COMPARISON_METRICS = [
    ("retrieval_hit_rate", "Retrieval hit rate"),
    ("mean_token_f1", "Mean token F1"),
    ("judge_accuracy", "Judge accuracy"),
    ("mean_judge_score", "Mean judge score (1-5)"),
]


def _recovery(baseline: float, corrupted: float, repaired: float) -> str:
    drop = baseline - corrupted
    if abs(drop) < 1e-9:
        return "no drop"
    return f"{(repaired - corrupted) / drop:.0%}"


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
    corruption_log: dict[str, Any] | None = None,
) -> None:
    metric_rows = []
    for key, label in COMPARISON_METRICS:
        baseline = float(baseline_metrics.get(key, 0.0))
        corrupted = float(corrupted_metrics.get(key, 0.0))
        repaired = float(repaired_metrics.get(key, 0.0))
        metric_rows.append([label, baseline, corrupted, repaired, f"{corrupted - baseline:+.4f}", _recovery(baseline, corrupted, repaired)])

    corrupted_checks = {(c["expectation"], c.get("column")): c for c in corrupted_quality.get("checks", [])}
    check_rows = []
    for check in repaired_quality.get("checks", []):
        bad = corrupted_checks.get((check["expectation"], check.get("column")), {})
        check_rows.append(
            [
                check["expectation"],
                check.get("column"),
                f"{_status(bad.get('success', False))} ({_fmt(bad.get('unexpected_count'))})",
                f"{_status(check['success'])} ({_fmt(check.get('unexpected_count'))})",
            ]
        )
    check_rows.append(["freshness SLA (stale ratio)", "age_days", f"{_status(corrupted_freshness.get('is_fresh', False))} ({_fmt(corrupted_freshness.get('stale_ratio'))})", f"{_status(repaired_freshness.get('is_fresh', False))} ({_fmt(repaired_freshness.get('stale_ratio'))})"])
    check_rows.append(["**Overall gate**", "-", f"**{_status(corrupted_quality.get('success', False))}**", f"**{_status(repaired_quality.get('success', False))}**"])

    corruption_section = ""
    if corruption_log:
        counts = corruption_log.get("corruption_counts", {})
        corruption_section = f"""
## 1. Injected Corruptions

Input rows: {corruption_log.get("input_rows")} -> corrupted rows: {corruption_log.get("output_rows")} (seed={corruption_log.get("seed")})

{_table(["Corruption", "Affected rows"], [[kind, count] for kind, count in counts.items()])}
"""

    hit_drop = float(baseline_metrics.get("retrieval_hit_rate", 0)) - float(corrupted_metrics.get("retrieval_hit_rate", 0))
    f1_drop = float(baseline_metrics.get("mean_token_f1", 0)) - float(corrupted_metrics.get("mean_token_f1", 0))
    recovered = all(
        float(repaired_metrics.get(key, 0)) >= float(baseline_metrics.get(key, 0)) - 1e-9 for key, _ in COMPARISON_METRICS
    )

    text = f"""# Corruption Report - Baseline vs Corrupted vs Repaired
{corruption_section}
## 2. RAG Performance (3 states)

{_table(["Metric", "Baseline", "Corrupted", "Repaired", "Delta (corrupted - baseline)", "Recovery"], metric_rows)}

Recovery = (repaired - corrupted) / (baseline - corrupted); 100% nghia la lay lai toan bo phan bi mat.

## 3. Data Quality Gate

{_table(["Check", "Column", "Corrupted", "Repaired"], check_rows)}

## 4. Conclusion

- Corrupted data lam retrieval hit rate giam {hit_drop:.0%} va token F1 giam {f1_drop:.2f} so voi baseline, trong khi pipeline van chay binh thuong, khong nem loi (silent failure).
- Quality gate tren corrupted data: **{_status(corrupted_quality.get("success", False))}**, tren repaired data: **{_status(repaired_quality.get("success", False))}**.
- Repair tu raw snapshot {"da phuc hoi day du hieu nang ve muc baseline" if recovered else "CHUA phuc hoi day du hieu nang ve muc baseline"}.
"""
    write_text(report_path, text)