# Diễn giải mô hình HDBSCAN và Phân tích Dịch chuyển Thời gian (M3)

Người viết: **Thành viên 3 (M3 – Hoàng Tuấn Bảo - Advanced Modeling & Temporal Lead)**  
Dữ liệu: **Bản đầy đủ v1 do M1 phát hành (`master_v1`)** (4 tuần 17/04–14/05/2023, 535.167 chuyến đón xe, 304 toạ độ centroid; 3 lát cắt: `WEEKDAY_AM` 60.498, `WEEKDAY_PM` 86.617, `WEEKEND` 120.571 chuyến).  
Căn cứ: BA Specification v1.1 (Mục 1.3, 2.3.4, 2.3.5, 3.4.3).

---

## 1. Cấu hình Lựa chọn của HDBSCAN

Qua quá trình thực nghiệm và khảo sát lưới tham số trên lát cắt `WEEKDAY_AM` (Notebook 05, dữ liệu lưu tại `outputs/metrics/hdbscan_mcs_tuning_master_v1.csv` và `hdbscan_ms_tuning_master_v1.csv`):
- **Quy mô cụm tối thiểu (`min_cluster_size`):** Chọn **`mcs = 100`**. Ngưỡng này tương ứng với khoảng 0,16% tổng nhu cầu của lát cắt, đủ lớn để loại trừ các điểm gom vi mô cục bộ (micro-clusters $< 100$ chuyến không có ý nghĩa điều phối vĩ mô), giúp thu gọn từ $89$ cụm ($mcs=50$) xuống **$67$ cụm** thực chất, tỷ lệ nhiễu chỉ **$2,1\%$** ($1.275$ điểm).
- **Độ bảo thủ mật độ (`min_samples`):** Chọn **`ms = 10`** (giữ cố định trong vòng quét `min_cluster_size` để tránh rủi ro thay đổi ngầm R05). Khi $ms = 10$, tỷ lệ nhiễu (Noise Ratio) dao động ổn định ở mức **$0,9\% – 2,3\%$** trên cả 3 lát cắt.
- **Phương pháp chọn cụm (`cluster_selection_method`):** Chọn **`eom` (Excess of Mass)** nhằm tối đa hóa độ bền vững (stability) tổng thể của các cụm phân cấp.

---

## 2. So sánh Toàn diện Ba Mô hình: K-Means, DBSCAN và HDBSCAN

*(Bảng tổng hợp từ `outputs/metrics/baseline_metrics.csv` và `outputs/metrics/hdbscan_metrics.csv`)*

