# Checklist M3 – HDBSCAN & Temporal Analysis (Hoàng Tuấn Bảo)

Căn cứ: `docs/chi-tiet.md` (BA Specification v1.1, mục M3-01 đến M3-08).  
Nhánh Git: `m3/hdbscan-temporal`  
Dữ liệu sử dụng: Bản đầy đủ v1 do M1 phát hành (`master_v1`, 535.167 dòng, CRS `EPSG:26916`).

> **Trạng thái hiện tại (20/11/2026):** Benchmark đã chạy nhưng Application Control chặn `_hdbscan_linkage.dll`, nên chưa thể xác nhận backend hoặc tái fit. `sklearn.cluster.HDBSCAN` có sẵn nhưng thiếu persistence/condensed tree theo yêu cầu stability M3, nên không dùng thay thế. Temporal runner đã chạy thành công trên metrics/cluster artifacts cũ và tạo manifest/counts/tracking/biểu đồ/bản đồ; các kết quả phụ thuộc cluster vẫn provisional và cần chạy lại sau khi backend được xác nhận.

---

## Phần 1. Chuẩn bị Môi trường & Nhận Bàn Giao Dữ Liệu (M3-01)
- [x] **1.1 Nhận bàn giao dữ liệu từ M1:** Kiểm tra toàn vẹn băm SHA256 của `master_pickups_v1.parquet` (`7459bd276a0b77c3...`) và `model_input_sample_v1.parquet` (`1165613449110766...`). Khớp 100% manifest.
- [x] **1.2 Cấu hình thí nghiệm:** Bổ sung tham số HDBSCAN vào `config/experiment.yaml` (`min_cluster_size_candidates: [30, 50, 100, 200, 300, 500]`, `min_samples_candidates: [5, 10, 20, 50]`, phương pháp `eom`).
- [x] **1.3 Xây dựng module thuật toán:** `src/models/hdbscan.py` bao gồm:
  - `fit_hdbscan`: Fit mô hình và trả về `(labels, probabilities, clusterer)`.
  - `hdbscan_fit_predict`: Wrapper tương thích trực tiếp với hàm `run_and_log`.
  - `scan_min_cluster_size` & `scan_min_samples`: Quét lưới có đo thời gian, RAM và đánh giá metrics.
  - `get_cluster_persistence_table`: Trích xuất độ bền vững cụm.
- [ ] **1.4 Pilot & môi trường:** Runner `python -m src.models.benchmark_hdbscan` đã thử nhưng bị Application Control chặn extension native; cần môi trường/backend được phê duyệt để tạo `outputs/metrics/hdbscan_benchmark.csv` và `outputs/metrics/environment_hdbscan.txt`.

---

## Phần 2. Hyperparameter Tuning & Khảo Sát Tính Ổn Định (M3-02, M3-03, M3-05)
- [ ] **2.1 Khảo sát `min_cluster_size`:** Runner hiện lấy dải `[30, 50, 100, 200, 300, 500]` từ config và giữ `min_samples = 10`; cần chạy lại để tạo kết quả mới có persistence.
- [ ] **2.2 Khảo sát `min_samples`:** Runner hiện lấy dải `[5, 10, 20, 50]` từ config với `mcs = 100`; cần chạy lại và cập nhật nhận xét/chọn tham số theo kết quả mới.
- [x] **2.3 Xây dựng Notebook Tuning:** `notebooks/05_hdbscan_tuning.ipynb` và script `src/models/run_hdbscan.py`.
- [ ] **2.4 Biểu đồ Tuning:** Xuất lại sau khi hoàn tất tuning trên backend đã xác nhận.

---

## Phần 3. Chạy Mô Hình Chính Thức Trên 3 Lát Cắt (M3-04)
- [ ] **3.1–3.6 Fit & xuất artifacts:** Cần chạy lại 3 lát cắt sau khi backend được xác nhận; regenerate run log, labels, metrics, cluster table, stability CSV và map. Các file hiện có là kết quả cũ, chưa được xác minh backend.

---

## Phần 4. Phân Tích Lát Cắt Thời Gian & Hotspot Tracking (M3-06, M3-07)
- [x] **4.1 Thuật toán Ghép cặp Cụm (Cluster Matching):** Xây dựng `src/evaluation/temporal.py` với hàm `match_clusters` và `build_hotspot_tracking` dựa trên centroid gần nhất ($d \le 3.500\text{ m}$); khu vực hành chính chỉ là metadata diễn giải, không tham gia quyết định ghép.
- [x] **4.2 Đo lường dịch chuyển không gian - thời gian:** Tính khoảng cách $\Delta d$ (mét), biến động số chuyến $\Delta n$, tỷ trọng $\Delta\text{share}$ (%) giữa AM $\rightarrow$ PM và Ngày thường $\rightarrow$ Cuối tuần.
- [ ] **4.3 Xuất bảng theo dõi hotspot và counts:** Đã tạo tạm các CSV từ artifacts hiện có; cần chạy lại sau khi HDBSCAN tạo clusters đã xác minh backend.
- [x] **4.4 Xây dựng Notebook Phân tích Thời gian:** `notebooks/06_temporal_comparison.ipynb` và script `src/evaluation/run_temporal_comparison.py`.
- [ ] **4.5 Biểu đồ & Bản đồ dịch chuyển:** Đã tái sinh tạm từ cluster cũ; cần tạo lại sau khi xác nhận backend HDBSCAN.

---

## Phần 5. Tài Liệu Diễn Giải & Bàn Giao M4 (M3-08)
- [x] **5.1 Tài liệu Diễn giải Chuyên sâu:** `docs/Phan 5/hdbscan_interpretation.md`; các số liệu mô hình/tracking được đánh dấu chờ tái sinh.
- [x] **5.2 Báo cáo Kỹ thuật & Kịch bản Vấn đáp:** `reports/m3_hdbscan_temporal.md` (chuẩn bị sẵn nội dung cho M4 đưa vào Báo cáo Word/Slide và bộ câu hỏi vấn đáp Q7, Q8, Q9, Q10).
- [ ] **5.3 Biên bản Bàn giao H04 & H05:** Hoàn tất sau khi artifacts mới được tái sinh và trạng thái deliverables cập nhật.
- [ ] **5.4 Đồng bộ Git:** Chưa commit/push các thay đổi của lần rà soát này.
