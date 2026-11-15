# Chuẩn bị vấn đáp của M2 (K-Means và DBSCAN)

Người soạn: Chu Thành Tân (M2). Câu hỏi lấy từ Phần 7 của BA Spec (câu 3, 4, 5, 6, 9 do M2 trả lời chính), cộng thêm các câu dễ bị hỏi nối tiếp.

Mỗi câu trả lời dài 20–40 giây, theo đúng cấu trúc spec gợi ý: **định nghĩa → quyết định của nhóm → bằng chứng → giới hạn.** Cột "Mở sẵn" là file cần mở khi giảng viên hỏi sâu.

Số liệu là của **mẫu pilot 1 tuần**. Khi có dữ liệu chính thức, cập nhật lại các con số trước buổi bảo vệ.

---

## Phần A. Các câu M2 trả lời chính (theo spec)

### Câu 3. Vì sao không đưa trip_distance, trip_seconds và giờ vào K-Means/DBSCAN/HDBSCAN?

> Câu hỏi của nhóm là vị trí nào có nhiều lượt đón, nên vector chỉ gồm toạ độ x, y tính bằng mét. Nếu đưa quãng đường hay giờ vào thì các biến khác đơn vị sẽ lấn át nhau trong khoảng cách. Thời gian được dùng theo cách khác: nhóm tách 3 khung giờ rồi chạy riêng từng khung. Các biến còn lại dùng cho EDA và kiểm tra chất lượng.

Nếu bị hỏi sâu: ví dụ cờ tốc độ trên 80 mph và cờ quãng đường 0 được dùng để kiểm tra chất lượng, không đưa vào mô hình.

Mở sẵn: `config/experiment.yaml` (`project.features: [x_m, y_m]`, mục `time_slices`).

### Câu 4. K-Means tối ưu điều gì? Vì sao có thể chia sai các điểm nóng dọc tuyến đường?

> K-Means làm nhỏ nhất tổng bình phương khoảng cách từ mỗi điểm tới tâm cụm, gọi là SSE. Nó phải biết trước K và gán mọi điểm vào một cụm, nên hợp với cụm lồi, gần tròn. Trên dữ liệu của nhóm, dải dọc bờ hồ phía bắc bị K-Means cắt thành hai cụm theo ranh giới giữa hai tâm. Ở phía nam rất thưa, nó vẫn tạo một cụm riêng.

Nếu bị hỏi sâu: cụm phía nam chiếm khoảng 4–5% số lượt; DBSCAN coi 61–66% số lượt ở vùng đó là nhiễu.

Mở sẵn: `outputs/figures/m2_compare_regions_pilot_m2_v0.png` (vùng R1 phía nam, R3 phía bắc), `docs/Phan 5/baseline_interpretation.md`.

### Câu 5. DBSCAN phân biệt core point, border point và noise như thế nào?

> Một điểm là core nếu trong bán kính eps có ít nhất min_samples điểm, tính cả chính nó. Điểm border không đủ để làm core nhưng nằm trong bán kính eps của một điểm core. Điểm không thuộc cụm nào là noise, nhãn −1. Các điểm core nối nhau qua bán kính eps tạo thành một cụm.

Nếu bị hỏi sâu: vì toạ độ trùng nhiều, nhóm dùng dạng có trọng số (điểm là core khi tổng số lượt trong bán kính eps đạt min_samples). Kết quả giống hệt chạy trên từng lượt: 9/9 lần thử có ARI bằng 1.

Mở sẵn: `outputs/figures/slide_dbscan_nguyen_ly.png`, `docs/Phan 4/4.2-dbscan-full-vs-weighted.md`.

### Câu 6. Nhóm chọn eps bằng cách nào? eps có đơn vị gì?

> Toạ độ được chiếu sang hệ EPSG:26916 nên eps tính bằng mét. Nhóm vẽ đồ thị k-distance có trọng số, nhưng nó không có điểm gãy rõ vì các tâm khu cách nhau khoảng một ki-lô-mét. Nên nhóm chạy lưới 144 cấu hình rồi chọn eps 2000 mét, min_samples 1% số lượt: ra cùng 3 cụm ở cả 3 khung giờ và có chỉ số tốt nhất.

Nếu bị hỏi sâu: k-distance có trọng số là khoảng cách cần đi để gom đủ k lượt, cũng là eps để toạ độ đó thành core. Lưới gồm 8 eps × 6 min_samples × 3 khung giờ. Eps 500 m làm vụn thành vài chục cụm; eps ≥ 2500 m gộp gần hết thành phố.

Mở sẵn: `outputs/figures/dbscan_kdist_pilot_m2_v0.png`, `outputs/figures/dbscan_tuning_pilot_m2_v0.png`, `docs/Phan 4/4.4-dbscan-chon-cau-hinh.md`.

