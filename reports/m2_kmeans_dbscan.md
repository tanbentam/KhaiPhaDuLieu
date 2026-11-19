# Phần báo cáo của M2: K-Means và DBSCAN

Người viết: Chu Thành Tân (M2). Bản thảo Markdown để M4 ghép vào báo cáo Word (các chương 4, 5, 6).
Số liệu lấy từ **dữ liệu chính thức v1 bản đầy đủ do M1 phát hành (`master_v1`)** (4 tuần, 17/04–14/05/2023, 535.167 lượt đón sau làm sạch, 304 toạ độ; 3 lát cắt: `WEEKDAY_AM` 60.498, `WEEKDAY_PM` 86.617, `WEEKEND` 120.571). Nguồn bảng chuẩn: `outputs/metrics/baseline_metrics.csv` và `outputs/metrics/run_log.csv`.

Ký hiệu chung:
- Mỗi lượt đón $i$ có toạ độ $x_i \in \mathbb{R}^2$ (mét, hệ EPSG:26916).
- Vì toạ độ là tâm (centroid) của census tract nên rất nhiều lượt trùng toạ độ. Gọi $u_j$ là các toạ độ khác nhau và $w_j$ là số lượt đón tại $u_j$, với $\sum_j w_j = n$.
- Hai thuật toán đều chỉ dùng toạ độ $(x, y)$, không đưa giờ, quãng đường hay giá vào khoảng cách. Thời gian được dùng để tách 3 lát cắt chạy riêng: `WEEKDAY_AM` (T2–T6, 07:00–09:59), `WEEKDAY_PM` (T2–T6, 16:00–18:59), `WEEKEND` (T7–CN, cả ngày).

---

## 1. K-Means

### 1.1 Bài toán và hàm mục tiêu

K-Means chia $n$ điểm thành đúng $K$ cụm $C_1, \dots, C_K$, mỗi cụm có tâm $\mu_k$, sao cho tổng bình phương khoảng cách từ mỗi điểm tới tâm cụm của nó (SSE, hay *inertia*) là nhỏ nhất:

$$J = \sum_{k=1}^{K} \sum_{x_i \in C_k} \lVert x_i - \mu_k \rVert^2, \qquad \mu_k = \frac{1}{|C_k|}\sum_{x_i \in C_k} x_i .$$

**Dạng có trọng số.** Các lượt trùng toạ độ luôn có cùng khoảng cách tới mọi tâm, nên luôn rơi vào cùng một cụm. Gộp chúng lại thì hàm mục tiêu không đổi:

$$J = \sum_{j} w_j \lVert u_j - \mu_{c(j)} \rVert^2, \qquad \mu_k = \frac{\sum_{j \in C_k} w_j u_j}{\sum_{j \in C_k} w_j}.$$

Vì vậy nhóm fit K-Means trên 165–189 toạ độ duy nhất của mỗi lát cắt, với `sample_weight` = số lượt đón. Kết quả kiểm chứng trên dữ liệu thật (mục 3.1, 5.1): nhãn của từng lượt đón giống hệt khi fit trên toàn bộ lượt, inertia trùng khớp khi `n_init` đủ lớn, và tốc độ nhanh hơn khoảng 9–17 lần ở vòng quét Elbow.

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

Thử K = 2..15, `k-means++`, `max_iter = 300`, `seed = 42` (100% số lần chạy đều hội tụ).

- **Elbow:** vẽ J theo K và tìm điểm mà J ngừng giảm mạnh ("khuỷu tay"). Điểm khuỷu được gợi ý bằng khoảng cách lớn nhất từ đường cong tới dây cung nối hai đầu.
- **Silhouette:** với điểm $i$, gọi $a(i)$ là khoảng cách trung bình tới các điểm cùng cụm, $b(i)$ là khoảng cách trung bình nhỏ nhất tới một cụm khác. Khi đó $s(i) = \dfrac{b(i) - a(i)}{\max\{a(i), b(i)\}} \in [-1, 1]$; càng gần 1 thì cụm càng tách biệt.
- **Davies–Bouldin (DBI):** $\frac{1}{K}\sum_k \max_{l \ne k} \frac{\sigma_k + \sigma_l}{d(\mu_k, \mu_l)}$, trong đó $\sigma_k$ là khoảng cách trung bình từ điểm tới tâm cụm $k$. Càng thấp càng tốt.
- **Calinski–Harabasz (CH):** tỷ số giữa độ phân tán giữa các cụm và độ phân tán trong cụm, có hiệu chỉnh theo bậc tự do. Càng cao càng tốt.

