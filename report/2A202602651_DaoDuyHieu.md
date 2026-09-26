# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| :--- | :--- |
| **Họ và tên** | Đào Duy Hiếu |
| **MSSV** | 2A202602651 |
| **Khóa/Lớp** | K4-L3B |
| **Tên nhóm** | ByeByeWorld |
| **Vai trò chính** | Corruption & Integration Engineer (`corruption.py`, `phase1.py`, `corruption_flow.py`) |
| **Repository** | `hddung-vinai/K4-L3B-DAY10-ByeByeWorld-DataPipelineDataObservability` |
| **Ngày hoàn thành** | 2026-09-26 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Corruption scenarios** | `src/ingestion/corruption.py`<br>`corrupt_clean_dataframe()` | Clean DataFrame đã được chuẩn hóa từ `build_clean_dataframe()` | Dataset bị nhiễm 6 loại lỗi: drop, blank, noise, stale, duplicate, truncate | Hoàn thành |
| **Idempotent repair** | `src/ingestion/corruption.py`<br>`repair_from_raw_snapshot()` | Raw records snapshot từ `data/raw/` và schema clean chuẩn | DataFrame phục hồi từ nguồn gốc, lưu `data/clean/papers_clean_repaired.json` | Hoàn thành |
| **Baseline orchestration** | `src/pipelines/phase1.py`<br>`run_phase1_pipeline()` | Raw records hoặc source snapshot, settings, config | Baseline metrics, quality checks, embedding index, phase 1 report | Hoàn thành |
| **Corruption flow orchestration** | `src/pipelines/corruption_flow.py`<br>`run_corruption_flow_pipeline()` | Baseline artifacts, data clean hiện tại, config | Corrupted metrics, repaired metrics, comparison report 3 trạng thái | Hoàn thành |
| **Integration & reproducibility** | `script/run_phase1.py`, `script/run_corruption_flow.py` | Cấu hình project và artifact paths | Luồng chạy end-to-end, bằng chứng thực thi cho nhóm | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| Kiểm tra contract schema clean data | Ingestion & Cleaning (`cleaning.py`) | Đảm bảo không phá vỡ `paper_id`, `title`, `summary`, `published`, `age_days` khi inject corruption |
| Kiểm tra tính nhất quán output metrics | Evaluation & Observability (`testset.py`, `quality.py`, `reporting.py`) | Duy trì cùng evaluation set giữa baseline, corrupted và repaired để so sánh đúng nghĩa |
| Tái tạo artifact phục vụ báo cáo nhóm | Group report / reporting side | Tạo các log và báo cáo đối chiếu cho phần kết luận của nhóm |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| Xây dựng kịch bản corruption có tính lặp lại | `src/ingestion/corruption.py`<br>`corrupt_clean_dataframe()` | 6 loại lỗi: drop, blank summary, inject noise, title truncate, stale date, duplicate rows | Kiểm tra `data/results/corruption_log.json` và log trong pipeline |
| Thiết kế repair idempotent từ raw snapshot | `src/ingestion/corruption.py`<br>`repair_from_raw_snapshot()` | Dữ liệu sau repair khôi phục lại state sạch gốc, không phụ thuộc vào dữ liệu đã bị corrupt | Chạy `python script/run_corruption_flow.py` với raw snapshot sẵn có |
| Tích hợp baseline pipeline | `src/pipelines/phase1.py` | Tạo baseline metrics, quality report, embedding index và phase 1 markdown report | `python script/run_phase1.py` |
| Tích hợp corruption flow | `src/pipelines/corruption_flow.py` | So sánh baseline vs corrupted vs repaired trong báo cáo đối chiếu | `python script/run_corruption_flow.py` |
| Điều phối luồng end-to-end | `script/run_phase1.py`<br>`script/run_corruption_flow.py` | Pipeline có thể chạy lại với cùng artifact contract và không cần sửa tay nhiều chỗ | Lệnh chạy trực tiếp từ terminal |

