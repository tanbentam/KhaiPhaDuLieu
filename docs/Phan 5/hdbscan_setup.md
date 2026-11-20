# Thiết lập Môi trường & Mô hình HDBSCAN (Giai đoạn 1 - M3)

Người thực hiện: Thành viên 3 (M3 – Hoàng Tuấn Bảo)  
Ngày hoàn thành: 19/11/2026  
Nhánh Git: `m3/hdbscan-temporal`

> **Cập nhật trạng thái:** Đây là biên bản môi trường của lần chạy trước. Mã nguồn hiện không fallback sang scikit-learn khi `hdbscan` không nạp được; cần chạy `python -m src.models.benchmark_hdbscan` trên máy bàn giao để xác nhận `fit_predict`, `probabilities_`, `cluster_persistence_`, `condensed_tree_`, runtime/RAM và sinh environment snapshot hiện hành.

---

## 1. Xác thực Dữ liệu Đầu vào (Handoff từ M1)
Dữ liệu do M1 bàn giao đã được đặt vào thư mục `data/` và kiểm tra toàn vẹn băm SHA256:

| Tên File | Đường dẫn | Kích thước | SHA256 Thực tế | Trạng thái |
|---|---|---|---|---|
| Master Pickups v1 | `data/processed/master_pickups_v1.parquet` | ~26,5 MB | `7459bd276a0b77c32d905d9f4bc7165c1c77594e8b92ae5925173d069079da51` | Khớp 100% manifest |
| Model Input Sample v1 | `data/processed/model_input_sample_v1.parquet` | ~5,07 MB | `116561344911076645bad3aecd3be47a5097e1124b5d2a42ec748411d40e6d35` | Khớp 100% manifest |

- Tổng số dòng `master_v1`: 535.167 dòng, 304 toạ độ duy nhất.
- 3 lát cắt chính:
  - `WEEKDAY_AM`: 60.498 dòng (165 toạ độ duy nhất).
  - `WEEKDAY_PM`: 86.617 dòng (188 toạ độ duy nhất).
  - `WEEKEND`: 120.571 dòng (189 toạ độ duy nhất).

---

## 2. Đặc thù Triển khai HDBSCAN trên Dữ liệu Chicago Taxi
1. **Khác biệt với K-Means và DBSCAN:**
   - K-Means và DBSCAN của M2 tận dụng `sample_weight` trên 304 toạ độ duy nhất để fit trong < 0,1 giây.
   - Thư viện `hdbscan` của Python **không hỗ trợ tham số `sample_weight`** trong quá trình xây dựng cây tương hỗ (Mutual Reachability Graph).
   - Vì vậy, HDBSCAN sẽ fit trực tiếp trên toàn bộ điểm của từng lát cắt ($N = 60k - 120k$).
2. **Kiểm soát rủi ro tài nguyên (R02 trong BA Spec):**
   - Với không gian 2 chiều ($x_m, y_m$), HDBSCAN sử dụng KD-Tree / Ball-Tree nên tốc độ $O(N \log N)$ đến $O(N^2)$.
   - Đặt `gen_min_span_tree=False` khi fit diện rộng để tiết kiệm RAM; chỉ bật khi cần xuất hình phân tích condensed tree.
   - Khảo sát lưới tham số trên mẫu con hoặc bước nhảy hợp lý để tránh nghẽn CPU/RAM.
3. **Quy tắc cô lập tham số (R05 trong BA Spec):**
   - Trong thư viện `hdbscan`, nếu không truyền `min_samples`, giá trị này sẽ tự động ăn theo `min_cluster_size`.
   - Để tách biệt ảnh hưởng giữa **quy mô hotspot tối thiểu** (`min_cluster_size`) và **độ bảo thủ mật độ lõi** (`min_samples`), hàm `fit_hdbscan` luôn gán `min_samples` tường minh (mặc định = 10 trong vòng quét `min_cluster_size`).

---

## 3. Các Thành phần Đã Xây dựng
1. **Cấu hình thí nghiệm:** Bổ sung mục `hdbscan:` trong `config/experiment.yaml`.
2. **Module mô hình:** `src/models/hdbscan.py` bao gồm:
   - `fit_hdbscan`: Fit mô hình và trả về `(labels, probabilities, clusterer)`.
   - `hdbscan_fit_predict`: Wrapper tương thích trực tiếp với hàm `run_and_log` trong `src/evaluation/runlog.py`.
   - `scan_min_cluster_size`: Quét lưới `min_cluster_size` có đo đạc thời gian, RAM và đánh giá Silhouette/DBI/CH.
   - `scan_min_samples`: Quét lưới `min_samples` với `min_cluster_size` cố định.
   - `get_cluster_persistence_table`: Trích xuất độ bền vững của cụm (cluster persistence).
3. **Package Export:** Cập nhật `src/models/__init__.py`.
