# Diễn giải mô hình HDBSCAN và Phân tích Dịch chuyển Thời gian (M3)

Người viết: **Thành viên 3 (M3 – Hoàng Tuấn Bảo - Advanced Modeling & Temporal Lead)**  
Dữ liệu: **Bản đầy đủ v1 do M1 phát hành (`master_v1`)** (4 tuần 17/04–14/05/2023, 535.167 chuyến đón xe, 304 toạ độ centroid; 3 lát cắt: `WEEKDAY_AM` 60.498, `WEEKDAY_PM` 86.617, `WEEKEND` 120.571 chuyến).  
Căn cứ: BA Specification v1.1 (Mục 1.3, 2.3.4, 2.3.5, 3.4.3).

---

## 1. Cấu hình Lựa chọn của HDBSCAN

Qua quá trình thực nghiệm và khảo sát lưới tham số trên lát cắt `WEEKDAY_AM` (Notebook 05):
- **Quy mô cụm tối thiểu (`min_cluster_size`):** Chọn **`mcs = 100`**. Ngưỡng này tương ứng với khoảng 0,16% tổng nhu cầu của lát cắt, đủ lớn để loại trừ các điểm gom vi mô cục bộ (micro-clusters không có ý nghĩa nghiệp vụ) nhưng đủ nhạy để giữ lại các hotspot vệ tinh quan trọng như Hyde Park (Đại học Chicago) và Midway.
- **Độ bảo thủ mật độ (`min_samples`):** Chọn **`ms = 10`** (giữ cố định trong vòng quét `min_cluster_size` để tránh rủi ro thay đổi ngầm R05). Khi $ms = 10$, tỷ lệ nhiễu (Noise Ratio) dao động ổn định trong khoảng **9,5% – 12,0%**, tương đồng với mức độ loại bỏ nhiễu của DBSCAN cấu hình chính A.
- **Phương pháp chọn cụm (`cluster_selection_method`):** Chọn **`eom` (Excess of Mass)** nhằm tối đa hóa độ bền vững (stability) tổng thể của các cụm phân cấp.

---

## 2. So sánh Toàn diện Ba Mô hình: K-Means, DBSCAN và HDBSCAN

| Tiêu chí so sánh | K-Means ($K = 5$) | DBSCAN chính A (1%, 1500 m) | HDBSCAN ($mcs = 100, ms = 10$) |
|---|---|---|---|
| **Nguyên lý cốt lõi** | Phân hoạch Voronoi quanh tâm, tối thiểu hóa SSE | Kết nối mật độ với bán kính $\varepsilon$ cố định | Phân cấp mật độ dựa trên mutual reachability distance và stability |
| **Tham số cần định trước** | Số cụm $K$ | Bán kính $\varepsilon$ và số điểm láng giềng $min\_samples$ | Quy mô cụm tối thiểu $min\_cluster\_size$ và $min\_samples$ |
| **Tỷ lệ điểm nhiễu (Noise Ratio)** | $0,0\%$ (do ép buộc phân hoạch mọi điểm) | $9,4\% - 12,6\%$ | $9,8\% - 11,5\%$ |
| **Xử lý mật độ biến thiên** | Kém (ép vùng thưa phía nam thành 1 cụm khổng lồ $5,3\text{ km}$) | Kém (1 $\varepsilon$ duy nhất khiến Loop bị gộp với Lake View, còn Midway bị vỡ đôi cuối tuần) | **Tốt nhất** (giữ liền khối cụm Midway, tách được Hyde Park và dải ven hồ một cách tự nhiên) |
| **Ranh giới Sân bay O'Hare** | Bị loãng ra các toạ độ lân cận (7–9 toạ độ, bán kính $1,0–1,3\text{ km}$) | Rất chặt chẽ (đúng 2 toạ độ nhà ga, bán kính $0,4\text{ km}$) | **Rất chặt chẽ** (đúng 2 toạ độ trung tâm nhà ga, ranh giới rõ ràng) |
| **Cụm Sân bay Midway vào Cuối tuần** | Thuộc 1 cụm duy nhất (cụm 4) | Bị tách làm 2 cụm nhỏ sát nhau (vỡ cụm do $\varepsilon = 1500\text{ m}$) | **Khắc phục hoàn toàn:** giữ nguyên 1 cụm duy nhất có độ bền vững cao |
| **Thời gian Fit (Runtime)** | Cực nhanh ($0,12 - 0,16\text{ s}$ nhờ trọng số toạ độ) | Cực nhanh ($0,04 - 0,07\text{ s}$ nhờ trọng số toạ độ) | Vừa phải ($8 - 25\text{ s}$ trên dữ liệu đầy đủ không dùng trọng số) |
| **Silhouette Score (trên clustered)** | $0,726 - 0,753$ | $0,741 - 0,859$ | $0,760 - 0,830$ |
| **Davies-Bouldin Index (DBI)** | $0,445 - 0,477$ | $0,153 - 0,220$ | **$0,180 - 0,210$** (cấu trúc cụm phân tách rất tốt) |

