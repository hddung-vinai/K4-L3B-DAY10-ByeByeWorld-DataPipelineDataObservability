# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Hoàng Đức Dũng             |
| MSSV               | 2A202602798                     |
| Khóa/Lớp         | K4-L3B              |
| Tên nhóm         | ByeByeWorld     |
| Vai trò chính    | Data Ingestion & Cleaning owner, trưởng nhóm, chạy tích hợp                 |
| Repository         | https://github.com/hddung-vinai/K4-L3B-DAY10-ByeByeWorld-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Crossref ingestion | `src/ingestion/crossref.py`: `parse_crossref_payload()`, `fetch_source_records()`, `load_raw_records()` | Crossref REST API `/works` (query, filter, rows từ `Settings`) hoặc raw snapshot | `data/raw/crossref_response.json`, `data/raw/crossref_records.json`, `list[PaperRecord]` | Hoàn thành |
| Cleaning & data contract | `src/ingestion/cleaning.py`: `build_clean_dataframe()` | `list[PaperRecord]`, `run_date` | Clean DataFrame 16 cột (có `age_days`, `text_for_embedding`) → `data/clean/papers_clean.*` | Hoàn thành |
| Integration run & artifacts | `script/run_phase1.py`, `script/run_corruption_flow.py` | Code đã ghép của 3 thành viên | Toàn bộ `data/` (commit `399f8b2`) | Hoàn thành |
| Tài liệu nhóm | `report/group_report.md`, `docs/TEAM.md` | Artifacts trong `data/` | Báo cáo nhóm, bảng phân công | Hoàn thành |

`cleaning.py` là đầu vào của mọi module phía sau: `testset.py` và `quality.py` (Tú) đọc các cột `paper_id`, `summary`, `age_days`, `authors_joined`, `categories_joined`; `corruption.py` và `repair_from_raw_snapshot()` (Hiếu) dùng lại đúng schema và hàm `build_clean_dataframe()`.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Ghép code và chạy lại pipeline end-to-end | Tú (observability), Hiếu (pipelines) | 2 script chạy exit 0 trên commit `7b7c4fe`; artifacts commit ở `399f8b2` |
| Phát hiện lỗi mất ký tự `U+FFFD` khi chuyển file | Hiếu (`corruption.py`) | Hiếu sửa thành `"\ufffd\ufffd"`; xác nhận 3 summary corrupted có `U+FFFD` |
| Cấu hình LLM cho evaluation | Tú (LLM judge) | Chuyển từ Gemini (hết quota 20 request/ngày) sang OpenAI `gpt-4o-mini`; 30/30 câu được judge thật, 0 fallback |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Parse payload Crossref thành record chuẩn | `parse_crossref_payload()` | 24 `PaperRecord` từ 24 items | Parse snapshot cho kết quả khớp 100% với `crossref_records.json` mẫu của lab |
| Gọi API có retry và fallback offline | `fetch_source_records()` | Raw response + records | Giả lập lỗi 429 → đọc snapshot, vẫn ra 24 bài; gọi API thật → 24 bài |
| Làm sạch và tạo `text_for_embedding` | `build_clean_dataframe()` | 24 dòng clean, `age_days` 66–182 | Lệnh checkpoint in `Clean thành công 24 dòng`; GX baseline PASS 6/6 |
| Khử trùng lặp theo `paper_id` | `build_clean_dataframe()` | 0 dòng trùng | Thêm 1 bản ghi trùng: 25 dòng vào → 24 dòng ra |
| Chạy tích hợp | 2 script pipeline | Baseline 1.0/1.0, Corrupted 0.6/0.8, Repaired 1.0/1.0 (hit rate / token F1) | `data/reports/corruption_report.md` |

Output cụ thể do phần việc của tôi tạo ra: `data/clean/papers_clean.json` (24 dòng). Đây là "dữ liệu sạch" mà cả 3 trạng thái đều dựa vào. Repair gọi lại chính `build_clean_dataframe()` trên raw snapshot và cho ra dataset giống 100% baseline (`paper_id`, `title`, `summary`, `published`, `text_for_embedding`). Đó là lý do repair phục hồi 100% các metric.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Đưa metadata bài báo từ một API bên ngoài (có thể chậm, lỗi 429, trả dữ liệu thiếu trường, abstract lẫn thẻ XML) thành một bảng sạch với schema cố định mà các bước sau tin cậy được. Đồng thời phải giữ lại bản gốc để có thể chạy lại hoặc phục hồi mà không cần gọi API lần nữa.