| Tiêu chí so sánh | K-Means ($K = 5$) | DBSCAN chính A (1%, 1500 m) | HDBSCAN ($mcs = 100, ms = 10$) |
|---|---|---|---|
| **Nguyên lý cốt lõi** | Phân hoạch Voronoi quanh tâm, tối thiểu hóa SSE | Kết nối mật độ với bán kính $\varepsilon$ cố định | Phân cấp mật độ dựa trên mutual reachability distance và stability |
| **Tham số cần định trước** | Số cụm $K$ | Bán kính $\varepsilon$ và số điểm láng giềng $min\_samples$ | Quy mô cụm tối thiểu $min\_cluster\_size$ và $min\_samples$ |
| **Số cụm phát hiện** | Cố định 5 cụm | 3 – 4 cụm lớn | **63 – 78 cụm** (bắt được toàn bộ các điểm đón tập trung chi tiết) |
| **Tỷ lệ điểm nhiễu (Noise Ratio)** | $0,0\%$ (ép buộc phân hoạch mọi điểm) | $9,4\% - 12,6\%$ | **$0,9\% - 2,3\%$** (loại bỏ chính xác các toạ độ đơn lẻ thưa thớt) |
| **Tỷ lệ bao phủ (Coverage)** | $100,0\%$ | $87,4\% - 90,6\%$ | **$97,7\% - 99,1\%$** |
| **Xử lý mật độ biến thiên** | Kém (ép vùng thưa phía nam thành 1 cụm khổng lồ $5,3\text{ km}$) | Kém (1 $\varepsilon$ duy nhất khiến Loop bị gộp với Lake View, còn Midway bị vỡ đôi cuối tuần) | **Tốt nhất** (tách rạch ròi các toạ độ đông khách, giữ vững cụm Midway và O'Hare) |
| **Ranh giới Sân bay O'Hare** | Bị loãng ra các toạ độ lân cận (7–9 toạ độ, bán kính $1,0–1,3\text{ km}$) | Rất chặt chẽ (đúng 2 toạ độ nhà ga, bán kính $0,4\text{ km}$) | **Rất chặt chẽ** (tách thành 2 cụm nhà ga riêng biệt, nhận diện rõ từng terminal) |
| **Cụm Sân bay Midway vào Cuối tuần** | Thuộc 1 cụm duy nhất (cụm 4) | Bị tách làm 2 cụm nhỏ sát nhau (vỡ cụm do $\varepsilon = 1500\text{ m}$) | **Khắc phục hoàn toàn:** giữ nguyên cấu trúc cụm ổn định có độ bền vững cao |
| **Thời gian Fit (Runtime)** | $0,12 - 0,16\text{ s}$* (fit có trọng số $N=304$) | $0,04 - 0,07\text{ s}$* (fit có trọng số $N=304$) | $18,1 - 72,7\text{ s}$** (fit trên toàn bộ $N=60k - 120k$ dòng raw) |
| **Silhouette Score (trên clustered)** | $0,726 - 0,753$ | $0,741 - 0,859$ | **$0,981 - 0,991$** (bị kéo cao do $62,7\%$ cụm có bán kính 0) |
| **Davies-Bouldin Index (DBI)** | $0,445 - 0,477$ | $0,153 - 0,220$ | **$0,180 - 0,288$** (độ phân tách cụm rất tốt) |

> ### Lưu ý Phương pháp luận & Đánh giá Khoa học (Caveats):
> 1. **Khác biệt thời gian tính toán (* vs **):** K-Means và DBSCAN được fit có trọng số trên 304 điểm duy nhất (Python 3.10.6), trong khi HDBSCAN chạy trên toàn bộ tập điểm thô $60.498 - 120.571$ dòng (Python 3.11.9 Windows). Không thể so sánh trực tiếp runtime nếu không tính đến khác biệt số dòng đầu vào.
> 2. **Giải thích điểm Silhouette 0,98 - 0,99:** Trong dữ liệu Chicago, toạ độ bị nén về 304 centroid. Có **62,7% số cụm ở AM có bán kính nội cụm $RMS = 0\text{ m}$** (chỉ gồm 1 toạ độ centroid có $\ge 100$ chuyến). Khi đó, khoảng cách nội cụm $a(i) = 0$, công thức Silhouette $s(i) = \frac{b(i)-0}{b(i)} = 1,0$ kéo điểm trung bình toàn bộ lên sát 1,0. Đây là hiện tượng spatial coarsening của dữ liệu mở, cần giải trình rõ ràng trong báo cáo.

---

## 3. Phân tích Dịch chuyển Hotspot Theo Thời Gian (Temporal Tracking)

Dựa trên thuật toán ghép cặp cụm tâm gần nhất (`src.evaluation.temporal`, lưu tại `outputs/metrics/hotspot_tracking.csv`), sự dịch chuyển của các hotspot chính giữa các lát cắt được lượng hóa như sau:

> **Lưu ý về Hiện tượng "Dịch chuyển 0 m":** Có 53,8% cặp ghép có $\Delta d = 0\text{ m}$ do tâm cụm neo cố định vào cùng toạ độ centroid hành chính. Biến động ở đây là biến động về **lượng chuyến ($\Delta\text{trips}$) và thị phần ($\Delta\text{share}$)**, phản ánh cường độ nhu cầu tại hạ tầng cố định.

### 3.1. Dịch chuyển giữa Sáng ngày thường (`WEEKDAY_AM`) $\rightarrow$ Chiều ngày thường (`WEEKDAY_PM`):
- **Hotspot Sân bay Quốc tế O'Hare (Khu 76):**
   - Vị trí tâm cụm cố định ($\Delta d = 0\text{ m}$ tại nhà ga).
   - Tổng nhu cầu tăng vọt từ **$15,7\%$** (sáng: $9.469$ chuyến) lên **$20,4\%$** (chiều: $17.690$ chuyến). Phản ánh các chuyến bay hạ cánh dồn dập vào chiều tối.
- **Hotspot Near West Side (Khu 28):**
   - Nhu cầu đón xe tại Cụm 1 sụt giảm mạnh nhất: từ **$9,71\%$** ($5.874$ chuyến) vào buổi sáng xuống **$3,06\%$** ($2.651$ chuyến) vào buổi chiều ($\Delta\text{share} = -6,65\%$). Phản ánh nhu cầu đón xe buổi sáng quanh khu bệnh viện UIC và văn phòng phía Tây giảm sâu vào chiều.
- **Hotspot Trung tâm Loop (Khu 32):**
   - Tổng tỷ trọng đón khách tăng từ **$15,3\%$** (sáng) lên **$19,7\%$** (chiều) khi nhân viên công sở tan làm.
- **Hotspot Hyde Park (Khu 41 - ĐH Chicago):**
   - Buổi sáng: Cụm 29 đạt $351$ chuyến ($0,58\%$, bán kính $RMS = 117\text{ m}$).
   - Buổi chiều: Cụm 27 đạt $607$ chuyến ($0,70\%$, bán kính $RMS = 338\text{ m}$).

### 3.2. Dịch chuyển giữa Ngày làm việc (`WEEKDAY`) $\rightarrow$ Cuối tuần (`WEEKEND`):
- **Trọng tâm giải trí cuối tuần Near North Side (Khu 8):**
   - Nhu cầu đón xe bùng nổ mạnh mẽ: riêng Cụm 1 đạt **$12,0\%$** ($14.454$ chuyến), trở thành cụm đón khách nhộn nhịp nhất thành phố.
- **Sân bay O'Hare (Khu 76):**
   - Tiếp tục duy trì thị phần áp đảo **$24,2\%$** ($29.137$ chuyến trên 2 cụm nhà ga).
- **Sân bay Midway (Khu 56):**
   - Duy trì ổn định quanh $2,3\% - 3,3\%$ tổng nhu cầu ở cả ngày thường và cuối tuần.

---

## 4. Ý nghĩa Nghiệp vụ & Đóng góp Cho Bài Toán Điều Phối Taxi
1. **Phân bổ đội xe theo khung giờ:**
   - 07:00–10:00: Tập trung phương tiện tại Near West Side (Khu 28) và các trục hướng tâm vào Loop.
   - 16:00–19:00: Dịch chuyển trọng tâm sang đón khách tại Sân bay O'Hare (Khu 76) và các toà nhà văn phòng Loop (Khu 32).
   - Cuối tuần: Điều phối phương tiện dọc hành lang vui chơi giải trí Near North Side (Khu 8) và sân bay O'Hare.
2. **Cảnh báo nghiệp vụ bắt buộc:**
   - *Toạ độ đón xe là toạ độ centroid khu vực hành chính (không phải vị trí GPS chính xác của xe).*
   - *Hotspot được phát hiện là **điểm nóng về nhu cầu đón xe (pickup demand)**, không phải điểm ùn tắc giao thông (R11 trong BA Spec). Để xác định ùn tắc cần tích hợp thêm dữ liệu tốc độ lưu thông (GPS trajectories / traffic sensors).*
