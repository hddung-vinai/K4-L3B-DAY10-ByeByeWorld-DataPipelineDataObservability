# Phase 1 Report - Baseline RAG Pipeline

Generated at: 2026-09-26T04:31:17.523157+00:00

## 1. Source

| Field | Value |
|---|---|
| source_api | Crossref REST API |
| source_mode | raw_snapshot |
| source_query | agentic retrieval augmented generation large language model |
| source_filter | from-pub-date:2026-03-30,has-abstract:true |
| raw_records | 24 |
| clean_rows | 24 |
| test_questions | 10 |
| llm_provider | openai |
| embedding_model | sentence-transformers/all-MiniLM-L6-v2 |
| collection_name | papers-baseline |

## 2. Baseline Evaluation

| Metric | Value |
|---|---|
| Samples | 10 |
| Retrieval hit rate | 1.0000 |
| Mean token F1 | 1.0000 |
| Judge accuracy | 1.0000 |
| Mean judge score (1-5) | 5 |

Ragas: Set RUN_RAGAS=1 to enable the slower Ragas pass.

## 3. Data Quality Gate (Great Expectations 1.23.2)

Overall: **PASS** (GX expectations: PASS, freshness: PASS)

| Expectation | Column | Status | Unexpected count |
|---|---|---|---|
| expect_table_row_count_to_be_between | - | PASS | - |
| expect_column_values_to_not_be_null | paper_id | PASS | 0 |
| expect_column_values_to_be_unique | paper_id | PASS | 0 |
| expect_column_values_to_not_be_null | title | PASS | 0 |
| expect_column_values_to_not_be_null | text_for_embedding | PASS | 0 |
| expect_column_value_lengths_to_be_between | summary | PASS | 0 |

## 4. Freshness SLA

| Field | Value |
|---|---|
| Latest published | 2026-07-22 |
| Oldest published | 2026-03-28 |
| Stale rows | 1 / 24 |
| Stale ratio | 0.0417 |
| Max stale ratio (SLA) | 0.2500 |
| Threshold days | 180 |
| is_fresh | True |
