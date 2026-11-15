# Diễn giải baseline: K-Means và DBSCAN (M2)

Người viết: M2 (Chu Thành Tân). Dữ liệu: **mẫu pilot tạm `pilot_m2_v0`** (1 tuần 17–23/04/2023, 138.629 chuyến, 219 toạ độ centroid). Kết quả cần chạy lại khi có dữ liệu chính thức của M1.

Nguồn số liệu: `notebooks/m2_baseline_comparison.ipynb`, `outputs/metrics/m2_compare_pilot_m2_v0.csv`, `outputs/figures/m2_compare_regions_pilot_m2_v0.png`.

Lưu ý thuật ngữ: "hotspot" ở đây là **vùng có nhiều lượt đón taxi**, không phải điểm ùn tắc. Dữ liệu không có tốc độ hay lưu lượng xe (spec, rủi ro R11).

## Cấu hình so sánh

| Thuật toán | Cấu hình | Nguồn |
|---|---|---|
| K-Means | K = 5, `k-means++`, n_init = 50, fit trên toạ độ duy nhất có trọng số | mục 3.2–3.3 |
| DBSCAN (chính, B) | `min_samples` = 1% số chuyến của lát cắt, eps = 2000 m, có trọng số | mục 4.4 |
| DBSCAN (phụ, C) | 0,5%, eps = 1000 m | mục 4.4 |

Notebook fit lại cả hai mô hình và đối chiếu với file nhãn của các lần chạy chính thức: trùng 9/9 (3 lát cắt × K-Means, B, C).

## 1. Hai thuật toán giống nhau ở đâu

Bảng chéo số chuyến (cụm K-Means × cụm DBSCAN B) cho thấy hai thuật toán **đồng thuận ở các vùng dày**:

| Vùng | Cụm K-Means | Cụm DBSCAN B | Tỷ lệ trùng |
|---|---|---|---|
| Trung tâm (Loop, Near North; khu 8/32) | 0 | 0 | 97,1–99,6% |
| Sân bay O'Hare (khu 76) | 1 | 1 | 98,1–99,0% |
| Sân bay Midway (khu 56) | 4 | 2 | 92,1–93,5% |

ARI giữa K-Means và DBSCAN B (coi nhiễu là một nhãn riêng): 0,68 (AM), 0,80 (PM), 0,68 (WEEKEND).

## 2. Hai thuật toán khác nhau ở đâu (bản đồ phóng to WEEKDAY_PM)

Lưu ý khi đọc hình: màu chỉ để phân biệt các cụm **trong cùng một ô**. Màu ở ô K-Means và ô DBSCAN không tương ứng với nhau, vì nhãn của hai thuật toán độc lập.

### R1. Phía nam (khu 41/43, x 440–457 km, y 4610–4632 km)

- **K-Means** gom gần như toàn bộ phía nam thành một cụm riêng: cụm 3, chiếm 3,9–5,4% số chuyến, bán kính RMS 5,1–5,5 km, là cụm rộng nhất. Lý do: K-Means bắt buộc gán mọi điểm vào một cụm.
- **DBSCAN B** gán **61–66% số chuyến trong vùng này là nhiễu** (AM 62,2%, PM 65,7%, WEEKEND 61,2%). Phần còn lại, nằm sát trung tâm, được nối vào cụm trung tâm.
- Theo bảng chéo: 64–72% chuyến thuộc cụm 3 của K-Means là nhiễu ở DBSCAN B; 28–36% còn lại rơi vào cụm trung tâm.
- Diễn giải: phía nam có nhiều toạ độ nhưng mỗi toạ độ ít chuyến và nằm thưa (xem mục 3). Với tiêu chí mật độ, đây **không phải một hotspot**. Cụm 3 của K-Means là sản phẩm của việc ép mọi điểm vào K cụm.

### R2. Quanh O'Hare và tây bắc (x 420–442 km, y 4638–4653 km)

- **K-Means:** cụm O'Hare (cụm 1) có 6–8 toạ độ, bán kính RMS 1,0–1,3 km, vì kéo thêm các toạ độ ít chuyến ở phía đông sân bay. Các toạ độ tây bắc còn lại được gán vào cụm phía bắc (cụm 2).
- **DBSCAN B:** cụm O'Hare chỉ có **2 toạ độ** (chính sân bay), bán kính khoảng 0,4 km. Mọi toạ độ xung quanh là nhiễu (6,1–10,7% số chuyến trong khung).
- Diễn giải: DBSCAN cho ranh giới hotspot sân bay **chặt hơn**, đúng với thực tế là lượt đón tập trung ở nhà ga. K-Means làm cụm sân bay to ra vì tâm cụm là trung bình và mọi điểm phải thuộc một cụm.

### R3. Phía bắc dọc hồ (Lake View, khu 6; x 440–452 km, y 4636–4653 km)

