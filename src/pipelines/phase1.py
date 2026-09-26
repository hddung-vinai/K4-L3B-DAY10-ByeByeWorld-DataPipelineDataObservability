from __future__ import annotations

from typing import Any

from core.config import Settings, load_settings, require_llm_credentials
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex

DEMO_QUESTIONS = 2


def _load_or_fetch_records(settings: Settings):
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        print("[phase1] 1/7 Ingest: goi Crossref API")
        return fetch_source_records(settings), "crossref_api"
    print(f"[phase1] 1/7 Ingest: dung raw snapshot {settings.paths.raw_records_json}")
    return load_raw_records(settings.paths.raw_records_json), "raw_snapshot"


def _run_agent_demo(settings: Settings, index: LocalEmbeddingIndex, test_set: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        require_llm_credentials(settings)
        agent = build_agent(settings, index)
    except Exception as exc:
        print(f"[phase1] Bo qua agent demo: {exc}")
        return [{"skipped": str(exc)}]

    answers = []
    for item in test_set[:DEMO_QUESTIONS]:
        try:
            answer = run_agent_question(agent, item["question"])
            if isinstance(answer, list):  # Gemini tra ve list content blocks, chi giu phan text
                answer = "".join(block.get("text", "") if isinstance(block, dict) else str(block) for block in answer)
        except Exception as exc:
            answer = f"Agent error: {exc}"
        answers.append({"question": item["question"], "ground_truth": item["ground_truth"], "answer": answer})
    return answers


def run_phase1_pipeline(settings: Settings) -> dict[str, Any]:
    run_date = now_utc()
    paths = settings.paths

    records, source_mode = _load_or_fetch_records(settings)

    print("[phase1] 2/7 Clean")
    df = build_clean_dataframe(records, run_date)
    write_csv(df, paths.clean_csv)
    df.to_json(paths.clean_json, orient="records", indent=2, force_ascii=False)

    print("[phase1] 3/7 Quality gate (Great Expectations + freshness)")
    quality = run_data_quality_checks(df, settings, "baseline")
    freshness = build_freshness_report(df, settings, paths.freshness_report)
    if not quality["success"]:
        failed = [check["expectation"] for check in quality["checks"] if not check["success"]]
        print(f"[phase1] CANH BAO: quality gate FAIL {failed}, is_fresh={freshness['is_fresh']}")

    print("[phase1] 4/7 Index ChromaDB")
    index = LocalEmbeddingIndex.build(df, settings, paths.embeddings_json)

    if settings.refresh_test_set or not paths.eval_testset.exists():
        print("[phase1] 5/7 Sinh test set moi")
        test_set = build_test_set(df, paths.eval_testset)
    else:
        print(f"[phase1] 5/7 Dung test set co san {paths.eval_testset}")
        test_set = read_json(paths.eval_testset)

    print("[phase1] 6/7 Evaluate baseline")
    evaluation = evaluate_pipeline(settings, index, paths.eval_testset, paths.baseline_metrics, paths.baseline_answers)

    demo_answers = _run_agent_demo(settings, index, test_set)
    write_json(paths.demo_answers, demo_answers)

    print("[phase1] 7/7 Report")
    source_summary = {
        "source_api": settings.source_api,
        "source_mode": source_mode,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "raw_records": len(records),
        "clean_rows": len(df),
        "test_questions": len(test_set),
        "llm_provider": settings.llm_provider,
        "embedding_model": settings.embedding_model,
        "collection_name": index.collection_name,
        "run_at": run_date.isoformat(),
    }
    generate_phase1_report(paths.baseline_report, source_summary, evaluation.summary, quality, freshness)

    return {
        "source": source_summary,
        "metrics": evaluation.summary,
        "quality": quality,
        "freshness": freshness,
    }


def main() -> None:
    result = run_phase1_pipeline(load_settings())
    metrics = result["metrics"]
    print(
        "[phase1] Hoan tat: "
        f"rows={result['source']['clean_rows']}, "
        f"hit_rate={metrics['retrieval_hit_rate']:.2f}, "
        f"token_f1={metrics['mean_token_f1']:.2f}, "
        f"quality={result['quality']['success']}"
    )