### Cách triển khai

- **Raw preservation trước, biến đổi sau:** `fetch_source_records()` ghi nguyên JSON trả về vào `crossref_response.json` **chỉ khi gọi API thành công**, rồi mới parse. Nếu API lỗi, code đọc lại file đã lưu. Như vậy một lần gọi lỗi không bao giờ phá hỏng snapshot tốt.
- **Retry có backoff:** thử tối đa 3 lần với 429/500/502/503/504, chờ 1s rồi 2s, timeout 30s. Dùng tham số `select` để chỉ lấy các trường cần thiết, giảm dung lượng phản hồi.
- **Parse phòng thủ:** mọi trường đều đọc bằng `.get(...) or []`, vì Crossref thường thiếu `author`, `subject` hoặc `published`. Ngày lấy theo thứ tự ưu tiên `published` → `published-online` → `published-print` → `created`; `date-parts` thiếu tháng hoặc ngày thì mặc định là 1.
- **Cleaning không tin dữ liệu đầu vào:** bỏ thẻ HTML lần nữa và chuẩn hóa khoảng trắng; DOI viết thường để dedup đúng; `pd.to_datetime(errors="coerce", utc=True)` biến ngày lỗi thành `NaT` rồi lọc bỏ thay vì crash; `age_days` tính với `run_date` có múi giờ UTC.
- **`published` lưu dạng chuỗi `YYYY-MM-DD`**, vì ChromaDB metadata không nhận `Timestamp`.
- **Sắp xếp theo `published` giảm dần, rồi theo `paper_id`**, để output tất định giữa các lần chạy.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Crossref payload `message.items[]`; `Settings` (`source_query`, `source_filter`, `max_results = 24`, `paths`); `run_date` (UTC) |
| Output                         | `list[PaperRecord]` (11 trường); DataFrame gồm `paper_id, title, summary, authors, categories, primary_category, published, updated, abs_url, pdf_url, comment, age_days, authors_joined, categories_joined, summary_chars, text_for_embedding` |
| Module phụ thuộc             | `core/config.py`, `core/utils.py` (`normalize_whitespace`, `read_json`, `write_json`), `requests`, `pandas` |
| Module sử dụng output        | `observability/quality.py`, `evaluation/testset.py`, `retrieval/index.py`, `ingestion/corruption.py`, `pipelines/phase1.py`, `pipelines/corruption_flow.py` |
| Điều kiện lỗi cần xử lý | API 429/5xx/timeout; JSON hỏng; record thiếu DOI/title/abstract; DOI trùng; ngày không parse được; list tác giả hoặc subject rỗng |

### Cách xác minh

