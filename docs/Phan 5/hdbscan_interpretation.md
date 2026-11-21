# Diễn giải mô hình HDBSCAN và Phân tích Dịch chuyển Thời gian (M3)

Người viết: **Thành viên 3 (M3 – Hoàng Tuấn Bảo - Advanced Modeling & Temporal Lead)**  
Dữ liệu: **Bản đầy đủ v1 do M1 phát hành (`master_v1`)** (4 tuần 17/04–14/05/2023, 535.167 chuyến đón xe, 304 toạ độ centroid trên toàn bộ master; 3 lát cắt: `WEEKDAY_AM` 60.498 dòng / 165 toạ độ, `WEEKDAY_PM` 86.617 dòng / 188 toạ độ, `WEEKEND` 120.571 dòng / 189 toạ độ).  
Căn cứ: BA Specification v1.1 (Mục 1.3, 2.3.4, 2.3.5, 3.4.3), bản rà soát kỹ thuật 21/11/2026.

> **Trạng thái (Đã nghiệm thu chính thức 21/11/2026):** Toàn bộ pipeline M3 đã hoàn thành tái lập và kiểm định. Backend `hdbscan 0.8.44` (Cython/C) đã được xác nhận chính thức với benchmark bao phủ cỡ mẫu 50k theo NFR-02 (`outputs/metrics/environment_hdbscan.txt`, `outputs/metrics/hdbscan_benchmark.csv`). Thuật toán HDBSCAN được cấu hình cố định `approx_min_span_tree=False`, sắp xếp tiền định theo `trip_id`, triệt tiêu hoàn toàn độ nhạy thứ tự dòng (đã kiểm định qua 3 seed xáo dòng ngẫu nhiên). Bảng độ bền vững `outputs/metrics/hdbscan_stability_master_v1.csv` đã được trích xuất đủ 208 cụm. Thuật toán ghép cặp thời gian đã nâng cấp thành đối sánh hai chiều (Two-Way Nearest Centroid Matching) 5 trạng thái tường minh với cờ quy mô cuối tuần 199 chuyến. Tất cả số liệu dưới đây được trích xuất trực tiếp từ các file CSV chính thức.

---

## 1. Cấu hình Lựa chọn của HDBSCAN

Qua quá trình thực nghiệm và khảo sát lưới tham số đầy đủ trên lát cắt `WEEKDAY_AM` (dữ liệu lưu tại `outputs/metrics/hdbscan_mcs_tuning_master_v1.csv` và `hdbscan_ms_tuning_master_v1.csv`):
- **Quy mô cụm tối thiểu (`min_cluster_size`):** Chọn **`mcs = 100`**. Ngưỡng này tương ứng với khoảng $0,16\%$ tổng nhu cầu của lát cắt, đủ lớn để loại trừ các điểm gom vi mô cục bộ (micro-clusters $< 100$ chuyến không có ý nghĩa điều phối vĩ mô), giúp thu gọn từ $102$ cụm ($mcs=30$) và $89$ cụm ($mcs=50$) xuống **$67$ cụm** thực chất, tỷ lệ nhiễu chỉ **$2,11\%$** ($1.278$ điểm), Silhouette $0,981$, DBI $0,288$, CH $1.455.397$.
- **Độ bảo thủ mật độ (`min_samples`):** Chọn **`ms = 10`** (giữ cố định trong vòng quét `min_cluster_size` để tránh rủi ro thay đổi ngầm R05). Khi $ms = 10$, tỷ lệ nhiễu (Noise Ratio) dao động ổn định ở mức **$0,93\% – 2,27\%$** trên cả 3 lát cắt ($2,11\%$ ở AM; $2,27\%$ ở PM; $0,93\%$ ở Weekend). Khảo sát $ms \in [5, 10, 20, 50]$ cho thấy số cụm luôn giữ nguyên 67 cụm và DBI giữ nguyên $0,288$.
- **Thuật toán cây khung:** Bắt buộc thiết lập **`approx_min_span_tree = False`** để thuật toán xây dựng cây khung nhỏ nhất (MST) chính xác tuyệt đối, không phụ thuộc thứ tự dòng khi có nhiều điểm trùng toạ độ.
- **Phương pháp chọn cụm (`cluster_selection_method`):** Chọn **`eom` (Excess of Mass)** nhằm tối đa hóa độ bền vững (stability) tổng thể của các cụm phân cấp.
- **Thời gian chạy (Runtime):** Trên backend C-extension `hdbscan 0.8.44` (Python 3.11.9), thời gian fit ở bước tuning là $1,35\text{ s}$ và ở lần fit chính thức là $1,39\text{ s}$ trên $60.498$ dòng thô.

