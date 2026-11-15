# Tư liệu slide của M2 (gửi M4)

Người soạn: Chu Thành Tân (M2). M4 dựng bộ slide và thống nhất hình thức; file này cung cấp nội dung, hình và lời nói cho **2 slide do M2 trình bày** theo kịch bản 12 phút của spec (mục 5.2):
- **Slide 6:** K-Means và DBSCAN, nguyên lý và tham số. Khoảng **1 phút 25 giây**.
- **Slide 8:** bảng chỉ số, runtime và nhiễu. Khoảng **1 phút** (nằm trong khung 3 phút 30 giây của slide 8–10).

Số liệu lấy từ **mẫu pilot tạm** (1 tuần). Khi có dữ liệu chính thức của M1, M2 sẽ cập nhật lại các con số và thông báo cho M4.

Nguyên tắc của spec: mỗi slide một thông điệp; không chèn ảnh chụp code; chữ đủ lớn; có ảnh PNG dự phòng khi không có Internet.

---

## Slide 6. K-Means và DBSCAN: nguyên lý và tham số

**Thông điệp:** K-Means chia theo khoảng cách tới tâm và bắt mọi điểm phải vào một cụm; DBSCAN gom theo mật độ và tách được nhiễu.

**Bố cục đề xuất:** 2 cột. Bên trái là K-Means, bên phải là DBSCAN. Mỗi cột có 1 hình và tối đa 3 dòng chữ.

| | K-Means | DBSCAN |
|---|---|---|
| Hình | `outputs/figures/slide_kmeans_nguyen_ly.png` (3 bước: khởi tạo, gán, cập nhật tâm) | `outputs/figures/slide_dbscan_nguyen_ly.png` (core / border / noise, vòng eps) |
| Dòng 1 | Mục tiêu: nhỏ nhất SSE = Σ ‖x − μ‖² | Core: trong bán kính eps có ≥ min_samples lượt đón |
| Dòng 2 | Chọn K = 5 (Elbow + Silhouette + bản đồ) | Chọn eps = 2000 m, min_samples = 1% số lượt (lưới 144 cấu hình) |
| Dòng 3 | Mọi điểm phải thuộc một cụm | Điểm không thuộc cụm nào là nhiễu (nhãn −1) |

Ghi chú nhỏ cuối slide: *Toạ độ là tâm census tract nên nhiều lượt trùng toạ độ; nhóm chạy cả hai thuật toán trên toạ độ có trọng số (kết quả giống hệt chạy trên từng lượt).*

**Lời nói (khoảng 1 phút 25 giây):**

> Hai thuật toán baseline của nhóm là K-Means và DBSCAN.
>
> K-Means chọn trước K tâm, rồi lặp hai bước: gán mỗi điểm về tâm gần nhất, sau đó dời tâm về trung bình của cụm. Mục tiêu là làm nhỏ nhất tổng bình phương khoảng cách tới tâm. Nhóm thử K từ 2 đến 15; khuỷu Elbow và Silhouette đều chỉ về K bằng 5, và bản đồ với 5 cụm dễ diễn giải nhất. Điểm cần nhớ: K-Means bắt buộc mọi điểm phải vào một cụm, kể cả những vùng rất thưa.
>
> DBSCAN thì gom theo mật độ. Một điểm là điểm lõi nếu trong bán kính eps có ít nhất min_samples lượt đón. Các điểm lõi gần nhau nối thành cụm; điểm nằm ở rìa là điểm biên; điểm không thuộc cụm nào là nhiễu. Thuật toán không cần biết trước số cụm.
>
> Vì toạ độ là tâm của từng khu nên các khu cách nhau khoảng một ki-lô-mét. Giá trị min_samples từ 5 đến 20 trong đề xuất ban đầu gần như không lọc được nhiễu. Nhóm đặt min_samples bằng 1% số lượt của mỗi khung giờ, và chọn eps bằng 2000 mét sau khi chạy lưới 144 cấu hình.

---

## Slide 8. Bảng chỉ số, runtime và nhiễu

**Thông điệp:** Không có thuật toán thắng ở mọi chỉ số. Silhouette phải đọc cùng Noise Ratio, số cụm và bản đồ.

**Bảng đề xuất** (lát WEEKDAY_PM làm ví dụ; bảng đầy đủ 3 lát cắt để ở phụ lục):

