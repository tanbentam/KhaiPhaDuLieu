# Chuẩn bị vấn đáp của M2 (K-Means và DBSCAN)

Người soạn: Chu Thành Tân (M2). Câu hỏi lấy từ Phần 7 của BA Spec (câu 3, 4, 5, 6, 9 do M2 trả lời chính), cộng thêm các câu dễ bị hỏi nối tiếp.

Mỗi câu trả lời dài 20–40 giây, theo đúng cấu trúc spec gợi ý: **định nghĩa → quyết định của nhóm → bằng chứng → giới hạn.** Cột "Mở sẵn" là file cần mở khi giảng viên hỏi sâu.

Số liệu lấy từ **dữ liệu chính thức bản đầy đủ v1 của M1 (`master_v1`)** (4 tuần 17/04–14/05/2023, 535.167 lượt đón sau làm sạch, 304 toạ độ), khớp với `outputs/metrics/baseline_metrics.csv`.

---

## Phần A. Các câu M2 trả lời chính (theo spec)

### Câu 3. Vì sao không đưa trip_distance, trip_seconds và giờ vào K-Means/DBSCAN/HDBSCAN?

> Câu hỏi của nhóm là vị trí nào có nhiều lượt đón, nên vector chỉ gồm toạ độ x, y tính bằng mét. Nếu đưa quãng đường hay giờ vào thì các biến khác đơn vị sẽ lấn át nhau trong khoảng cách. Thời gian được dùng theo cách khác: nhóm tách 3 khung giờ rồi chạy riêng từng khung. Các biến còn lại dùng cho EDA và kiểm tra chất lượng.

Nếu bị hỏi sâu: ví dụ cờ tốc độ trên 80 mph và cờ quãng đường 0 được dùng để kiểm tra chất lượng (gắn cờ `flag_*`), không đưa vào mô hình và không loại dòng.

Mở sẵn: `config/experiment.yaml` (`project.features: [x_m, y_m]`, mục `time_slices`).

### Câu 4. K-Means tối ưu điều gì? Vì sao có thể chia sai các điểm nóng dọc tuyến đường?

> K-Means làm nhỏ nhất tổng bình phương khoảng cách từ mỗi điểm tới tâm cụm, gọi là SSE. Nó phải biết trước K và gán mọi điểm vào một cụm, nên hợp với cụm lồi, gần tròn. Trên dữ liệu của nhóm, dải dọc bờ hồ phía bắc bị K-Means cắt thành hai cụm theo ranh giới giữa hai tâm. Ở phía nam rất thưa, nó vẫn tạo một cụm riêng rộng nhất, bán kính trên 5 km.

Nếu bị hỏi sâu: cụm phía nam chiếm 4,3–5,7% số lượt; DBSCAN coi 79–93% số lượt ở khung phía nam là nhiễu (100% cụm 3 K-Means vào chiều ngày thường và cuối tuần; chỉ sáng ngày thường tách được Hyde Park).

Mở sẵn: `outputs/figures/m2_compare_regions_master_v1.png` (vùng R1 phía nam, R3 phía bắc), `docs/Phan 5/baseline_interpretation.md`.

### Câu 5. DBSCAN phân biệt core point, border point và noise như thế nào?

> Một điểm là core nếu trong bán kính eps có ít nhất min_samples điểm, tính cả chính nó. Điểm border không đủ để làm core nhưng nằm trong bán kính eps của một điểm core. Điểm không thuộc cụm nào là noise, nhãn −1. Các điểm core nối nhau qua bán kính eps tạo thành một cụm.

Nếu bị hỏi sâu: vì toạ độ trùng nhiều, nhóm dùng dạng có trọng số (điểm là core khi tổng số lượt trong bán kính eps đạt min_samples). Kiểm chứng trên dữ liệu thật ở 10k–20k lượt: 6/6 lần khớp hoàn toàn số cụm và tập nhiễu, 5/6 lần ARI bằng 1,0000 và 1 lần bằng 0,99995 (do thứ tự gán điểm biên giữa 2 cụm).

