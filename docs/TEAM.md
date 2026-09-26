# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `ByeByeWorld`
- **Mã Nhóm / Lớp:** `K4-L3B-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3B-DAY10-ByeByeWorld-DataPipelineDataObservability`
- **Link Repository:** https://github.com/hddung-vinai/K4-L3B-DAY10-ByeByeWorld-DataPipelineDataObservability

---

## # Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Hoàng Đức Dũng | 2A202602798 | hddung18102005@gmail.com | Trưởng nhóm, Data Ingestion & Cleaning, chạy tích hợp (`crossref.py`, `cleaning.py`, raw/clean schema, artifacts `data/`, báo cáo nhóm) | `report/2A202602798_HoangDucDung.md` |
| 2 | Trần Tuấn Tú | 2A202602840 | trantuantu2004@gmail.com | Observability & Evaluation (`testset.py`, `quality.py` GX 1.x, `reporting.py`) | `report/2A202602840_TranTuanTu.md` |
| 3 | Đào Duy Hiếu | 2A202602651 | Hieudao8bit@gmail.com | Corruption & Pipeline Orchestration (`corruption.py`, `phase1.py`, `corruption_flow.py`) | `report/2A202602651_DaoDuyHieu.md` |

Nhóm có 3 thành viên. Phần RAG & Vector Index (`retrieval/index.py`, `embeddings.py`, `qa.py`) dùng starter code, không chỉnh sửa. Việc gọi index cho 3 collection nằm trong pipeline do Hiếu phụ trách.

---

## # Cá nhân

### ## HoangDucDung-2A202602798
- **Vai trò:** Trưởng nhóm, phụ trách Ingestion & Cleaning, chạy tích hợp và bàn giao artifacts.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng `src/ingestion/crossref.py`: `parse_crossref_payload()` bóc tách payload Crossref thành `PaperRecord` (DOI, title, abstract bỏ thẻ JATS, authors, subject, ngày, URL); `fetch_source_records()` gọi API với retry/backoff cho 429/5xx, lưu raw response, fallback đọc snapshot khi API lỗi; `load_raw_records()` đọc lại snapshot.
  - Xây dựng `src/ingestion/cleaning.py`: `build_clean_dataframe()` chuẩn hóa text, parse ngày, tính `age_days`, tạo `authors_joined`, `categories_joined`, `summary_chars`, `text_for_embedding`, lọc dòng lỗi và khử trùng lặp `paper_id`.
  - Phát hiện dữ liệu Crossref thật thiếu `subject`, khôi phục raw snapshot để giữ nguồn dữ liệu nhất quán cho cả nhóm.
  - Ghép code của 3 thành viên, chạy lại `run_phase1.py` và `run_corruption_flow.py`, commit artifacts `data/` (commit `399f8b2`); viết `report/group_report.md` và `docs/TEAM.md`.
- **Điều học được / Đóng góp chính:**
  - Raw preservation là điểm tựa để repair idempotent: chỉ ghi đè raw khi gọi API thành công, và repair luôn dựng lại từ raw thay vì vá dữ liệu hỏng.

### ## TranTuanTu-2A202602840
- **Vai trò:** Phụ trách Data Observability & Benchmark Evaluation.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng `src/evaluation/testset.py`: bộ 10 câu hỏi phủ 4 loại `summary`, `authors`, `date`, `categories`, định dạng câu hỏi khớp với router của `qa.py`, ground truth theo DOI.
  - Thiết lập Quality Gate theo Great Expectations 1.x (ephemeral context, 6 expectations) và Freshness SLA (`age_days > 180`, tối đa 25%) trong `src/observability/quality.py`.
  - Viết `src/observability/reporting.py`: báo cáo `phase1_report.md` và bảng đối chiếu 3 trạng thái `corruption_report.md`.
- **Điều học được / Đóng góp chính:**
  - Quality gate biến silent failure thành tín hiệu nhìn thấy được, nhưng chỉ bắt được những lỗi đã có luật tương ứng.

### ## DaoDuyHieu-2A202602651
- **Vai trò:** Phụ trách Corruption Suite & Pipeline Orchestration.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng `src/ingestion/corruption.py`: 6 kịch bản lỗi (drop latest 20%, blank summary, inject noise, truncate title, stale date, duplicate rows) với `seed = 42`, ghi log chi tiết vào `data/results/corruption_log.json`.
  - Nối pipeline baseline trong `src/pipelines/phase1.py` (ingest → clean → quality gate → index → test set → evaluate → report).
  - Nối luồng corruption → evaluate → repair → compare trong `src/pipelines/corruption_flow.py`, gồm `repair_from_raw_snapshot()` idempotent và 3 collection ChromaDB riêng biệt.
- **Điều học được / Đóng góp chính:**
  - Cô lập từng trạng thái dữ liệu (collection và artifact riêng, cùng một test set) để so sánh công bằng giữa baseline, corrupted và repaired.
