# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4             |
| Tên nhóm         | ByeByeWorld     |
| Repository         | https://github.com/hddung-vinai/K4-L3B-DAY10-ByeByeWorld-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26               |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Hoàng Đức Dũng | 2A202602798 | Data ingestion & cleaning owner, integration run | crossref.py, cleaning.py; thống nhất raw/clean schema; chạy lại pipeline trên code đã ghép và commit artifacts `data/` |
| 2 | Trần Tuấn Tú | 2A202602840 | Evaluation & observability owner | testset.py, quality.py, reporting.py |
| 3 | Đào Duy Hiếu | 2A202602651 | Corruption & orchestration owner | corruption.py, phase1.py, corruption_flow.py |

## 2. Tóm tắt kết quả

**Tóm tắt của nhóm:**

Nhóm đã hoàn thành toàn bộ pipeline: thu thập metadata bài báo từ Crossref (có retry và fallback về raw snapshot), làm sạch dữ liệu, index vào ChromaDB bằng `all-MiniLM-L6-v2`, sinh bộ đánh giá 10 câu, đánh giá RAG, kiểm định chất lượng bằng Great Expectations 1.x kèm Freshness SLA, tiêm 6 loại lỗi, phục hồi từ raw snapshot và lập báo cáo đối chiếu 3 trạng thái.

Baseline tạo ra đủ artifact trong `data/clean/`, `data/chroma/`, `data/embeddings/`, `data/eval/`, `data/quality/`, `data/results/` và `data/reports/`, đạt `retrieval_hit_rate = 1.0`, `mean_token_f1 = 1.0`, quality gate PASS 6/6.

Corruption ảnh hưởng rõ nhất là **drop latest records**: 3 trong 10 bài của test set bị xóa khỏi corpus, làm hit rate giảm từ 1.0 xuống 0.6. **Stale date** là lỗi gây sai câu trả lời rõ nhất: câu hỏi ngày xuất bản trả về ngày đã bị lùi 365 ngày dù retrieval vẫn đúng bài. Quality gate bắt được duplicate, blank summary và stale date (FAIL), nhưng **không bắt được** drop records, noise và truncate title, đây là các silent failure.

Repair dựng lại dữ liệu sạch từ `data/raw/crossref_records.json`, phục hồi 100% cả 4 metric về mức baseline và gate trở lại PASS 6/6.

