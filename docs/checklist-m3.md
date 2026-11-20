# Checklist M3 – HDBSCAN & Temporal Analysis (Hoàng Tuấn Bảo)

Căn cứ: `docs/chi-tiet.md` (BA Specification v1.1, mục M3-01 đến M3-08).  
Nhánh Git: `m3/hdbscan-temporal`  
Dữ liệu sử dụng: Bản đầy đủ v1 do M1 phát hành (`master_v1`, 535.167 dòng, CRS `EPSG:26916`).

---

## Phần 1. Chuẩn bị Môi trường & Nhận Bàn Giao Dữ Liệu (M3-01)
- [x] **1.1 Nhận bàn giao dữ liệu từ M1:** Kiểm tra toàn vẹn băm SHA256 của `master_pickups_v1.parquet` (`7459bd276a0b77c3...`) và `model_input_sample_v1.parquet` (`1165613449110766...`). Khớp 100% manifest.
- [x] **1.2 Cấu hình thí nghiệm:** Bổ sung tham số HDBSCAN vào `config/experiment.yaml` (`min_cluster_size_candidates: [30, 50, 100, 200, 300, 500]`, `min_samples_candidates: [5, 10, 20, 50]`, phương pháp `eom`).
- [x] **1.3 Xây dựng module thuật toán:** `src/models/hdbscan.py` bao gồm:
  - `fit_hdbscan`: Fit mô hình và trả về `(labels, probabilities, clusterer)`.
  - `hdbscan_fit_predict`: Wrapper tương thích trực tiếp với hàm `run_and_log`.
  - `scan_min_cluster_size` & `scan_min_samples`: Quét lưới có đo thời gian, RAM và đánh giá metrics.
  - `get_cluster_persistence_table`: Trích xuất độ bền vững cụm.

---

## Phần 2. Hyperparameter Tuning & Khảo Sát Tính Ổn Định (M3-02, M3-03, M3-05)
- [x] **2.1 Khảo sát `min_cluster_size`:** Giữ cố định `min_samples = 10` để tránh bẫy R05, quét qua dải $[30, 50, 100, 200, 300, 500]$ trên `WEEKDAY_AM`. Chọn $mcs = 100$ để loại bỏ micro-clusters và bảo toàn các hotspot chính.
- [x] **2.2 Khảo sát `min_samples`:** Thử $ms \in [5, 10, 20]$ với $mcs = 100$. Chọn $ms = 10$ để đạt cấu trúc cụm ổn định, Noise Ratio thấp quanh $2,1\%$.
- [x] **2.3 Xây dựng Notebook Tuning:** `notebooks/05_hdbscan_tuning.ipynb` và script `src/models/run_hdbscan.py`.
- [x] **2.4 Biểu đồ Tuning:** Xuất `outputs/figures/hdbscan_tuning_master_v1.png`.

---

## Phần 3. Chạy Mô Hình Chính Thức Trên 3 Lát Cắt (M3-04)
- [x] **3.1 Fit độc lập 3 lát cắt:** Chạy trên `WEEKDAY_AM` ($60.498$ dòng), `WEEKDAY_PM` ($86.617$ dòng), `WEEKEND` ($120.571$ dòng) với cấu hình `min_cluster_size = 100, min_samples = 10, cluster_selection_method = 'eom'`.
- [x] **3.2 Ghi log chuẩn 28 cột:** Tự động ghi tiếp nối vào `outputs/metrics/run_log.csv` qua `run_and_log`.
- [x] **3.3 Lưu file nhãn kèm xác suất:** Lưu `outputs/labels/<run_id>.parquet` (chứa `trip_id`, `label`, `probability`).
- [x] **3.4 Xuất bảng metrics chính thức:** Dùng `export_metrics_table` xuất `outputs/metrics/hdbscan_metrics.csv` khớp cấu trúc 100% với `baseline_metrics.csv`.
- [x] **3.5 Lập bảng chi tiết cụm:** Xuất `outputs/metrics/hdbscan_clusters_master_v1.csv` qua hàm `cluster_table`.
- [x] **3.6 Bản đồ tương tác Folium:** Xuất `outputs/maps/hdbscan_map_master_v1.html` với đầy đủ 3 layer thời gian.

---

## Phần 4. Phân Tích Lát Cắt Thời Gian & Hotspot Tracking (M3-06, M3-07)
- [x] **4.1 Thuật toán Ghép cặp Cụm (Cluster Matching):** Xây dựng `src/evaluation/temporal.py` với hàm `match_clusters` và `build_hotspot_tracking` dựa trên khoảng cách Euclidean gần nhất ($d \le 3.500\text{ m}$) kết hợp khu vực hành chính.
- [x] **4.2 Đo lường dịch chuyển không gian - thời gian:** Tính khoảng cách $\Delta d$ (mét), biến động số chuyến $\Delta n$, tỷ trọng $\Delta\text{share}$ (%) giữa AM $\rightarrow$ PM và Ngày thường $\rightarrow$ Cuối tuần.
- [x] **4.3 Xuất bảng theo dõi hotspot:** `outputs/metrics/hotspot_tracking.csv`.
- [x] **4.4 Xây dựng Notebook Phân tích Thời gian:** `notebooks/06_temporal_comparison.ipynb` và script `src/evaluation/run_temporal_comparison.py`.
- [x] **4.5 Biểu đồ & Bản đồ dịch chuyển:**
  - Biểu đồ phân tích biến động: `outputs/figures/temporal_hotspot_shifts.png`.
  - Bản đồ Folium vector dịch chuyển: `outputs/maps/hdbscan_temporal_shift_map.html`.

---

## Phần 5. Tài Liệu Diễn Giải & Bàn Giao M4 (M3-08)
- [x] **5.1 Tài liệu Diễn giải Chuyên sâu:** `docs/Phan 5/hdbscan_interpretation.md` (diễn giải so sánh 3 mô hình, tính thích ứng của HDBSCAN trước bài toán mật độ biến thiên, kèm các lưu ý phương pháp luận về cụm bán kính 0 m kéo Silhouette lên 0,99/kéo DBI xuống thấp, và hiện tượng dịch chuyển 0 m).
- [x] **5.2 Báo cáo Kỹ thuật & Kịch bản Vấn đáp:** `reports/m3_hdbscan_temporal.md` (chuẩn bị sẵn nội dung cho M4 đưa vào Báo cáo Word/Slide và bộ câu hỏi vấn đáp Q7, Q8, Q9, Q10).
- [x] **5.3 Biên bản Bàn giao H04 & H05:** `docs/Phan 5/5.5-bien-ban-ban-giao-m3.md`.
- [x] **5.4 Đồng bộ Git:** Toàn bộ mã nguồn, cấu hình, notebook và tài liệu đã được commit và push lên nhánh `m3/hdbscan-temporal`.