### Câu 9. Silhouette cao nhất có đồng nghĩa mô hình tốt nhất không? Xử lý noise khi tính metrics thế nào?

> Không. Silhouette ưu ái cụm lồi, và trên dữ liệu của nhóm còn bị đẩy lên vì nhiều lượt trùng toạ độ. Ví dụ DBSCAN eps 500 mét có Silhouette 0,85 nhưng thực ra là vài chục cụm vụn. Nhóm tính chỉ số trên các lượt có cụm, luôn báo kèm Noise Ratio và số cụm, và chọn tham số dựa trên cả chỉ số lẫn bản đồ.

Nếu bị hỏi sâu: nhóm báo thêm Silhouette tính trên toạ độ duy nhất; K-Means có 0,74 theo lượt nhưng chỉ 0,41 theo toạ độ. Mỗi chỉ số đều ghi kèm số điểm dùng để tính.

Mở sẵn: `outputs/figures/dbscan_tuning_pilot_m2_v0.png` (cột eps 500), `outputs/metrics/kmeans_kscan_pilot_m2_v0.csv`, `src/evaluation/metrics.py`.

---

## Phần B. Các câu dễ bị hỏi nối tiếp

### B1. Vì sao chọn K = 5 mà không phải K = 2, dù K = 2 có Silhouette cao hơn?

> Elbow có khuỷu ở K = 5 ở cả 3 khung giờ. Từ K bằng 5 trở đi, mỗi lần thêm cụm chỉ giảm SSE khoảng 10 đến 19%. Trong khoảng K từ 4 trở lên, K bằng 5 có Silhouette cao nhất và DBI thấp nhất. K bằng 2 có chỉ số tốt hơn nhưng chỉ tách sân bay O'Hare khỏi phần còn lại, quá thô để gọi là các vùng nóng. Bản đồ với K bằng 5 cho 5 vùng rõ ràng: trung tâm, O'Hare, phía bắc, phía nam và Midway.

Mở sẵn: `outputs/figures/kmeans_elbow_pilot_m2_v0.png`, `outputs/figures/kmeans_kscan_pilot_m2_v0.png`, `outputs/figures/kmeans_candidates_pilot_m2_v0.png`.

### B2. Vì sao n_init = 50 mà không phải 10 như đề xuất ban đầu?

> K-Means chỉ hội tụ về cực tiểu cục bộ, nên phải khởi tạo nhiều lần rồi lấy lần tốt nhất. Với n_init bằng 10, từ K bằng 6 trở lên SSE tệ hơn mức tốt nhất tới 7 đến 14%, làm đường Elbow gồ ghề và dễ đọc sai khuỷu. Với n_init bằng 50, kết quả ổn định. Vì nhóm chạy trên khoảng 150 toạ độ có trọng số nên tăng n_init gần như không tốn thêm thời gian.

Mở sẵn: `docs/Phan 3/3.1-kmeans-elbow.md`.

### B3. Chạy trên "toạ độ có trọng số" có làm thay đổi kết quả không?

> Không. Các lượt trùng toạ độ có cùng khoảng cách tới mọi tâm nên luôn rơi vào cùng cụm. Hàm mục tiêu của K-Means và điều kiện điểm core của DBSCAN, khi tính theo trọng số, đều tương đương với tính trên từng lượt. Nhóm đã kiểm chứng: DBSCAN 9 trên 9 lần ARI bằng 1, K-Means với n_init đủ lớn cũng cho nhãn giống hệt. Lợi ích là bộ nhớ: DBSCAN chạy trên từng lượt cần khoảng 1 GB với 30 nghìn lượt và tăng theo bình phương, còn chạy có trọng số gần như không tốn thêm RAM.

Mở sẵn: `outputs/figures/dbscan_full_vs_weighted_pilot_m2_v0.png`, `docs/Phan 4/4.0-quyet-dinh-dbscan.md`.

### B4. Vì sao min_samples không dùng 5 đến 20 như spec?

> Vì mỗi toạ độ trung bình có vài chục lượt đón. Với min_samples từ 5 đến 20, 97 đến gần 100% số lượt nằm ở toạ độ tự là core, nên DBSCAN không lọc được nhiễu: Noise Ratio dưới 3% ở mọi eps. Nhóm đặt min_samples theo tỷ lệ số lượt của mỗi khung giờ (0,1 đến 1%) để công bằng giữa khung 15 nghìn lượt và khung 30 nghìn lượt. Thay đổi này đã ghi rõ trong log, kèm số đo.