Mở sẵn: `outputs/figures/slide_dbscan_nguyen_ly.png`, `outputs/metrics/dbscan_full_vs_weighted_master_v1.csv`.

### Câu 6. Nhóm chọn eps bằng cách nào? eps có đơn vị gì?

> Toạ độ được chiếu sang hệ EPSG:26916 nên eps tính bằng mét. Nhóm vẽ đồ thị k-distance có trọng số, nhưng nó không có điểm gãy rõ vì các tâm khu cách nhau trung vị khoảng 800 mét. Nên nhóm chạy lưới 144 cấu hình rồi chọn cấu hình chính A với eps 1500 mét, min_samples 1% số lượt: vượt trội các ứng viên khác trên cả 3 khung giờ về Silhouette, Silhouette theo toạ độ và DBI.

Nếu bị hỏi sâu: k-distance có trọng số là khoảng cách cần đi để gom đủ k lượt, cũng là eps để toạ độ đó thành core. Lưới gồm 8 eps × 6 min_samples × 3 khung giờ. Eps 500 m làm vụn thành 18–113 cụm; eps ≥ 2500 m gộp 68–84% thành phố thành một cụm.

Mở sẵn: `outputs/figures/dbscan_kdist_master_v1.png`, `outputs/figures/dbscan_tuning_master_v1.png`, `docs/Phan 5/5.1-chay-ba-lat-cat.md`.

### Câu 9. Silhouette cao nhất có đồng nghĩa mô hình tốt nhất không? Xử lý noise khi tính metrics thế nào?

> Không. Silhouette ưu ái cụm lồi, và trên dữ liệu của nhóm còn bị đẩy lên vì nhiều lượt trùng toạ độ. Ví dụ DBSCAN eps 500 mét có Silhouette tới 0,859 nhưng thực ra là hàng chục cụm vụn. Nhóm tính chỉ số trên các lượt có cụm, luôn báo kèm Noise Ratio và số cụm, và chọn tham số dựa trên cả chỉ số lẫn bản đồ.

Nếu bị hỏi sâu: nhóm báo thêm Silhouette tính trên toạ độ duy nhất; K-Means có 0,73–0,75 theo lượt nhưng chỉ 0,40–0,42 theo toạ độ. Mỗi chỉ số đều ghi kèm số điểm dùng để tính (`n_points_metric`, `silhouette_sample`).

Mở sẵn: `outputs/figures/dbscan_tuning_master_v1.png` (cột eps 500), `outputs/metrics/kmeans_kscan_master_v1.csv`, `src/evaluation/metrics.py`.

---

## Phần B. Các câu dễ bị hỏi nối tiếp

### B1. Vì sao chọn K = 5 mà không phải K = 2, dù K = 2 có Silhouette cao hơn?

> Elbow có khuỷu ở K = 5 ở cả 3 khung giờ: tăng lên K = 5 giảm SSE 32–37%, còn từ K = 6 trở đi mỗi lần thêm cụm chỉ giảm 15–23%. Trong vùng K từ 4 trở lên, K bằng 5 đạt tốt nhất đồng thời Silhouette theo lượt, Silhouette theo toạ độ và DBI ở cả 3 khung giờ. K bằng 2 chỉ tách sân bay O'Hare khỏi phần còn lại, quá thô. Bản đồ K = 5 cho 5 vùng rõ ràng: trung tâm, O'Hare, phía bắc, phía nam và Midway.

Mở sẵn: `outputs/figures/kmeans_elbow_master_v1.png`, `outputs/figures/kmeans_kscan_master_v1.png`, `outputs/figures/kmeans_candidates_master_v1.png`.

### B2. Vì sao n_init = 50 mà không phải 10 như đề xuất ban đầu?

