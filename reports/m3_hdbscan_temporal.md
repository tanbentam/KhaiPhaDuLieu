# BÁO CÁO KỸ THUẬT VÀ TƯ LIỆU THUYẾT TRÌNH (PHẦN M3)
## Chuyên đề: Phân Cụm Mật Độ Phân Cấp HDBSCAN & Phân Tích Dịch Chuyển Hotspot Theo Lát Cắt Thời Gian

- **Người thực hiện:** Thành viên 3 (M3 – Hoàng Tuấn Bảo - Advanced Modeling & Temporal Lead)
- **Người phối hợp / Reviewer:** M2 (Baseline Review), M4 (Visualization & Report Editor)
- **Nhánh làm việc:** `m3/hdbscan-temporal`
- **Bộ dữ liệu chính thức:** `master_v1` (535.167 dòng, CRS `EPSG:26916`, 304 toạ độ centroid)

> **Trạng thái bàn giao:** Các số liệu HDBSCAN trong artifacts hiện có chưa được xác nhận bằng backend sau rà soát. Log cũ ghi version package nhưng không xác định backend import thực tế; bảng tuning cũng chưa có persistence. Mã nguồn hiện yêu cầu package `hdbscan` và dừng rõ ràng nếu không nạp được backend hoặc thiếu stability outputs. Trước khi M4 dùng số liệu như kết quả cuối, cần chạy `python -m src.models.benchmark_hdbscan`, `python -m src.models.run_hdbscan` và `python -m src.evaluation.run_temporal_comparison` trong môi trường đã kiểm tra được.

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
Artifacts hiện có khảo sát lưới tham số trên lát cắt `WEEKDAY_AM` (khung giờ 07:00–09:59, $60.498$ dòng, $304$ toạ độ duy nhất) và lưu tại `outputs/metrics/`. Kết quả dưới đây cần được tái sinh sau khi xác nhận backend:
- **Khảo sát `min_cluster_size`:** Giữ `min_samples = 10` cố định (tránh thay đổi ngầm theo R05), khảo sát $mcs \in [50, 100, 200]$:
  - Khi $mcs = 50$: Thu được $89$ cụm, phân rã thành nhiều micro-clusters nhỏ lẻ, tỷ lệ nhiễu cực thấp $0,7\%$ ($416$ điểm), Silhouette $0,991$, DBI $0,225$.
  - Khi $mcs = 100$: Thu được $67$ cụm, loại bỏ các điểm gom quá nhỏ, bảo toàn các điểm đón khách thực chất, tỷ lệ nhiễu $2,1\%$ ($1.275$ điểm), Silhouette $0,981$, DBI $0,288$, thời gian fit ghi nhận ở bước tuning là $32,9\text{ s}$ (lúc chạy chính thức là $18,1\text{ s}$ do dao động tải hệ thống/bộ đệm CPU).
  - Khi $mcs = 200$: Thu được $51$ cụm, tỷ lệ nhiễu tăng lên $3,1\%$ ($1.863$ điểm), nhiều cụm nhỏ bị loại bỏ, Silhouette $0,954$, DBI $0,344$.
- **Khảo sát `min_samples`:** Cố định $mcs = 100$, khảo sát $ms \in [5, 10, 20]$:
  - $ms = 5$: $67$ cụm, nhiễu $2,10\%$ ($1.272$ điểm), Silhouette $0,980$, DBI $0,288$.
  - $ms = 10$: $67$ cụm, nhiễu $2,11\%$ ($1.275$ điểm), Silhouette $0,981$, DBI $0,288$.
  - $ms = 20$: $67$ cụm, nhiễu $2,13\%$ ($1.287$ điểm), Silhouette $0,981$, DBI $0,288$.
  - *Nhận xét:* Do tính chất toạ độ centroid Chicago có mật độ chuyến rất tập trung tại các toạ độ đông khách, biến thiên $ms$ từ 5 đến 20 ảnh hưởng rất ít đến số cụm và tỷ lệ nhiễu.

$\Rightarrow$ **Cấu hình chính thức chốt:** `min_cluster_size = 100`, `min_samples = 10`, `cluster_selection_method = 'eom'`.

Script và notebook hiện lấy dải tuning/cấu hình cuối từ `config/experiment.yaml`; lần chạy kế tiếp sẽ dùng đủ dải đã khai báo trong config.

---

## 3. BẢNG SO SÁNH CHỈ SỐ GIỮA 3 MÔ HÌNH TRÊN DỮ LIỆU `master_v1`

*(Các con số HDBSCAN dưới đây được trích từ artifacts hiện có; xem trạng thái bàn giao ở đầu báo cáo và không coi là kết quả cuối trước khi chạy lại backend đã xác nhận.)*

