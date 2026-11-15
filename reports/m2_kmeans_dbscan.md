# Phần báo cáo của M2: K-Means và DBSCAN

Người viết: Chu Thành Tân (M2). Bản thảo Markdown để M4 ghép vào báo cáo Word (các chương 4, 5, 6).
Số liệu lấy từ **mẫu pilot tạm `pilot_m2_v0`** (1 tuần, 17–23/04/2023, 138.629 lượt đón, 219 toạ độ). Khi có dữ liệu chính thức của M1 thì chạy lại notebook và thay số.

Ký hiệu chung:
- Mỗi lượt đón $i$ có toạ độ $x_i \in \mathbb{R}^2$ (mét, hệ EPSG:26916).
- Vì toạ độ là tâm (centroid) của census tract nên rất nhiều lượt trùng toạ độ. Gọi $u_j$ là các toạ độ khác nhau và $w_j$ là số lượt đón tại $u_j$, với $\sum_j w_j = n$.
- Hai thuật toán đều chỉ dùng toạ độ $(x, y)$, không đưa giờ, quãng đường hay giá vào khoảng cách. Thời gian được dùng để tách 3 lát cắt chạy riêng: WEEKDAY_AM (T2–T6, 07:00–09:59), WEEKDAY_PM (T2–T6, 16:00–18:59), WEEKEND (T7–CN, cả ngày).

---

## 1. K-Means

### 1.1 Bài toán và hàm mục tiêu

K-Means chia $n$ điểm thành đúng $K$ cụm $C_1, \dots, C_K$, mỗi cụm có tâm $\mu_k$, sao cho tổng bình phương khoảng cách từ mỗi điểm tới tâm cụm của nó (SSE, hay *inertia*) là nhỏ nhất:

$$J = \sum_{k=1}^{K} \sum_{x_i \in C_k} \lVert x_i - \mu_k \rVert^2, \qquad \mu_k = \frac{1}{|C_k|}\sum_{x_i \in C_k} x_i .$$

**Dạng có trọng số.** Các lượt trùng toạ độ luôn có cùng khoảng cách tới mọi tâm, nên luôn rơi vào cùng một cụm. Gộp chúng lại thì hàm mục tiêu không đổi:

$$J = \sum_{j} w_j \lVert u_j - \mu_{c(j)} \rVert^2, \qquad \mu_k = \frac{\sum_{j \in C_k} w_j u_j}{\sum_{j \in C_k} w_j}.$$

Vì vậy nhóm fit K-Means trên khoảng 130–155 toạ độ duy nhất của mỗi lát cắt, với `sample_weight` = số lượt đón. Kết quả kiểm chứng ở mục 3.1–3.2 của log M2: nhãn của từng lượt đón giống hệt khi fit trên toàn bộ lượt (ARI = 1), inertia bằng nhau khi n_init đủ lớn.

### 1.2 Thuật toán Lloyd và khởi tạo k-means++

```
Đầu vào: điểm u_j, trọng số w_j, số cụm K, số lần khởi tạo n_init
Lặp n_init lần:
    Khởi tạo K tâm bằng k-means++:
        chọn tâm đầu tiên ngẫu nhiên (theo trọng số)
        mỗi tâm tiếp theo chọn với xác suất tỷ lệ w_j * D(u_j)^2,
        trong đó D là khoảng cách tới tâm gần nhất đã chọn
    Lặp tới khi tâm không đổi hoặc đạt max_iter:
        Gán:      c(j) = argmin_k ||u_j - mu_k||^2
        Cập nhật: mu_k = trung bình có trọng số của các u_j có c(j) = k
Trả về lần chạy có J nhỏ nhất
```

- Mỗi bước gán và cập nhật đều không làm J tăng, và số cách chia là hữu hạn, nên thuật toán luôn hội tụ. Nhưng nó chỉ hội tụ về **cực tiểu cục bộ**, nên phải chạy nhiều lần khởi tạo (`n_init`) rồi lấy lần tốt nhất.
- Độ phức tạp mỗi vòng lặp là $O(nKd)$; ở đây $d = 2$.
- Giả định ngầm: các cụm lồi, gần tròn, kích thước và độ phân tán tương đương nhau. K-Means không có khái niệm nhiễu: mọi điểm đều phải thuộc một cụm.

### 1.3 Chọn K