---

## 2. So sánh Toàn diện Ba Mô hình: K-Means, DBSCAN và HDBSCAN

Bảng số liệu tổng hợp chính thức trích từ `outputs/metrics/baseline_metrics.csv` và `outputs/metrics/hdbscan_metrics.csv`:

| Tiêu chí so sánh | K-Means ($K = 5$) | DBSCAN chính A ($1\%, 1.500\text{m}$) | HDBSCAN ($mcs = 100, ms = 10$) |
|---|---|---|---|
| **Nguyên lý cốt lõi** | Phân hoạch Voronoi quanh tâm, tối thiểu hóa SSE | Kết nối mật độ với bán kính $\varepsilon$ cố định | Phân cấp mật độ dựa trên mutual reachability distance và stability |
| **Tham số cần định trước** | Số cụm $K$ | Bán kính $\varepsilon$ và số điểm láng giềng $min\_samples$ | Quy mô cụm tối thiểu $min\_cluster\_size$ và $min\_samples$ |
| **Số cụm phát hiện** | Cố định 5 cụm | 3 – 4 cụm lớn | **63 – 78 cụm** (nhận diện chi tiết từng điểm gom toạ độ có $\ge 100$ chuyến) |
| **Tỷ lệ điểm nhiễu (Noise Ratio)** | $0,0\%$ (ép buộc phân hoạch mọi điểm) | $9,4\% - 12,6\%$ | **$0,9\% - 2,3\%$** ($2,1\%$ AM, $2,3\%$ PM, $0,9\%$ WE) |
| **Tỷ lệ bao phủ (Coverage)** | $100,0\%$ | $87,4\% - 90,6\%$ | **$97,7\% - 99,1\%$** |
| **Thị phần cụm lớn nhất** | $52,7\% - 62,5\%$ (cụm trung tâm khổng lồ) | $62,1\% - 68,9\%$ (dải trung tâm gộp rộng) | **$10,6\% - 12,8\%$** (Cụm sân bay O'Hare) |
| **Số điểm tính metric ($N_{\text{metric}}$)** | $60.498 - 120.571$ (toàn bộ điểm) | $52.850 - 108.657$ (chỉ điểm có nhãn) | $59.220 - 119.454$ (chỉ điểm có nhãn) |
| **Silhouette Score (trên clustered)** | $0,726 - 0,753$ | $0,741 - 0,859$ | **$0,981 - 0,991$** (bị kéo cao do $63,0\%$ cụm có bán kính $\approx 0\text{ m}$) |
| **Davies-Bouldin Index (DBI)** | $0,445 - 0,477$ | **$0,153 - 0,220$** (thấp hơn / tốt hơn HDBSCAN) | $0,180 - 0,288$ (cao hơn DBSCAN ở cả 3 lát cắt) |
| **Calinski-Harabasz (CH)** | $249.064 - 650.286$ | $189.276 - 904.682$ | **$1.455.397 - 7.865.544$** |
| **Bộ nhớ đỉnh (Peak RAM)** | $379,3 - 534,6\text{ MB}$ | $432,3 - 572,4\text{ MB}$ | **$361,0 - 422,6\text{ MB}$** |
| **Thời gian Fit (Runtime)** | $0,12 - 0,16\text{ s}$* (fit có trọng số $N_{\text{fit}} \le 189$) | $0,04 - 0,07\text{ s}$* (fit có trọng số $N_{\text{fit}} \le 189$) | $1,39 - 3,03\text{ s}$** (fit unweighted $N_{\text{fit}} = 60k - 120k$) |
| **Ranh giới Sân bay O'Hare** | Bị loãng ra các toạ độ lân cận (7–9 toạ độ, bán kính $1,0–1,3\text{ km}$) | Rất chặt chẽ (đúng 2 toạ độ nhà ga, bán kính $0,4\text{ km}$) | **Rất chặt chẽ** (tách thành 2 cụm nhà ga riêng biệt) |
| **Cụm Sân bay Midway** | Thuộc 1 cụm duy nhất gộp diện rộng | Bị tách làm 2 cụm nhỏ sát nhau (vỡ cụm do $\varepsilon = 1500\text{ m}$) | **Tương tự DBSCAN:** phân tách Midway thành 2 cụm độc lập do khoảng cách giữa 2 toạ độ điểm đón |

---

## 3. Quyết định Nghiệp vụ & Phương pháp luận Thống nhất Giữa M2 và M3

### 3.1. Quyết định Báo cáo Silhouette Score và Davies-Bouldin Index (DBI) Công bằng
Để đảm bảo tính trung thực khoa học theo yêu cầu của Team Lead và BA Specification v1.1:
1. **Không dùng Silhouette cao để tuyên bố HDBSCAN vượt trội hơn:** 
   - Điểm Silhouette của HDBSCAN đạt rất cao ($0,981 - 0,991$) là do **$131/208$ cụm ($63,0\%$)** chỉ gồm duy nhất một toạ độ centroid (bán kính nội cụm $RMS = 0\text{ m}$). Khi khoảng cách nội cụm $a(i) = 0$, công thức toán học $s(i) = \frac{b(i)-0}{\max(a(i),b(i))} = 1,0$ sẽ kéo điểm trung bình toàn bộ lên sát 1,0.
   - Đây là hệ quả tất yếu từ cấu trúc nén toạ độ (Spatial Coarsening) của cổng dữ liệu mở Chicago, không phản ánh thuật toán có chất lượng vượt trội thần kỳ.
2. **Thừa nhận DBSCAN có Davies-Bouldin Index tốt hơn HDBSCAN:**
   - Chỉ số DBI của DBSCAN đạt từ **$0,153$ đến $0,220$**, thấp hơn (tốt hơn) so với HDBSCAN (**$0,180$ đến $0,288$**) ở cả 3 lát cắt.
   - **Lý do:** DBSCAN chỉ phân hoạch thành 3–4 cụm đại diện vĩ mô rất cách xa nhau (khoảng cách giữa các tâm cụm rất lớn so với độ phân tán nội cụm). Ngược lại, HDBSCAN phát hiện mạng lưới 63–78 cụm chi tiết phân bố rải rác toàn thành phố, khiến khoảng cách giữa các cặp cụm lân cận nhỏ lại, làm tăng tỷ số $R_{ij}$. Vì vậy, **DBI của HDBSCAN không được in đậm** trong bảng báo cáo.
3. **Quy tắc nghiệm thu:** Mọi báo cáo về Silhouette/DBI bắt buộc phải đi kèm **Noise Ratio**, **Coverage**, số điểm tính chỉ số **$N_{\text{metric}}$**, và tỷ lệ cụm đơn toạ độ.

### 3.2. Thống nhất Giới hạn So sánh Thời gian Chạy (Runtime) Giữa M2 và M3
Hai thành viên M2 và M3 đã thống nhất nguyên tắc báo cáo runtime:
- **Khác biệt cốt lõi về biểu diễn dữ liệu khi fit:**
  - K-Means và DBSCAN (M2) được tối ưu hóa bằng cách fit có trọng số (`sample_weight`) trên đúng các toạ độ duy nhất của từng lát cắt ($N_{\text{fit}} = 165 - 189$ điểm), chạy trên môi trường Python 3.10.6. Do $N_{\text{fit}}$ rất nhỏ, thời gian chạy chỉ mất $0,04 - 0,16\text{ s}$.
  - HDBSCAN (M3) sử dụng package `hdbscan 0.8.44` (Cython/C) trên Python 3.11.9. Do thuật toán cây khoảng cách tương hỗ (Mutual Reachability Graph) không hỗ trợ `sample_weight`, mô hình bắt buộc phải fit trên toàn bộ $N_{\text{fit}} = 60.498 - 120.571$ dòng chuyến rời rạc.
- **Thống nhất:** **Tuyệt đối không so sánh trực tiếp runtime** giữa HDBSCAN và K-Means/DBSCAN. Mức chênh lệch $1,39 - 3,03\text{ s}$ so với $< 0,2\text{ s}$ chỉ phản ánh sự khác biệt về quy mô tập điểm đưa vào fit ($N_{\text{fit}} \approx 60.000 - 120.000$ vs $N_{\text{fit}} \le 189$), hoàn toàn không phản ánh tốc độ thuần túy của thuật toán. Trong mọi bảng biểu và slide, M4 phải giữ nguyên hai dấu chú thích `*` và `**` này.

---

## 4. Phân tích Dịch chuyển Hotspot Theo Thời Gian (Temporal Tracking)

Thuật toán ghép cặp đối xứng hai chiều (Two-Way Nearest Centroid Matching với ngưỡng $d_{\text{max}} = 3.500\text{ m}$ định nghĩa tại `config/experiment.yaml`) phân loại toàn bộ 229 dòng chuyển tiếp trong `outputs/metrics/hotspot_tracking.csv` thành 5 trạng thái:
- **Chuyển tiếp Sáng $\rightarrow$ Chiều (`WEEKDAY_AM -> WEEKDAY_PM` - 70 dòng):**
  - **54 STABLE**: Ghép đối xứng 1-1, duy trì cấu trúc hotspot ổn định.
  - **9 MERGED**: Nhiều cụm sáng gộp vào cụm chiều tại các điểm nút giao thông.
  - **5 SPLIT**: Một cụm sáng tách ra thành nhiều cụm chiều.
  - **2 DISSOLVED**: Cụm 34 (khu 25 - Austin, 313 chuyến) và Cụm 36 (khu 59 - McKinley Park, 291 chuyến) tiêu biến vào buổi chiều do nhu cầu giảm dưới ngưỡng $mcs=100$.
  - **0 EMERGING**: Toàn bộ các cụm buổi chiều đều có nguồn gốc từ buổi sáng trong phạm vi $3.500\text{ m}$.
- **Chuyển tiếp Chiều $\rightarrow$ Cuối tuần (`WEEKDAY_PM -> WEEKEND` - 78 dòng):**
  - **52 STABLE**, **22 SPLIT** (hiện tượng phân tách mạnh mẽ sang các khu vui chơi giải trí cuối tuần), **0 MERGED**, **0 DISSOLVED**, **4 EMERGING** (các cụm mới xuất hiện ở ngoại vi).
- **Chuyển tiếp Sáng $\rightarrow$ Cuối tuần (`WEEKDAY_AM -> WEEKEND` - 81 dòng):**
  - **52 STABLE**, **23 SPLIT**, **5 MERGED**, **0 DISSOLVED**, **1 EMERGING**.

### 4.1. Bản chất Hiện tượng "Dịch chuyển 0 m" và Dịch chuyển Thực sự
- **103 cặp $\Delta d = 0\text{ m}$ (46,4% số cặp đối sánh):** Toàn bộ $103/103$ cặp đều là các cụm đơn toạ độ (`n_coords_from = 1, n_coords_to = 1`). Tâm cụm neo cố định vào cùng toạ độ centroid khu vực hành chính (census tract). Khoảng cách $0\text{ m}$ phản ánh giới hạn làm mờ dữ liệu (Spatial Coarsening); sự biến động của điểm nóng thực chất thể hiện qua **sự tăng/giảm số chuyến ($\Delta\text{trips}$) và tỷ trọng thị phần ($\Delta\text{share}$)**.
- **119 cặp $\Delta d > 0\text{ m}$ (53,6% số cặp đối sánh):** Toàn bộ $119/119$ cặp đều là các cụm đa toạ độ (`coord_note = multi_coord_shift`). Trọng tâm cụm dịch chuyển từ $0,9\text{ m}$ đến $3.122\text{ m}$ do sự biến đổi về thành phần toạ độ thành viên và phân bổ lại trọng số chuyến đi giữa các toạ độ.

### 4.2. Cờ Ngưỡng Quy mô Cuối tuần (`below_scaled_threshold`)
Do quy mô lát cắt Cuối tuần ($120.571$ chuyến) lớn gần gấp đôi lát cắt Sáng ($60.498$ chuyến), nếu áp ngưỡng cố định 100 chuyến sẽ xuất hiện các cụm nhỏ lẻ. Quy đổi theo tỷ trọng tương đương, ngưỡng quy mô cuối tuần là **$199\text{ chuyến}$**. Nhóm đã gắn cờ `below_scaled_threshold = True` cho 41 dòng chuyển tiếp cuối tuần có quy mô cụm đích $< 199$ chuyến để M4 lọc bỏ hoặc chú thích khi trình bày.

---

## 5. Bảng Đối chiếu và Đính chính các Tuyên bố Số liệu (Claim Register C01–C08)

Nhằm đảm bảo sự nhất quán tuyệt đối giữa báo cáo văn bản và dữ liệu số học thực tế, bảng dưới đây tổng hợp chi tiết hiện trạng các khẳng định C01–C08:

| Claim ID | Chủ đề | Tuyên bố ban đầu / Hiểu nhầm trước rà soát | Số liệu chính thức từ CSV (`master_v1`) | Giải thích & Biện pháp xử lý | Trạng thái |
|---|---|---|---|---|---|
| **C01** | HDBSCAN Noise Ratio | "HDBSCAN có Noise Ratio ≈ 10% (10,8%)" | **AM: 2,11%**, **PM: 2,27%**, **Weekend: 0,93%** (`hdbscan_metrics.csv`) | Hiểu nhầm số liệu của DBSCAN A (9,4%–12,6%). HDBSCAN thực tế bao phủ đến 97,7%–99,1% dữ liệu. Đã sửa số chính thức vào báo cáo. | **RESOLVED** |
| **C02** | Dải Noise Ratio | "HDBSCAN Noise Ratio dao động 9,8%–11,5%" | **0,93% – 2,27%** trên cả 3 lát cắt | Đã đính chính thành dải 0,9%–2,3% trong toàn bộ tài liệu diễn giải. | **RESOLVED** |
| **C03** | Số lượng cụm | "$mcs=100$ phát hiện 4 cụm lớn ổn định" | **AM: 67 cụm**, **PM: 63 cụm**, **Weekend: 78 cụm** | 4 cụm lớn là kết quả của DBSCAN A. HDBSCAN nhận diện mạng lưới vi mô 63–78 cụm chi tiết. Đã cập nhật đúng số cụm. | **RESOLVED** |
| **C04** | Silhouette & DBI | "Silhouette đạt 0,78 và DBI đạt 0,19" | **Silhouette: 0,981 – 0,991**; **DBI: 0,180 – 0,288** | Số 0,78 là của bản chạy thử cũ. Số chính thức là 0,98–0,99 do hiện tượng nén toạ độ (Spatial Coarsening). Đã cập nhật kèm caveat. | **RESOLVED** |
| **C05** | Thị phần O'Hare (Khu 76) | "O'Hare tăng từ 11,5% (sáng) lên 16,8% (chiều)" | **Cụm lớn nhất (Cụm 0): 10,6% $\rightarrow$ 12,8%**; **Tổng toàn khu 76: 15,7% $\rightarrow$ 20,4% $\rightarrow$ 24,2%** | Số cũ là ước lượng nháp. Đã phân biệt rõ giữa thị phần của cụm lớn nhất và tổng nhu cầu toàn khu vực hành chính 76. | **RESOLVED** |
| **C06** | Dịch chuyển Cụm Trung tâm | "Tâm cụm trung tâm dịch chuyển khoảng 800–900 m (hoặc 650–950 m) về phía bắc" | **Các cụm lớn ($\ge 2000$ chuyến) dịch chuyển: $0\text{ m}, 0\text{ m}, 0\text{ m}, 0\text{ m}, 0\text{ m}, 0\text{ m}, 83\text{ m}, 0\text{ m}, 0\text{ m}$** | Không có cụm lớn nào dịch 650–950m. Tâm cụm cố định tại centroid; nhu cầu tăng tại chỗ ở Loop/Near North chứ không di chuyển vật lý. Đã sửa trong báo cáo. | **RESOLVED** |
| **C07** | Hotspot Hyde Park (Khu 41) | "Hyde Park xuất hiện rõ ở sáng (611 chuyến, 1,0%), tan rã chiều/cuối tuần" | **AM: Cụm 29 ($351$ chuyến, $0,58\%$); PM: Cụm 27 ($607$ chuyến, $0,70\%$); Weekend: Cụm 24 ($748$ chuyến, $0,62\%$)** | Số 611 chuyến là của DBSCAN A. HDBSCAN nhận diện Hyde Park liên tục ở cả 3 lát cắt với số chuyến chiều và cuối tuần cao hơn sáng. Đã sửa đúng số liệu. | **RESOLVED** |
| **C08** | Thị phần Midway (Khu 56) | "Midway giữ tỷ trọng 4,2%–4,8% ở cả 3 lát cắt" | **Σ share cụm HDBSCAN: AM: 2,74%, PM: 3,29%, Weekend: 3,80%** (Tổng thô khu 56: 2,71%, 3,29%, 3,80%) | Số 4,2%–4,8% là số liệu nháp cũ. Đã cập nhật đúng số liệu từ `hdbscan_clusters_master_v1.csv` và xác nhận HDBSCAN tách Midway thành 2 cụm độc lập. | **RESOLVED** |

---

## 6. Ý nghĩa Nghiệp vụ & Đóng góp Cho Bài Toán Điều Phối Taxi
*(Lưu ý: Các diễn giải về phân bổ đội xe, sinh viên ĐH Chicago, bệnh viện UIC hay nhân viên tan sở là giả thuyết suy luận bối cảnh đô thị, không phải thuộc tính trực tiếp ghi nhận trong dữ liệu).*

1. **Gợi ý phân bổ phương tiện theo khung giờ:**
   - 07:00–09:59: Tăng cường phương tiện tại Near West Side (Khu 28) và các trục hướng tâm vào Loop.
   - 16:00–18:59: Dịch chuyển trọng tâm sang đón khách tại Sân bay O'Hare (Khu 76) và các toà nhà văn phòng Loop (Khu 32).
   - Cuối tuần: Điều phối phương tiện dọc hành lang vui chơi giải trí Near North Side (Khu 8) và sân bay O'Hare.
2. **Cảnh báo nghiệp vụ bắt buộc:**
   - *Toạ độ đón xe là toạ độ centroid khu vực hành chính (không phải vị trí GPS chính xác của xe).*
   - *Hotspot được phát hiện là **điểm nóng về nhu cầu đón xe (pickup demand)**, không phải điểm ùn tắc giao thông (R11 trong BA Spec). Để xác định ùn tắc cần tích hợp thêm dữ liệu tốc độ lưu thông (GPS trajectories / traffic sensors).*