```bash
python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Tín hiệu hoàn thành: Đã tải {len(r)} bài báo')"
python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Tín hiệu hoàn thành: Clean thành công {len(df)} dòng')"
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** 24 bài báo, 24 dòng clean, 2 script exit 0, baseline quality gate PASS.
- **Kết quả thực tế:** đúng như kỳ vọng. `Đã tải 24 bài báo`, `Clean thành công 24 dòng`, `[phase1] Hoan tat: rows=24, hit_rate=1.00, token_f1=1.00, quality=True`, bảng 3 trạng thái in ra console.
- **Artifact/log:** `data/raw/`, `data/clean/papers_clean.json`, `data/quality/baseline_quality_report.json`, `data/reports/phase1_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi gọi Crossref API thật, 24 bản ghi trả về đều không có trường `subject`, và `fetch_source_records()` đã ghi đè raw snapshot của lab bằng dữ liệu này.
- **Các phương án đã cân nhắc:** (1) Giữ dữ liệu thật và bỏ loại câu hỏi `categories` khỏi test set; (2) Suy ra categories từ nguồn khác (journal/ISSN); (3) Khôi phục raw snapshot của lab và để pipeline mặc định dùng snapshot, chỉ gọi API khi đặt `REFRESH_SOURCE=1`.
- **Phương án đã chọn:** (3).
- **Lý do:** Đề bài yêu cầu test set phủ đủ 4 loại câu hỏi và các lần chạy phải tái hiện được. Dùng snapshot cố định giúp mọi thành viên và người chấm chạy ra cùng dữ liệu, không phụ thuộc mạng hay rate limit, và giữ được raw làm điểm tựa cho repair. Đánh đổi là dữ liệu không phải bản mới nhất; điều này chấp nhận được vì cờ `REFRESH_SOURCE` vẫn cho phép lấy dữ liệu mới khi cần.
- **Bằng chứng quyết định phù hợp:** sau khi khôi phục, `categories_joined` có giá trị ở 24/24 dòng, test set phân bổ 3/3/2/2, `phase1_report.md` ghi `source_mode = raw_snapshot`, và repair phục hồi 100% metric vì raw không đổi.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ValueError: Khong du paper hop le cho cau hoi dang 'categories'.` khi sinh test set trên dữ liệu vừa gọi API.
- **Lệnh hoặc bước tái hiện:** chạy lệnh checkpoint của `fetch_source_records()` khi có mạng, tạo lại `papers_clean.json`, rồi chạy `build_test_set()`.
- **Nguyên nhân gốc:** Crossref không trả `subject` cho các bản ghi này, nên `categories = []` ở mọi dòng. Đồng thời, lần gọi API thành công đã ghi đè snapshot của lab, nên mọi bước sau đều nhận dữ liệu thiếu categories.
- **Cách xử lý:** `git checkout -- data/raw/` để lấy lại snapshot; tạo lại `papers_clean.json` từ snapshot; `phase1.py` chỉ gọi API khi `REFRESH_SOURCE=1` hoặc khi chưa có raw.
- **Cách xác minh sau khi sửa:** `git status data/raw` sạch; chạy lệnh checkpoint bước 5 in `Sinh được 10 câu hỏi test` với đủ 4 loại; `run_phase1.py` in `1/7 Ingest: dung raw snapshot`.
- **Điều học được:** Dữ liệu từ API bên ngoài có thể "đúng định dạng nhưng thiếu nội dung". Cần kiểm tra độ đầy đủ của từng trường (ví dụ tỉ lệ `categories` rỗng) ngay ở bước ingestion, và không để một lần gọi API tự ý ghi đè snapshot đang được cả nhóm dùng.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Crossref đến vector index:** `fetch_source_records()` gọi `/works` với query, filter và `rows = 24`, lưu JSON gốc vào `data/raw/`, parse thành `PaperRecord`. `build_clean_dataframe()` làm sạch và ghép `text_for_embedding`. `LocalEmbeddingIndex.build()` mã hóa `text_for_embedding` bằng `all-MiniLM-L6-v2` (đã normalize) và nạp vào collection ChromaDB (cosine) cùng metadata `paper_id`, `title`, `published`, `authors_joined`, `categories_joined`, `summary`.
2. **Evaluation set và ground-truth ID:** mỗi câu hỏi gắn với đúng một DOI trong `ground_truth_doc_ids`. `retrieval_hit` đúng khi DOI đó nằm trong top-4 kết quả; `token_f1` và LLM judge so câu trả lời với `ground_truth` (câu đầu của summary, tên tác giả, ngày hoặc categories).
3. **Quality checks khác freshness:** quality checks (GX) kiểm tra **cấu trúc và tính hợp lệ** tại một thời điểm: số dòng, null, trùng lặp, độ dài summary. Freshness kiểm tra **độ mới theo thời gian**: tỉ lệ bài có `age_days > 180` không được vượt 25%. Dữ liệu có thể đúng hoàn toàn về cấu trúc nhưng vẫn cũ, như ở trạng thái corrupted: 4/6 check đúng cấu trúc nhưng 40.9% số bài đã stale.
4. **Cùng test set:** để chênh lệch metric chỉ đến từ dữ liệu. Nếu đổi câu hỏi giữa các trạng thái thì không phân biệt được điểm giảm do corruption hay do câu hỏi khó hơn.
5. **Repair thành công dựa trên:** `repaired_quality_report.json` PASS 6/6 và freshness 4.17% (bằng baseline), cùng `repaired_metrics.json` có hit rate 1.0, token F1 1.0, judge accuracy 1.0, judge score 5.0 (bằng baseline), thể hiện trong `corruption_report.md` với mức phục hồi 100%.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      1.0 |       0.6 |      1.0 | 3 miss do bài bị drop, 1 miss do title bị cắt làm mất exact lookup |
| `mean_token_f1`      |      1.0 |       0.8 |      1.0 | Giảm chủ yếu ở câu hỏi date do stale_date |
| `judge_accuracy`     |      1.0 |       0.8 |      1.0 | Cao hơn hit rate vì bài lấy nhầm có cùng tác giả |
| `mean_judge_score`   |      5.0 |       4.3 |      5.0 | eval_003 = 1, eval_007 = 2 |
| Quality checks         |  6/6 PASS |  4/6 FAIL |  6/6 PASS | Bắt được duplicate và blank summary |
| Freshness status       |  Fresh (4.17%) |  Stale (40.91%) |  Fresh (4.17%) | Bắt được stale_date |

### Kết luận từ số liệu

1. **Drop latest records** (5 dòng) → row count 22 vẫn PASS, gate không báo → `retrieval_hit_rate` 1.0 → 0.6 (eval_002/003/006 miss vì bài đúng không còn trong corpus).
2. **Repair từ raw snapshot** qua đúng `build_clean_dataframe()` của tôi → gate PASS 6/6 và freshness 4.17% → cả 4 metric về đúng mức baseline.

**Corruption ảnh hưởng rõ nhất:** `drop_latest_records`. Nó gây ra 3/4 số lần retrieval miss và **không để lại tín hiệu nào** trên quality gate. Với phần ingestion của tôi, đây là rủi ro thực tế nhất: một lần gọi API trả thiếu dữ liệu (ví dụ bị cắt trang hoặc filter sai) sẽ làm RAG tệ đi mà không ai biết.

**Kết quả khác kỳ vọng:** tôi kỳ vọng câu hỏi authors bị miss thì sẽ trả lời sai, nhưng judge vẫn chấm 5/5. Khi đối chiếu `corrupted_answers.json`, tôi thấy bài được lấy nhầm là các bài "Advanced Perspectives on …" trong snapshot, có cùng nhóm tác giả với bài gốc. Câu trả lời đúng một cách tình cờ, nên chỉ nhìn `judge_accuracy` sẽ đánh giá thấp mức độ hỏng; phải đọc kèm `retrieval_hit_rate`.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về data pipeline:** Raw preservation và cleaning tất định là điều kiện để repair idempotent. Vì repair dựng lại từ raw bằng đúng hàm cleaning, kết quả luôn giống baseline dù chạy bao nhiêu lần.
2. **Về data quality/observability:** Gate chỉ bắt được những lỗi đã có luật. Trong 6 loại lỗi, drop, noise và truncate đều lọt qua, nên cần thêm các check so với lần chạy trước (row count delta) chứ không chỉ check trong một lần chạy.
3. **Về ảnh hưởng của data đến RAG agent:** Retrieval đúng chưa chắc đã trả lời đúng (eval_007 lấy đúng bài nhưng ngày đã bị lùi), và retrieval sai chưa chắc đã trả lời sai (câu authors). Vì vậy cần đo cả retrieval lẫn answer quality.

### Nếu có thêm thời gian

Thêm kiểm tra độ đầy đủ ngay ở bước ingestion: ghi vào raw một file thống kê gồm tỉ lệ rỗng của `subject`, `author`, `abstract` và số record so với lần gọi trước. Nếu tỉ lệ `subject` rỗng > 50% hoặc số record giảm > 10% thì không ghi đè snapshot. Đo hiệu quả bằng cách gọi API thật (vốn thiếu `subject`) và kiểm tra rằng snapshot được giữ nguyên, đồng thời `drop_latest_records` bị phát hiện trong `corrupted_quality_report.json`.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Hoàng Đức Dũng
**Ngày xác nhận:** 2026-09-26