Kết quả trên `master_v1`:

1. **Khuỷu Elbow nằm ở K = 5 ở cả 3 lát cắt.** Khi tăng từ K = 4 lên K = 5, J giảm mạnh 31,7–37,3%; từ K = 6 trở đi, mỗi lần thêm một cụm chỉ giảm 15,4–23,0%.
2. **Với `n_init = 10` (giá trị trong spec), K-Means dễ rơi vào cực tiểu cục bộ khi K ≥ 6**: J tệ hơn mức tốt nhất tới 8,3–11,3% (`weighted` và `full`), còn với `n_init = 50` sai lệch tối đa chỉ 0,9%. Nhóm dùng **`n_init = 50`**.
3. Trong khoảng K ≥ 4, **K = 5 đạt cao nhất đồng thời Silhouette theo lượt, Silhouette theo toạ độ và thấp nhất DBI ở cả 3 lát cắt**. K = 2 có chỉ số cao hơn nhưng chỉ tách sân bay O'Hare khỏi phần còn lại, quá thô. CH tăng đều đến K = 15 nên không giúp chọn.
4. Bản đồ với K = 5 cho 5 vùng địa lý rõ ràng và nhất quán giữa cả 3 lát cắt.

**Chốt K = 5.**

### 1.4 Kết quả K-Means (K = 5)

| Lát cắt | Số lượt | Toạ độ duy nhất | Silhouette (theo lượt) | Silhouette (theo toạ độ) | DBI | Cụm lớn nhất | Thời gian fit |
|---|---:|---:|---:|---:|---:|---:|---:|
| WEEKDAY_AM | 60.498 | 165 | 0,733 | 0,416 | 0,445 | 62,3% | 0,122 s |
| WEEKDAY_PM | 86.617 | 188 | 0,753 | 0,398 | 0,459 | 62,5% | 0,140 s |
| WEEKEND | 120.571 | 189 | 0,726 | 0,406 | 0,477 | 52,7% | 0,157 s |

| Cụm | Vùng | AM | PM | WEEKEND |
|---:|---|---:|---:|---:|
| 0 | Trung tâm (Loop, Near North; khu 8/32) | 62,3% | 62,5% | 52,7% |
| 1 | Sân bay O'Hare (khu 76) | 16,0% | 20,7% | 24,5% |
| 2 | Phía bắc dọc hồ (Lake View; khu 6) | 12,8% | 8,9% | 13,5% |
| 3 | Phía nam (khu 41/43) | 5,7% | 4,3% | 5,3% |
| 4 | Sân bay Midway (khu 56) | 3,1% | 3,5% | 4,1% |

Silhouette tính theo lượt (0,726–0,753) cao hơn nhiều so với tính theo toạ độ duy nhất (0,398–0,416). Lý do: các lượt trùng toạ độ có khoảng cách 0 tới nhau, làm $a(i)$ rất nhỏ. Khi trình bày cần nêu cả hai con số.

---

## 2. DBSCAN

### 2.1 Các định nghĩa

Với bán kính $\varepsilon$ (`eps`) và ngưỡng `min_samples` (`minPts`):

- **Lân cận eps:** $N_\varepsilon(p) = \{q : d(p, q) \le \varepsilon\}$, gồm cả chính $p$.
- **Điểm lõi (core):** $p$ là core nếu $|N_\varepsilon(p)| \ge \text{minPts}$. Ở dạng có trọng số (scikit-learn), điều kiện là $\sum_{q \in N_\varepsilon(p)} w_q \ge \text{minPts}$.
- **Đạt tới trực tiếp theo mật độ:** $q$ đạt tới trực tiếp từ $p$ nếu $p$ là core và $q \in N_\varepsilon(p)$.
- **Đạt tới theo mật độ:** có một chuỗi điểm core $p = p_1, \dots, p_m$ nối liền nhau theo quan hệ trên và kết thúc ở $q$.
- **Liên thông theo mật độ:** $p$ và $q$ cùng đạt tới được từ một điểm core $o$.
- **Cụm:** tập liên thông theo mật độ, lớn nhất có thể. **Điểm biên (border)** thuộc cụm nhưng không phải core. **Nhiễu** là điểm không thuộc cụm nào, nhãn −1.

