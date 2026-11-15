# Checklist M2 – K-Means & DBSCAN (Chu Thành Tân)

Căn cứ: `docs/chi-tiet.md` (tóm tắt BA Spec v1.1, mục M2-01 đến M2-08), đã lược bỏ phần thủ tục quản lý dự án không cần cho môn học.

Quy ước:
- Làm lần lượt từng mục. Xong mục nào thì kiểm thử, viết log, đánh dấu `[x]`.
- Log mỗi mục: `docs/Phan <phần>/<mục>-<tên-ngắn>.md`, theo bố cục Mục tiêu → Đã làm → File thay đổi → Kiểm thử → Lưu ý. Mục lục log ở `docs/logs.md`.
- `[chờ M1]`: cần mẫu dữ liệu do M1 phát hành. Trong lúc chờ thì dùng dữ liệu giả lập (`make_blobs` cộng thêm nhiễu) hoặc tự lấy một mẫu pilot nhỏ, ghi rõ trong log.
- `[đề xuất]`: việc chưa được nhóm duyệt. Phải hỏi nhóm trước khi làm.
- Cố định cho mọi lần chạy: feature chỉ gồm `[x_m, y_m]` (EPSG:26916, đơn vị mét), metric Euclidean, seed 42, cùng tập `trip_id` với M3.

## Phần 1. Chuẩn bị

- [x] 1.1 Môi trường Python cho phần M2: venv, `scikit-learn`, `numpy`, `pandas`, `pyarrow`, `matplotlib`, `psutil`, `folium`. Ghi phiên bản thư viện. Cài thử `hdbscan` ngay từ đầu, vì Windows hay lỗi khi cài gói này.
  - Done khi: import được tất cả thư viện; ghi lại cấu hình máy (CPU, số nhân, RAM).
  - Lưu ý: cấu trúc repo và `requirements.txt` chung thuộc phần của M1/M4. Nếu cần thay đổi thì ghi thành đề xuất.
- [ ] 1.2 Thống nhất với M1 và M3 về định dạng dữ liệu đầu vào (tên file, các cột `trip_id`, `x_m`, `y_m`, `time_slice`) và định dạng file log kết quả.
  - Done khi: có một đoạn mô tả định dạng được M1 và M3 xác nhận, ghi trong log.

## Phần 2. Hạ tầng thí nghiệm dùng chung (M2-01)

- [x] 2.1 Viết file cấu hình thí nghiệm: seed, các lát cắt thời gian, cỡ mẫu, lưới tham số cho K-Means và DBSCAN.
- [x] 2.2 Viết hàm đánh giá dùng chung (`src/evaluation/`):
  - Số cụm, số điểm nhiễu, Noise Ratio, coverage, kích thước cụm (min, median, max, tỷ trọng cụm lớn nhất).
  - Silhouette, Davies-Bouldin, Calinski-Harabasz, chỉ tính trên các điểm đã được gán cụm, ghi kèm số điểm dùng để tính. Silhouette tính trên mẫu con tối đa 20k điểm.
  - Bỏ qua và ghi N/A khi số cụm nhỏ hơn 2.
- [ ] 2.3 Viết hàm đo runtime (`perf_counter`) và RAM đỉnh (`psutil`). Mỗi lần chạy ghi một dòng vào `runs/baseline_run_log.csv` gồm `run_id`, thuật toán, tham số, cỡ mẫu, kết quả, thời gian, phiên bản thư viện.
  - Done phần 2 khi: chạy thử trên dữ liệu giả lập ra đúng số liệu. Kiểm tra các trường hợp biên: toàn bộ là nhiễu, chỉ có 1 cụm, nhiều điểm trùng toạ độ.

## Phần 3. K-Means (M2-02, M2-03) [chờ M1]

