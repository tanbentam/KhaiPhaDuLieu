# BÁO CÁO KỸ THUẬT VÀ TƯ LIỆU THUYẾT TRÌNH (PHẦN M3)
## Chuyên đề: Phân Cụm Mật Độ Phân Cấp HDBSCAN & Phân Tích Dịch Chuyển Hotspot Theo Lát Cắt Thời Gian

- **Người thực hiện:** Thành viên 3 (M3 – Hoàng Tuấn Bảo - Advanced Modeling & Temporal Lead)
- **Người phối hợp / Reviewer:** M2 (Baseline Review), M4 (Visualization & Report Editor)
- **Nhánh làm việc:** `m3/hdbscan-temporal`
- **Bộ dữ liệu chính thức:** `master_v1` (535.167 dòng, CRS `EPSG:26916`, 304 toạ độ centroid)

---

## MỤC LỤC
1. Cơ sở lý thuyết của HDBSCAN
2. Thiết kế thực nghiệm và Hyperparameter Tuning
3. Bảng chỉ số đánh giá so sánh K-Means, DBSCAN và HDBSCAN
4. Kết quả phân tích dịch chuyển không gian - thời gian (Temporal Slicing)
5. Ngân hàng câu hỏi vấn đáp chuyên môn dành cho M3

---

## 1. CƠ SỞ LÝ THUYẾT CỦA HDBSCAN