Thử K = 2..15, `k-means++`, max_iter = 300, seed = 42.

- **Elbow:** vẽ J theo K và tìm điểm mà J ngừng giảm mạnh ("khuỷu tay"). Điểm khuỷu được gợi ý bằng khoảng cách lớn nhất từ đường cong tới dây cung nối hai đầu.
- **Silhouette:** với điểm $i$, gọi $a(i)$ là khoảng cách trung bình tới các điểm cùng cụm, $b(i)$ là khoảng cách trung bình nhỏ nhất tới một cụm khác. Khi đó $s(i) = \dfrac{b(i) - a(i)}{\max\{a(i), b(i)\}} \in [-1, 1]$; càng gần 1 thì cụm càng tách biệt.
- **Davies–Bouldin (DBI):** $\frac{1}{K}\sum_k \max_{l \ne k} \frac{\sigma_k + \sigma_l}{d(\mu_k, \mu_l)}$, trong đó $\sigma_k$ là khoảng cách trung bình từ điểm tới tâm cụm $k$. Càng thấp càng tốt.
- **Calinski–Harabasz (CH):** tỷ số giữa độ phân tán giữa các cụm và độ phân tán trong cụm, có hiệu chỉnh theo bậc tự do. Càng cao càng tốt.

Kết quả trên mẫu pilot:

1. **Khuỷu Elbow nằm ở K = 5 ở cả 3 lát cắt.** Từ K = 5–6 trở đi, mỗi lần thêm một cụm chỉ giảm J khoảng 10–19%.
2. **Với n_init = 10 (giá trị trong spec), K-Means thường rơi vào cực tiểu cục bộ khi K ≥ 6**: J tệ hơn mức tốt nhất tới 7–13,6%, làm đường Elbow gồ ghề. Với n_init = 50 thì cách có trọng số và cách chạy trên từng lượt cho kết quả trùng nhau. Nhóm dùng **n_init = 50**.
3. Trong khoảng K ≥ 4, **K = 5 có Silhouette cao nhất và DBI thấp nhất ở cả 3 lát cắt**. K = 2 có chỉ số tốt hơn nhưng chỉ tách sân bay O'Hare khỏi phần còn lại, quá thô. CH tăng đều theo K nên không giúp chọn.
4. Bản đồ với K = 5 cho 5 vùng dễ diễn giải và gần như giống nhau ở cả 3 lát cắt.

**Chốt K = 5.**

### 1.4 Kết quả K-Means (K = 5)

| Lát cắt | Số lượt | Silhouette (theo lượt) | Silhouette (theo toạ độ) | DBI | Cụm lớn nhất | Thời gian fit |
|---|---|---|---|---|---|---|
| WEEKDAY_AM | 15.657 | 0,743 | 0,405 | 0,434 | 61,7% | 0,088 s |
| WEEKDAY_PM | 22.413 | 0,746 | 0,411 | 0,450 | 63,5% | 0,106 s |
| WEEKEND | 30.143 | 0,728 | 0,405 | 0,471 | 51,3% | 0,116 s |

| Cụm | Vùng | AM | PM | WEEKEND |
|---|---|---|---|---|
| 0 | Trung tâm (Loop, Near North) | 61,7% | 63,5% | 51,3% |
| 1 | Sân bay O'Hare | 17,2% | 20,1% | 25,1% |
| 2 | Phía bắc dọc hồ (Lake View) | 12,3% | 9,1% | 14,2% |
| 3 | Phía nam | 5,4% | 3,9% | 5,3% |
| 4 | Sân bay Midway | 3,3% | 3,4% | 4,1% |

Silhouette tính theo lượt (0,73–0,75) cao hơn nhiều so với tính theo toạ độ duy nhất (khoảng 0,41). Lý do: các lượt trùng toạ độ có khoảng cách 0 tới nhau, làm $a(i)$ rất nhỏ. Khi trình bày cần nêu cả hai con số.

---

## 2. DBSCAN

### 2.1 Các định nghĩa

Với bán kính $\varepsilon$ (eps) và ngưỡng `min_samples` (minPts):