- [ ] 3.1 Elbow: thử K từ 2 đến 15, `k-means++`, `n_init=10`, `random_state=42`. Lưu inertia ra `kmeans_elbow.csv` và vẽ `kmeans_elbow.png`.
- [ ] 3.2 Silhouette, Davies-Bouldin, Calinski-Harabasz theo K. Chọn K cuối dựa trên elbow, silhouette, kích thước cụm và bản đồ. Ghi rõ lý do chọn.
- [ ] 3.3 Fit với K đã chọn. Lưu nhãn theo `trip_id` (`kmeans_labels.parquet`) và vẽ bản đồ centroid cùng các cụm (`kmeans_map.html`).
  - Done phần 3 khi: có bảng K và lý do chọn; không chọn K chỉ vì inertia nhỏ; kiểm tra `n_iter_` để chắc thuật toán đã hội tụ.

## Phần 4. DBSCAN (M2-04, M2-05) [chờ M1]

- [ ] 4.1 Đồ thị k-distance với k bằng các giá trị min_samples 5, 10, 15, 20. Trước đó thống kê số toạ độ duy nhất, vì dữ liệu centroid có nhiều điểm trùng nhau sẽ tạo đoạn phẳng hoặc khoảng cách 0. Từ đồ thị rút ra các eps ứng viên quanh điểm gãy (knee).
- [ ] 4.2 Chạy thử tăng dần cỡ mẫu 10k, 30k, 50k, theo dõi RAM. Dừng tăng khi RAM vượt 80–85%.
- [ ] 4.3 Chạy lưới eps × min_samples (eps khởi điểm 150–1000 m, chỉnh theo knee). Lưu `dbscan_tuning.csv` gồm số cụm, Noise Ratio, kích thước cụm, runtime, RAM.
- [ ] 4.4 Chọn cấu hình cuối dựa trên bản đồ, coverage, Noise Ratio và ý nghĩa hotspot. Lưu `dbscan_labels.parquet` và `dbscan_params.json`, vẽ `dbscan_map.html`, tô điểm nhiễu màu xám.
  - Done phần 4 khi: mọi cấu hình đã chạy đều được ghi log; lý do chọn eps dựa trên đồ thị k-distance chứ không chọn theo cảm tính.

## Phần 5. Phân tích và so sánh baseline (M2-06, M2-07) [chờ M1]

- [ ] 5.1 Chạy K-Means và DBSCAN trên 3 lát cắt WEEKDAY_AM, WEEKDAY_PM, WEEKEND, cùng tập `trip_id` với M3.
- [ ] 5.2 Lập `baseline_metrics.csv` theo đúng định dạng đã thống nhất với M3 để M4 ghép bảng được.
- [ ] 5.3 So sánh hình dạng cụm và điểm nhiễu: chọn ít nhất 2 vùng mà hai thuật toán cho kết quả khác nhau, có bản đồ phóng to. Kiểm tra điểm nhiễu là ngoại lệ thật hay do eps quá nhỏ. Viết vào `baseline_interpretation.md`.
  - Done phần 5 khi: mọi nhận xét đều có bản đồ hoặc số liệu đi kèm; không kết luận "ùn tắc".

## Phần 6. Benchmark chính thức trên máy Tân [đề xuất]

- [ ] 6.1 Hỏi nhóm có đồng ý chạy benchmark chính thức cả 3 thuật toán trên máy Tân hay không. Chỉ làm tiếp khi nhóm đồng ý.
- [ ] 6.2 Chạy K-Means, DBSCAN và HDBSCAN (dùng tham số do M3 chốt) trên cùng mẫu chính thức, lặp 2–3 lần để kiểm tra độ ổn định. Ghi runtime và RAM.
  - Lưu ý: tham số HDBSCAN thuộc M3, ở đây chỉ chạy, không tự chỉnh.

## Phần 7. Báo cáo và bảo vệ (M2-08)

- [ ] 7.1 Viết phần báo cáo về K-Means và DBSCAN: nguyên lý, pseudocode, công thức (hàm mục tiêu SSE, điều kiện core point), ưu và nhược điểm, cách chọn K, eps, min_samples, kết quả.
- [ ] 7.2 Làm 3–4 slide: minh hoạ phép gán và cập nhật centroid, minh hoạ core/border/noise, bảng chỉ số, bản đồ.
- [ ] 7.3 Chuẩn bị trả lời các câu 3, 4, 5, 6, 9 trong phần vấn đáp của `docs/chi-tiet.md`. Mỗi câu trả lời được trong 20–40 giây.
