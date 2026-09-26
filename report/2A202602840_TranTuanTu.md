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
| Tinh chỉnh cấu hình LLM Judge | Evaluation (`metrics.py`, `llm.py`) | Cấu hình model `gemini-3.8-flash` và thiết lập `max_retries=1` kèm cơ chế heuristic fallback khi gặp rate limit 429 |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| Xây dựng bộ test set 10 câu hỏi | `src/evaluation/testset.py`<br>`data/eval/test_set.json` | 10 câu hỏi phủ đủ 4 nhóm (`summary`, `authors`, `date`, `categories`) kèm ground-truth doc IDs | `python script/verify_cp2.py`<br>In ra: `Tín hiệu hoàn thành: Sinh được 10 câu hỏi test` |
| Thiết lập Data Quality Gate GX 1.x | `src/observability/quality.py`<br>`data/quality/*_quality_report.json` | 4 Expectations thiết yếu: RowCount, NotNull, Unique, Length | `python script/verify_cp1.py`<br>In ra: `Quality check status = True` (Baseline) và `False` (Corrupted) |
| Giám sát Freshness SLA | `src/observability/quality.py`<br>`data/quality/freshness_report.json` | Cảnh báo `is_fresh=False` khi tỷ lệ quá hạn 180 ngày > 25% | `python script/verify_cp1.py`<br>Baseline: `1/24` stale (4.2% -> `is_fresh=True`) |
| Xuất báo cáo đối chiếu 3 trạng thái | `src/observability/reporting.py`<br>`data/reports/corruption_report.md` | Bảng Markdown đối chiếu định lượng Baseline vs Corrupted vs Repaired | `python script/run_corruption_flow.py` xuất bảng đối chiếu đầy đủ |