- **Lân cận eps:** $N_\varepsilon(p) = \{q : d(p, q) \le \varepsilon\}$, gồm cả chính $p$.
- **Điểm lõi (core):** $p$ là core nếu $|N_\varepsilon(p)| \ge \text{minPts}$. Ở dạng có trọng số (scikit-learn), điều kiện là $\sum_{q \in N_\varepsilon(p)} w_q \ge \text{minPts}$.
- **Đạt tới trực tiếp theo mật độ:** $q$ đạt tới trực tiếp từ $p$ nếu $p$ là core và $q \in N_\varepsilon(p)$.
- **Đạt tới theo mật độ:** có một chuỗi điểm core $p = p_1, \dots, p_m$ nối liền nhau theo quan hệ trên và kết thúc ở $q$.
- **Liên thông theo mật độ:** $p$ và $q$ cùng đạt tới được từ một điểm core $o$.
- **Cụm:** tập liên thông theo mật độ, lớn nhất có thể. **Điểm biên (border)** thuộc cụm nhưng không phải core. **Nhiễu** là điểm không thuộc cụm nào, nhãn −1.

DBSCAN không cần biết trước số cụm, tìm được cụm có hình dạng bất kỳ (ví dụ dải dọc bờ hồ) và tự loại nhiễu. Nhược điểm là chỉ dùng **một** eps cho mọi vùng, nên khó xử lý khi các vùng có mật độ rất khác nhau.

### 2.2 Thuật toán

```
Đầu vào: điểm, eps, min_samples (và trọng số w nếu có)
Với mỗi điểm p: tìm N_eps(p) bằng cây tìm kiếm không gian
Đánh dấu p là core nếu tổng trọng số trong N_eps(p) >= min_samples
cum = 0
Với mỗi điểm core p chưa có nhãn:
    cum = cum + 1; gán nhãn cum cho p
    Mở rộng theo chiều rộng: với mỗi điểm q trong N_eps của một điểm core đã thuộc cụm,
        nếu q chưa có nhãn thì gán nhãn cum;
        nếu q cũng là core thì tiếp tục mở rộng từ q
Các điểm không có nhãn: nhiễu (-1)
```

- Độ phức tạp trung bình khoảng $O(n \log n)$ nhờ cây tìm kiếm. Trường hợp xấu nhất là $O(n^2)$ về thời gian.
- Bản cài đặt của scikit-learn lưu toàn bộ danh sách láng giềng, nên bộ nhớ có thể tới $O(n^2)$. Đây là rủi ro R01 trong spec.

### 2.3 Ba điều chỉnh so với spec (đã duyệt)

Số đo trên mẫu pilot cho thấy chạy đúng như spec sẽ không hợp với dữ liệu centroid:

1. **Fit trên toạ độ duy nhất với trọng số.** Các lượt trùng toạ độ có khoảng cách 0 nên luôn là láng giềng của nhau; tổng trọng số thay cho số điểm. Vì vậy kết quả tương đương chính xác với chạy trên từng lượt: trên dữ liệu thật, 9/9 lần thử có ARI = 1, cùng số cụm và cùng tập nhiễu. Cách chạy trên từng lượt tốn RAM tăng theo bình phương cỡ mẫu: khoảng 1 GB ở 30k lượt, ngoại suy 11–25 GB ở 100–150k lượt. Cách có trọng số nhanh hơn 13–55 lần và gần như không tốn RAM.
2. **`min_samples` theo tỷ lệ số lượt của lát cắt** (0,1 / 0,3 / 0,5 / 1%). Với 5–20 như spec, 97–99,8% lượt nằm ở toạ độ tự là core, nên DBSCAN gần như không lọc được nhiễu (Noise ≤ 3% ở mọi eps).
3. **eps 500–3000 m.** Các toạ độ cách nhau trung vị khoảng 0,9–1 km; với eps nhỏ hơn khoảng 300 m hầu như không toạ độ nào nối được với toạ độ khác.

### 2.4 Chọn eps và min_samples

