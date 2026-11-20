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
Thực nghiệm khảo sát lưới tham số được thực thi trên lát cắt `WEEKDAY_AM` ($60.498$ dòng, $304$ toạ độ duy nhất) và lưu tại `outputs/metrics/`:
- **Khảo sát `min_cluster_size`:** Giữ `min_samples = 10` cố định (tránh thay đổi ngầm theo R05), khảo sát $mcs \in [50, 100, 200]$:
  - Khi $mcs = 50$: Thu được $89$ cụm, phân rã thành nhiều micro-clusters nhỏ lẻ, tỷ lệ nhiễu cực thấp $0,7\%$ ($416$ điểm), Silhouette $0,991$, DBI $0,225$.
  - Khi $mcs = 100$: Thu được $67$ cụm, loại bỏ các điểm gom quá nhỏ, bảo toàn các điểm đón khách thực chất, tỷ lệ nhiễu $2,1\%$ ($1.275$ điểm), Silhouette $0,981$, DBI $0,288$, thời gian fit $32,9\text{ s}$.
  - Khi $mcs = 200$: Thu được $51$ cụm, tỷ lệ nhiễu tăng lên $3,1\%$ ($1.863$ điểm), nhiều cụm nhỏ bị loại bỏ, Silhouette $0,954$, DBI $0,344$.
- **Khảo sát `min_samples`:** Cố định $mcs = 100$, khảo sát $ms \in [5, 10, 20]$:
  - $ms = 5$: $67$ cụm, nhiễu $2,10\%$ ($1.272$ điểm), Silhouette $0,980$, DBI $0,288$.
  - $ms = 10$: $67$ cụm, nhiễu $2,11\%$ ($1.275$ điểm), Silhouette $0,981$, DBI $0,288$.
  - $ms = 20$: $67$ cụm, nhiễu $2,13\%$ ($1.287$ điểm), Silhouette $0,981$, DBI $0,288$.
  - *Nhận xét:* Do tính chất toạ độ centroid Chicago có mật độ chuyến rất tập trung tại các toạ độ đông khách, biến thiên $ms$ từ 5 đến 20 ảnh hưởng rất ít đến số cụm và tỷ lệ nhiễu.

$\Rightarrow$ **Cấu hình chính thức chốt:** `min_cluster_size = 100`, `min_samples = 10`, `cluster_selection_method = 'eom'`.

---

## 3. BẢNG SO SÁNH CHỈ SỐ GIỮA 3 MÔ HÌNH TRÊN DỮ LIỆU `master_v1`

*(Dữ liệu trích xuất chính thức từ `outputs/metrics/baseline_metrics.csv` và `outputs/metrics/hdbscan_metrics.csv`)*

| Thuật toán | Lát cắt thời gian | Số điểm ($N$) | Số cụm | Noise Ratio (%) | Coverage (%) | Cụm lớn nhất (%) | Silhouette | Davies-Bouldin | Runtime (s) | RAM thêm (MB) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **K-Means** ($K=5$) | WEEKDAY_AM | 60.498 | 5 | 0,0% | 100,0% | 62,3% | 0,733 | 0,445 | 0,12 s* | 2,2 MB |
| | WEEKDAY_PM | 86.617 | 5 | 0,0% | 100,0% | 62,5% | 0,753 | 0,459 | 0,14 s* | 2,7 MB |
| | WEEKEND | 120.571 | 5 | 0,0% | 100,0% | 52,7% | 0,726 | 0,477 | 0,16 s* | 3,7 MB |
| **DBSCAN A** ($1\%, 1500\text{m}$) | WEEKDAY_AM | 60.498 | 4 | 12,6% | 87,4% | 68,9% | 0,741 | 0,220 | 0,04 s* | 3,3 MB |
| | WEEKDAY_PM | 86.617 | 3 | 9,4% | 90,6% | 66,9% | 0,859 | 0,153 | 0,06 s* | 2,7 MB |
| | WEEKEND | 120.571 | 4 | 9,9% | 90,1% | 62,1% | 0,825 | 0,159 | 0,07 s* | 4,3 MB |
| **HDBSCAN** ($mcs=100, ms=10$) | WEEKDAY_AM | 60.498 | 67 | 2,1% | 97,9% | 10,6% | **0,981** | **0,288** | 18,13 s** | 14,2 MB |
| | WEEKDAY_PM | 86.617 | 63 | 2,3% | 97,7% | 12,8% | **0,990** | **0,180** | 57,15 s** | 17,9 MB |
| | WEEKEND | 120.571 | 78 | 0,9% | 99,1% | 12,6% | **0,991** | **0,269** | 72,68 s** | 23,3 MB |

