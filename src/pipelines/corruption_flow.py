from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records, parse_crossref_payload
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import COMPARISON_METRICS, generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _save_dataframe(df: pd.DataFrame, csv_path, json_path) -> None:
    write_csv(df, csv_path)
    df.to_json(json_path, orient="records", indent=2, force_ascii=False)


def _check_and_evaluate(
    settings: Settings,
    df: pd.DataFrame,
    stage: str,
    embeddings_path,
    metrics_path,
    answers_path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    quality = run_data_quality_checks(df, settings, stage)
    freshness = build_freshness_report(df, settings, settings.paths.quality_dir / f"{stage}_freshness_report.json")
    failed = [check["expectation"] for check in quality["checks"] if not check["success"]]
    print(f"[{stage}] quality={quality['success']} failed={failed} is_fresh={freshness['is_fresh']}")

    index = LocalEmbeddingIndex.build(df, settings, embeddings_path)
    evaluation = evaluate_pipeline(settings, index, settings.paths.eval_testset, metrics_path, answers_path)
    return evaluation.summary, quality, freshness


def repair_from_raw_snapshot(settings: Settings, run_date) -> pd.DataFrame:
    """Idempotent repair: dung lai dataset sach tu raw snapshot, khong goi API, khong sua du lieu hong.

    Chay bao nhieu lan cung cho cung mot ket qua va ghi de (overwrite) artifacts repaired.
    """
    paths = settings.paths
    if paths.raw_records_json.exists():
        records = load_raw_records(paths.raw_records_json)
    else:
        records = parse_crossref_payload(read_json(paths.raw_api_response))
    repaired = build_clean_dataframe(records, run_date)
    _save_dataframe(repaired, paths.repaired_clean_csv, paths.repaired_clean_json)
    return repaired


def _print_comparison(baseline: dict, corrupted: dict, repaired: dict, corrupted_quality: dict, repaired_quality: dict) -> None:
    header = f"{'Metric':<24}{'Baseline':>10}{'Corrupted':>11}{'Repaired':>10}"
    print("\n" + header)
    print("-" * len(header))
    for key, label in COMPARISON_METRICS:
        print(f"{label:<24}{baseline.get(key, 0):>10.3f}{corrupted.get(key, 0):>11.3f}{repaired.get(key, 0):>10.3f}")
    print(f"{'Quality gate':<24}{'PASS':>10}{_status(corrupted_quality):>11}{_status(repaired_quality):>10}\n")


def _status(quality: dict) -> str:
    return "PASS" if quality.get("success") else "FAIL"


def run_corruption_flow_pipeline(settings: Settings) -> dict[str, Any]:
    paths = settings.paths
    run_date = now_utc()

    # 1. Load baseline (phai chay phase1 truoc)
    if not paths.baseline_metrics.exists() or not paths.clean_json.exists() or not paths.eval_testset.exists():
        raise FileNotFoundError("Chua co baseline. Hay chay `python script/run_phase1.py` truoc.")
    baseline_metrics = read_json(paths.baseline_metrics)
    clean_df = pd.read_json(paths.clean_json)

    # 2-5. Corrupt -> luu -> quality gate -> index -> evaluate
    print("[corruption] 1/3 Tiem loi vao du lieu sach")
    corrupted_df = corrupt_clean_dataframe(clean_df, paths.corruption_log)
    _save_dataframe(corrupted_df, paths.corrupted_clean_csv, paths.corrupted_clean_json)
    corrupted_metrics, corrupted_quality, corrupted_freshness = _check_and_evaluate(
        settings, corrupted_df, "corrupted", paths.corrupted_embeddings_json, paths.corrupted_metrics, paths.corrupted_answers
    )

    # 6-7. Repair tu raw snapshot -> quality gate -> index -> evaluate
    print("[corruption] 2/3 Repair tu raw snapshot")
    repaired_df = repair_from_raw_snapshot(settings, run_date)
    repaired_metrics, repaired_quality, repaired_freshness = _check_and_evaluate(
        settings, repaired_df, "repaired", paths.repaired_embeddings_json, paths.repaired_metrics, paths.repaired_answers
    )
    if not repaired_quality["success"]:
        print("[repaired] CANH BAO: du lieu sau repair van khong qua quality gate!")

    # 8. Report
    print("[corruption] 3/3 Bao cao doi chieu")
    generate_corruption_report(
        paths.comparison_report,
        baseline_metrics,
        corrupted_metrics,
        repaired_metrics,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
        corruption_log=read_json(paths.corruption_log),
    )
    _print_comparison(baseline_metrics, corrupted_metrics, repaired_metrics, corrupted_quality, repaired_quality)
    print(f"[corruption] Report: {paths.comparison_report}")

    return {
        "baseline": baseline_metrics,
        "corrupted": corrupted_metrics,
        "repaired": repaired_metrics,
        "corrupted_quality": corrupted_quality,
        "repaired_quality": repaired_quality,
        "corruption_log": read_json(paths.corruption_log),
    }


def main() -> None:
    run_corruption_flow_pipeline(load_settings())