> K-Means chỉ hội tụ về cực tiểu cục bộ, nên phải khởi tạo nhiều lần rồi lấy lần tốt nhất. Với n_init bằng 10, từ K bằng 6 trở lên SSE tệ hơn mức tốt nhất tới 8,3–11,3%, làm đường Elbow gồ ghề và dễ đọc sai khuỷu. Với n_init bằng 50, sai lệch tối đa dưới 0,9%. Vì nhóm chạy trên 165–189 toạ độ có trọng số nên tăng n_init gần như không tốn thêm thời gian.

Mở sẵn: `outputs/metrics/kmeans_elbow_master_v1.csv`, `docs/Phan 3/3.1-kmeans-elbow.md`.

### B3. Chạy trên "toạ độ có trọng số" có làm thay đổi kết quả không?

> Không. Các lượt trùng toạ độ có cùng khoảng cách tới mọi tâm nên luôn rơi vào cùng cụm. Hàm mục tiêu của K-Means và điều kiện điểm core của DBSCAN, khi tính theo trọng số, đều tương đương với tính trên từng lượt. Nhóm đã kiểm chứng trên dữ liệu 4 tuần: DBSCAN khớp 6/6 số cụm và tập nhiễu ở cỡ 10k–20k (ARI 0,99995–1,0000). Lợi ích là bộ nhớ: ở khung cuối tuần hơn 120 nghìn lượt, chạy trên từng lượt ước tính tốn 7,2 đến 17,4 GB RAM và sẽ tràn bộ nhớ máy 16 GB, còn chạy có trọng số chỉ tốn 3,7 MB và 0,06 giây.

Mở sẵn: `outputs/figures/dbscan_full_vs_weighted_master_v1.png`, `docs/Phan 4/4.0-quyet-dinh-dbscan.md`.

### B4. Vì sao min_samples không dùng 5 đến 20 như spec?

> Vì mỗi toạ độ có rất nhiều lượt đón. Trên dữ liệu 4 tuần, với min_samples từ 5 đến 20 thì 99,5 đến 99,9% số lượt nằm ở toạ độ tự là core, nên DBSCAN hầu như không lọc được nhiễu: Noise Ratio tối đa chỉ 0,38% ở mọi eps. Nhóm đặt min_samples bằng tỷ lệ số lượt của mỗi khung giờ (0,1 đến 1%) để công bằng giữa khung 60 nghìn lượt và khung 120 nghìn lượt. Thay đổi này đã ghi rõ trong log, kèm số đo.

Mở sẵn: `docs/Phan 4/4.0-quyet-dinh-dbscan.md`, `outputs/metrics/dbscan_kdist_master_v1.csv`.

### B5. Điểm nhiễu của DBSCAN là dữ liệu sai à? Có nên xoá không?

> Không. Phần lớn nhiễu là vùng thưa thật ở xa tâm mật độ: 69 đến 84% toạ độ nhiễu cách điểm core gần nhất hơn 3 km, gấp đôi eps, với trung vị 4,8 đến 5,9 km. Chỉ 3 đến 7 toạ độ mỗi khung giờ nằm sát ngưỡng eps. Lượt nhiễu có tỷ lệ cờ chất lượng cao hơn một chút, nhưng tuyệt đại đa số không có cờ nào. Vì vậy nhiễu phản ánh vị trí ít người đón taxi, không phải bản ghi lỗi, và nhóm không xoá chúng.

Mở sẵn: `docs/Phan 5/baseline_interpretation.md` (mục 3).

### B6. K-Means có Noise Ratio bằng 0, vậy có phải giữ dữ liệu tốt hơn DBSCAN?

> Không. Noise Ratio bằng 0 là do thiết kế: K-Means không có khái niệm nhiễu và bắt buộc gán mọi điểm vào cụm, kể cả điểm rất xa. Hệ quả là nó tạo cụm phía nam rộng nhất, bán kính 5,3 đến 5,5 km, dù vùng đó rất thưa. Khi so sánh, nhóm luôn đặt Noise Ratio cạnh các chỉ số khác và ghi rõ điểm này.