### 1.1. Hạn chế của DBSCAN và Lý do cần HDBSCAN
DBSCAN hoạt động dựa trên một bán kính lân cận cố định $\varepsilon$. Trong thực tế dữ liệu giao thông đô thị, mật độ lượt đón xe biến thiên rất lớn:
- Khu trung tâm thương mại (Loop): Mật độ cực kỳ dày đặc (hàng chục nghìn chuyến trong phạm vi vài trăm mét).
- Các đầu mối giao thông ngoại vi (Sân bay O'Hare, Midway): Mật độ cao nhưng tách biệt về mặt không gian.
- Các khu trường học/dân cư phụ cận (Hyde Park): Mật độ vừa phải, thưa hơn trung tâm.

Nếu chọn $\varepsilon$ lớn (ví dụ $1.500\text{ m}$), DBSCAN sẽ gom cả dải trung tâm và dải dân cư phía bắc thành một khối khổng lồ, đồng thời làm đứt gãy các cụm mật độ trung bình như Midway vào cuối tuần. Nếu chọn $\varepsilon$ nhỏ (ví dụ $1.000\text{ m}$), vùng trung tâm bị vỡ vụn thành hàng chục cụm nhỏ và tỷ lệ nhiễu tăng vọt.

### 1.2. Nguyên lý Hoạt động của HDBSCAN
HDBSCAN giải quyết bài toán trên qua 5 bước toán học:
1. **Chuyển đổi không gian khoảng cách (Transforming the space):**  
   Xác định khoảng cách lõi (Core Distance) của điểm $p$ với tham số $k = min\_samples$:
   $$\text{core}_k(p) = d(p, N_k(p))$$
   Định nghĩa khoảng cách tiếp cận tương hỗ (Mutual Reachability Distance):
   $$d_{\text{mreach-}k}(a, b) = \max\{\text{core}_k(a), \text{core}_k(b), d(a, b)\}$$
   Khoảng cách này giúp đẩy các điểm nằm ở vùng thưa ra xa nhau hơn, trong khi vẫn giữ nguyên khoảng cách giữa các điểm ở vùng dày đặc.
2. **Xây dựng Cây khung nhỏ nhất (Minimum Spanning Tree - MST):**  
   Xây dựng đồ thị liên kết tối thiểu nối tất cả các điểm dựa trên trọng số $d_{\text{mreach-}k}$.
3. **Xây dựng Cây phân cấp (Cluster Hierarchy):**  
   Biến đổi MST thành cây phân cấp đơn liên kết (Single-linkage Dendrogram).
4. **Nén Cây phân cấp (Condensing the Tree):**  
   Duyệt từ gốc lên ngọn cây. Tại mỗi phân nhánh, nếu một nhánh con có số phần tử $< min\_cluster\_size$, nhánh đó bị coi là các điểm rơi rụng (points falling out), không tạo nhánh mới. Chỉ khi cả hai nhánh đều $\ge min\_cluster\_size$, một sự phân tách cụm thật sự mới được ghi nhận.
5. **Trích xuất Cụm ổn định (Extracting Stable Clusters):**  
   Với mỗi cụm $C$, độ bền vững (Cluster Stability / Persistence) được tính bằng tích phân của độ sâu $\lambda = 1 / d_{\text{mreach}}$:
   $$S(C) = \sum_{p \in C} (\lambda_{\text{drop}}(p) - \lambda_{\text{birth}}(C))$$
   Thuật toán chọn tập hợp các cụm tối đa hóa tổng độ bền vững (Excess of Mass - EOM).

---

## 2. KẾT QUẢ THỰC NGHIỆM VÀ HYPERPARAMETER TUNING

### 2.1. Khảo sát `min_cluster_size` và `min_samples`
- **Khảo sát `min_cluster_size`:** Giữ `min_samples = 10` cố định, thử nghiệm qua dải $[30, 50, 100, 200, 300, 500]$ trên lát cắt `WEEKDAY_AM` ($60.498$ dòng):
  - Khi $mcs = 30$: Thu được 14 cụm, xuất hiện nhiều micro-clusters cục bộ, Silhouette thấp ($0,62$).
  - Khi $mcs = 100$: Thu được 4 cụm lớn ổn định (Loop/Near North, O'Hare, Midway, Hyde Park), tỷ lệ nhiễu $10,8\%$, Silhouette đạt $0,78$, DBI đạt $0,19$.
  - Khi $mcs \ge 300$: Cụm Hyde Park bị gộp vào nhiễu, làm mất thông tin khu vực giáo dục phía nam.
- **Khảo sát `min_samples`:** Thử $ms \in [5, 10, 20, 50]$ với $mcs = 100$:
  - $ms = 5$: Quá lỏng lẻo, nhiễu chỉ $6,2\%$ nhưng cụm bị kéo dài.
  - $ms = 10$: Cân bằng hoàn hảo, Noise Ratio quanh $10\%$, ranh giới cụm chặt chẽ.
  - $ms \ge 20$: Quá bảo thủ, Noise Ratio tăng vọt lên $> 18\%$.

$\Rightarrow$ **Cấu hình chính thức chốt:** `min_cluster_size = 100`, `min_samples = 10`, `cluster_selection_method = 'eom'`.

---

## 3. BẢNG SO SÁNH CHỈ SỐ GIỮA 3 MÔ HÌNH TRÊN DỮ LIỆU `master_v1`

| Thuật toán | Lát cắt thời gian | Số điểm | Số cụm | Noise Ratio (%) | Coverage (%) | Cụm lớn nhất (%) | Silhouette | Davies-Bouldin | Runtime (s) | RAM thêm (MB) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **K-Means** ($K=5$) | WEEKDAY_AM | 60.498 | 5 | 0,0% | 100,0% | 62,3% | 0,733 | 0,445 | 0,12 s | 2,2 MB |
| | WEEKDAY_PM | 86.617 | 5 | 0,0% | 100,0% | 62,5% | 0,753 | 0,459 | 0,14 s | 2,7 MB |
| | WEEKEND | 120.571 | 5 | 0,0% | 100,0% | 52,7% | 0,726 | 0,477 | 0,16 s | 3,7 MB |
| **DBSCAN A** ($1\%, 1500\text{m}$) | WEEKDAY_AM | 60.498 | 4 | 12,6% | 87,4% | 68,9% | 0,741 | 0,220 | 0,04 s | 3,3 MB |
| | WEEKDAY_PM | 86.617 | 3 | 9,4% | 90,6% | 66,9% | 0,859 | 0,153 | 0,06 s | 2,7 MB |
| | WEEKEND | 120.571 | 4 | 9,9% | 90,1% | 62,1% | 0,825 | 0,159 | 0,07 s | 4,3 MB |
| **HDBSCAN** ($mcs=100, ms=10$) | WEEKDAY_AM | 60.498 | 4 | 10,8% | 89,2% | 65,4% | **0,782** | **0,192** | 9,4 s | 1.150 MB |
| | WEEKDAY_PM | 86.617 | 3 | 9,1% | 90,9% | 65,8% | **0,845** | **0,161** | 14,2 s | 1.620 MB |
| | WEEKEND | 120.571 | 3 | 8,9% | 91,1% | 61,4% | **0,812** | **0,174** | 22,6 s | 2.380 MB |

> **Ghi chú đánh giá khoa học:**
> - K-Means đạt Noise Ratio = 0% do thiết kế toán học ép mọi điểm vào tâm gần nhất, chứ không phải do mô hình nhận diện điểm tốt hơn.
> - HDBSCAN đạt chỉ số Davies-Bouldin vượt trội so với K-Means ($0,16 - 0,19$ so với $0,45 - 0,48$), chứng minh các cụm mật độ phân tách rõ ràng và không bị ép hình dạng lồi (convex spherical shape).

---

## 4. KẾT QUẢ PHÂN TÍCH DỊCH CHUYỂN HOTSPOT THEO THỜI GIAN

Dựa trên bảng `outputs/metrics/hotspot_tracking.csv` và bản đồ `outputs/maps/hdbscan_temporal_shift_map.html`:

1. **Hotspot Trung tâm (Loop - Near North Side):**
   - Sáng $\rightarrow$ Chiều: Tâm cụm dịch chuyển **$820\text{ m}$** về phía bắc (từ Loop sang Near North Side / Streeterville).
   - Tỷ trọng duy trì ổn định mức áp đảo: $65,4\%$ vào buổi sáng và $65,8\%$ vào buổi chiều.
2. **Hotspot Sân bay O'Hare (Khu vực 76):**
   - Vị trí tâm cụm cố định tuyệt đối (dịch chuyển $\Delta d < 120\text{ m}$).
   - Nhu cầu đón xe tăng vọt từ $11,5\%$ tổng số chuyến vào buổi sáng lên $16,8\%$ vào buổi chiều.
3. **Hotspot Sân bay Midway (Khu vực 56):**
   - Giữ vững tỷ trọng $4,2\% - 4,8\%$ ở cả 3 lát cắt.
   - Khoảng cách dịch chuyển $\Delta d < 180\text{ m}$.
4. **Hotspot Hyde Park (Khu vực 41):**
   - Xuất hiện rõ ràng nhất ở lát cắt `WEEKDAY_AM` ($611$ chuyến), phản ánh nhu cầu đón xe sáng sớm của sinh viên và cán bộ Đại học Chicago. Vào buổi chiều và cuối tuần, nhu cầu phân tán rộng ra các khu vực xung quanh và trở thành các điểm thưa.

---

## 5. BỘ CÂU HỎI VẤN ĐÁP DÀNH CHO THÀNH VIÊN 3 (DEFENSE Q&A PLAYBOOK)

### Câu Q7: HDBSCAN khác DBSCAN ở điểm cốt lõi nào? HDBSCAN có phải lúc nào cũng tốt hơn DBSCAN không?
*Trả lời (khoảng 30 giây):*
"Điểm cốt lõi là DBSCAN sử dụng một bán kính $\varepsilon$ cố định cho toàn bộ không gian, trong khi HDBSCAN xây dựng cây phân cấp mật độ dựa trên khoảng cách tiếp cận tương hỗ (mutual reachability distance) và lựa chọn các cụm có độ ổn định (stability) cao nhất qua nhiều mức mật độ khác nhau. Nhờ đó, HDBSCAN xử lý tốt các bộ dữ liệu có mật độ không đồng đều như giao thông Chicago. Tuy nhiên, HDBSCAN không phải lúc nào cũng tốt hơn: thuật toán có độ phức tạp tính toán và tiêu thụ bộ nhớ cao hơn nhiều so với DBSCAN, đồng thời không dễ áp dụng trọng số mẫu (`sample_weight`) như cách nhóm đã tối ưu cho DBSCAN."

### Câu Q8: Tham số `min_cluster_size` và `min_samples` có ý nghĩa gì? Vì sao phải cố định `min_samples` khi tune `min_cluster_size`?
*Trả lời (khoảng 30 giây):*
"`min_cluster_size` là quy mô tối thiểu để một nhánh trên cây phân cấp được công nhận là một cụm riêng biệt; tham số này phản ánh quy mô hotspot tối thiểu theo góc nhìn nghiệp vụ. Trong khi đó, `min_samples` kiểm soát mức độ bảo thủ của mật độ thông qua khoảng cách lõi (core distance). Trong thư viện `hdbscan`, nếu không đặt `min_samples` thì nó sẽ tự động nhận giá trị bằng `min_cluster_size`. Do đó, khi tăng `min_cluster_size`, mức độ bảo thủ cũng vô tình tăng theo khiến tỷ lệ nhiễu tăng vọt. Nhóm đã cố định tường minh `min_samples = 10` để tách biệt rạch ròi ảnh hưởng của hai tham số này theo đúng khuyến nghị trong tài liệu chính thức của HDBSCAN."

### Câu Q9: Silhouette cao nhất có đồng nghĩa với mô hình tốt nhất không? Nhóm xử lý điểm nhiễu khi tính metrics như thế nào?
*Trả lời (khoảng 30 giây):*
"Không. Silhouette Score được xây dựng dựa trên khoảng cách Euclidean đến tâm/điểm gần nhất và có xu hướng thiên vị các cụm hình cầu, dạng lồi. Đối với các mô hình mật độ như DBSCAN và HDBSCAN, nhóm chỉ tính Silhouette, Davies-Bouldin và Calinski-Harabasz trên các điểm đã được gán cụm (`clustered-only`), và bắt buộc phải báo cáo song song tỷ lệ nhiễu (Noise Ratio) cùng tỷ lệ bao phủ (Coverage). Việc chọn mô hình tối ưu không dựa vào một chỉ số đơn lẻ mà dựa trên sự cân bằng giữa chất lượng cụm, tỷ lệ nhiễu hợp lý, tính ổn định và khả năng diễn giải trên bản đồ địa lý."
