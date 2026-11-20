# Phân công đợt 2 cho Thành viên 4 (M4 – Hà Xuân Đại)

Căn cứ: BA Specification v1.1 (mục 2.4, 2.5, 3.4.4, 3.5, 5.3, 5.4, 6, A4) và hiện trạng repo ngày 20/11/2026 (main sau PR #2 của M3).
**Phạm vi đợt này:** kỹ thuật, trực quan hóa, kiểm thử/QA, đóng gói và tái lập. **Loại trừ:** báo cáo Word (M4-06), slide và kịch bản nói (M4-07), rehearsal/phân vai Q&A (phần của M4-09).

## 1. Rà soát hiện trạng so với BA

| Hạng mục BA | Hiện trạng trước đợt này | Kết luận |
|---|---|---|
| M1 – data, EDA, master_v1 (535.167 dòng, 304 tọa độ, EPSG:26916) | Đã có: `src/data`, notebook 01–02, `outputs/metrics/eda`, `preprocess`, manifest | Đủ để M4 dùng; thiếu tọa độ EDA **theo lát cắt** (chỉ có bảng tóm tắt) |
| M2 – K-Means, DBSCAN | Đã có: notebook 03–04, `baseline_metrics.csv` (6 dòng), `*_clusters_master_v1.csv`, bản đồ Folium riêng | Đủ (H03) |
| M3 – HDBSCAN, temporal | Đã có: notebook 05–06, `hdbscan_metrics.csv`, `hotspot_tracking.csv`, bản đồ, biên bản H04/H05 | Có số liệu; **văn bản M3 lệch CSV** (mục 4) |
| M4-01 board, quy ước | Chưa có (`.gitignore` ghi "M4 phụ trách cấu trúc repo") | **Thiếu → làm** |
| M4-02 style chuẩn | Chưa có; mỗi người dùng màu/DPI riêng (M3 dùng xanh-đỏ-lục cho lát cắt, 150 dpi) | **Thiếu → làm** |
| M4-03 heatmap pickup | Chỉ có PNG EDA 06 (không phải bản đồ tương tác) | **Thiếu → làm** |
| M4-04 bản đồ 3 thuật toán cùng extent | Có 3 bản đồ riêng nhưng mỗi file `fit_bounds` riêng, không cùng thang kích thước | **Thiếu bản đồ chuẩn hóa → làm** |
| M4-05 `metrics_comparison.csv`, biểu đồ so sánh | Chưa có file; biên bản M3 chỉ ghi đoạn mã nối | **Thiếu → làm** |
| M4-08 README, notebook 07, clean-run | Không có `README.md`, không có notebook 07, không có log clean-run; 1 notebook còn đường dẫn `D:\...` | **Thiếu → làm** |
| M4-09 QA nhất quán | Chưa có | **Thiếu → làm** (phần kỹ thuật) |

## 2. Danh sách task và trạng thái

Trạng thái ghi theo bằng chứng chạy được trong repo (xem `docs/M4/project_board.csv`).

| Mã | Mục tiêu / cách làm | Đầu ra | DoD (nghiệm thu) | Phối hợp | Trạng thái |
|---|---|---|---|---|---|
| **M4-01** Quản lý & chuẩn trình bày | Board theo mã WBS; quy tắc `run_id`, đặt tên artifact, quy trình bàn giao | `docs/M4/project_board.csv`, `CONTRIBUTING.md`, `docs/M4/artifact_naming.md` | Mọi task có owner/deadline/status/reviewer; quy tắc đặt tên bao phủ mọi artifact | Cả nhóm cập nhật board | Xong |
| **M4-02** Bộ style chuẩn | Palette Okabe-Ito theo thuật toán, màu riêng cho lát cắt, noise xám, 300 dpi, chú thích nguồn/n/giới hạn | `src/visualization/style.py`, `docs/M4/visual_style_guide.md` | Mọi chart M4 dùng chung style; cluster/noise màu nhất quán | M2/M3 dùng style cho hình mới | Xong |
| **M4-03** Heatmap pickup | Folium HeatMap trọng số = số chuyến/centroid, lớp top-15, nền OSM hoặc không nền; PNG tĩnh dự phòng | `outputs/maps/pickup_demand_heatmap.html`, `outputs/figures/comparison/pickup_demand_heatmap.png` | 304/304 tọa độ trong bbox; tiêu đề nêu thời gian + n; ghi rõ centroid ≠ GPS | M1 xác nhận tọa độ | Xong (tổng). **Mở:** heatmap theo lát cắt cần tọa độ theo lát cắt từ M1 |
| **M4-04** Bản đồ 3 thuật toán | Vẽ tâm cụm từ bảng cụm của M2/M3, **cùng extent, zoom, thang diện tích**; noise không vẽ; vòng RMS ≠ ranh giới | `cluster_map_{kmeans,dbscan,hdbscan}.html`, `cluster_map_comparison.html`, `algorithm_comparison*.png` | Legend + title; không gán lại nhãn; số cụm/noise trên hình khớp CSV (QA-08) | M2/M3 xác nhận; M1 xác nhận CRS | Xong ở mức tâm cụm. **Mở:** bản đồ cấp điểm cần `outputs/labels/*.parquet` (chạy trên Colab/máy M2) |
| **M4-05** Metrics & temporal | Gộp H05 (9 dòng) có kiểm tra schema/sample; small multiples runtime/noise/cụm/Silhouette/Coverage; phân bố dịch chuyển | `metrics_comparison.csv`, `runtime_noise_comparison.png`, `temporal_hotspot_comparison.png`, `cluster_comparison.html` | Số khớp CSV nguồn; Silhouette luôn đi kèm Coverage; footer nêu giới hạn runtime | M2/M3 chịu trách nhiệm số | Xong |
| **M4-08** README, Git, clean-run | README theo BA 5.3; notebook 07; `.gitattributes` (chấm dứt nhiễu CRLF); `requirements` thêm plotly; `check_repo.py`; log clean-run | `README.md`, `notebooks/07_visualization_reporting.ipynb`, `scripts/{build_m4,run_qa,check_repo}.py`, `logs/clean_run_20261120.md` | Clone → tạo venv → `pytest` + `build_m4.py` chạy không sửa path; repo không có raw data/secret/absolute path | M1: bước tạo data; M2/M3: lệnh chạy model | Xong (clean-run trên Linux/Python 3.13). **Mở:** thử trên Windows và Colab |
| **M4-09** QA kỹ thuật | 17 nhóm kiểm tra: schema, cùng sample/n_points, Σ chuyến + noise, CRS (pyproj), tracking ↔ cụm, chế độ fit, claim register | `src/qa/consistency.py`, `scripts/run_qa.py`, `tests/test_m4.py`, `docs/M4/final_QA_checklist.md`, `outputs/metrics/qa_*.csv` | 0 FAIL; mọi WARN có owner và quyết định | Trả WARN/claim về M1/M2/M3 | Xong. Rehearsal/Q&A **loại trừ** |
| **M4-10** Trả kết quả QA cho owner | Gửi `docs/M4/m4-handoff-discrepancies.md`; theo dõi phản hồi; chạy lại `run_qa.py` sau khi M3 sửa | file ghi nhận + comment issue | Mỗi mục có owner trả lời và quyết định (sửa văn bản / chạy lại / chấp nhận giới hạn) | **M3 (chính), M2** | **Đang chờ** |
| **M4-11** Bản đồ cấp điểm + heatmap theo lát cắt | Trên máy có `data/` và `outputs/labels/`: dùng `cluster_map` có sẵn với extent từ `shared_extent` | `outputs/maps/*_points_*.html` (đặt tên theo `artifact_naming.md`) | Cùng tập `trip_id`, cùng extent với M4-04 | M2 (nhãn K-Means/DBSCAN), M3 (HDBSCAN), M1 (dữ liệu) | Chưa làm (thiếu dữ liệu trong repo) |
| **M4-12** Release kỹ thuật | Khi M4-10 xong: chạy lại build + QA, commit, gắn tag `v1.0-tech` | tag Git, `m4_artifact_manifest.csv` mới | 0 FAIL; manifest khớp file; mỗi thành viên clean-run phần mình (H08) | Cả nhóm | Chưa làm |

## 3. Điểm phối hợp theo mã bàn giao BA

| Bàn giao | Gói M4 cần | Đã nhận | Việc M4 đã làm |
|---|---|---|---|
| H01/H02 (M1) | CRS, manifest, `pickup_coords.csv` | Có | QA-09/10 xác nhận tọa độ trong bbox, x,y khớp lat,lon (sai số < 1 m) |
| H03 (M2) | `baseline_metrics.csv`, bảng cụm | Có | QA-01…08 |
| H04/H05 (M3) | `hdbscan_metrics.csv`, `hotspot_tracking.csv` | Có | Gộp H05; **ký nhận có điều kiện** (xem mục 4) |
| H06 (M4 ↔ M1/M2/M3) | Gói hình cùng extent | Đã dựng | Chờ owner xác nhận nhãn/vị trí từng bản đồ |
| H07/H08 | Phần báo cáo, release | Ngoài phạm vi đợt này | — |

## 4. Rủi ro và phụ thuộc cần lưu ý khi bàn giao

Các mục dưới đây do `scripts/run_qa.py` phát hiện; M4 **không tự sửa số liệu**, chỉ trả về owner (chi tiết số trong `docs/M4/m4-handoff-discrepancies.md`).

| # | Rủi ro | Mức | Owner xử lý | Hành động |
|---|---|---|---|---|
| R-A | **Văn bản M3 lệch CSV chính thức**: 8/10 khẳng định kiểm tra không khớp (noise "≈10%" vs 0,9–2,3%; "4 cụm" vs 63–78; Silhouette 0,78 vs 0,98–0,99; dịch chuyển 820 m không có trong tracking; O'Hare 11,5→16,8% vs 15,7→20,4%; Hyde Park "611 chuyến/1,0%" trùng cụm DBSCAN A khu 41, không phải HDBSCAN; Midway 4,2–4,8% vs 2,7–3,8%) | Cao | M3 | Đối chiếu lại với run_id chính thức; sửa văn bản hoặc giải thích run nào đã sinh ra con số. Chưa đưa các câu này vào bất kỳ sản phẩm nào cho đến khi xong |
| R-B | **Cách fit khác nhau**: K-Means/DBSCAN fit *weighted* trên tọa độ duy nhất; HDBSCAN fit trên toàn bộ điểm (thư viện không hỗ trợ `sample_weight`) → runtime 18–73 s vs 0,04–0,16 s không so trực tiếp được; Python 3.10.6 vs 3.11.9 | Cao | M2 + M3 | Nêu rõ trong mọi chart/bảng (đã làm); cân nhắc chạy HDBSCAN trên tọa độ duy nhất hoặc ghi chú chính thức |
| R-C | **Silhouette/DBI HDBSCAN bị thổi phồng**: 63% cụm chỉ gồm 1 tọa độ (bán kính 0) vì tọa độ trùng nhau tạo mật độ vô hạn khi `min_samples=10` | Cao | M3 | Không dùng "Silhouette cao nhất" để kết luận HDBSCAN tốt nhất; cần Silhouette trên tọa độ duy nhất hoặc DBCV nếu còn thời gian |
| R-D | **"Dịch chuyển 0 m"**: 54–57% cặp MATCHED dịch 0 m vì cụm trùng 1 centroid | Trung bình | M3 | Diễn giải là giới hạn độ phân giải centroid, không phải "đứng yên tuyệt đối" |
| R-E | **Tính nhất quán mẫu**: bốn nguồn phải cùng `sample_id=master_v1` và cùng `n_points` mỗi lát cắt (đã PASS). Mọi chạy lại phải tăng phiên bản, không ghi đè | Trung bình | M1/M2/M3 | QA-02/03 chạy lại sau mỗi lần phát hành |
| R-F | **CRS/lat–lon**: mọi tọa độ hiển thị là lat/lon từ EPSG:26916; khoảng cách tính theo mét trong UTM. Đảo lat/lon sẽ rơi ngoài bbox | Thấp (đã PASS) | M1 | QA-09 chạy lại khi có bảng mới |
| R-G | **`run_id` truy vết**: mỗi chart/bản đồ chỉ dùng run_id trong `metrics_comparison.csv`; không trộn run khác nhau (pilot_m2_v0 vs master_v1) trên cùng hình | Trung bình | Tất cả | `m4_artifact_manifest.csv` ghi nguồn + SHA-256 |
| R-H | **Diễn giải bản đồ**: centroid ≠ GPS; hotspot = nhu cầu đón, không phải ùn tắc; K-Means noise = 0 không phải ưu điểm; vòng RMS ≠ ranh giới cụm; noise không tô thành hotspot | Cao | M4 | Chú thích đã đặt trong mọi hình/bản đồ M4; QA-17 kiểm tra HTML (bản đồ `hdbscan_temporal_shift_map.html` của M3 thiếu chú thích → M3 bổ sung) |
| R-I | **Phụ thuộc Internet**: HTML Folium cần tải Leaflet và nền OSM; mất mạng bản đồ trống | Trung bình | M4 | Luôn có PNG 300 dpi dự phòng; lớp "Không nền (offline)" |
| R-J | **Dữ liệu/nhãn không nằm trong repo** (`data/`, `outputs/labels/` bị ignore) | Trung bình | M1/M2/M3 | Chia sẻ qua Drive; M4-11 phụ thuộc điều này |
| R-K | Nhiễu CRLF: 127 file hiển thị "đã sửa" chỉ vì đuôi dòng | Thấp | M4 | Đã thêm `.gitattributes`; commit riêng, không lẫn với thay đổi nội dung |

## 5. Thứ tự thực hiện đề xuất cho các task còn mở

1. M3 trả lời R-A, R-B, R-C (ưu tiên, chặn mọi sản phẩm sau này) → M4 chạy `python scripts/run_qa.py`.
2. M1/M2/M3 cung cấp nhãn trên một máy chung → M4-11.
3. M4-12: build lại, QA 0 FAIL, commit (tách commit `.gitattributes`/CRLF), tag.

## 6. Cách chạy lại toàn bộ phần M4

```bash
pip install -r requirements.txt
python -m pytest -q tests          # 11 test
python scripts/build_m4.py         # 14 artifact + manifest
python scripts/run_qa.py           # bảng QA + claim register
python scripts/check_repo.py       # repo sạch
```
