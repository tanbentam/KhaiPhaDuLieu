# Diễn giải baseline: K-Means và DBSCAN (M2)

Người viết: M2 (Chu Thành Tân). Dữ liệu: **bản đầy đủ v1 do M1 phát hành (`master_v1`)** (4 tuần 17/04–14/05/2023, 535.167 chuyến sau làm sạch, 304 toạ độ centroid; 3 lát cắt: `WEEKDAY_AM` 60.498, `WEEKDAY_PM` 86.617, `WEEKEND` 120.571).

Nguồn số liệu: `notebooks/m2_baseline_comparison.ipynb`, `outputs/metrics/m2_compare_master_v1.csv`, `outputs/figures/m2_compare_regions_master_v1.png`, `outputs/metrics/baseline_metrics.csv`.

Lưu ý thuật ngữ: "hotspot" ở đây là **vùng có nhiều lượt đón taxi**, không phải điểm ùn tắc. Dữ liệu không có tốc độ hay lưu lượng xe (spec, rủi ro R11).

## Cấu hình so sánh

| Thuật toán | Cấu hình | Nguồn |
|---|---|---|
| K-Means | K = 5, `k-means++`, `n_init = 50`, fit trên toạ độ duy nhất có trọng số | mục 3.2, 5.1 |
| DBSCAN (chính, A) | `min_samples` = 1% số chuyến của lát cắt (`605 / 867 / 1206`), `eps = 1500 m`, có trọng số | mục 5.1 |
| DBSCAN (phụ, C) | 0,5% số chuyến (`303 / 434 / 603`), `eps = 1000 m`, có trọng số | mục 5.1 |

Notebook fit lại cả hai mô hình từ `config/experiment.yaml` và đối chiếu với file nhãn của lần chạy chính thức (mục 5.1): **trùng 9/9** (3 lát cắt × K-Means, A, C).

## 1. Hai thuật toán giống nhau ở đâu

Bảng chéo số chuyến (cụm K-Means × cụm DBSCAN A) cho thấy hai thuật toán **đồng thuận cao ở các vùng dày cốt lõi**:

| Vùng | Cụm K-Means | Cụm DBSCAN A | Tỷ lệ trùng |
|---|---|---|---|
| Trung tâm (Loop, Near North; khu 8/32) | 0 | 0 | 97,0–98,9% |
| Sân bay O'Hare (khu 76) | 1 | 1 | 97,7–98,8% |
| Sân bay Midway (khu 56) | 4 | 2 (và cụm 3 ở WEEKEND) | PM 93,8%; AM 56,0% (44,0% vùng rìa thành nhiễu); WEEKEND tổng 92,7% nhưng tách thành 2 cụm sát nhau (55,2% + 37,5%) |

ARI giữa K-Means và DBSCAN A:
- Tính trên mọi chuyến (coi nhiễu là một nhãn riêng): **0,706** (`WEEKDAY_AM`), **0,820** (`WEEKDAY_PM`), **0,743** (`WEEKEND`).
- Chỉ tính trên các chuyến DBSCAN A gán cụm: **0,726** (`WEEKDAY_AM`), **0,837** (`WEEKDAY_PM`), **0,745** (`WEEKEND`).

## 2. Hai thuật toán khác nhau ở đâu (bản đồ phóng to `WEEKDAY_PM`)

Lưu ý khi đọc hình `outputs/figures/m2_compare_regions_master_v1.png`: màu chỉ để phân biệt các cụm **trong cùng một ô**. Màu ở ô K-Means và ô DBSCAN không tương ứng với nhau, vì nhãn của hai thuật toán độc lập.

### R1. Phía nam (khu 41/43, x 440–457 km, y 4610–4632 km)

- **K-Means** gom gần như toàn bộ phía nam thành một cụm riêng: cụm 3, chiếm 4,3–5,7% số chuyến (3.472–6.375 chuyến), bán kính RMS 5,25–5,46 km, là cụm rộng nhất. Lý do: K-Means bắt buộc gán mọi điểm vào một cụm.
- **DBSCAN A** gán **78,6–92,7% số chuyến trong khung R1 là nhiễu** (`WEEKDAY_AM` 78,6%, `WEEKDAY_PM` 91,1% = 3.909/4.290 chuyến, `WEEKEND` 92,7%).
- Theo bảng chéo trên cụm 3 của K-Means: **100% chuyến thuộc cụm 3 bị DBSCAN A gán nhiễu ở `WEEKDAY_PM` (3.757/3.757) và `WEEKEND` (6.375/6.375)**. Riêng `WEEKDAY_AM`, DBSCAN A tách được một cụm nhỏ ở Hyde Park (cụm 3, khu 41, 611 chuyến = 17,6% cụm 3 K-Means), còn 82,4% vẫn là nhiễu.
- Diễn giải: trừ cụm nhỏ Hyde Park vào sáng ngày thường, phần lớn phía nam có nhiều toạ độ thưa và ít chuyến; theo tiêu chí mật độ, đây **không phải một hotspot liên tục**. Cụm 3 của K-Means chủ yếu sinh ra do ràng buộc phân hoạch toàn bộ dữ liệu.

