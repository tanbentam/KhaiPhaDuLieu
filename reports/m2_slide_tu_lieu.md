# Tư liệu slide của M2 (gửi M4)

Người soạn: Chu Thành Tân (M2). M4 dựng bộ slide và thống nhất hình thức; file này cung cấp nội dung, hình và lời nói cho **2 slide do M2 trình bày** theo kịch bản 12 phút của spec (mục 5.2):
- **Slide 6:** K-Means và DBSCAN, nguyên lý và tham số. Khoảng **1 phút 25 giây**.
- **Slide 8:** bảng chỉ số, runtime và nhiễu. Khoảng **1 phút** (nằm trong khung 3 phút 30 giây của slide 8–10).

Số liệu lấy từ **dữ liệu chính thức v1 bản đầy đủ của M1 (`master_v1`)** (4 tuần 17/04–14/05/2023, 535.167 lượt đón sau làm sạch, 304 toạ độ), khớp với `outputs/metrics/baseline_metrics.csv`.

Nguyên tắc của spec: mỗi slide một thông điệp; không chèn ảnh chụp code; chữ đủ lớn; có ảnh PNG dự phòng khi không có Internet.

---

## Slide 6. K-Means và DBSCAN: nguyên lý và tham số

**Thông điệp:** K-Means chia theo khoảng cách tới tâm và bắt mọi điểm phải vào một cụm; DBSCAN gom theo mật độ và tách được nhiễu.

**Bố cục đề xuất:** 2 cột. Bên trái là K-Means, bên phải là DBSCAN. Mỗi cột có 1 hình và tối đa 3 dòng chữ.

| | K-Means | DBSCAN |
|---|---|---|
| Hình | `outputs/figures/slide_kmeans_nguyen_ly.png` (3 bước: khởi tạo, gán, cập nhật tâm) | `outputs/figures/slide_dbscan_nguyen_ly.png` (core / border / noise, vòng eps) |
| Dòng 1 | Mục tiêu: nhỏ nhất SSE = Σ ‖x − μ‖² | Core: trong bán kính eps có ≥ min_samples lượt đón |
| Dòng 2 | Chọn K = 5 (Elbow + Silhouette + bản đồ) | Chọn eps = 1500 m, min_samples = 1% số lượt (lưới 144 cấu hình) |
| Dòng 3 | Mọi điểm phải thuộc một cụm | Điểm không thuộc cụm nào là nhiễu (nhãn −1) |

Ghi chú nhỏ cuối slide: *Toạ độ là tâm census tract nên nhiều lượt trùng toạ độ; nhóm chạy cả hai thuật toán trên 165–189 toạ độ duy nhất có trọng số (cùng hàm mục tiêu / điều kiện core như chạy trên từng lượt).*

**Lời nói (khoảng 1 phút 25 giây):**

> Hai thuật toán baseline của nhóm là K-Means và DBSCAN.
>
> K-Means chọn trước K tâm, rồi lặp hai bước: gán mỗi điểm về tâm gần nhất, sau đó dời tâm về trung bình của cụm. Mục tiêu là làm nhỏ nhất tổng bình phương khoảng cách tới tâm. Nhóm thử K từ 2 đến 15; khuỷu Elbow và Silhouette đều chỉ về K bằng 5, và bản đồ với 5 cụm dễ diễn giải nhất. Điểm cần nhớ: K-Means bắt buộc mọi điểm phải vào một cụm, kể cả những vùng rất thưa.
>
> DBSCAN thì gom theo mật độ. Một điểm là điểm lõi nếu trong bán kính eps có ít nhất min_samples lượt đón. Các điểm lõi gần nhau nối thành cụm; điểm nằm ở rìa là điểm biên; điểm không thuộc cụm nào là nhiễu. Thuật toán không cần biết trước số cụm.
>
> Vì toạ độ là tâm của từng khu nên các khu cách nhau trung vị khoảng 800 mét. Giá trị min_samples từ 5 đến 20 trong đề xuất ban đầu gần như không lọc được nhiễu. Nhóm đặt min_samples bằng 1% số lượt của mỗi khung giờ, và chọn eps bằng 1500 mét sau khi chạy lưới 144 cấu hình trên dữ liệu 4 tuần.

---

## Slide 8. Bảng chỉ số, runtime và nhiễu

**Thông điệp:** Không có thuật toán thắng ở mọi chỉ số. Silhouette phải đọc cùng Noise Ratio, số cụm và bản đồ.

**Bảng đề xuất** (lát `WEEKDAY_PM`, 86.617 lượt làm ví dụ; bảng đầy đủ 3 lát cắt để ở phụ lục):

| Chỉ số | K-Means (`K = 5`) | DBSCAN A (`1%, eps 1500 m`) | HDBSCAN (`mcs=100, ms=10`) |
|---|---|---|---|
| Số cụm | 5 | 3 | 63 |
| Noise Ratio | 0% (do thiết kế) | 9,4% | 2,3% |
| Silhouette (theo lượt / theo toạ độ) | 0,753 / 0,398 | 0,859 / 0,702 | 0,990* (63% cụm bán kính 0 m) |
| Davies–Bouldin | 0,459 | 0,153 | 0,180 |
| Cụm lớn nhất | 62,5% | 66,9% | 12,8% |
| Thời gian fit | 0,14 s (188 toạ độ) | 0,06 s (188 toạ độ) | 2,34 s (86.617 lượt) |