> ### Các Lưu ý Phương pháp luận & Phân tích Tính Hợp lệ (Methodological Caveats):
> 1. **Khác biệt cách fit và Runtime (* vs **):** 
>    - K-Means và DBSCAN được fit có trọng số (`sample_weight`) trên đúng 304 toạ độ duy nhất ($N_{\text{fit}} = 304$), chạy trên môi trường Python 3.10.6 nên thời gian chỉ mất $0,04 - 0,16\text{ s}$.
>    - HDBSCAN dựng cây khoảng cách tiếp cận tương hỗ (mutual reachability MST) trên toàn bộ tập điểm rời rạc ($N_{\text{fit}} = 60.498 - 120.571$), chạy trên môi trường Python 3.11.9 (Windows) nên thời gian từ $18,1\text{ s}$ đến $72,7\text{ s}$. Vì vậy, sự chênh lệch thời gian phản ánh số điểm đầu vào của mô hình ($N=304$ vs $N \approx 10^5$), không so sánh trực tiếp hiệu năng ngang hàng.
> 2. **Hiện tượng Silhouette bị thổi phồng (0,98 - 0,99) do bán kính cụm bằng 0:**
>    - Trong dữ liệu taxi Chicago, toạ độ đã bị làm mờ về tâm của census tract/khu vực (chỉ có 304 toạ độ).
>    - Thống kê từ `hdbscan_clusters_master_v1.csv` cho thấy có **62,7% số cụm ở AM (42/67 cụm)** có bán kính nội cụm $RMS = 0\text{ m}$ (chỉ gồm duy nhất một toạ độ centroid có $\ge 100$ lượt đón).
>    - Với các điểm trong cụm bán kính 0, khoảng cách nội cụm $a(i) = 0$, dẫn đến điểm Silhouette cục bộ $s(i) = \frac{b(i) - 0}{\max(a(i), b(i))} = 1,0$. Hiện tượng nén toạ độ này đã kéo Silhouette trung bình của HDBSCAN lên mức $0,98 - 0,99$. Đây là hạn chế về độ phân giải của dữ liệu (Spatial Coarsening), cần giải trình rõ khi bảo vệ đồ án.
> 3. **Lưu ý nghiệp vụ bắt buộc:**
>    - *Toạ độ đón xe là toạ độ centroid khu vực hành chính (không phải vị trí GPS chính xác của xe).*
>    - *Hotspot thể hiện điểm tập trung nhu cầu đón xe (pickup demand), không phải điểm ùn tắc giao thông.*

---

## 4. KẾT QUẢ PHÂN TÍCH DỊCH CHUYỂN HOTSPOT THEO THỜI GIAN

*(Dữ liệu chính thức từ `outputs/metrics/hotspot_tracking.csv` và `hdbscan_clusters_master_v1.csv`)*

Thuật toán ghép cặp cụm (Hungarian Matching với ngưỡng $\le 3.500\text{ m}$) đã ghép thành công **229 cặp chuyển tiếp**. 

### 4.1. Bản chất của hiện tượng "Dịch chuyển 0 m":
Trong bảng `hotspot_tracking.csv`, có **53,8% cặp ghép (105/195 cặp MATCHED)** có khoảng cách dịch chuyển $\Delta d = 0\text{ m}$.  
Điều này xảy ra do tâm cụm của cả hai lát cắt đều neo tại cùng một toạ độ centroid hành chính cố định. **Khoảng cách $0\text{ m}$ không có nghĩa nhu cầu đứng yên**, mà thể hiện vị trí hạ tầng đón khách cố định (như nhà ga sân bay, toà cao ốc), trong khi sự biến động dịch chuyển thể hiện qua **sự tăng/giảm số chuyến ($\Delta\text{trips}$) và tỷ trọng thị phần ($\Delta\text{share}$)**.

### 4.2. Phân tích Chi tiết Các Vùng Trọng Điểm:
1. **Cụm Sân bay Quốc tế O'Hare (Khu vực 76):**
   - Được HDBSCAN nhận diện qua 2 cụm nhà ga lớn (Cụm 0 và Cụm 4 ở AM; Cụm 0 và Cụm 2 ở PM/Weekend).
   - Tâm cụm cố định tuyệt đối tại vị trí nhà ga ($\Delta d = 0\text{ m}$).
   - **Tỷ trọng nhu cầu tăng vọt theo thời gian:**
     - Buổi sáng (`WEEKDAY_AM`): $15,7\%$ tổng nhu cầu ($9.469$ chuyến: Cụm 0 chiếm $10,6\%$, Cụm 4 chiếm $5,1\%$).
     - Buổi chiều (`WEEKDAY_PM`): Tăng lên **$20,4\%$** ($17.690$ chuyến: Cụm 0 chiếm $12,8\%$, Cụm 2 chiếm $7,7\%$).
     - Cuối tuần (`WEEKEND`): Chiếm tới **$24,2\%$** ($29.137$ chuyến: Cụm 0 chiếm $12,6\%$, Cụm 2 chiếm $11,5\%$).
   - *Ý nghĩa nghiệp vụ:* Nhu cầu hạ cánh và đón taxi từ sân bay về thành phố dồn dập vào chiều tối và dịp cuối tuần.