- **K-Means** tách phía bắc thành một cụm riêng: cụm 2, chiếm 9,1–14,2% số chuyến.
- **DBSCAN B** **gộp phía bắc vào cụm trung tâm**, vì các toạ độ dọc hồ nối liền nhau trong bán kính 2 km tạo thành một dải liên tục. Các toạ độ thưa ở rìa tây thì thành nhiễu (15–37% chuyến của cụm 2 K-Means là nhiễu ở DBSCAN B).
- Diễn giải: đây là điểm mạnh của DBSCAN, vì nó theo được cụm **có dạng dải** dọc bờ hồ, còn K-Means cắt dải này bằng ranh giới giữa hai tâm. Nhưng nó cũng là điểm yếu của eps lớn: Loop và Lake View là hai vùng khác nhau nhưng bị gộp. Ở cấu hình phụ C (eps 1000 m) hai vùng này tách ra (C có 13–14 cụm), đổi lại có nhiều cụm vụn. ARI giữa B và C chỉ 0,48–0,54, cho thấy DBSCAN rất nhạy với eps.

## 3. Nhiễu của DBSCAN B là ngoại lệ thật hay do eps quá nhỏ?

| | WEEKDAY_AM | WEEKDAY_PM | WEEKEND |
|---|---|---|---|
| Toạ độ nhiễu / chuyến nhiễu | 56 / 1.563 | 67 / 1.553 | 56 / 1.976 |
| Trung vị số chuyến mỗi toạ độ: nhiễu / có cụm | 20 / 34 | 14 / 35 | 21 / 24 |
| Trung vị khoảng cách tới toạ độ core gần nhất | 5,2 km | 5,3 km | 5,7 km |
| Toạ độ nhiễu cách core trong (eps, 1,25 × eps] = 2–2,5 km | 5 | 9 | 6 |
| Toạ độ nhiễu cách core > 2 × eps = 4 km | 39 | 48 | 40 |
| Toạ độ nhiễu được gán cụm ở cấu hình C | 6 (28% chuyến nhiễu) | 5 (19%) | 2 (18%) |

Kết luận:

- **Phần lớn nhiễu là vùng thưa thật, không phải do eps quá nhỏ.** 70–72% toạ độ nhiễu cách toạ độ core gần nhất hơn 4 km (gấp đôi eps), trung vị hơn 5 km. Mỗi toạ độ nhiễu cũng ít chuyến hơn toạ độ có cụm.
- Chỉ 5–9 toạ độ nhiễu mỗi lát cắt nằm "sát ngưỡng" (cách core 2–2,5 km). Đây là phần nhiễu **có thể do chọn eps**.
- Đổi sang cấu hình C (eps nhỏ hơn nhưng `min_samples` cũng nhỏ hơn) chỉ cứu được 2–6 toạ độ, tức 18–28% số chuyến nhiễu.
- **Nhiễu không đồng nghĩa với bản ghi lỗi.** Chuyến nhiễu có tỷ lệ cờ chất lượng cao hơn một chút: tốc độ > 80 mph 0,13–0,32% so với 0,03–0,04%; thời lượng 0 là 2,1–4,5% so với 1,5–2,0%. Quãng đường 0 thì không nhất quán: AM/PM 14,5–16,1% so với 8,5–9,9%, nhưng WEEKEND 7,5% so với 9,7%. Tuyệt đại đa số chuyến nhiễu không có cờ nào. Vì vậy nhiễu chủ yếu phản ánh **vị trí thưa** chứ không phải dữ liệu sai, và không nên xoá các chuyến này khỏi dữ liệu.

## 4. Tóm tắt điểm mạnh và yếu (dùng cho báo cáo và vấn đáp)

| | K-Means (K = 5) | DBSCAN B (1%, 2000 m) |
|---|---|---|
| Phải chọn trước | Số cụm K | eps và `min_samples` |
| Nhiễu | Không có; mọi chuyến đều thuộc một cụm (Noise Ratio = 0 theo thiết kế, không phải ưu điểm) | 6,6–10,0% chuyến là nhiễu, chủ yếu ở vùng thưa phía nam và tây bắc |
| Hình dạng cụm | Lồi quanh tâm, nên cắt dải dọc hồ thành 2 cụm | Theo mật độ, nên giữ được dải dọc hồ |
| Ranh giới hotspot sân bay | Rộng (6–8 toạ độ, 1,0–1,3 km) | Chặt (2 toạ độ, 0,4 km) |
| Độ nhạy tham số | Ổn định khi n_init đủ lớn (mục 3.1) | Rất nhạy với eps: B có 3 cụm, C có 13–14 cụm, ARI(B, C) chỉ 0,48–0,54 |
| Hạn chế chính | Tạo "cụm" ở vùng thưa (phía nam) | Một eps cho mọi mật độ: hoặc gộp Loop với Lake View (eps lớn), hoặc vụn (eps nhỏ). Đây là lý do cần HDBSCAN (M3) |

## Giới hạn

- Toạ độ là **centroid** của census tract hoặc community area, không phải GPS. Hotspot là ở mức khu vực.
- Mẫu pilot chỉ 1 tuần. Các con số phải chạy lại khi có dữ liệu của M1.
- Silhouette và DBI đều bị đẩy lên do nhiều chuyến trùng toạ độ (mục 3.2, 4.3), nên phần so sánh trên dựa chủ yếu vào bảng chéo, bản đồ và phân tích nhiễu.
