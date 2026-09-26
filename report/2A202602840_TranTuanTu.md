# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| :--- | :--- |
| **Họ và tên** | Trần Tuấn Tú |
| **MSSV** | 2A202602840 |
| **Khóa/Lớp** | K4-L3B |
| **Tên nhóm** | ByeByeWorld |
| **Vai trò chính** | Observability & Evaluation Engineer (`testset.py`, `quality.py`, `reporting.py`) |
| **Repository** | `hddung-vinai/K4-L3B-DAY10-ByeByeWorld-DataPipelineDataObservability` |
| **Ngày hoàn thành** | 2026-09-26 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Benchmark Test Set** | `src/evaluation/testset.py`<br>`build_test_set()` | Cleaned DataFrame 24 bài báo (`data/clean/papers_clean.json`) | File benchmark 10 câu hỏi chuẩn hóa `data/eval/test_set.json` phủ 4 nhóm nghiệp vụ | Hoàn thành |
| **Data Quality Gate** | `src/observability/quality.py`<br>`run_data_quality_checks()` | Cleaned/Corrupted/Repaired DataFrame, settings, `report_name` | JSON report kiểm định `data/quality/{name}_quality_report.json` theo chuẩn Great Expectations 1.x | Hoàn thành |
| **Freshness SLA Monitor** | `src/observability/quality.py`<br>`build_freshness_report()` | DataFrame có cột `age_days`, `published`, settings | JSON report `data/quality/freshness_report.json` đánh giá tỷ lệ bài quá hạn với ngưỡng 180 ngày | Hoàn thành |
| **Observability Reporting** | `src/observability/reporting.py`<br>`generate_phase1_report()`,<br>`generate_corruption_report()` | Metrics evaluation, kết quả GX 1.x, freshness payload | Báo cáo Markdown `data/reports/phase1_report.md` và `data/reports/corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| Tích hợp QA Router & Testset Contract | Retrieval & Agent (`qa.py`, `agent.py`) | Định dạng câu hỏi bọc tiêu đề bài báo trong `'...'` giúp router trích xuất đúng ngữ cảnh chính xác 100% |
| Đối chiếu LLM Judge với ground truth | Evaluation (`metrics.py`) | Ground truth của test set có cùng định dạng với câu trả lời mà `qa.py` trích xuất, nên LLM judge (`gpt-4o-mini`) chấm 30/30 câu không cần fallback heuristic |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| Xây dựng bộ test set 10 câu hỏi | `src/evaluation/testset.py`<br>`data/eval/test_set.json` | 10 câu hỏi phủ đủ 4 nhóm (summary 3, authors 3, date 2, categories 2) kèm ground-truth doc IDs | Lệnh checkpoint bước 5 (`build_test_set`)<br>In ra: `Tín hiệu hoàn thành: Sinh được 10 câu hỏi test` |
| Thiết lập Data Quality Gate GX 1.x | `src/observability/quality.py`<br>`data/quality/*_quality_report.json` | 4 loại Expectation (RowCount, NotNull ×3 cột, Unique, Length) = 6 checks | Lệnh checkpoint bước 4 (`run_data_quality_checks`)<br>In ra: `Quality check status = True`; trên corrupted: `success = False` |
| Giám sát Freshness SLA | `src/observability/quality.py`<br>`data/quality/freshness_report.json` | Cảnh báo `is_fresh=False` khi tỷ lệ quá hạn 180 ngày > 25% | `data/quality/freshness_report.json`<br>Baseline: `1/24` stale (4.17% -> `is_fresh=True`) |
| Xuất báo cáo đối chiếu 3 trạng thái | `src/observability/reporting.py`<br>`data/reports/corruption_report.md` | Bảng Markdown đối chiếu định lượng Baseline vs Corrupted vs Repaired | `python script/run_corruption_flow.py` xuất bảng đối chiếu đầy đủ |

**Một output cụ thể do phần việc của tôi tạo ra:**
Bảng đối chiếu tổng hợp 3 trạng thái trong [`data/reports/corruption_report.md`](../data/reports/corruption_report.md) chứng minh hiện tượng suy giảm ngầm (Silent Failure) khi Retrieval Hit Rate sụt từ 100% xuống 60%, Token F1 giảm từ 1.0 xuống 0.8, và phục hồi trở lại 100% sau khi sửa chữa.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. **Thiếu chốt kiểm dịch dữ liệu (Data Quality Gate):** Dữ liệu văn bản học thuật khi thu thập có thể bị khuyết thiếu, tiêu đề bị cắt ngắn, trùng lặp DOI, hoặc abstract rỗng. Nếu không có Quality Gate tự động, pipeline vẫn nạp dữ liệu lỗi vào vector database, dẫn tới AI trả lời sai (Silent Failure) mà không báo lỗi runtime.
2. **Dữ liệu lỗi thời (Data Staleness):** Lĩnh vực AI biến đổi liên tục, các bài báo quá cũ (> 180 ngày) có thể dẫn tới khuyến nghị lỗi thời. Cần có SLA Freshness cảnh báo tự động.
3. **Đo lường định lượng khách quan:** Cần bộ Benchmark Test Set cố định phủ nhiều dạng câu hỏi để đánh giá công bằng chất lượng RAG qua các chu trình biến đổi dữ liệu.

### Cách triển khai

1. **Chuẩn Great Expectations 1.x Ephemeral Context:**
   Sử dụng API mới nhất của GX 1.x thay vì cú pháp cũ bị deprecated:
   ```python
   context = gx.get_context(mode="ephemeral")
   data_source = context.data_sources.add_pandas(name="papers_source")
   data_asset = data_source.add_dataframe_asset(name="papers_asset")
   batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
   batch = batch_def.get_batch(batch_parameters={"dataframe": df})
   ```
   Định nghĩa 4 loại Expectation thiết yếu (6 checks), gom vào một `ExpectationSuite` và validate một lần bằng `batch.validate(suite)`:
   - `ExpectTableRowCountToBeBetween(min_value=5, max_value=5000)`: Chặn dataset rỗng hoặc phình bất thường.
   - `ExpectColumnValuesToNotBeNull` cho 3 cột `paper_id`, `title`, `text_for_embedding`: Đảm bảo định danh và nội dung để embed.
   - `ExpectColumnValuesToBeUnique(column="paper_id")`: Chặn trùng lặp DOI (ghost vectors).
   - `ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30)`: Chặn tóm tắt rỗng hoặc bị cắt cụt.

   Kết quả rút gọn (tên expectation, cột, pass/fail, `unexpected_count`) cùng freshness được ghi vào `data/quality/{report_name}_quality_report.json`. `success = gx_success and is_fresh`.

2. **Giám sát Freshness SLA:**
   - Tính tỷ lệ: `stale_ratio = (df["age_days"] > 180).sum() / len(df)`.
   - SLA vi phạm (`is_fresh = False`) khi `stale_ratio > 0.25` (25%).

3. **Sinh Benchmark Test Set đa dạng:**
   Tạo 10 câu hỏi bao phủ 4 nhóm nghiệp vụ (xoay vòng → 3/3/2/2), mỗi câu về một bài khác nhau, với mẫu câu khớp từ khóa router của `qa.py`:
   - `summary`: *"What is the summary of the paper '{title}'?"* $\rightarrow$ Ground truth: `first_sentence(summary)`
   - `authors`: *"Who authored the paper '{title}'?"* $\rightarrow$ Ground truth: `authors_joined`
   - `date`: *"When was the paper '{title}' published?"* $\rightarrow$ Ground truth: `published`
   - `categories`: *"What categories does the paper '{title}' belong to?"* $\rightarrow$ Ground truth: `categories_joined`

   Loại bài có dấu `'` trong tiêu đề (vì `qa.py` tách tiêu đề giữa hai dấu `'`), sắp xếp theo `paper_id` để test set tất định. Nếu một loại câu hỏi không còn bài phù hợp thì chuyển sang loại kế tiếp và in cảnh báo.

4. **Tự động xuất báo cáo Markdown:**
   Hàm `generate_phase1_report` và `generate_corruption_report` tổng hợp metrics, kết quả validation GX và SLA Freshness thành file Markdown trực quan.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input** | `pd.DataFrame` chứa các cột `paper_id`, `title`, `summary`, `authors_joined`, `categories_joined`, `published`, `age_days` |
| **Output** | `data/eval/test_set.json` (10 items), `data/quality/*_quality_report.json`, `data/reports/*.md` |
| **Module phụ thuộc** | `core/config.py`, `core/utils.py`, `ingestion/cleaning.py` |
| **Module sử dụng output** | `evaluation/metrics.py` (dùng test_set), `pipelines/phase1.py`, `pipelines/corruption_flow.py` |
| **Điều kiện lỗi cần xử lý** | DataFrame < 10 bản ghi, cột `age_days` bị khuyết, định dạng ngày tháng không chuẩn |

### Cách xác minh

```bash
# Xác minh Quality Gate & Freshness (checkpoint bước 4):
python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); print('Tín hiệu hoàn thành: Quality check status =', res['success'])"

# Xác minh Test Set (checkpoint bước 5):
python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(f'Tín hiệu hoàn thành: Sinh được {len(ts)} câu hỏi test')"

# Chạy toàn bộ chu trình kiểm tra báo cáo:
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** 
  - Bước 4: `Quality check status = True`, `is_fresh = True`.
  - Bước 5: `Sinh được 10 câu hỏi test`.
  - `run_corruption_flow.py`: Báo cáo đối chiếu 3 trạng thái có đầy đủ số liệu chứng minh sụt giảm và phục hồi.
- **Kết quả thực tế:** Cả 4 lệnh chạy thành công với exit code 0. Bước 4 in `True`, bước 5 in `10`; corrupted gate `FAIL` (unique `paper_id`: 6, độ dài `summary`: 3, stale 40.91%), repaired gate `PASS`.
- **Artifact/log:** `data/quality/baseline_quality_report.json`, `data/quality/corrupted_quality_report.json`, `data/eval/test_set.json`, `data/reports/corruption_report.md`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần chọn phương thức cấu hình Great Expectations 1.x: Lưu ngữ cảnh ra ổ đĩa (`gx/` filesystem context) hay dùng Ephemeral In-Memory Context (`gx.get_context(mode="ephemeral")`).
- **Các phương án đã cân nhắc:**
  1. *Phương án A:* Khởi tạo thư mục `great_expectations/` trên ổ đĩa bằng CLI (`gx init`) và lưu Data Context tĩnh.
  2. *Phương án B:* Khởi tạo Ephemeral Context thuần Python trong bộ nhớ mỗi khi chạy pipeline.
- **Phương án đã chọn:** Chọn Phương án B (Ephemeral Context).
- **Lý do:** 
  - Đảm bảo tính Idempotent: Mỗi lần pipeline chạy đều độc lập, không bị xung đột cache, không sinh file rác vào repository.
  - Phù hợp hoàn hảo với kiến trúc pipeline tự động: Khi kiểm thử nhiều trạng thái liên tiếp (`baseline`, `corrupted`, `repaired`), ephemeral context cho phép nạp DataFrame động và validate tức thì mà không lo lock file SQLite hay metadata cũ của GX.
- **Bằng chứng quyết định phù hợp:** Pipeline chạy trơn tru qua cả 3 trạng thái với thời gian thực thi nhanh, không phát sinh lỗi xung đột tên Data Asset hay DataSource.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  ValueError: Khong du paper hop le cho cau hoi dang 'categories'.
  ```
- **Lệnh hoặc bước tái hiện:** Chạy `build_test_set()` trên `papers_clean.json` được tạo từ dữ liệu Crossref API thật (thay vì raw snapshot của lab).
- **Nguyên nhân gốc:** Cả 24 bản ghi Crossref thật không có trường `subject`, nên `categories_joined` rỗng ở mọi dòng. Bản đầu của `build_test_set()` yêu cầu mỗi loại câu hỏi phải có bài phù hợp và `raise` ngay khi thiếu.
- **Cách xử lý:** 
  1. Thêm cơ chế chuyển loại câu hỏi: nếu một loại không còn bài phù hợp thì thử loại kế tiếp trong `QUESTION_PLAN` và in cảnh báo `[testset] Canh bao: ...`, thay vì crash.
  2. Phối hợp với ingestion (Dũng) khôi phục raw snapshot của lab (có `subject`) để test set phủ đủ 4 loại.
- **Cách xác minh sau khi sửa:** Trên dữ liệu API thật: sinh 10 câu (summary 5, authors 3, date 2) kèm cảnh báo. Trên snapshot: 10 câu phân bổ 3/3/2/2, không cảnh báo, và `qa.py` trích xuất khớp 10/10 ground truth khi được đưa đúng bài.
- **Điều học được:** Bộ đánh giá phải kiểm tra độ đầy đủ của dữ liệu nguồn trước khi sinh câu hỏi; dữ liệu "đúng schema" vẫn có thể rỗng ở những trường mà evaluation phụ thuộc.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   - Metadata bài báo được Crossref API trả về dạng JSON thô.
   - Pipeline bóc tách DOI, tác giả, ngày đăng, loại bỏ thẻ `<jats:p>` trong abstract và lưu trữ raw snapshot.
   - Module Cleaning chuẩn hóa dữ liệu, tính `age_days`, ghép `text_for_embedding` gồm 5 trường thông tin (Title, Authors, Published, Categories, Summary) và khử trùng lặp.
   - Text được đưa qua mô hình `sentence-transformers/all-MiniLM-L6-v2` để sinh vector 384 chiều và nạp vào ChromaDB collection với không gian khoảng cách Cosine.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   - Bộ test set chứa các câu hỏi đa dạng kèm danh sách `ground_truth_doc_ids` (ID của bài báo chứa thông tin gốc).
   - Khi Agent truy vấn, hệ thống lấy Top-K tài liệu được vector search trả về. Nếu ID tài liệu gốc nằm trong Top-K, `retrieval_hit = True` (dùng để tính Retrieval Hit Rate).
   - Câu trả lời của Agent được so khớp với `ground_truth` thông qua Token F1 và LLM Judge để đo lường độ chính xác nội dung.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - **Quality checks (GX 1.x):** Kiểm tra tính toàn vẹn về mặt cấu trúc và cú pháp của dữ liệu (Schema, Not Null, Unique, độ dài chuỗi ký tự, số lượng dòng). Đây là chốt chặn phát hiện dữ liệu bị hỏng, khuyết thiếu hoặc biến dạng.
   - **Freshness monitoring (SLA):** Kiểm tra tính hợp thời về mặt thời gian (Temporal Validity). Dữ liệu có thể hoàn toàn đúng schema, không null, nhưng nếu đã quá cũ (> 180 ngày) thì không còn phù hợp để phục vụ các bài toán truy vấn kiến thức mới.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   - Giữ nguyên biến độc lập trong phương pháp luận thực nghiệm: Để đo lường chính xác tác động của Data Corruption và hiệu quả của Idempotent Repair, tập câu hỏi đánh giá và tiêu chuẩn chấm điểm phải hoàn toàn nhất quán. Nếu thay đổi test set giữa các pha, kết quả chênh lệch sẽ bị nhiễu do độ khó của câu hỏi chứ không phản ánh đúng chất lượng dữ liệu.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - **Về Metric:** `retrieval_hit_rate` phục hồi từ 60% lên 100%, `mean_token_f1` phục hồi từ 0.8 lên 1.0.
   - **Về Observability:** Quality Gate chuyển từ `FAIL` (4/6) sang `PASS` (6/6); Freshness SLA chuyển từ `STALE` (40.91%) sang `FRESH` (4.17%).
   - **Về Artifact:** Dữ liệu sạch tái tạo tại `data/clean/papers_clean_repaired.json` có 24 dòng, nội dung (`paper_id`, `title`, `summary`, `published`, `text_for_embedding`) trùng khớp với `data/clean/papers_clean.json` ban đầu, được khôi phục trực tiếp từ raw snapshot bất biến.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| :--- | :---: | :---: | :---: | :--- |
| `retrieval_hit_rate` | 100.00% | 60.00% | 100.00% | 4 câu miss: 3 do bài bị drop (eval_002/003/006), 1 do tiêu đề bị cắt (eval_010) |
| `mean_token_f1` | 1.0000 | 0.8000 | 1.0000 | Giảm do 2 câu hỏi `date` trả về ngày đã bị lùi 365 ngày |
| `judge_accuracy` | 100.00% | 80.00% | 100.00% | Cao hơn hit rate vì 3 câu `authors` lấy nhầm bài nhưng bài đó có cùng tác giả |
| `mean_judge_score` | 5.00 | 4.30 | 5.00 | eval_003 = 1 điểm, eval_007 = 2 điểm |
| Quality checks | PASS (6/6) | FAIL (4/6) | PASS (6/6) | GX 1.x phát hiện vi phạm Unique (6 giá trị trùng) và độ dài Summary (3 dòng rỗng) |
| Freshness status | FRESH (4.17%) | STALE (40.91%) | FRESH (4.17%) | Stale date lùi `published` 365 ngày trên 8 dòng |

### Kết luận từ số liệu

1. **Chuỗi 1 (Corruption):** Stale date (8 dòng) → Freshness `STALE` (40.91% > 25%) → câu hỏi `date` trả lời sai (eval_007 lấy đúng bài nhưng trả `2025-06-03`, judge 2/5) → Token F1 giảm xuống 0.8. Trong khi đó, drop latest records **không** làm gate báo lỗi (row count 22 vẫn trong 5–5000) nhưng làm Retrieval Hit Rate giảm xuống 60%: đây là **Silent Failure**.
2. **Chuỗi 2 (Repair):** Kích hoạt Idempotent Repair tái tạo từ raw snapshot $\rightarrow$ Quality Gate trở lại `PASS` 6/6, Freshness trở lại `FRESH` $\rightarrow$ Toàn bộ chỉ số Agent phục hồi 100% về trạng thái Baseline ban đầu.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**
- Lỗi **Drop 20% bài báo mới nhất** ảnh hưởng nặng nhất tới retrieval: 3 bài của test set bị xóa khỏi corpus nên không thể tìm thấy tài liệu gốc, và quality gate hiện tại không có luật nào bắt được lỗi này. Lỗi **Stale date** ảnh hưởng rõ nhất tới câu trả lời. Blank summary bị gate bắt được nhưng không rơi vào bài nào của test set, nên không làm giảm metric.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Tầm quan trọng của Data Quality Gate sớm:** Lỗi dữ liệu không làm crash server RAG mà âm thầm làm giảm sút câu trả lời của AI (Silent Failure). Cần chặn đứng dữ liệu bẩn bằng Great Expectations trước khi embedding.
2. **Thiết kế Idempotent Pipeline & Data Lineage:** Luôn bảo toàn bản sao thô (Raw Preservation) bất biến. Khi tầng serving bị ô nhiễm, ta luôn có khả năng tự phục hồi sạch sẽ 100% từ cội nguồn.
3. **Đánh giá đa chiều (Multi-faceted Observability):** Quan sát dữ liệu phải kết hợp giữa tính đúng đắn cấu trúc (Schema/Null/Unique) và tính hợp thời nghiệp vụ (Freshness SLA).

### Nếu có thêm thời gian
- Xây dựng một **Drift Monitoring Dashboard** bằng Streamlit hiển thị biểu đồ phân bố độ dài abstract, phân bố khoảng cách vector embedding theo thời gian thực để phát hiện Semantic Drift trước khi chất lượng suy giảm.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Tuấn Tú  
**Ngày xác nhận:** 2026-09-26