**Một output cụ thể do phần việc của tôi tạo ra:**
Bảng đối chiếu tổng hợp 3 trạng thái trong [`data/reports/corruption_report.md`](file:///home/tu/VinLab/K4-L3B-DAY10-ByeByeWorld-DataPipelineDataObservability/data/reports/corruption_report.md) chứng minh hiện tượng suy giảm ngầm (Silent Failure) khi Retrieval Hit Rate sụt từ 100% xuống 50%, Token F1 giảm từ 1.0000 xuống 0.7729, và phục hồi trở lại 100% sau khi sửa chữa.

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
   Định nghĩa 4 Expectations thiết yếu:
   - `ExpectTableRowCountToBeBetween(min_value=20, max_value=30)`: Chặn việc mất mát dữ liệu quy mô lớn (> 20% bản ghi).
   - `ExpectColumnValuesToNotBeNull(column="paper_id")` & `ExpectColumnValuesToNotBeNull(column="title")`: Đảm bảo định danh bắt buộc.
   - `ExpectColumnValuesToBeUnique(column="paper_id")`: Chặn trùng lặp DOI.
   - `ExpectColumnValueLengthsToBeBetween(column="title", min_value=8)` & `(column="summary", min_value=20)`: Chặn tiêu đề hoặc tóm tắt bị cắt cụt.

2. **Giám sát Freshness SLA:**
   - Tính tỷ lệ: `stale_ratio = (df["age_days"] > 180).sum() / len(df)`.
   - SLA vi phạm (`is_fresh = False`) khi `stale_ratio > 0.25` (25%).

3. **Sinh Benchmark Test Set đa dạng:**
   Tạo 10 câu hỏi bao phủ 4 nhóm nghiệp vụ với mẫu câu chuẩn hóa:
   - `summary`: *"What is the summary of '{title}'?"* $\rightarrow$ Ground truth: `first_sentence(summary)`
   - `authors`: *"Who authored '{title}'?"* $\rightarrow$ Ground truth: `authors_joined`
   - `date`: *"When was '{title}' published?"* $\rightarrow$ Ground truth: `published`
   - `categories`: *"What categories does '{title}' belong to?"* $\rightarrow$ Ground truth: `categories_joined`

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
source .venv/bin/activate
# Xác minh Quality Gate & Freshness (CP1):
python script/verify_cp1.py

# Xác minh Test Set (CP2):
python script/verify_cp2.py

# Chạy toàn bộ chu trình kiểm tra báo cáo (CP3 & CP5):
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** 
  - `verify_cp1.py`: `Quality check status = True`, `is_fresh = True`.
  - `verify_cp2.py`: `Sinh được 10 câu hỏi test`.
  - `run_corruption_flow.py`: Báo cáo đối chiếu 3 trạng thái có đầy đủ số liệu chứng minh sụt giảm và phục hồi.
- **Kết quả thực tế:** Cả 4 lệnh chạy thành công với exit code 0.
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
  ClientError: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota... limit: 5 requests per minute, model: gemini-3.8-flash. Please retry in 58s.'}}
  ```
- **Lệnh hoặc bước tái hiện:** Chạy `python script/run_phase1.py` khi đánh giá liên tiếp 10 câu hỏi qua LLM Judge.
- **Nguyên nhân gốc:** Quota tầng Free Tier của Google Gemini API giới hạn 5 requests/phút (5 RPM). Mặc định `ChatGoogleGenerativeAI` kích hoạt retry lũy tiến khiến tiến trình bị dừng (sleep) 60 giây nhiều lần.
- **Cách xử lý:** 
  1. Cấu hình `max_retries=1` cho model client trong [`src/retrieval/llm.py`](file:///home/tu/VinLab/K4-L3B-DAY10-ByeByeWorld-DataPipelineDataObservability/src/retrieval/llm.py#L16-L22).
  2. Tận dụng cơ chế Fallback Heuristic Judge sẵn có trong `src/evaluation/metrics.py`: Nếu API tạm hết quota, hệ thống tự động fallback tính Token F1 chính xác mà không làm crash pipeline hay tắc nghẽn luồng chạy.
- **Cách xác minh sau khi sửa:** Chạy lại `python script/run_phase1.py` và `python script/run_corruption_flow.py`, tiến trình hoàn thành mượt mà trong thời gian ngắn mà không bị treo.
- **Điều học được:** Khi thiết kế hệ thống quan sát và đánh giá (Evaluation Observability), luôn phải có cơ chế Circuit Breaker / Fallback Heuristic để pipeline không bị phụ thuộc tuyệt đối vào độ khả dụng của dịch vụ LLM bên ngoài.

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
   - **Về Metric:** `retrieval_hit_rate` phục hồi từ 50% lên 100%, `mean_token_f1` phục hồi từ 0.7729 lên 1.0000.
   - **Về Observability:** Quality Gate chuyển từ `FAILED` sang `PASSED`; Freshness SLA chuyển từ `STALE` sang `FRESH`.
   - **Về Artifact:** Dữ liệu sạch tái tạo tại `data/clean/papers_clean_repaired.json` có số dòng (24), nội dung và hash đồng nhất với `data/clean/papers_clean.json` ban đầu, được khôi phục trực tiếp từ raw snapshot bất biến.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| :--- | :---: | :---: | :---: | :--- |
| `retrieval_hit_rate` | 100.00% | 50.00% | 100.00% | Bị sụt giảm một nửa do 20% bài bị drop và tiêu đề/abstract bị hỏng |
| `mean_token_f1` | 1.0000 | 0.7729 | 1.0000 | Giảm mạnh do tóm tắt bị blank hoặc chèn chuỗi rác |
| `judge_accuracy` | 100.00% | 80.00% | 100.00% | Các câu hỏi thuộc bài báo bị lỗi trả về sai hoặc không tìm thấy |
| `mean_judge_score` | 5.00 | 3.80 | 5.00 | Điểm định tính sụt giảm rõ rệt theo chất lượng trả lời |
| Quality checks | PASSED | FAILED | PASSED | GX 1.x phát hiện vi phạm Unique (duplicate rows) và RowCount |
| Freshness status | FRESH | STALE | FRESH | Tỷ lệ stale vọt lên do bị tiêm bài lùi về năm 2023 |

### Kết luận từ số liệu

1. **Chuỗi 1 (Corruption):** Tiêm 6 lỗi dữ liệu (Drop, Blank, Noise, Truncate, Stale, Duplicate) $\rightarrow$ Quality Gate báo `FAILED` và Freshness báo `STALE` $\rightarrow$ Retrieval Hit Rate sụt giảm nghiêm trọng từ 100% xuống 50%, Token F1 giảm xuống 0.7729 (Minh chứng rõ nét hiện tượng **Silent Failure**).
2. **Chuỗi 2 (Repair):** Kích hoạt Idempotent Repair tái tạo từ raw snapshot $\rightarrow$ Quality Gate trở lại `PASSED`, Freshness trở lại `FRESH` $\rightarrow$ Toàn bộ chỉ số Agent phục hồi 100% về trạng thái Baseline ban đầu.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**
- Lỗi **Drop 20% bài báo mới nhất** và **Blank Summary** ảnh hưởng nặng nhất. Khi bài báo bị drop, câu hỏi liên quan hoàn toàn không thể tìm thấy tài liệu gốc (Hit Rate = 0 cho các câu đó). Khi abstract bị xóa rỗng, câu trả lời suy biến thành chuỗi rỗng hoặc thông báo không tìm thấy, kéo sụt Token F1.

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