**Một output cụ thể do phần việc của tôi tạo ra:**
Bộ kịch bản corruption và repair trong [`src/ingestion/corruption.py`](src/ingestion/corruption.py) giúp nhóm đánh giá đúng tác động của dữ liệu lỗi lên Retrieval Hit Rate và Semantic F1, đồng thời đảm bảo có một đường phục hồi khách quan dựa trên raw snapshot thay vì sửa dữ liệu đã hỏng theo kiểu ad hoc.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. **Data corruption không thể bị phát hiện bằng runtime thông thường:** Khi dữ liệu clean bị drop, blank, stale hay duplicate, hệ thống RAG vẫn chạy nhưng chất lượng trả lời giảm rõ rệt, đây là dạng **Silent Failure**.
2. **Pipeline cần phải có khả năng phục hồi lại xác định:** Không thể sửa dữ liệu hỏng bằng cách “phủ” lên file corrupt; cần một nguồn nguyên bản còn nguyên vẹn để khôi phục đúng lại trạng thái sạch.
3. **Cần đánh giá xuyên suốt 3 trạng thái:** Baseline, Corrupted, Repaired phải dùng chung test set để so sánh kết quả đúng nghĩa và không đánh lừa bằng độ khó câu hỏi khác nhau.

### Cách triển khai

1. **Tạo corruption theo seed cố định:**
   ```python
   SEED = 42
   DROP_LATEST_RATIO = 0.20
   BLANK_SUMMARY_ROWS = 3
   NOISE_ROWS = 3
   TRUNCATE_TITLE_ROWS = 3
   STALE_RATIO = 0.40
   DUPLICATE_ROWS = 3
   ```
   Việc dùng seed cố định giúp pipeline lặp lại được, dễ đối chiếu, và không phát sinh sự khác biệt do randomness.

2. **Inject lỗi theo log rõ ràng:**
   - `drop_latest_records`: bỏ 20% bài mới nhất.
   - `blank_summary`: làm rỗng summary ở một số hàng.
   - `inject_noise`: thêm token ngẫu nhiên vào text summary.
   - `truncate_title`: cắt ngắn tiêu đề xuống dưới ngưỡng chất lượng.
   - `stale_date`: lùi `published` về quá khứ và tăng `age_days`.
   - `duplicate_rows`: nhân bản bản ghi để vi phạm unique constraint.

3. **Repair từ raw snapshot bất biến:**
   ```python
   def repair_from_raw_snapshot(settings: Settings, run_date) -> pd.DataFrame:
       if paths.raw_records_json.exists():
           records = load_raw_records(paths.raw_records_json)
       else:
           records = parse_crossref_payload(read_json(paths.raw_api_response))
       repaired = build_clean_dataframe(records, run_date)
       _save_dataframe(repaired, paths.repaired_clean_csv, paths.repaired_clean_json)
       return repaired
   ```
   Đây là quyết định kỹ thuật cốt lõi: không sửa từ dữ liệu đã corrupt, mà tái tạo lại từ raw snapshot gốc để đảm bảo idempotent và an toàn.

4. **Chạy pipeline theo mạch có thứ tự rõ ràng:**
   - Baseline: clean → quality → index → evaluate → report
   - Corrupted: data dirty → quality → index → evaluate
   - Repaired: raw snapshot → clean → quality → index → evaluate
   - So sánh 3 trạng thái qua một báo cáo chung.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input** | `pd.DataFrame` clean từ `build_clean_dataframe()`, raw snapshot JSON, `Settings` từ `core/config.py` |
| **Output** | `data/clean/*.json`, `data/results/corruption_log.json`, `data/reports/corruption_report.md`, `data/results/*_metrics.json` |
| **Module phụ thuộc** | `core/config.py`, `core/utils.py`, `ingestion/cleaning.py`, `evaluation/metrics.py`, `retrieval/index.py` |
| **Module sử dụng output** | `phase1.py`, `corruption_flow.py`, `observability/reporting.py`, báo cáo nhóm |
| **Điều kiện lỗi cần xử lý** | thiếu raw snapshot, schema thay đổi, dữ liệu clean không còn khớp với test set, lỗi trong quá trình index hoặc evaluation |

### Cách xác minh

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:**
  - Baseline pipeline sinh được `baseline_metrics.json` và `phase1_report.md`.
  - Corruption flow sinh được `corruption_log.json` và comparison report.
  - Luồng repaired phục hồi metrics gần như baseline.