DBSCAN không cần biết trước số cụm, tìm được cụm có hình dạng bất kỳ (ví dụ dải dọc bờ hồ) và tự loại nhiễu. Nhược điểm là chỉ dùng **một** `eps` cho mọi vùng, nên khó xử lý khi các vùng có mật độ rất khác nhau.

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

Số đo thực nghiệm trên cả pilot và `master_v1` cho thấy chạy đúng như giá trị khởi điểm trong spec sẽ không phù hợp với dữ liệu centroid:

1. **Fit trên toạ độ duy nhất với trọng số.** Các lượt trùng toạ độ có khoảng cách 0 nên luôn là láng giềng của nhau; tổng trọng số thay cho số điểm. Kiểm chứng trên `WEEKEND` của `master_v1` ở cỡ 10k và 20k (6 cấu hình): 6/6 khớp hoàn toàn số cụm và tập nhiễu (`same_noise = True`), 5/6 có `ARI = 1,0000`, 1 cấu hình có `ARI = 0,99995` (do tính không tất định thứ tự gán điểm biên giữa 2 cụm). Về bộ nhớ, ở cỡ 20k cách `full` tốn 189–456 MB; ở toàn bộ `WEEKEND` (`120.571` lượt), cách `full` ước tính tốn **7,2–17,4 GB RAM** (vượt RAM 15,2 GB của máy) nên phải bỏ qua, trong khi cách có trọng số chỉ tốn **3,7 MB RAM** và **0,06 s** (nhanh hơn 13–53 lần ở các cỡ đo được).
2. **`min_samples` theo tỷ lệ số lượt của lát cắt** (0,1 / 0,3 / 0,5 / 1%). Với 5–20 như spec, 99,5–99,9% số lượt trên `master_v1` nằm ở toạ độ tự là core, nên DBSCAN gần như không lọc được nhiễu (Noise Ratio tối đa chỉ 0,38% ở mọi `eps`).
3. **`eps` 500–3000 m.** Các toạ độ duy nhất cách nhau trung vị khoảng 795–837 m (phân vị 10% khoảng 304–313 m); với `eps < 300 m` hầu như không toạ độ nào nối được với toạ độ khác.

### 2.4 Chọn `eps` và `min_samples`

- **k-distance có trọng số:** với mỗi toạ độ, là khoảng cách nhỏ nhất để gom đủ $k$ lượt (tính cả chính nó). Đây chính là ngưỡng `eps` để toạ độ đó trở thành core. Đã kiểm chứng trên dữ liệu thực: đặt `eps` bằng giá trị này thì toạ độ là core, giảm đi $10^{-6}$ m thì không (0/80 sai).
- Trên dữ liệu centroid, đồ thị k-distance **không có một điểm gãy rõ ràng** mà tăng theo bậc thang (nhóm `spec` gợi ý 1,0–1,5 km; nhóm tỷ lệ gợi ý 2,3–4,0 km). Vì vậy `eps` phải chọn bằng **lưới tham số**.
- **Lưới:** 8 `eps` × 6 `min_samples` × 3 lát cắt = 144 cấu hình. Quan sát trên `master_v1`:
  - `eps = 500 m` cho Silhouette rất cao (0,805–0,859) nhưng đó là **kết quả giả**: gần như mỗi toạ độ thành một cụm riêng (18–113 cụm).
  - `eps ≥ 2500 m` gộp phần lớn thành phố thành một cụm (67,6–84,1%).
  - Vùng hợp lý là `min_samples` 0,5–1% với `eps` 1000–2000 m.
- **So sánh 4 ứng viên** A (`1%, 1500 m`), B (`1%, 2000 m`), C (`0,5%, 1000 m`), D (`0,5%, 1250 m`) trên bảng chỉ số và bản đồ `master_v1`, rồi chốt:
  - **Cấu hình chính A:** 1% số lượt, `eps = 1500 m`. Vượt trội B ở cả 3 lát cắt về Silhouette (trung bình **0,809** so với 0,764), Silhouette theo toạ độ (trung bình **0,639** so với 0,455) và DBI (trung bình **0,177** so với 0,214); đồng thời tách được Hyde Park (khu 41) vào sáng ngày thường, trong khi B ở `WEEKDAY_AM` sinh cụm nhỏ sát rìa bắc dải Trung tâm (khu 2) làm Silhouette theo toạ độ tụt còn 0,244.
  - **Cấu hình phụ C:** 0,5%, `eps = 1000 m`, dùng để minh hoạ độ nhạy của `eps`.