### B7. DBSCAN có nhược điểm gì? Nếu dùng eps nhỏ hơn thì sao?

> DBSCAN dùng một eps cố định cho mọi mật độ. Với cấu hình chính eps 1500 mét, nó vừa gộp Loop với Lake View thành một dải lớn, lại vừa làm sân bay Midway bị tách thành 2 cụm nhỏ vào cuối tuần. Nếu hạ xuống eps 1000 mét và min_samples 0,5% thì số cụm tăng từ 3–4 lên 11–13 và xuất hiện nhiều cụm vụn; độ tương đồng ARI giữa hai cấu hình chỉ 0,53 đến 0,61. Đây là lý do nhóm so sánh tiếp với HDBSCAN do M3 thực hiện.

Mở sẵn: `outputs/figures/dbscan_candidates_master_v1.png` (hàng A và C).

### B8. Vì sao gọi là "hotspot" mà không phải điểm ùn tắc?

> Vì dữ liệu chỉ có số lượt đón taxi, không có tốc độ hay lưu lượng xe. Hotspot ở đây là vùng có nhiều lượt đón. Muốn kết luận về ùn tắc cần dữ liệu cảm biến giao thông hoặc quỹ đạo GPS. Ngoài ra toạ độ là tâm của từng khu, nên hotspot là ở mức khu vực, không phải một góc phố.

### B9. Thời gian chạy và độ phức tạp của hai thuật toán?

> K-Means mỗi vòng lặp có độ phức tạp tỷ lệ với số điểm nhân K nhân số chiều. DBSCAN trung bình khoảng n log n nhờ cây tìm kiếm, nhưng bản của scikit-learn lưu cả danh sách láng giềng nên bộ nhớ có thể tới n bình phương. Trên dữ liệu chính thức 4 tuần, cả hai fit dưới 0,2 giây (0,12–0,16 giây với K-Means; 0,04–0,07 giây với DBSCAN) vì chạy trên 165–189 toạ độ có trọng số. Khi so sánh thời gian với HDBSCAN phải ghi rõ mỗi thuật toán chạy trên đầu vào nào, vì thư viện HDBSCAN không hỗ trợ trọng số.

Mở sẵn: `outputs/metrics/baseline_metrics.csv` (cột `runtime_fit_sec`, `mem_delta_mb`).

---

## Ghi nhớ nhanh (đọc lại trước khi vào phòng)

| Thuật toán | Cấu hình | Số cụm | Noise | Silhouette (lượt / toạ độ) |
|---|---|---:|---:|---|
| K-Means | `K = 5`, `n_init = 50` | 5 | 0% | 0,73–0,75 / 0,40–0,42 |
| DBSCAN A (chính) | `1%` số lượt (`605/867/1.206`), `eps = 1500 m` | 3–4 | 9,4–12,6% | 0,74–0,86 / 0,56–0,70 |
| DBSCAN C (phụ) | `0,5%` (`303/434/603`), `eps = 1000 m` | 11–13 | 7,4–9,4% | 0,60–0,72 / 0,44–0,50 |

- Dữ liệu chính thức `master_v1`: 535.167 lượt đón sau làm sạch, 304 toạ độ, 4 tuần 17/04–14/05/2023. Hệ toạ độ EPSG:26916 (mét).
- 3 khung giờ: `WEEKDAY_AM` (60.498 lượt, 07:00–09:59), `WEEKDAY_PM` (86.617 lượt, 16:00–18:59), `WEEKEND` (120.571 lượt, cả ngày).
- Đồng thuận giữa hai thuật toán: trung tâm, O'Hare (và Midway vào chiều ngày thường). Khác nhau: phía nam (R1), quanh O'Hare (R2), phía bắc dọc hồ (R3).