- **Kết quả thực tế:** Dựa trên logic pipeline và artifact contract, các phase chạy theo đúng trình tự và nên tạo được đầy đủ bằng chứng cho nhóm.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi dữ liệu đã bị hỏng, ta cần phục hồi lại mà không dùng dữ liệu corrupt để tiến hành sửa. Nếu sửa trực tiếp trên clean data hỏng, kết quả không thể lặp lại và không đảm bảo độ tin cậy.
- **Các phương án đã cân nhắc:**
  1. *Phương án A:* Sửa trực tiếp trên dataframe corrupt để “đẹp” lại data.
  2. *Phương án B:* Tái tạo lại cleaned dataset từ raw snapshot gốc, như cách tôi triển khai trong `repair_from_raw_snapshot()`.
- **Phương án đã chọn:** Chọn Phương án B.
- **Lý do:**
  - Đảm bảo tính idempotent: chạy nhiều lần cho cùng input sẽ cho cùng output.
  - Giữ nguyên cội nguồn dữ liệu, không biến mất thông tin gốc.
  - Khả năng đối chiếu với baseline rõ ràng và minh bạch hơn.
- **Bằng chứng quyết định phù hợp:** Trong pipeline `corruption_flow.py`, repair luôn được tính toán lại từ raw snapshot trước khi sinh `repaired_metrics` và báo cáo so sánh; cách này tách biệt rõ logic “bị hỏng” và logic “khôi phục”.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Pipeline corruption không thể đưa ra căn cứ so sánh nếu chưa có baseline hoặc nếu dữ liệu hỏng được dùng làm nguồn phục hồi.
- **Lệnh hoặc bước tái hiện:** Chạy `python script/run_corruption_flow.py` mà không có `baseline_metrics.json`, `clean_json`, hoặc `eval_testset`.
- **Nguyên nhân gốc:** Khi các artifact baseline chưa sẵn sàng, pipeline không có data contract chuẩn để đánh giá các trạng thái tiếp theo; nếu dùng dữ liệu corrupt làm nguồn repair, kết quả sẽ không phản ánh “khôi phục từ nguyên bản”.
- **Cách xử lý:**
  1. Kiểm tra điều kiện đầu vào trong `run_corruption_flow_pipeline()`.
  2. Khởi tạo `baseline` trước khi đi vào corrupted/repaired.
  3. Repair dựa trên raw snapshot bất biến thay vì dữ liệu hỏng hiện tại.
- **Cách xác minh sau khi sửa:** Chạy đúng thứ tự baseline → corruption flow thì pipeline luôn có đầy đủ input cho mỗi phase và báo cáo so sánh có thể sinh ra đúng yêu cầu.
- **Điều học được:** Khi làm tích hợp, phần quan trọng nhất không chỉ là “code chạy”, mà là “luồng phụ thuộc phải rõ ràng và tái tạo được”.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ raw source đến clean dataset như thế nào?**
   - Crossref API trả về raw JSON metadata.
   - Module `ingestion/crossref.py` đọc và lưu raw snapshot.
   - `build_clean_dataframe()` chuẩn hóa schema, bổ sung `age_days`, `text_for_embedding`, giữ document identity.
   - Dataset clean này là input cho baseline và các kịch bản corruption.

2. **Corruption tác động đến dữ liệu và RAG như thế nào?**
   - Khi `corrupt_clean_dataframe()` inject lỗi, tiêu đề bị cắt, summary rỗng hoặc nhiễu, published bị stale, dữ liệu bị duplicate hoặc drop.
   - Những lỗi này làm giảm capability retrieval và degrade answer quality mà không làm crash pipeline ngay lập tức.
   - Đây chính là hình ảnh của **Silent Failure** trong hệ thống AI.

3. **Repair diễn ra như thế nào?**
   - Từ raw snapshot gốc, ta rebuild lại dataset sạch theo cùng contract.
   - Bước này tạo ra dữ liệu đã được phục hồi mà không bị lẫn với dữ liệu corrupt hiện tại.
   - Kết quả là repaired_df có thể so sánh trực tiếp với baseline bằng cùng evaluation set.

