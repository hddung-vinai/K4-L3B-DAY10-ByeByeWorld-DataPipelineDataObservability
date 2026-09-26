# Corruption Report - Baseline vs Corrupted vs Repaired

## 1. Injected Corruptions

Input rows: 24 -> corrupted rows: 22 (seed=42)

| Corruption | Affected rows |
|---|---|
| drop_latest_records | 5 |
| blank_summary | 3 |
| inject_noise | 3 |
| truncate_title | 3 |
| stale_date | 8 |
| duplicate_rows | 3 |

## 2. RAG Performance (3 states)

| Metric | Baseline | Corrupted | Repaired | Delta (corrupted - baseline) | Recovery |
|---|---|---|---|---|---|
| Retrieval hit rate | 1.0000 | 0.6000 | 1.0000 | -0.4000 | 100% |
| Mean token F1 | 1.0000 | 0.8000 | 1.0000 | -0.2000 | 100% |
| Judge accuracy | 1.0000 | 0.8000 | 1.0000 | -0.2000 | 100% |
| Mean judge score (1-5) | 5.0000 | 4.3000 | 5.0000 | -0.7000 | 100% |

Recovery = (repaired - corrupted) / (baseline - corrupted); 100% nghia la lay lai toan bo phan bi mat.

## 3. Data Quality Gate

| Check | Column | Corrupted | Repaired |
|---|---|---|---|
| expect_table_row_count_to_be_between | - | PASS (-) | PASS (-) |
| expect_column_values_to_not_be_null | paper_id | PASS (0) | PASS (0) |
| expect_column_values_to_be_unique | paper_id | FAIL (6) | PASS (0) |
| expect_column_values_to_not_be_null | title | PASS (0) | PASS (0) |
| expect_column_values_to_not_be_null | text_for_embedding | PASS (0) | PASS (0) |
| expect_column_value_lengths_to_be_between | summary | FAIL (3) | PASS (0) |
| freshness SLA (stale ratio) | age_days | FAIL (0.4091) | PASS (0.0417) |
| **Overall gate** | - | **FAIL** | **PASS** |

## 4. Conclusion

- Corrupted data lam retrieval hit rate giam 40% va token F1 giam 0.20 so voi baseline, trong khi pipeline van chay binh thuong, khong nem loi (silent failure).
- Quality gate tren corrupted data: **FAIL**, tren repaired data: **PASS**.
- Repair tu raw snapshot da phuc hoi day du hieu nang ve muc baseline.