Lưu ý cho M4:
- Cột K-Means và DBSCAN lấy trực tiếp từ `outputs/metrics/baseline_metrics.csv`. Cột HDBSCAN lấy từ `outputs/metrics/hdbscan_metrics.csv` (`hdbscan 0.8.44`, `approx_min_span_tree=False`, cùng 28 cột `RUN_LOG_COLUMNS`).
- **Không so trực tiếp runtime và Silhouette của HDBSCAN với K-Means/DBSCAN:** K-Means và DBSCAN fit có trọng số trên 188 toạ độ duy nhất, còn HDBSCAN fit trên toàn bộ 86.617 lượt; 63% cụm HDBSCAN chỉ gồm 1 toạ độ tâm vùng (bán kính 0 m) nên Silhouette bị đẩy lên ~0,99.
- Bảng 3 lát cắt cho phụ lục: lấy từ `reports/m2_kmeans_dbscan.md` (mục 1.4 và 2.5) và `outputs/metrics/metrics_comparison.csv`.

**Lời nói (khoảng 1 phút):**

> Đây là bảng chỉ số của khung chiều ngày thường với hơn 86 nghìn lượt đón. K-Means cho 5 cụm và không có nhiễu, nhưng đó là do thiết kế: nó bắt mọi điểm phải vào cụm, không phải vì dữ liệu sạch hơn. DBSCAN với bán kính 1500 mét cho 3 cụm lớn và để 9,4% số lượt là nhiễu, chủ yếu ở phía nam và tây bắc. HDBSCAN với ngưỡng 100 chuyến tách thành 63 cụm nhỏ hơn với 2,3% nhiễu.
>
> Cần đọc Silhouette thật cẩn thận: các lượt trùng toạ độ có khoảng cách bằng 0 nên Silhouette tính theo lượt bị đẩy lên mạnh — nhất là ở HDBSCAN (0,990) vì hơn 60% cụm chỉ gồm đúng một tâm vùng. Vì vậy nhóm báo thêm Silhouette theo toạ độ duy nhất cho K-Means (0,40) và DBSCAN (0,70), và lưu ý thời gian fit không so ngang vì K-Means/DBSCAN chạy có trọng số trên 188 toạ độ, còn HDBSCAN chạy trên toàn bộ 86 nghìn lượt.
>
> Kết luận của nhóm: không chọn mô hình chỉ vì một chỉ số, mà xét cùng lúc Noise Ratio, số cụm và bản đồ ở slide tiếp theo.

---

## Hình kết quả chính thức (`master_v1`, cho slide 9, 10 hoặc slide dự phòng)

| Mục đích | File | Ghi chú |
|---|---|---|
| Bản đồ so sánh vùng bất đồng (slide 9) | `outputs/figures/m2_compare_regions_master_v1.png` | Phía nam, O'Hare và phía bắc, K-Means bên trái, DBSCAN A bên phải |
| Elbow K-Means (dự phòng) | `outputs/figures/kmeans_elbow_master_v1.png` | Khuỷu ở K = 5 ở cả 3 lát cắt |
| Chỉ số theo K (dự phòng) | `outputs/figures/kmeans_kscan_master_v1.png` | K = 5 tối ưu đồng thời Silhouette, Sil. toạ độ và DBI trong vùng K ≥ 4 |
| Bản đồ K = 5 (dự phòng) | `outputs/figures/kmeans_candidates_master_v1.png` | Hàng trên: K = 5 |
| k-distance có trọng số (dự phòng, nếu bị hỏi cách chọn eps) | `outputs/figures/dbscan_kdist_master_v1.png` | |
| Lưới tham số DBSCAN (dự phòng) | `outputs/figures/dbscan_tuning_master_v1.png` | 144 cấu hình trên `master_v1` |
| Độ nhạy eps: A, B, C, D (dự phòng) | `outputs/figures/dbscan_candidates_master_v1.png` | Hàng A (chính, 3–4 cụm) so với hàng C (phụ, 11–13 cụm) |
| RAM khi chạy trên từng lượt (dự phòng) | `outputs/figures/dbscan_full_vs_weighted_master_v1.png` | 120k lượt ước tính 7,2–17,4 GB với full vs 3,7 MB với weighted |
| Bản đồ tương tác (demo) | `outputs/maps/kmeans_map_master_v1.html`, `outputs/maps/dbscan_map_master_v1.html` | Cần Internet để tải nền; luôn kèm PNG dự phòng |

Có thể vẽ lại 2 hình minh hoạ nguyên lý bằng:

```python
from src.visualization.illustrations import kmeans_steps_figure, dbscan_points_figure
kmeans_steps_figure("outputs/figures/slide_kmeans_nguyen_ly.png")
dbscan_points_figure("outputs/figures/slide_dbscan_nguyen_ly.png")
```