Giới hạn lớn nhất: dữ liệu Crossref thật hiện không có trường `subject`, nên nhóm dùng raw snapshot của lab làm nguồn cho các lần chạy chính thức.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API (https://api.crossref.org/works)
    -> data/raw/crossref_response.json + crossref_records.json   (raw preservation)
    -> build_clean_dataframe: clean text, age_days, text_for_embedding, dedup
    -> quality gate (GX 1.x) + freshness SLA                     -> data/quality/
    -> embedding all-MiniLM-L6-v2 + ChromaDB "papers-baseline"   -> data/chroma/, data/embeddings/
    -> test set 10 câu (dùng chung 3 trạng thái)                   -> data/eval/test_set.json
    -> evaluation baseline                                        -> data/results/baseline_*.json
    -> corruption (6 loại, seed=42)                               -> data/clean/papers_clean_corrupted.*
    -> quality gate + re-index "papers-corrupted" + re-evaluate   -> data/results/corrupted_*.json
    -> repair từ raw snapshot                                     -> data/clean/papers_clean_repaired.*
    -> quality gate + re-index "papers-repaired" + re-evaluate    -> data/results/repaired_*.json
    -> comparison report                                          -> data/reports/corruption_report.md
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref REST API `/works` hoặc raw snapshot | Gọi API với retry/backoff cho 429/5xx, lưu JSON gốc, parse thành `PaperRecord`, fallback snapshot khi API lỗi | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Hoàng Đức Dũng |
| Cleaning          | `list[PaperRecord]`, `run_date` | Bỏ thẻ HTML/JATS, chuẩn hóa khoảng trắng, parse ngày, tính `age_days`, ghép `text_for_embedding`, lọc dòng lỗi, dedup `paper_id` | `data/clean/papers_clean.csv`, `.json` | Hoàng Đức Dũng |
| Embedding/index   | Clean DataFrame | `all-MiniLM-L6-v2` (normalize), ChromaDB cosine, mỗi trạng thái một collection | `data/chroma/`, `data/embeddings/*.json` | Starter code, Hiếu gọi trong pipeline |
| Evaluation        | Clean DataFrame, index | 10 câu (summary/authors/date/categories), hit rate, token F1, LLM judge | `data/eval/test_set.json`, `data/results/*_metrics.json`, `*_answers.json` | Trần Tuấn Tú |
| Observability     | DataFrame từng trạng thái | 6 expectations GX 1.x + Freshness SLA (`age_days > 180`, tối đa 25%) | `data/quality/*_quality_report.json`, `*freshness_report.json` | Trần Tuấn Tú |
| Corruption/repair | Clean DataFrame; raw snapshot | 6 loại corruption có seed; repair dựng lại từ raw | `data/results/corruption_log.json`, `data/clean/papers_clean_{corrupted,repaired}.*` | Đào Duy Hiếu |
| Orchestration     | Settings, các module trên | `run_phase1_pipeline`, `run_corruption_flow_pipeline` | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Đào Duy Hiếu |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | `openai`         |
| `LLM_MODEL`                | `gpt-4o-mini`         |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2`         |
| Số lượng Crossref records | 24 (`max_results = 24`)         |
| Retrieval`top_k`           | 4         |
| Freshness threshold          | 180 ngày, tối đa 25% bài quá hạn         |
| Random seed, nếu có        | 42 (corruption)         |

`REFRESH_SOURCE` và `REFRESH_TEST_SET` để trống: pipeline dùng raw snapshot và test set có sẵn.

### Lệnh cài đặt

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

### Lệnh chạy

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công (exit 0) | 2026-09-26 11:31 (GMT+7) | `data/reports/phase1_report.md`, `data/results/baseline_metrics.json` |
| Corruption flow   | Thành công (exit 0) | 2026-09-26 11:32 (GMT+7) | `data/reports/corruption_report.md`, `data/results/{corrupted,repaired}_metrics.json` |

Hai lệnh được chạy lại trên code đã ghép của cả 3 thành viên (commit `7b7c4fe`), sau đó artifacts được commit ở `399f8b2`.

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API `https://api.crossref.org/works` |
| Query/filter                | `query=agentic retrieval augmented generation large language model`, `filter=from-pub-date:<hôm nay − 180 ngày>,has-abstract:true`, `rows=24` |
| Thời điểm lấy dữ liệu | Các lần chạy chính thức dùng raw snapshot trong `data/raw/` (`source_mode = raw_snapshot`). API thật được gọi thử ngày 2026-09-26 và trả về 24 bản ghi, nhưng không bản ghi nào có `subject` nên không được dùng. |
| Số record nhận được    | 24 items → 24 `PaperRecord` → 24 dòng clean |
| Cơ chế retry/backoff      | Tối đa 3 lần cho HTTP 429/500/502/503/504, backoff 1s rồi 2s, timeout 30s. Nếu vẫn lỗi thì đọc lại `crossref_response.json` đã lưu. Chỉ ghi đè raw khi gọi API thành công. |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id` | str | Có | DOI, chuyển về chữ thường | Thiếu → bỏ record; trùng → giữ bản đầu |
| `title` | str | Có | Tiêu đề (nối list `title` của Crossref) | Rỗng sau khi làm sạch → bỏ record |
| `summary` | str | Có | Abstract đã bỏ thẻ `<jats:p>` | Rỗng hoặc < 50 ký tự → bỏ record |
| `authors` / `authors_joined` | list[str] / str | Không | `given + family`, nối bằng `, ` | Thiếu → list rỗng |
| `categories` / `categories_joined` | list[str] / str | Không | Trường `subject` của Crossref | Thiếu → list rỗng; `primary_category = ""` |
| `published` | str `YYYY-MM-DD` | Có | Lấy `published` → `published-online` → `published-print` → `created` | Không parse được → bỏ record |
| `updated` | str `YYYY-MM-DD` | Không | `indexed.date-time` | Thiếu → bằng `published` |
| `abs_url`, `pdf_url` | str | Không | Link DOI; link PDF nếu có | Thiếu PDF → dùng `abs_url` |
| `age_days` | int | Có (tính ra) | `(run_date − published).days` | Tính từ `published` hợp lệ |
| `summary_chars` | int | Có (tính ra) | Độ dài summary | Dùng cho quality check |
| `text_for_embedding` | str | Có (tính ra) | 5 phần: Title, Authors, Published, Categories, Summary | Luôn được tạo từ các cột đã làm sạch |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Bỏ thẻ HTML/JATS và `html.unescape` trong abstract | Validity | 24 | Abstract gốc có `<jats:p>` trong `crossref_response.json`, không còn trong `papers_clean.json` |
| Chuẩn hóa khoảng trắng cho mọi trường text | Consistency | 24 | Đối chiếu `papers_clean.json` |
| Loại record thiếu `paper_id`/`title`/`published` hoặc summary < 50 ký tự | Completeness | 0 | 24 records vào → 24 dòng ra |
| Khử trùng lặp theo `paper_id` (DOI viết thường) | Uniqueness | 0 | GX `expect_column_values_to_be_unique` PASS trên baseline |
| Chuẩn hóa ngày về `YYYY-MM-DD` | Validity/Consistency | 24 | Cột `published` trong `papers_clean.csv` |

**Cách tạo `text_for_embedding`, document ID và `age_days`:**

- `text_for_embedding` ghép 5 dòng `Title / Authors / Published / Categories / Summary`. Nhờ vậy vector mang cả thông tin tác giả, ngày và lĩnh vực, không chỉ nội dung tóm tắt.
- Document ID là DOI viết thường (`paper_id`). ChromaDB dùng `record_id = "<paper_id>::<index>"`, nên các dòng trùng ở trạng thái corrupted vẫn được nạp vào index, đúng kiểu "ghost vector" cần mô phỏng.
- `age_days = (run_date − published).days`, với `run_date` là thời điểm chạy theo UTC. Baseline có `age_days` từ 66 đến 182.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 10                 |
| Các`question_type`                    | summary (3), authors (3), date (2), categories (2)                  |
| Ground-truth document ID                 | `ground_truth_doc_ids = [paper_id]`; mỗi câu một bài khác nhau; retrieval hit khi DOI đúng nằm trong top-k     |
| Embedding model                          | `sentence-transformers/all-MiniLM-L6-v2`                  |
| Vector store/collection                  | ChromaDB (cosine): `papers-baseline`, `papers-corrupted`, `papers-repaired`                 |
| Retrieval`top_k`                       | 4                   |
| LLM provider/model                       | OpenAI `gpt-4o-mini` (LLM judge và agent demo)                   |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` (sha256 bắt đầu bằng `894364952480`) |

**Vì sao test set được giữ nguyên:** muốn đo tác động của dữ liệu thì chỉ được thay đổi đúng một biến là dữ liệu. Nếu mỗi trạng thái dùng một bộ câu hỏi khác, chênh lệch điểm có thể đến từ độ khó của câu hỏi chứ không phải từ corruption. Test set được sinh một lần từ dữ liệu sạch. `phase1.py` chỉ sinh lại khi file chưa tồn tại hoặc khi đặt `REFRESH_TEST_SET=1`, còn `corruption_flow.py` luôn đọc đúng file này cho cả corrupted và repaired.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/`                          | Có | 24 items / 24 records |
| Cleaned dataset          | `data/clean/`                        | Có | `papers_clean.csv/.json`, 24 dòng |
| Embedding manifest/index | `data/embeddings/`                   | Có | Manifest 3 collection; vector trong `data/chroma/` |
| Evaluation set           | `data/eval/`                         | Có | 10 câu, 4 loại |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | Kèm `baseline_answers.json` |
| Quality/freshness        | `data/quality/`                      | Có | `baseline_quality_report.json`, `freshness_report.json` |
| Baseline report          | `data/reports/phase1_report.md`      | Có | Sinh tự động bởi pipeline |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` |     1.0 | 10/10 câu có bài đúng trong top-4. Câu hỏi chứa tiêu đề trong `'...'` nên `qa.py` tra cứu chính xác được bài |
| `mean_token_f1`      |     1.0 | Câu trả lời trích xuất trùng khớp hoàn toàn với ground truth |
| `judge_accuracy`     |     1.0 | GPT-4o-mini đánh giá 10/10 câu đúng |
| `mean_judge_score`   |     5.0 | Điểm tối đa ở mọi câu |
| Ragas, nếu có        | N/A | Không bật `RUN_RAGAS=1` vì tốn thêm nhiều lượt gọi LLM; token F1 và LLM judge đã đủ đo độ suy giảm |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| `ExpectTableRowCountToBeBetween` | Completeness | 5–5000 dòng | PASS (24) | `data/quality/baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull(paper_id)` | Completeness | 0 null | PASS (0) | như trên |
| `ExpectColumnValuesToBeUnique(paper_id)` | Uniqueness | 0 trùng | PASS (0) | như trên |
| `ExpectColumnValuesToNotBeNull(title)` | Completeness | 0 null | PASS (0) | như trên |
| `ExpectColumnValuesToNotBeNull(text_for_embedding)` | Completeness | 0 null | PASS (0) | như trên |
| `ExpectColumnValueLengthsToBeBetween(summary)` | Validity | ≥ 30 ký tự | PASS (0 vi phạm) | như trên |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | Clean DataFrame trước khi index (cột `age_days`, `published`)            |
| Timestamp mới nhất       | 2026-07-22 (cũ nhất: 2026-03-28)                         |
| Ngưỡng freshness         | `age_days > 180` là stale; SLA cho phép tối đa 25% stale                         |
| Trạng thái baseline      | Fresh               |
| Lý do                     | 1/24 bài stale (4.17%), bài 2026-03-28 có `age_days = 182`, thấp hơn nhiều so với ngưỡng 25% |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| `drop_latest_records` | Sort `published` giảm dần, bỏ 20% đầu (`ceil(24 × 0.2)`) | 5 | Row count giảm | Row count vẫn trong 5–5000 → **gate không bắt**; 3 câu test (eval_002/003/006) mất bài đúng → retrieval miss | Dựng lại từ raw (24 records) |
| `blank_summary` | Gán `summary = ""` | 3 | Summary length FAIL | GX length check **FAIL (3)** | Như trên |
| `inject_noise` | Chèn token rác (`#@!$`, `U+FFFD`, `NaN`...) vào ~25% số từ của summary | 3 | Khó phát hiện bằng rule hiện có | **Gate không bắt**; eval_007 và eval_008 vẫn hit | Như trên |
| `truncate_title` | Cắt title còn 7 ký tự | 3 | Không có check độ dài title | **Gate không bắt**; eval_010 mất exact-title lookup → retrieval miss | Như trên |
| `stale_date` | Lùi `published` 365 ngày, `age_days + 365`, trên 40% số dòng | 8 | Freshness FAIL | Stale 9/22 = **40.9% > 25% → FAIL**; eval_003 và eval_007 trả lời ngày sai | Như trên |
| `duplicate_rows` | Nhân đôi dòng sau khi đã làm hỏng | 3 | Unique FAIL | GX unique **FAIL (6 giá trị trùng)** | Như trên |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log ghi `seed = 42`, `input_rows = 24`, `output_rows = 22`, số dòng theo từng loại lỗi, và từng sự kiện gồm `paper_id`, trường bị sửa, giá trị trước và sau. Nhờ vậy mọi thay đổi đều truy vết và tái hiện được.

**Repair phục hồi từ nguồn đáng tin cậy như thế nào:** `repair_from_raw_snapshot()` không sửa từng dòng hỏng. Hàm bỏ toàn bộ dataset corrupted, đọc lại `data/raw/crossref_records.json` (hoặc parse lại `crossref_response.json`), rồi cho qua cùng hàm `build_clean_dataframe()` như baseline. Raw snapshot không bị pipeline sửa đổi, nên đây là nguồn đáng tin cậy. Repair là **idempotent**: chạy 2 lần cho kết quả giống hệt nhau, và nội dung (`paper_id`, `title`, `summary`, `published`, `text_for_embedding`) giống 100% dữ liệu sạch baseline. Kết quả được ghi đè vào `papers_clean_repaired.*` và collection `papers-repaired` được tạo lại từ đầu, nên chạy lại không sinh vector trùng.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   |      1.0 |       0.6 |      1.0 |                     −0.4 |            100% | 4 câu miss: 3 do drop, 1 do truncate title |
| `mean_token_f1`        |      1.0 |       0.8 |      1.0 |                     −0.2 |            100% | 2 câu date trả lời sai |
| `judge_accuracy`       |      1.0 |       0.8 |      1.0 |                     −0.2 |            100% | Cao hơn hit rate vì 3 câu authors miss vẫn trả lời đúng |
| `mean_judge_score`     |      5.0 |       4.3 |      5.0 |                     −0.7 |            100% | eval_003 = 1 điểm, eval_007 = 2 điểm |
| Quality checks pass/fail |  6/6 PASS |  4/6 (FAIL) |  6/6 PASS |              −2 check |            100% | FAIL: unique `paper_id`, độ dài `summary` |
| Freshness status         |  Fresh (4.17%) |  Stale (40.91%) |  Fresh (4.17%) |                 +36.7 điểm % |            100% | Vượt SLA 25% do stale_date |

Mức phục hồi = (repaired − corrupted) / (baseline − corrupted).

Kết luận nhân quả:

1. **Drop latest records** (5 dòng, trong đó có bài của eval_002/003/006) → quality gate **không** báo lỗi vì 19 dòng còn lại vẫn nằm trong ngưỡng 5–5000 → `retrieval_hit_rate` giảm 1.0 → 0.6. Pipeline vẫn chạy bình thường, đây là silent failure. Bằng chứng: `corrupted_answers.json` (`retrieval_hit = false` ở eval_002/003/006/010), `corrupted_quality_report.json` (row count PASS).
2. **Stale date** (8 dòng) → freshness SLA **FAIL** (40.91% > 25%) → câu hỏi ngày xuất bản trả lời sai: eval_007 vẫn retrieval đúng bài nhưng trả về `2025-06-03` (judge 2/5), eval_003 trả về `2025-06-08` (judge 1/5) → `mean_token_f1` giảm 1.0 → 0.8.
3. **Repair từ raw snapshot** → gate trở lại PASS 6/6, stale 4.17% → cả 4 metric về đúng 1.0/1.0/1.0/5.0. Bằng chứng: `repaired_quality_report.json`, `repaired_metrics.json`.

Kết quả khác kỳ vọng: 3 câu authors (eval_002/006/010) bị retrieval miss nhưng judge vẫn chấm đúng 5/5. Nhóm kiểm tra `corrupted_answers.json` và thấy bài được lấy nhầm là các bài "Advanced Perspectives on …" / "An extended empirical study …" trong snapshot, có **cùng nhóm tác giả** với bài gốc. Vì vậy câu trả lời đúng một cách tình cờ, và `judge_accuracy` (0.8) cao hơn `retrieval_hit_rate` (0.6).

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Sau khi ingestion gọi Crossref API thật, `build_test_set()` không tạo được câu hỏi loại `categories`. Lần đầu báo `ValueError: Khong du paper hop le cho cau hoi dang 'categories'`; sau khi thêm fallback thì test set chỉ còn 3 loại câu hỏi.
- **Nguyên nhân:** Cả 24 bản ghi Crossref thật đều không có trường `subject`, nên `categories_joined` rỗng ở mọi dòng. Ngoài ra, `fetch_source_records()` ghi đè raw snapshot của lab bằng dữ liệu thật này, nên các bước sau đều nhận dữ liệu thiếu categories.
- **Cách xử lý:** Khôi phục snapshot bằng `git checkout -- data/raw/`. Trong `phase1.py`, chỉ gọi API khi `REFRESH_SOURCE=1` hoặc khi chưa có raw, còn lại dùng `load_raw_records()`. `testset.py` giữ fallback đổi loại câu hỏi và in cảnh báo thay vì crash.
- **Cách xác minh:** `python script/run_phase1.py` in `1/7 Ingest: dung raw snapshot`; `categories_joined` không rỗng ở 24/24 dòng; `test_set.json` có phân bổ 3/3/2/2 và `git status data/raw` sạch.

Vấn đề phụ khi ghép code: ký tự `U+FFFD` trong `NOISE_TOKENS` của `corruption.py` bị mất (thành 2 dấu cách) khi chuyển file giữa các thành viên. Nhóm sửa bằng cách viết dạng escape `"\ufffd\ufffd"` để file chỉ chứa ASCII, rồi chạy lại để xác nhận 3 summary bị nhiễm có chứa `U+FFFD`.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Quality gate không bắt được drop records, noise và truncate title | 3/6 loại lỗi lọt qua gate, gây silent failure (hit rate −0.4) | Thêm `ExpectColumnValueLengthsToBeBetween("title", min_value=8)`, so row count với lần chạy trước (giảm > 10% → FAIL), regex phát hiện `U+FFFD`/token rác. Đo bằng số loại lỗi bị FAIL trong `corrupted_quality_report.json` (mục tiêu 6/6) |
| Gate FAIL chỉ in cảnh báo, không chặn việc index | Dữ liệu bẩn vẫn vào ChromaDB | Thêm chế độ strict: `raise` khi `success = False` ở phase1. Kiểm chứng bằng cách chạy với dữ liệu corrupted và kỳ vọng exit code ≠ 0 |
| Test set dễ (tiêu đề nằm trong câu hỏi, exact lookup) | Baseline đạt 1.0 nên khó thấy suy giảm tinh tế | Thêm câu hỏi paraphrase không chứa tiêu đề. Đo hit rate baseline, kỳ vọng < 1.0 và nhạy hơn với noise |
| Dữ liệu Crossref thật thiếu `subject` | Không dùng được dữ liệu mới cho câu hỏi categories | Lấy lĩnh vực từ nguồn khác (ví dụ ISSN → subject của journal) hoặc bỏ loại câu hỏi categories khi tỉ lệ rỗng > 50% |
| LLM judge không tất định | Điểm judge có thể lệch nhẹ giữa các lần chạy | Chạy judge 3 lần và lấy trung vị, hoặc bật Ragas (`RUN_RAGAS=1`) để có thêm metric |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
