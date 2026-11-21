# Checklist M3 – HDBSCAN & Temporal Analysis (Hoàng Tuấn Bảo)

Căn cứ: `docs/chi-tiet.md` (BA Specification v1.1, mục M3-01 đến M3-08), bản rà soát đồ án 21/11/2026.  
Nhánh Git: `m3/hdbscan-temporal`  
Dữ liệu sử dụng: Bản đầy đủ v1 do M1 phát hành (`master_v1`, 535.167 dòng, CRS `EPSG:26916`).

> **Trạng thái hiện tại (Đã nghiệm thu 21/11/2026):** Toàn bộ các vấn đề rà soát M3 đã được xử lý triệt để. Backend `hdbscan 0.8.44` (Cython/C) đã được xác nhận chính thức với đầy đủ benchmark (kể cả cỡ mẫu 50.000 điểm theo NFR-02) và file môi trường. Thuật toán HDBSCAN đã được cố định `approx_min_span_tree=False`, sắp xếp tiền định theo `trip_id` và vượt qua kiểm định 3 lần xáo dòng (shuffle stability). Bảng độ bền vững `hdbscan_stability_master_v1.csv` đã được tạo đủ 208 cụm. Thuật toán ghép cụm không gian - thời gian được nâng cấp thành đối sánh hai chiều 5 trạng thái (STABLE, MERGED, SPLIT, EMERGING, DISSOLVED) kèm cờ ngưỡng quy mô cuối tuần 199 chuyến. Tất cả unit tests và bộ kiểm tra QA-01 đến QA-17 đều đạt PASS.

---

## Phần 1. Chuẩn bị Môi trường & Nhận Bàn Giao Dữ Liệu (M3-01)
- [x] **1.1 Nhận bàn giao dữ liệu từ M1:** Kiểm tra toàn vẹn băm SHA256 của `master_pickups_v1.parquet` (`7459bd276a0b77c3...`) và `model_input_sample_v1.parquet` (`1165613449110766...`). Khớp 100% manifest.
- [x] **1.2 Cấu hình thí nghiệm:** Bổ sung tham số HDBSCAN vào `config/experiment.yaml` (`min_cluster_size_candidates: [30, 50, 100, 200, 300, 500]`, `min_samples_candidates: [5, 10, 20, 50]`, `approx_min_span_tree: false`, phương pháp `eom`, `temporal.match_max_distance_m: 3500.0`).
- [x] **1.3 Xây dựng module thuật toán:** `src/models/hdbscan.py` bao gồm:
  - `fit_hdbscan`: Fit mô hình với `approx_min_span_tree=False`, trả về `(labels, probabilities, clusterer)`.
  - `hdbscan_fit_predict`: Wrapper tương thích trực tiếp với hàm `run_and_log`.
  - `scan_min_cluster_size` & `scan_min_samples`: Quét lưới có đo thời gian, RAM, persistence và đánh giá metrics.
  - `get_cluster_persistence_table`: Trích xuất độ bền vững cụm.
- [x] **1.4 Pilot & môi trường:** Đã chạy `python -m src.models.benchmark_hdbscan` trên môi trường Python 3.11.9 với `hdbscan 0.8.44`, bao phủ cỡ mẫu 5k, 10k, 30k, 50k (đạt chuẩn NFR-02); đã tạo `outputs/metrics/hdbscan_benchmark.csv` và `outputs/metrics/environment_hdbscan.txt`.

---

## Phần 2. Hyperparameter Tuning & Khảo Sát Tính Ổn Định (M3-02, M3-03, M3-05)
- [x] **2.1 Khảo sát `min_cluster_size`:** Runner quét đủ 6 giá trị `[30, 50, 100, 200, 300, 500]` trên dữ liệu `WEEKDAY_AM` với `min_samples = 10`; xuất `outputs/metrics/hdbscan_mcs_tuning_master_v1.csv` đầy đủ có cột `mean_persistence = 1.0` (không có NaN).
- [x] **2.2 Khảo sát `min_samples`:** Runner quét đủ 4 giá trị `[5, 10, 20, 50]` với `mcs = 100`; xuất `outputs/metrics/hdbscan_ms_tuning_master_v1.csv` đầy đủ (số cụm giữ nguyên 67, DBI 0.288).
- [x] **2.3 Xây dựng Notebook Tuning & Kiểm định Ổn định:** `notebooks/05_hdbscan_tuning.ipynb` và script `src/models/run_hdbscan.py`. Thêm kiểm định xáo dòng 3 seed (42, 123, 999) xuất `outputs/metrics/hdbscan_shuffle_stability.csv` chứng minh tính ổn định tuyệt đối.
- [x] **2.4 Biểu đồ Tuning:** Xuất `outputs/figures/hdbscan_tuning_master_v1.png` với đầy đủ lưới tham số.