| Thuật toán | Lát cắt thời gian | Số điểm ($N$) | Số cụm | Noise Ratio (%) | Coverage (%) | Cụm lớn nhất (%) | Silhouette | Davies-Bouldin | Runtime (s) | RAM thêm (MB) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **K-Means** ($K=5$) | WEEKDAY_AM (07:00–09:59) | 60.498 | 5 | 0,0% | 100,0% | 62,3% | 0,733 | 0,445 | 0,12 s* | 2,2 MB |
| | WEEKDAY_PM (16:00–18:59) | 86.617 | 5 | 0,0% | 100,0% | 62,5% | 0,753 | 0,459 | 0,14 s* | 2,7 MB |
| | WEEKEND (cả ngày) | 120.571 | 5 | 0,0% | 100,0% | 52,7% | 0,726 | 0,477 | 0,16 s* | 3,7 MB |
| **DBSCAN A** ($1\%, 1500\text{m}$) | WEEKDAY_AM (07:00–09:59) | 60.498 | 4 | 12,6% | 87,4% | 68,9% | 0,741 | 0,220 | 0,04 s* | 3,3 MB |
| | WEEKDAY_PM (16:00–18:59) | 86.617 | 3 | 9,4% | 90,6% | 66,9% | 0,859 | 0,153 | 0,06 s* | 2,7 MB |
| | WEEKEND (cả ngày) | 120.571 | 4 | 9,9% | 90,1% | 62,1% | 0,825 | 0,159 | 0,07 s* | 4,3 MB |
| **HDBSCAN** ($mcs=100, ms=10$) | WEEKDAY_AM (07:00–09:59) | 60.498 | 67 | 2,1% | 97,9% | 10,6% | **0,981** | **0,288** | 18,13 s** | 14,2 MB |
| | WEEKDAY_PM (16:00–18:59) | 86.617 | 63 | 2,3% | 97,7% | 12,8% | **0,990** | **0,180** | 57,15 s** | 17,9 MB |
| | WEEKEND (cả ngày) | 120.571 | 78 | 0,9% | 99,1% | 12,6% | **0,991** | **0,269** | 72,68 s** | 23,3 MB |

> ### Các Lưu ý Phương pháp luận & Phân tích Tính Hợp lệ (Methodological Caveats):
> 1. **Khác biệt cách fit và Dao động Runtime (* vs **):** 
>    - K-Means và DBSCAN được fit có trọng số (`sample_weight`) trên đúng 304 toạ độ duy nhất ($N_{\text{fit}} = 304$), chạy trên môi trường Python 3.10.6 nên thời gian chỉ mất $0,04 - 0,16\text{ s}$.
>    - HDBSCAN dựng cây khoảng cách tiếp cận tương hỗ (mutual reachability MST) trên toàn bộ tập điểm rời rạc ($N_{\text{fit}} = 60.498 - 120.571$), chạy trên môi trường Python 3.11.9 (Windows) nên thời gian từ $18,1\text{ s}$ đến $72,7\text{ s}$.
>    - *Dao động runtime:* Ngay trong HDBSCAN với cùng tham số $mcs=100, ms=10$ trên `WEEKDAY_AM`, runtime có sự dao động tự nhiên từ $18,1\text{ s}$ (lần fit chính thức) đến $32,9\text{ s}$ (lần quét lưới), phản ánh mức độ chiếm dụng CPU/thread tại thời điểm chạy. Vì vậy, các con số runtime chỉ có giá trị tham khảo định lượng, không thể dùng để so sánh trực tiếp hiệu năng ngang hàng giữa các thuật toán.
> 2. **Hiện tượng Silhouette và Davies-Bouldin bị ảnh hưởng bởi cụm bán kính 0:**
>    - Trong dữ liệu taxi Chicago, toạ độ đã bị làm mờ về tâm của census tract/khu vực (304 toạ độ duy nhất).
>    - Thống kê chính xác từ `hdbscan_clusters_master_v1.csv` cho thấy tỷ lệ cụm đơn toạ độ (bán kính nội cụm $RMS \approx 0\text{ m}$) chiếm tỷ trọng áp đảo:
>      - `WEEKDAY_AM`: **39/67 cụm = 58,2%**
>      - `WEEKDAY_PM`: **41/63 cụm = 65,1%**
>      - `WEEKEND`: **51/78 cụm = 65,4%**
>      - Toàn bộ 3 lát cắt: **131/208 cụm = 63,0%**
>    - *Ảnh hưởng tới chỉ số nội tại:* 
>      - **Silhouette:** Khi khoảng cách nội cụm $a(i) = 0$, điểm Silhouette từng điểm đạt $s(i) = \frac{b(i)-0}{\max(a(i),b(i))} = 1,0$, kéo Silhouette trung bình lên $0,98 - 0,99$.
>      - **Davies-Bouldin Index (DBI):** Độ phân tán nội cụm $s_i \approx 0$ khiến tử số $s_i + s_j$ trong công thức $R_{ij} = \frac{s_i + s_j}{d(c_i, c_j)}$ bị thu hẹp đáng kể, từ đó kéo chỉ số DBI xuống thấp nhân tạo ($0,18 - 0,29$). Do đó, DBI thấp không hoàn toàn phản ánh thuật toán "vượt trội", mà là hệ quả từ hiện tượng nén toạ độ của dữ liệu (Spatial Coarsening).
> 3. **Lưu ý nghiệp vụ bắt buộc:**
>    - *Toạ độ đón xe là toạ độ centroid khu vực hành chính (không phải vị trí GPS chính xác của xe).*
>    - *Hotspot thể hiện điểm tập trung nhu cầu đón xe (pickup demand), không phải điểm ùn tắc giao thông.*