### 2.5 Kết quả DBSCAN

| Lát cắt | Cấu hình | `min_samples` | Số cụm | Noise | Silhouette (lượt / toạ độ) | DBI | Cụm lớn nhất | Fit |
|---|---|---:|---:|---:|---|---:|---:|---:|
| WEEKDAY_AM | A | 605 | 4 | 12,6% | 0,741 / 0,560 | 0,220 | 68,9% | 0,037 s |
| WEEKDAY_PM | A | 867 | 3 | 9,4% | 0,859 / 0,702 | 0,153 | 66,9% | 0,055 s |
| WEEKEND | A | 1.206 | 4 | 9,9% | 0,825 / 0,656 | 0,159 | 62,1% | 0,070 s |
| WEEKDAY_AM | C | 303 | 13 | 9,4% | 0,597 / 0,442 | 0,253 | 50,5% | 0,033 s |
| WEEKDAY_PM | C | 434 | 11 | 7,4% | 0,686 / 0,495 | 0,255 | 49,7% | 0,052 s |
| WEEKEND | C | 603 | 13 | 8,8% | 0,720 / 0,468 | 0,241 | 39,0% | 0,072 s |

Các cụm chính của cấu hình A:
1. Hành lang trung tâm và phía bắc dọc hồ (khu 8/32/6): 62,1–68,9% số lượt.
2. Sân bay O'Hare (khu 76): 15,7–24,2%, chỉ gồm 2 toạ độ, bán kính RMS 0,41–0,44 km.
3. Sân bay Midway (khu 56): 1,8% (`WEEKDAY_AM`), 3,3% (`WEEKDAY_PM`), và ở `WEEKEND` tách làm 2 cụm nhỏ sát nhau (2,3% + 1,5% = 3,8%).
4. Riêng `WEEKDAY_AM` xuất hiện thêm cụm thứ 4 tại Hyde Park (khu 41): 1,0% (611 lượt, 6 toạ độ).

Phần lớn phía nam và tây bắc là nhiễu.

---

## 3. So sánh K-Means và DBSCAN

**Đồng thuận** ở các vùng dày cốt lõi: trung tâm (97,0–98,9% số lượt trùng), O'Hare (97,7–98,8%); ở Midway, `WEEKDAY_PM` trùng 93,8%, `WEEKDAY_AM` trùng 56,0% (44,0% vùng rìa thành nhiễu), còn `WEEKEND` tổng 92,7% được giữ cụm nhưng tách thành 2 cụm nhỏ sát nhau. ARI giữa K-Means và DBSCAN A (coi nhiễu là một nhãn riêng) là **0,706 / 0,820 / 0,743** (AM / PM / WEEKEND).

**Khác nhau** ở 3 vùng (hình `outputs/figures/m2_compare_regions_master_v1.png`):

| Vùng | K-Means (`K = 5`) | DBSCAN A (`1%, 1500 m`) | Diễn giải |
|---|---|---|---|
| Phía nam (R1) | Một cụm riêng (4,3–5,7%), bán kính rộng nhất (5,25–5,46 km) | 78,6–92,7% số lượt trong vùng là nhiễu (100% cụm 3 K-Means ở PM/WE; AM tách được Hyde Park 17,6%) | Vùng thưa. K-Means tạo "cụm" rộng chỉ vì phải gán mọi điểm |
| O'Hare và tây bắc (R2) | Cụm rộng: 7–9 toạ độ, bán kính 1,00–1,34 km | Cụm chặt: 2 toạ độ nhà ga, 0,41–0,44 km; xung quanh là nhiễu (6,3–11,8%) | DBSCAN cho ranh giới hotspot sân bay sát thực tế hơn |
| Phía bắc dọc hồ (R3) | Cụm riêng (8,9–13,5%) | Gộp 60,6–74,5% vào dải trung tâm; rìa tây bắc là nhiễu (5,2–6,8% khung R3) | DBSCAN giữ được cụm hình dải dọc hồ, nhưng `eps = 1500 m` vẫn gộp Loop với Lake View |