### R2. Quanh O'Hare và tây bắc (x 420–442 km, y 4638–4653 km)

- **K-Means:** cụm O'Hare (cụm 1) gồm 7–9 toạ độ, bán kính RMS 1,00–1,34 km, kéo thêm các toạ độ ít chuyến ở phía đông sân bay. Các toạ độ tây bắc còn lại bị gán vào cụm phía bắc (cụm 2).
- **DBSCAN A:** cụm O'Hare chỉ giữ đúng **2 toạ độ** (chính sân bay, bán kính RMS 0,41–0,44 km). Toàn bộ toạ độ xung quanh là nhiễu (**6,3–11,8%** số chuyến trong khung R2; `WEEKDAY_PM` là 1.194/18.884 chuyến).
- Diễn giải: DBSCAN cho ranh giới hotspot sân bay **chặt hơn**, đúng với đặc điểm lượt đón tập trung ngay nhà ga. K-Means làm cụm sân bay rộng ra vì mọi điểm phải thuộc tâm gần nhất.

### R3. Phía bắc dọc hồ (Lake View, khu 6; x 440–452 km, y 4636–4653 km)

- **K-Means** tách phía bắc thành một cụm riêng: cụm 2, chiếm 8,9–13,5% số chuyến (bán kính RMS 3,55–3,86 km).
- **DBSCAN A** **gộp dải dọc hồ phía bắc vào cụm trung tâm** (cụm 0), chiếm 60,6–74,5% số chuyến của cụm 2 K-Means, vì các toạ độ dọc hồ nối liền nhau trong bán kính 1,5 km. Các toạ độ thưa ở rìa tây bắc bị gán nhiễu (25,5–39,4% cụm 2 K-Means; **5,2–6,8%** số chuyến trong khung R3, `WEEKDAY_PM` là 3.385/53.359 chuyến).
- Diễn giải: DBSCAN theo được cụm **dạng dải** dọc bờ hồ thay vì cắt ngang như K-Means, nhưng với một ngưỡng `eps` duy nhất (1,5 km), nó vẫn gộp Loop với Lake View thành một dải lớn. Ở cấu hình phụ C (`eps = 1000 m`), hai vùng này tách ra nhưng đổi lại phát sinh 11–13 cụm nhỏ; tương tự ở `WEEKEND` bản thân A (1,5 km) làm khu Midway tách làm 2 cụm nhỏ sát nhau. ARI giữa A và C chỉ 0,525–0,608, cho thấy DBSCAN rất nhạy với `eps`.

## 3. Nhiễu của DBSCAN A là ngoại lệ thật hay do `eps` quá nhỏ?

| Chỉ số | `WEEKDAY_AM` | `WEEKDAY_PM` | `WEEKEND` |
|---|---:|---:|---:|
| Toạ độ nhiễu / chuyến nhiễu | 77 / 7.648 (12,6%) | 93 / 8.137 (9,4%) | 83 / 11.914 (9,9%) |
| Trung vị số chuyến / toạ độ: nhiễu / có cụm | 60,0 / 53,5 | 38,0 / 23,0 | 86,0 / 25,5 |
| Số chuyến lớn nhất tại 1 toạ độ nhiễu | 571 | 743 | 837 |
| Trung vị khoảng cách tới toạ độ core gần nhất | 4,8 km | 5,7 km | 5,9 km |
| Toạ độ nhiễu cách core trong `(eps, 1,25 × eps]` = 1,5–1,875 km | 5 | 3 | 7 |
| Toạ độ nhiễu cách core `> 2 × eps` = 3 km | 53 (68,8%) | 78 (83,9%) | 68 (81,9%) |
| Toạ độ nhiễu được gán cụm ở cấu hình C | 10 (34,6% chuyến nhiễu) | 10 (29,2%) | 13 (25,4%) |

Kết luận:

- **Phần lớn nhiễu là vùng thưa thật ở xa các tâm mật độ, không phải do `eps` quá nhỏ.** Từ 68,8% đến 83,9% toạ độ nhiễu nằm cách toạ độ core gần nhất hơn 3 km (gấp đôi `eps`), trung vị 4,8–5,9 km (gấp 3,2–3,9 lần `eps`).
- **Vì sao trung vị số chuyến/toạ độ của nhiễu lớn hơn nhóm có cụm?** Nhóm có cụm bao gồm nhiều toạ độ biên (border) ít chuyến nhưng nằm trong bán kính 1,5 km quanh dải trung tâm nên được nối vào cụm 0, kéo trung vị xuống (23–53,5 chuyến). Ngược lại, các toạ độ nhiễu ở ngoại vi tuy có trung vị 38–86 chuyến (tối đa 571–837 chuyến, vẫn dưới ngưỡng 1% = 605–1.206 chuyến) nhưng đứng cô lập cách xa các điểm core, nên không đủ mật độ địa phương để thành hotspot.
- Chỉ **3–7 toạ độ** mỗi lát cắt nằm sát ngưỡng (1,5–1,875 km) — đây mới là phần nhiễu nhạy cảm với lựa chọn `eps`. Đổi sang cấu hình phụ C (`0,5%, 1000 m`) chỉ chuyển 10–13 toạ độ (25,4–34,6% chuyến nhiễu) thành cụm.
- **Nhiễu không đồng nghĩa với bản ghi lỗi.** Tỷ lệ cờ chất lượng ở chuyến nhiễu cao hơn nhóm có cụm một phần nhỏ ở một số cờ (`flag_speed_gt_80`: 0,12–0,30% so với 0,04%; `flag_zero_duration`: 2,61–4,34% so với 1,31–1,67%; `flag_missing_area`: 0,08–0,60% so với 0,00%; `flag_end_before_start`: 0,00–0,01% so với 0,00%), còn `flag_zero_distance` không nhất quán giữa các lát cắt (AM/PM 12,16–15,95% so với 8,81–9,64%, nhưng WEEKEND 9,67% so với 10,09%). Tuyệt đại đa số chuyến nhiễu không có cờ nào, nên nhiễu phản ánh **vị trí thưa**, không phải dữ liệu hỏng và không nên xoá khỏi tập gốc.

## 4. Tóm tắt điểm mạnh và yếu (dùng cho báo cáo và vấn đáp)

| Tiêu chí | K-Means (`K = 5`) | DBSCAN A (`1%, 1500 m`) |
|---|---|---|
| Phải chọn trước | Số cụm `K` | `eps` và `min_samples` |
| Nhiễu | Không có (`Noise Ratio = 0` do thiết kế, không phải ưu điểm) | 9,4–12,6% chuyến là nhiễu, tập trung ở vùng thưa phía nam và tây bắc |
| Hình dạng cụm | Lồi quanh tâm; cắt ngang dải dọc hồ thành 2 cụm | Theo mật độ; giữ liền dải dọc hồ, tách được Hyde Park vào sáng ngày thường |
| Ranh giới hotspot sân bay | Rộng (O'Hare 7–9 toạ độ, 1,00–1,34 km) | Chặt (O'Hare 2 toạ độ, 0,41–0,44 km) |
| Độ nhạy tham số | Ổn định khi `n_init = 50` (mục 3.1, 5.1) | Rất nhạy với `eps`: A có 3–4 cụm (và tách đôi Midway vào cuối tuần), C có 11–13 cụm, `ARI(A, C)` chỉ 0,525–0,608 |
| Hạn chế chính | Ép vùng thưa phía nam thành 1 cụm lớn (bán kính 5,3–5,5 km) | Một `eps` cố định cho mọi mật độ: vừa gộp Loop–Lake View, vừa làm đứt Midway vào cuối tuần. Đây là lý do cần HDBSCAN (M3) |

## Giới hạn

- Toạ độ là **centroid** của census tract hoặc community area, không phải GPS; kết quả phản ánh mật độ đón xe ở cấp khu vực.
- Kết quả trên chạy ở bản đầy đủ `master_v1` (4 tuần); cần đối chiếu cùng tập `trip_id` với HDBSCAN của M3 (Hoàng Tuấn Bảo).
- Silhouette và DBI đều bị kéo lên do rất nhiều chuyến trùng toạ độ, nên diễn giải ở đây kết hợp cả bảng chéo, bản đồ phóng to, `silhouette_unique` và phân tích khoảng cách nhiễu.