---

## Phần 3. Chạy Mô Hình Chính Thức Trên 3 Lát Cắt (M3-04)
- [x] **3.1–3.6 Fit & xuất artifacts chính thức:**
  - Chạy chính thức 3 lát cắt với `approx_min_span_tree=False`, sắp xếp theo `trip_id`.
  - Cập nhật nhật ký `run_log.csv` ghi rõ backend `hdbscan 0.8.44` và `approx_min_span_tree: false`.
  - Xuất bảng độ bền vững `outputs/metrics/hdbscan_stability_master_v1.csv` (đầy đủ 208 cụm).
  - Cập nhật `outputs/metrics/hdbscan_metrics.csv` và `outputs/metrics/hdbscan_clusters_master_v1.csv` (AM: 67 cụm, PM: 63 cụm, Weekend: 78 cụm).
  - Tạo bản đồ phân cụm `outputs/maps/hdbscan_map_master_v1.html` có chú thích centroid.

---

## Phần 4. Phân Tích Lát Cắt Thời Gian & Hotspot Tracking (M3-06, M3-07)
- [x] **4.1 Thuật toán Ghép cặp Cụm (Cluster Matching):** Xây dựng đối sánh hai chiều (Two-Way Nearest Centroid Matching) với ngưỡng $d \le 3.500\text{ m}$ trong `src/evaluation/temporal.py`, phân loại thành 5 trạng thái tường minh (`STABLE`, `MERGED`, `SPLIT`, `EMERGING`, `DISSOLVED`).
- [x] **4.2 Đo lường dịch chuyển không gian - thời gian:** Tính khoảng cách $\Delta d$ (mét), biến động số chuyến $\Delta n$, tỷ trọng $\Delta\text{share}$ (%), mức độ trùng toạ độ (`single_coord_zero_shift` vs `multi_coord_shift`) và cờ quy mô cuối tuần `below_scaled_threshold` (< 199 chuyến).
- [x] **4.3 Xuất bảng theo dõi hotspot và counts:** Đã tạo `outputs/metrics/hotspot_tracking.csv` (229 dòng phân tích), `outputs/metrics/temporal_sample_counts.csv`, `outputs/metrics/time_slice_manifest.csv`.
- [x] **4.4 Xây dựng Notebook Phân tích Thời gian:** Cập nhật `notebooks/06_temporal_comparison.ipynb` (sửa toàn bộ nhận xét số liệu O'Hare, Midway, Hyde Park theo CSV chính thức) và script `src/evaluation/run_temporal_comparison.py`.
- [x] **4.5 Biểu đồ & Bản đồ dịch chuyển:** 
  - Tái sinh `outputs/figures/temporal_hotspot_shifts.png` (Subplot 1: Top 10 cặp ghép demand share & khoảng cách; Subplot 2: Phân bố 5 trạng thái chuyển tiếp).
  - Tái sinh bản đồ tương tác `outputs/maps/hdbscan_temporal_shift_map.html`.

---

## Phần 5. Tài Liệu Diễn Giải & Bàn Giao M4 (M3-08)
- [x] **5.1 Tài liệu Diễn giải Chuyên sâu:** `docs/Phan 5/hdbscan_interpretation.md` đồng bộ toàn bộ số liệu và caveat phương pháp luận.
- [x] **5.2 Báo cáo Kỹ thuật & Kịch bản Vấn đáp:** `reports/m3_hdbscan_temporal.md` hoàn thiện đầy đủ nội dung, bảng so sánh 3 mô hình kèm N_metric, CH, Peak RAM, giải thích hiện tượng persistence 1.0, dịch chuyển 0m, và bộ câu hỏi vấn đáp Q7–Q10.
- [x] **5.3 Biên bản Bàn giao H04 & H05:** Hoàn tất toàn bộ artifacts, metrics, figures và maps bàn giao cho M4 làm báo cáo tổng hợp và slide.
- [x] **5.4 Kiểm thử & Đồng bộ Git:** 
  - Bộ kiểm thử unit test `tests/test_m3.py` đạt 100% PASS.
  - Bộ kiểm tra QA `scripts/run_qa.py` đạt 31 PASS, 0 FAIL.
  - Commit đầy đủ các thay đổi vào nhánh `m3/hdbscan-temporal`.