> **Lưu ý so sánh:** M2 fit K-Means/DBSCAN trên 304 tọa độ có trọng số; HDBSCAN fit trên từng dòng chuyến vì implementation không nhận `sample_weight`. Đây là khác biệt về biểu diễn lúc fit. Không so sánh trực tiếp runtime; khi diễn giải metrics phải giữ caveat này và nêu rõ số điểm dùng để tính metrics.

---

## 4. KẾT QUẢ PHÂN TÍCH DỊCH CHUYỂN HOTSPOT THEO THỜI GIAN

*(Tracking hiện có được tạo từ artifacts HDBSCAN trước khi xác nhận backend; cần tái sinh cùng với nhãn/cụm trước khi M4 chốt các cặp và cluster ID.)*

Các tổng lượt theo `pickup_community_area` dưới đây được tính trực tiếp trên dữ liệu nguồn M1, bao gồm cả lượt bị gán noise. Chúng không đồng nghĩa với tổng kích thước các cụm có `top_community_area` tương ứng.

Thuật toán ghép cặp theo tâm gần nhất (Nearest Centroid Matching với ngưỡng tối đa $\le 3.500\text{ m}$) tạo ra **229 dòng phân tích**:
- **195 cặp MATCHED:** ghép thành công giữa các cụm tương đồng vị trí. Do thuật toán ghép tham lam (không ràng buộc một-một), có 4 cụm đích nhận ghép từ nhiều cụm nguồn lân cận.
- **32 cụm EMERGING:** cụm mới xuất hiện ở lát cắt sau mà không có cụm nguồn tương ứng trong phạm vi $\le 3.500\text{ m}$.
- **2 cụm DISSOLVED:** cụm ở lát cắt trước tiêu biến, không tìm thấy cụm đích tiếp nối.

### 4.1. Bản chất của hiện tượng "Dịch chuyển 0 m":
Trong số 195 cặp MATCHED, có **105 cặp (53,8%)** có khoảng cách dịch chuyển tâm $\Delta d = 0\text{ m}$.  
Điều này xảy ra do tâm cụm của cả hai lát cắt đều neo tại cùng một toạ độ centroid cố định. **Khoảng cách $0\text{ m}$ không có nghĩa nhu cầu đứng yên**, mà thể hiện vị trí hạ tầng đón khách cố định (như nhà ga sân bay, toà cao ốc), trong khi sự biến động dịch chuyển thể hiện qua **sự tăng/giảm số chuyến ($\Delta\text{trips}$) và tỷ trọng thị phần ($\Delta\text{share}$)**.

### 4.2. Phân tích Chi tiết Các Khu Vực Trọng Điểm:
*(Lưu ý: Các diễn giải về "bệnh viện UIC", "nhân viên tan làm", "nhà ga sân bay" là các giả thuyết suy luận bối cảnh đô thị, không phải thuộc tính trực tiếp ghi nhận trong dữ liệu).*

1. **Cụm Sân bay Quốc tế O'Hare (Khu vực 76):**
   - Được HDBSCAN nhận diện qua 2 cụm lớn (Cụm 0 và Cụm 4 ở AM; Cụm 0 và Cụm 2 ở PM/Weekend), tâm cố định $\Delta d = 0\text{ m}$.
   - **Tỷ trọng nhu cầu tăng theo thời gian:**
     - Buổi sáng (`WEEKDAY_AM`): $15,7\%$ tổng lượt trong lát cắt ($9.469$ chuyến).
     - Buổi chiều (`WEEKDAY_PM`): **$20,4\%$** ($17.693$ chuyến).
     - Cuối tuần (`WEEKEND`): **$24,2\%** ($29.137$ chuyến).
   - Số lượt ở trên lấy trực tiếp từ `pickup_community_area=76`; không phụ thuộc vào cluster ID. Kích thước/ID cụm sẽ được cập nhật từ artifacts sau lần chạy đã xác nhận backend.