**Nhiễu của DBSCAN A chủ yếu là vùng thưa thật, không phải do `eps` quá nhỏ:**
- 68,8–83,9% toạ độ nhiễu cách toạ độ core gần nhất hơn 3 km (gấp đôi `eps`); trung vị 4,8–5,9 km (gấp 3,2–3,9 lần `eps`).
- Chỉ 3–7 toạ độ mỗi lát cắt nằm sát ngưỡng `eps` (`1,5–1,875 km`).
- Cấu hình phụ C chỉ chuyển lại được 25,4–34,6% số lượt nhiễu vào cụm.
- Nhiễu cũng **không đồng nghĩa với bản ghi lỗi**: tỷ lệ cờ chất lượng của lượt nhiễu chỉ nhỉnh hơn một phần nhỏ ở một số cờ (`flag_speed_gt_80` 0,12–0,30% so với 0,04%; `flag_zero_duration` 2,61–4,34% so với 1,31–1,67%), và tuyệt đại đa số lượt nhiễu không có cờ nào.

| Tiêu chí | K-Means (`K = 5`) | DBSCAN A (`1%, 1500 m`) |
|---|---|---|
| Tham số phải chọn | `K` | `eps`, `min_samples` |
| Nhiễu | Không có (Noise = 0 theo thiết kế, không phải ưu điểm) | 9,4–12,6% |
| Hình dạng cụm | Lồi quanh tâm | Bất kỳ, theo mật độ |
| Độ nhạy tham số | Ổn định khi `n_init = 50` | Rất nhạy với `eps`: A có 3–4 cụm (và tách đôi Midway vào cuối tuần), C có 11–13 cụm, `ARI(A, C)` chỉ 0,525–0,608 |
| Thời gian fit (có trọng số) | 0,12–0,16 s | 0,04–0,07 s |
| Hạn chế chính | Tạo cụm ở vùng thưa; cắt dải dọc hồ | Một `eps` cho mọi mật độ: vừa gộp Loop–Lake View, vừa làm đứt Midway ở `WEEKEND` |

Hạn chế "một `eps` cho mọi mật độ" là lý do để so sánh tiếp với HDBSCAN (phần của M3 – Hoàng Tuấn Bảo). HDBSCAN xét nhiều mức mật độ cùng lúc thay vì một `eps` cố định.

---

## 4. Lưu ý về đánh giá

- Silhouette, DBI và CH được tính **trên các lượt có cụm** (bỏ nhiễu) và luôn ghi kèm Noise Ratio và coverage, theo quy tắc của spec (mục 2.4).
- Ba chỉ số này vốn ưu ái cụm lồi và **bị đẩy lên rất mạnh** khi có nhiều lượt trùng toạ độ. Ví dụ: K-Means có Silhouette 0,726–0,753 theo lượt nhưng chỉ 0,398–0,416 theo toạ độ; DBSCAN `eps = 500 m` có Silhouette tới 0,859 nhưng đó là cụm vụn (18–113 cụm). Vì vậy nhóm không chọn tham số chỉ theo một chỉ số, mà kết hợp với bảng chéo, bản đồ và phân tích nhiễu.
- Thời gian fit rất nhỏ vì chạy trên 165–189 toạ độ duy nhất có trọng số. Khi so sánh thời gian với HDBSCAN (thư viện không hỗ trợ trọng số) phải ghi rõ mỗi thuật toán chạy trên đầu vào nào.

## 5. Hạn chế

1. Toạ độ là centroid của census tract hoặc community area, không phải GPS, nên hotspot ở đây là ở **mức khu vực**.
2. Thời gian trong dữ liệu đã làm tròn 15 phút. Các lát cắt dùng khung 3 giờ nên không bị ảnh hưởng.
3. Hotspot là vùng nhiều lượt đón taxi, **không phải điểm ùn tắc**: dữ liệu không có tốc độ hay lưu lượng xe.
4. Kết quả trên chạy trên bản đầy đủ `master_v1` (4 tuần, 535.167 lượt); cần chốt đối chiếu trên cùng tập `trip_id` với HDBSCAN của M3.

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