- **k-distance có trọng số:** với mỗi toạ độ, là khoảng cách nhỏ nhất để gom đủ $k$ lượt (tính cả chính nó). Đây chính là ngưỡng eps để toạ độ đó trở thành core. Đã kiểm chứng: đặt eps bằng giá trị này thì toạ độ là core, giảm đi 1e-6 m thì không (0/80 sai).
- Trên dữ liệu centroid, đồ thị k-distance **không có một điểm gãy rõ ràng** mà tăng theo bậc thang. Các điểm gãy gợi ý chia thành 2 nhóm, khoảng 0,8–1,3 km và khoảng 2,6–3,8 km. Vì vậy eps phải chọn bằng **lưới tham số**.
- **Lưới:** 8 eps × 6 `min_samples` × 3 lát cắt = 144 cấu hình. Quan sát chính:
  - eps = 500 m cho Silhouette rất cao (0,82–0,85) nhưng đó là **kết quả giả**: gần như mỗi toạ độ thành một cụm riêng (17–96 cụm).
  - eps ≥ 2500 m gộp phần lớn thành phố thành một cụm (67–83%).
  - Vùng hợp lý là `min_samples` 0,5–1% với eps 1000–2000 m.
- **So sánh 4 ứng viên** trên bảng chỉ số và bản đồ, rồi chốt:
  - **Cấu hình chính B:** 1% số lượt, eps = 2000 m. Ổn định nhất: cùng 3 cụm ở cả 3 lát cắt, chỉ số tốt nhất (Silhouette trung bình 0,81, theo toạ độ 0,61, DBI 0,19).
  - **Cấu hình phụ C:** 0,5%, eps = 1000 m, dùng để minh hoạ độ nhạy của eps.

### 2.5 Kết quả DBSCAN

| Lát cắt | Cấu hình | min_samples | Số cụm | Noise | Silhouette (lượt / toạ độ) | DBI | Cụm lớn nhất | Fit |
|---|---|---|---|---|---|---|---|---|
| WEEKDAY_AM | B | 157 | 3 | 10,0% | 0,803 / 0,593 | 0,189 | 70,1% | 0,022 s |
| WEEKDAY_PM | B | 225 | 3 | 6,9% | 0,835 / 0,650 | 0,165 | 70,1% | 0,041 s |
| WEEKEND | B | 302 | 3 | 6,6% | 0,796 / 0,596 | 0,212 | 64,7% | 0,047 s |
| WEEKDAY_AM | C | 79 | 14 | 9,6% | 0,622 / 0,347 | 0,247 | 50,5% | 0,024 s |
| WEEKDAY_PM | C | 113 | 13 | 7,1% | 0,703 / 0,390 | 0,200 | 48,1% | 0,043 s |
| WEEKEND | C | 151 | 14 | 8,1% | 0,730 / 0,460 | 0,227 | 39,1% | 0,046 s |

3 cụm của cấu hình B, giống nhau ở cả 3 lát cắt:
1. Hành lang trung tâm và phía bắc dọc hồ: 64,7–70,1% số lượt.
2. Sân bay O'Hare: 16,9–24,9%, chỉ gồm 2 toạ độ, bán kính khoảng 0,4 km.
3. Sân bay Midway: 3,0–3,9%.

Phía nam và tây bắc là nhiễu.

---

## 3. So sánh K-Means và DBSCAN

**Đồng thuận** ở các vùng dày: trung tâm (97–99,6% số lượt trùng), O'Hare (98–99%), Midway (92–93,5%). ARI giữa K-Means và DBSCAN B là 0,68 / 0,80 / 0,68 (AM / PM / WEEKEND).

**Khác nhau** ở 3 vùng (có bản đồ phóng to):

| Vùng | K-Means | DBSCAN B | Diễn giải |
|---|---|---|---|
| Phía nam | Một cụm riêng (3,9–5,4%), bán kính rộng nhất (5,1–5,5 km) | 61–66% số lượt trong vùng là nhiễu | Vùng thưa. K-Means tạo "cụm" chỉ vì phải gán mọi điểm |
| O'Hare | Cụm rộng: 6–8 toạ độ, 1,0–1,3 km | Cụm chặt: 2 toạ độ, khoảng 0,4 km | DBSCAN cho ranh giới hotspot sân bay sát thực tế hơn |
| Phía bắc dọc hồ | Cụm riêng (9,1–14,2%) | Gộp vào dải trung tâm | DBSCAN theo được cụm hình dải, nhưng eps 2000 m gộp cả Loop với Lake View |

**Nhiễu của DBSCAN B chủ yếu là vùng thưa thật, không phải do eps quá nhỏ:**
- 70–72% toạ độ nhiễu cách toạ độ core gần nhất hơn 4 km (gấp đôi eps); trung vị hơn 5 km.
- Chỉ 5–9 toạ độ mỗi lát cắt nằm sát ngưỡng eps.
- Cấu hình C chỉ gán lại được 18–28% số lượt nhiễu vào cụm.
- Nhiễu cũng **không đồng nghĩa với bản ghi lỗi**: tỷ lệ cờ chất lượng của lượt nhiễu chỉ cao hơn chút ít, và phần lớn lượt nhiễu không có cờ nào.