2. **Khu vực Công sở Loop (Khu vực 32):**
   - Tập trung nhiều cụm tài chính văn phòng (Cụm 2, 5, 10 ở AM; Cụm 1, 4, 5 ở PM).
   - Tổng tỷ trọng đón khách tăng từ **$15,3\%$ (sáng)** lên **$19,7\%$ (chiều)** do làn sóng nhân viên công sở tan làm đón xe.

3. **Khu vực Near West Side (Khu vực 28 - Bệnh viện UIC & Công sở phía Tây):**
   - Biến động mạnh nhất về sụt giảm thị phần: Cụm 1 ở AM chiếm **$9,71\%$** ($5.874$ chuyến), nhưng sang PM ghép với Cụm 9 chỉ còn **$3,06\%$** ($2.651$ chuyến), giảm sâu **$-6,65\%$ điểm thị phần**. Phản ánh đặc thù hành khách đến khám bệnh và làm việc buổi sáng, giảm mạnh vào chiều.

4. **Khu vực Giải trí Near North Side (Khu vực 8 - River North & Michigan Ave):**
   - Ngày thường duy trì ổn định $11,9\% - 13,2\%$, nhưng bùng nổ vào cuối tuần (`WEEKEND`): riêng Cụm 1 đã đạt **$12,0\%$** ($14.454$ chuyến), trở thành tâm điểm vui chơi, ăn uống lớn nhất thành phố.

5. **Khu vực Giáo dục Hyde Park (Khu vực 41 - Đại học Chicago):**
   - Ở lát cắt `WEEKDAY_AM`: HDBSCAN phát hiện Cụm 29 ($351$ chuyến, $0,58\%$, bán kính $RMS = 117\text{ m}$).
   - Ở lát cắt `WEEKDAY_PM`: Cụm 27 ($607$ chuyến, $0,70\%$, bán kính $RMS = 338\text{ m}$).
   - Cuối tuần (`WEEKEND`): Tách thành Cụm 30 ($629$ chuyến) và Cụm 74 ($119$ chuyến).
   - *(Đính chính: Con số "611 chuyến, 1,0%" là của cụm DBSCAN M2, không phải của HDBSCAN).*

6. **Các cụm dịch chuyển không gian thực sự ($\Delta d > 0$):**
   - Xuất hiện ở các khu vực có nhiều toạ độ lân cận: Cụm 6 $\rightarrow$ Cụm 10 ở Lake View dịch chuyển $83\text{ m}$, Cụm 28 ở Grand Boulevard dịch chuyển $194\text{ m}$, Cụm 29 ở Hyde Park dịch chuyển $119\text{ m}$, Cụm 44 ở Lake View dịch chuyển $1.441\text{ m}$.

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

### Câu Q10: Vì sao Silhouette của HDBSCAN lên tới 0,98 - 0,99 và hơn 50% cặp cụm có khoảng cách dịch chuyển 0 m?
*Trả lời (khoảng 30 giây):*
"Đây là hệ quả trực tiếp từ đặc thù làm mờ dữ liệu (anonymization) của cổng dữ liệu mở Chicago: hơn 535.000 chuyến đi được nén về đúng 304 toạ độ tâm khu vực hành chính (centroid). Khi HDBSCAN phân cụm với $mcs = 100$, có tới 62,7% số cụm chỉ gồm duy nhất một toạ độ centroid có trên 100 chuyến (bán kính nội cụm bằng 0). Khi khoảng cách nội cụm $a(i) = 0$, công thức toán học sẽ cho điểm Silhouette $s(i) = 1,0$, kéo trung bình lên 0,98 - 0,99. Tương tự, 53,8% cặp ghép có dịch chuyển $\Delta d = 0\text{ m}$ vì tâm cụm cố định tại cùng toạ độ centroid; sự dịch chuyển ở đây không phải di chuyển toạ độ địa lý mà thể hiện qua sự thay đổi mạnh mẽ về số chuyến và tỷ trọng thị phần nhu cầu."