2. **Khu vực Trung tâm Loop (Khu vực 32):**
   - Tổng lượt theo `pickup_community_area=32` là **$17,98\%$** ($10.875$ chuyến) ở AM, **$22,53\%$** ($19.516$ chuyến) ở PM và **$13,54\%$** ($16.328$ chuyến) vào cuối tuần. Đây là tổng theo vùng từ dữ liệu nguồn, không phải phép cộng theo `top_community_area` của các cluster.

3. **Khu vực Near West Side (Khu vực 28):**
   - Thể hiện sự sụt giảm thị phần lớn nhất trong chuyển tiếp sáng $\rightarrow$ chiều: Cụm 1 ở AM chiếm **$9,71\%$** ($5.874$ chuyến), sang PM ghép với Cụm 9 chỉ còn **$3,06\%$** ($2.650$ chuyến), giảm sâu **$-6,65\%$ điểm thị phần**. 
   - *Lưu ý:* Mức giảm $-6,65\%$ điểm là lớn nhất ở chuyển tiếp ngày thường (AM $\rightarrow$ PM). Ở chuyển tiếp sáng $\rightarrow$ cuối tuần (AM $\rightarrow$ Weekend), Cụm 1 sang Cụm 16 còn sụt giảm mạnh hơn: **$-8,15\%$ điểm** (từ $9,71\%$ xuống $1,56\%$).

4. **Khu vực Near North Side (Khu vực 8):**
   - Tổng lượt theo `pickup_community_area=8` là **$19,18\%$** ($11.604$ chuyến) ở AM, **$22,93\%$** ($19.857$ chuyến) ở PM và **$23,48\%$** ($28.312$ chuyến) vào cuối tuần.
   - Kích thước cụm cuối tuần nêu trong artifacts hiện có cần được xác nhận lại sau lần chạy backend đã xác nhận; không suy ra tổng lượt toàn khu vực từ một cluster hoặc từ `top_community_area`.

5. **Sân bay Midway (Khu vực 56):**
   - Tương tự DBSCAN, HDBSCAN cũng phân tách khu vực Midway thành **2 cụm riêng biệt** (ở AM là Cụm 15 & 22; PM là Cụm 13 & 20; Cuối tuần là Cụm 10 & 17) do khoảng cách giữa 2 toạ độ điểm đón.
   - Tổng lượt theo `pickup_community_area=56` là **$2,71\%$** ($1.637$ chuyến) ở AM $\rightarrow$ **$3,29\%$** ($2.850$ chuyến) ở PM $\rightarrow$ **$3,80\%$** ($4.576$ chuyến) vào cuối tuần. Đây là số liệu vùng từ dữ liệu nguồn; số lượt trong các cụm đại diện khu vực có thể khác do noise/cách gán cụm.

6. **Khu vực Hyde Park (Khu vực 41):**
   - Ở `WEEKDAY_AM`: HDBSCAN phát hiện Cụm 29 ($351$ chuyến, $0,58\%$, bán kính $RMS = 117\text{ m}$).
   - Ở `WEEKDAY_PM`: Cụm 27 ($607$ chuyến, $0,70\%$, bán kính $RMS = 338\text{ m}$).
   - Dữ liệu nguồn có $750$ lượt thuộc `pickup_community_area=41` vào cuối tuần. Các cluster ID/kích thước từng cụm trong artifacts hiện có cần được xác nhận lại sau lần chạy backend đã xác nhận.

7. **Các cụm dịch chuyển không gian thực sự ($\Delta d > 0$):**
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
"Đây là hệ quả trực tiếp từ đặc thù làm mờ dữ liệu (anonymization) của cổng dữ liệu mở Chicago: hơn 535.000 chuyến đi được nén về đúng 304 toạ độ tâm khu vực hành chính (centroid). Khi HDBSCAN phân cụm với $mcs = 100$, có tới 58,2% cụm ở AM và 63,0% tổng số cụm trên cả 3 lát cắt chỉ gồm duy nhất một toạ độ centroid (bán kính nội cụm bằng 0). Khi khoảng cách nội cụm $a(i) = 0$, công thức toán học sẽ cho điểm Silhouette $s(i) = 1,0$, đồng thời kéo chỉ số Davies-Bouldin xuống thấp. Tương tự, 53,8% cặp ghép (105/195 cặp MATCHED) có dịch chuyển $\Delta d = 0\text{ m}$ vì tâm cụm cố định tại cùng toạ độ centroid; sự dịch chuyển ở đây thể hiện qua sự thay đổi mạnh mẽ về số chuyến và tỷ trọng thị phần nhu cầu."