Mở sẵn: `docs/Phan 4/4.0-quyet-dinh-dbscan.md`, `docs/Phan 4/4.1-dbscan-k-distance.md`.

### B5. Điểm nhiễu của DBSCAN là dữ liệu sai à? Có nên xoá không?

> Không. Phần lớn nhiễu là vùng thưa thật: 70 đến 72% toạ độ nhiễu cách điểm core gần nhất hơn 4 km, gấp đôi eps. Chỉ 5 đến 9 toạ độ mỗi khung giờ nằm sát ngưỡng eps. Lượt nhiễu có tỷ lệ cờ chất lượng cao hơn một chút, nhưng phần lớn không có cờ nào. Vì vậy nhiễu phản ánh vị trí ít người đón taxi, không phải bản ghi lỗi, và nhóm không xoá chúng.

Mở sẵn: `docs/Phan 5/baseline_interpretation.md` (mục 3).

### B6. K-Means có Noise Ratio bằng 0, vậy có phải giữ dữ liệu tốt hơn DBSCAN?

> Không. Noise Ratio bằng 0 là do thiết kế: K-Means không có khái niệm nhiễu và bắt buộc gán mọi điểm vào cụm, kể cả điểm rất xa. Hệ quả là nó tạo cụm phía nam rộng nhất, bán kính khoảng 5 km, dù vùng đó rất thưa. Khi so sánh, nhóm luôn đặt Noise Ratio cạnh các chỉ số khác và ghi rõ điểm này.

### B7. DBSCAN có nhược điểm gì? Nếu dùng eps nhỏ hơn thì sao?

> DBSCAN dùng một eps cho mọi vùng. Với eps 2000 mét, Loop và Lake View bị gộp chung một cụm. Hạ xuống eps 1000 mét với min_samples 0,5% thì số cụm tăng từ 3 lên 13 đến 14 và có nhiều cụm vụn; độ tương đồng giữa hai cấu hình chỉ khoảng 0,5 theo ARI. Đây là lý do nhóm so sánh tiếp với HDBSCAN, thuật toán xét nhiều mức mật độ thay vì một eps cố định; phần đó do M3 trình bày.

Mở sẵn: `outputs/figures/dbscan_candidates_pilot_m2_v0.png` (hàng B và C).

### B8. Vì sao gọi là "hotspot" mà không phải điểm ùn tắc?

> Vì dữ liệu chỉ có số lượt đón taxi, không có tốc độ hay lưu lượng xe. Hotspot ở đây là vùng có nhiều lượt đón. Muốn kết luận về ùn tắc cần dữ liệu cảm biến giao thông hoặc quỹ đạo GPS. Ngoài ra toạ độ là tâm của từng khu, nên hotspot là ở mức khu vực, không phải một góc phố.

### B9. Thời gian chạy và độ phức tạp của hai thuật toán?

> K-Means mỗi vòng lặp có độ phức tạp tỷ lệ với số điểm nhân K nhân số chiều. DBSCAN trung bình khoảng n log n nhờ cây tìm kiếm, nhưng bản của scikit-learn lưu cả danh sách láng giềng nên bộ nhớ có thể tới n bình phương. Trên mẫu pilot, cả hai fit dưới 0,2 giây vì chạy trên khoảng 150 toạ độ có trọng số. Khi so sánh thời gian với HDBSCAN phải ghi rõ mỗi thuật toán chạy trên đầu vào nào, vì thư viện HDBSCAN không hỗ trợ trọng số.

Mở sẵn: `outputs/metrics/run_log.csv` (cột `runtime_fit_sec`, `mem_delta_mb`).

---

## Ghi nhớ nhanh (đọc lại trước khi vào phòng)

| Thuật toán | Cấu hình | Số cụm | Noise | Silhouette (lượt / toạ độ) |
|---|---|---|---|---|
| K-Means | K = 5, n_init = 50 | 5 | 0% | 0,73–0,75 / khoảng 0,41 |
| DBSCAN B | 1% số lượt, eps 2000 m | 3 | 6,6–10,0% | 0,80–0,84 / 0,59–0,65 |
| DBSCAN C | 0,5%, eps 1000 m | 13–14 | 7,1–9,6% | 0,62–0,73 / 0,35–0,46 |

- Dữ liệu: 138.629 lượt đón, 219 toạ độ, 1 tuần 17–23/04/2023 (pilot). Hệ toạ độ EPSG:26916 (mét).
- Khung giờ: sáng ngày thường 07:00–09:59, chiều ngày thường 16:00–18:59, cuối tuần cả ngày.
- Đồng thuận giữa hai thuật toán: trung tâm, O'Hare, Midway. Khác nhau: phía nam, quanh O'Hare, phía bắc dọc hồ.