| Chỉ số | K-Means (K = 5) | DBSCAN (1%, eps 2000 m) | HDBSCAN |
|---|---|---|---|
| Số cụm | 5 | 3 | M3 điền |
| Noise Ratio | 0% (do thiết kế) | 6,9% | M3 điền |
| Silhouette (theo lượt / theo toạ độ) | 0,746 / 0,411 | 0,835 / 0,650 | M3 điền |
| Davies–Bouldin | 0,450 | 0,165 | M3 điền |
| Cụm lớn nhất | 63,5% | 70,1% | M3 điền |
| Thời gian fit | 0,11 s | 0,04 s | M3 điền |

Lưu ý cho M4:
- Cột HDBSCAN do M3 cung cấp, lấy từ `run_log.csv` theo cùng định dạng (mục 5.2 của checklist M2, chờ M3).
- **Thời gian fit của K-Means và DBSCAN là thời gian chạy trên khoảng 150 toạ độ có trọng số.** HDBSCAN không hỗ trợ trọng số nên có thể chạy trên từng lượt. Nhóm cần ghi rõ dưới bảng để so sánh không bị sai.
- Bảng 3 lát cắt cho phụ lục: lấy từ `reports/m2_kmeans_dbscan.md` (mục 1.4 và 2.5).

**Lời nói (khoảng 1 phút):**

> Đây là bảng chỉ số của khung chiều ngày thường. K-Means cho 5 cụm và không có nhiễu, nhưng đó là do thiết kế: nó bắt mọi điểm phải vào cụm, không phải vì dữ liệu sạch hơn. DBSCAN cho 3 cụm và để khoảng 7% số lượt là nhiễu, chủ yếu ở phía nam và tây bắc.
>
> Silhouette của DBSCAN cao hơn, nhưng cần đọc cẩn thận: các lượt trùng toạ độ có khoảng cách bằng 0 nên Silhouette tính theo lượt bị đẩy lên. Vì vậy nhóm báo thêm Silhouette tính theo toạ độ duy nhất: 0,41 với K-Means và 0,65 với DBSCAN. Thời gian fit của cả hai chỉ dưới 0,2 giây, vì chạy trên khoảng 150 toạ độ có trọng số.
>
> Kết luận của nhóm: không chọn mô hình chỉ vì một chỉ số. Nhóm xét cùng lúc Noise Ratio, số cụm và bản đồ, như các bạn sẽ thấy ở slide tiếp theo.

---

## Hình kết quả có sẵn (cho slide 9, 10 hoặc slide dự phòng)

| Mục đích | File | Ghi chú |
|---|---|---|
| Bản đồ so sánh vùng bất đồng (slide 9) | `outputs/figures/m2_compare_regions_pilot_m2_v0.png` | Phía nam, O'Hare và phía bắc, K-Means bên trái, DBSCAN bên phải |
| Elbow K-Means (dự phòng) | `outputs/figures/kmeans_elbow_pilot_m2_v0.png` | Khuỷu ở K = 5 ở cả 3 lát cắt |
| Chỉ số theo K (dự phòng) | `outputs/figures/kmeans_kscan_pilot_m2_v0.png` | |
| Bản đồ K = 5 (dự phòng) | `outputs/figures/kmeans_candidates_pilot_m2_v0.png` | Hàng trên: K = 5 |
| k-distance có trọng số (dự phòng, nếu bị hỏi cách chọn eps) | `outputs/figures/dbscan_kdist_pilot_m2_v0.png` | |
| Lưới tham số DBSCAN (dự phòng) | `outputs/figures/dbscan_tuning_pilot_m2_v0.png` | 144 cấu hình |
| Độ nhạy eps: B và C (dự phòng) | `outputs/figures/dbscan_candidates_pilot_m2_v0.png` | Hàng B (3 cụm) so với hàng C (13–14 cụm) |
| RAM khi chạy trên từng lượt (dự phòng) | `outputs/figures/dbscan_full_vs_weighted_pilot_m2_v0.png` | Giải thích vì sao chạy có trọng số |
| Bản đồ tương tác (demo) | `outputs/maps/kmeans_map_pilot_m2_v0.html`, `outputs/maps/dbscan_map_pilot_m2_v0.html` | Cần Internet để tải nền; luôn kèm PNG dự phòng |

Có thể vẽ lại 2 hình minh hoạ nguyên lý bằng:

```python
from src.visualization.illustrations import kmeans_steps_figure, dbscan_points_figure
kmeans_steps_figure("outputs/figures/slide_kmeans_nguyen_ly.png")
dbscan_points_figure("outputs/figures/slide_dbscan_nguyen_ly.png")
```