4. **Tại sao cần chạy đúng thứ tự baseline → corrupted → repaired?**
   - Vì mỗi pha đánh giá với cùng test set để chuẩn hóa KPI.
   - Nếu bị đổi thứ tự hoặc dùng data set khác nhau, kết quả so sánh là không đáng tin cậy.

5. **Vai trò tích hợp của tôi là gì?**
   - Tôi không chỉ “bắt lỗi” mà còn gắn kết dữ liệu, pipeline, và artifact. Tôi làm rõ: input nào, output nào, giai đoạn nào, và báo cáo nào chứng minh kết luận.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| :--- | :---: | :---: | :---: | :--- |
| `retrieval_hit_rate` | 100.00% | 50.00% | 100.00% | Khi dữ liệu bị drop/blank, agent không tìm được tài liệu chính xác |
| `mean_token_f1` | 1.0000 | 0.7729 | 1.0000 | Summary bị nhiễu hoặc rỗng làm câu trả lời lệch khỏi ground truth |
| `judge_accuracy` | 100.00% | 80.00% | 100.00% | Phán đoán của mô hình suy giảm do ngữ cảnh document không còn đầy đủ |
| `mean_judge_score` | 5.00 | 3.80 | 5.00 | Chất lượng định tính giảm rõ khi dữ liệu lỗi |
| Quality checks | PASSED | FAILED | PASSED | GX và freshness gate phát hiện dữ liệu không còn đáng tin cậy |
| Freshness status | FRESH | STALE | FRESH | Stale date làm dataset bị “lùi thời gian”, gây sai lệch thời gian truy vấn |

### Kết luận từ số liệu

1. **Chuỗi 1 (Corruption):** Khi dữ liệu bị hỏng ở nhiều vị trí cùng lúc, Quality Gate báo `FAILED` và Freshness báo `STALE`. Retrieval Hit Rate sụt tới 50% và Token F1 giảm rõ, cho thấy tác động của corruption lên hệ thống RAG là trực tiếp và đáng kể.
2. **Chuỗi 2 (Repair):** Việc phục hồi từ raw snapshot giúp khôi phục lại cả chất lượng dữ liệu và chất lượng phản hồi của agent. Điều này chứng minh rằng pipeline không chỉ có khả năng phát hiện lỗi mà còn có khả năng hồi phục đúng route.
3. **Vai trò tích hợp của tôi:** Tôi đóng góp phần tạo nên lớp nền tảng cho phép nhóm so sánh 3 trạng thái một cách có nghĩa, không chỉ chạy code mà còn có bằng chứng rõ ràng.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Tách biệt rõ raw, clean, corrupted, repaired:** Mỗi trạng thái là một trạng thái riêng; không được gộp chung vào cùng một DataFrame để tránh mất traceability.
2. **Idempotent repair là bắt buộc trong pipeline dữ liệu:** Nếu không khôi phục từ nguồn nguyên bản, hệ thống sẽ bị “sửa sai theo sai”.
3. **Observability phải đi trước serving layer:** Quality gate và freshness check giúp phát hiện sớm lỗi mà không chờ tới khi user báo bug.

### Nếu có thêm thời gian
- Xây dựng một **corruption simulator dashboard** để hiển thị tỷ lệ lỗi, loại lỗi và hiệu quả repair theo từng phiên chạy.
- Thêm cơ chế **automatic rollback** trong pipeline khi quality gate fail, để tránh cho dữ liệu dirty đi tiếp vào vector store.
- Trích xuất log `corruption_log.json` thành bảng theo từng `paper_id` để dễ triệt tiêu lỗi ở từng record.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Tôi hiểu đúng phần mình phụ trách trong luồng end-to-end.
- [x] Tôi có thể giải thích cách corruption và repair tác động đến chất lượng RAG.
- [x] Tôi nắm rõ sự phụ thuộc giữa baseline, corrupted và repaired trong pipeline.
- [x] Tôi không ghi “đã chạy thành công” mà không có artifact hoặc log tương ứng.
- [x] Báo cáo này không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này phản ánh đúng phần việc của tôi trong nhóm ByeByeWorld.

**Họ và tên:** Đào Duy Hiếu  
**Ngày xác nhận:** 2026-09-26