| Tiêu chí | K-Means (K = 5) | DBSCAN B (1%, 2000 m) |
|---|---|---|
| Tham số phải chọn | K | eps, min_samples |
| Nhiễu | Không có (Noise = 0 theo thiết kế, không phải ưu điểm) | 6,6–10,0% |
| Hình dạng cụm | Lồi quanh tâm | Bất kỳ, theo mật độ |
| Độ nhạy tham số | Ổn định khi n_init đủ lớn | Rất nhạy với eps: B có 3 cụm, C có 13–14 cụm, ARI(B, C) chỉ 0,48–0,54 |
| Thời gian fit (có trọng số) | 0,09–0,12 s | 0,02–0,05 s |
| Hạn chế chính | Tạo cụm ở vùng thưa; cắt dải dọc hồ | Một eps cho mọi mật độ: gộp (eps lớn) hoặc vụn (eps nhỏ) |

Hạn chế "một eps cho mọi mật độ" là lý do để so sánh tiếp với HDBSCAN (phần của M3). HDBSCAN xét nhiều mức mật độ cùng lúc thay vì một eps cố định.

---

## 4. Lưu ý về đánh giá

- Silhouette, DBI và CH được tính **trên các lượt có cụm** (bỏ nhiễu) và luôn ghi kèm Noise Ratio và coverage, theo quy tắc của spec (mục 2.4).
- Ba chỉ số này vốn ưu ái cụm lồi và **bị đẩy lên rất mạnh** khi có nhiều lượt trùng toạ độ. Ví dụ: K-Means có Silhouette 0,74 theo lượt nhưng 0,41 theo toạ độ; DBSCAN eps 500 m có Silhouette 0,85 nhưng đó là cụm vụn. Vì vậy nhóm không chọn tham số chỉ theo một chỉ số, mà kết hợp với bảng chéo, bản đồ và phân tích nhiễu.
- Thời gian fit rất nhỏ vì chạy trên khoảng 150 toạ độ duy nhất. Khi so sánh thời gian với HDBSCAN (thư viện không hỗ trợ trọng số) phải ghi rõ mỗi thuật toán chạy trên đầu vào nào.

## 5. Hạn chế

1. Toạ độ là centroid của census tract hoặc community area, không phải GPS, nên hotspot ở đây là ở **mức khu vực**.
2. Thời gian trong dữ liệu đã làm tròn 15 phút. Các lát cắt dùng khung 3 giờ nên không bị ảnh hưởng.
3. Hotspot là vùng nhiều lượt đón taxi, **không phải điểm ùn tắc**: dữ liệu không có tốc độ hay lưu lượng xe.
4. Số liệu trên là của mẫu pilot 1 tuần, cần chạy lại trên dữ liệu chính thức.

## Tài liệu tham khảo

- J. MacQueen (1967). Some methods for classification and analysis of multivariate observations. *Proc. 5th Berkeley Symposium*.
- S. Lloyd (1982). Least squares quantization in PCM. *IEEE Trans. Information Theory*, 28(2).
- D. Arthur, S. Vassilvitskii (2007). k-means++: The advantages of careful seeding. *SODA*.
- M. Ester, H.-P. Kriegel, J. Sander, X. Xu (1996). A density-based algorithm for discovering clusters in large spatial databases with noise. *KDD*.
- E. Schubert, J. Sander, M. Ester, H.-P. Kriegel, X. Xu (2017). DBSCAN revisited, revisited. *ACM TODS*, 42(3).
- P. J. Rousseeuw (1987). Silhouettes: a graphical aid to the interpretation and validation of cluster analysis. *J. Comput. Appl. Math.*, 20.
- D. L. Davies, D. W. Bouldin (1979). A cluster separation measure. *IEEE TPAMI*, 1(2).
- T. Caliński, J. Harabasz (1974). A dendrite method for cluster analysis. *Communications in Statistics*, 3(1).
- scikit-learn: KMeans, DBSCAN, clustering evaluation (https://scikit-learn.org/stable/modules/clustering.html).