### Nhận xét Đột phá của HDBSCAN:
HDBSCAN chứng minh ưu thế vượt trội trong việc **giải quyết bài toán mật độ không đồng đều (variable density)** của giao thông đô thị Chicago:
1. **Không bị ép cụm như K-Means:** Không biến vùng nông thôn/ngoại ô thưa thớt phía nam thành một "điểm nóng giả tạo".
2. **Không bị nhạy cảm ngưỡng bán kính như DBSCAN:** Với DBSCAN, việc chọn $\varepsilon = 1500\text{ m}$ vừa làm dính chùm dải trung tâm với phía bắc, vừa làm đứt gãy cụm sân bay Midway vào cuối tuần. HDBSCAN nhờ đánh giá độ bền vững qua condensed tree đã tự động trích xuất được cả cụm siêu đậm đặc (O'Hare, Loop) lẫn các cụm mật độ trung bình (Midway, Hyde Park) mà không cần can thiệp tham số bán kính.

---

## 3. Phân tích Dịch chuyển Hotspot Theo Thời Gian (Temporal Tracking)

Dựa trên thuật toán ghép cặp cụm tâm gần nhất (`src.evaluation.temporal`), sự dịch chuyển của các hotspot chính giữa các lát cắt được lượng hóa như sau:

### 3.1. Dịch chuyển giữa Sáng ngày thường (`WEEKDAY_AM`) $\rightarrow$ Chiều ngày thường (`WEEKDAY_PM`):
- **Hotspot Trung tâm (Loop & Near North Side):**
  - Buổi sáng: Tập trung tại khu vực công sở Loop (Khu 32) và trạm ga tàu.
  - Buổi chiều: Tâm cụm dịch chuyển **$650 - 950\text{ m}$ về phía bắc** hướng sang khu ẩm thực, giải trí và mua sắm Near North Side (Khu 8) và Streeterville.
  - Tỷ trọng nhu cầu đón xe duy trì mức áp đảo ($62\% - 67\%$).
- **Hotspot Sân bay Quốc tế O'Hare (Khu 76):**
  - Tâm cụm dịch chuyển $< 150\text{ m}$ (gần như cố định tuyệt đối tại nhà ga).
  - Tỷ trọng đón xe tăng mạnh vào buổi chiều (từ $11,5\%$ lên $16,8\%$), phản ánh các chuyến bay hạ cánh cuối ngày và hành khách đón taxi về trung tâm.
- **Hotspot Hyde Park (Khu 41 - ĐH Chicago):**
  - Buổi sáng xuất hiện như một hotspot độc lập ($611$ chuyến, tỷ trọng $1,0\%$).
  - Buổi chiều nhu cầu phân tán ra các khu vực xung quanh và trở thành các điểm thưa (được gán nhãn nhiễu hợp lý).

### 3.2. Dịch chuyển giữa Ngày làm việc (`WEEKDAY`) $\rightarrow$ Cuối tuần (`WEEKEND`):
- **Trọng tâm giải trí cuối tuần:**
  - Nhu cầu đón xe tại khu vực dải ven hồ (Lake View, Lincoln Park) tăng mạnh vào cuối tuần, mở rộng bán kính phân tán từ $3,2\text{ km}$ lên $4,1\text{ km}$.
- **Sân bay Midway (Khu 56):**
  - Duy trì tỷ trọng ổn định $4,2\% - 4,8\%$ với bán kính tập trung chặt quanh nhà ga Cicero Ave.
  - Vị trí tâm cụm lệch không quá $180\text{ m}$ so với ngày thường.

---

## 4. Ý nghĩa Nghiệp vụ & Đóng góp Cho Bài Toán Điều Phối Taxi
1. **Phân bổ đội xe theo khung giờ:**
   - 07:00–10:00: Ưu tiên tập trung phương tiện tại các khu vực đón khách ven đô, khu dân cư phía nam (Hyde Park) và các đầu mối giao thông hướng vào Loop.
   - 16:00–19:00: Dịch chuyển trọng tâm sang Sân bay O'Hare và khu vực dịch vụ phía bắc sông Chicago (Near North Side).
   - Cuối tuần: Phân bổ linh hoạt dọc hành lang bờ hồ (Lakefront Corridor) phục vụ nhu cầu vui chơi giải trí.
2. **Cảnh báo về định nghĩa điểm nóng:**
   - Hotspot được phát hiện là **điểm nóng về nhu cầu đón xe (pickup demand)**, không phải điểm ùn tắc giao thông (R11 trong BA Spec). Để xác định ùn tắc cần tích hợp thêm dữ liệu tốc độ lưu thông (GPS trajectories / traffic sensors).
