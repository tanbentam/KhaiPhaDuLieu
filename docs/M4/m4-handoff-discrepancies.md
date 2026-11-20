# Ghi nhận trả về cho owner (M4 → M1/M2/M3)

Sinh bởi `python scripts/run_qa.py` ngày 20/11/2026 trên `master_v1`. M4 **không sửa số liệu hay văn bản chuyên môn**; mỗi mục cần owner xác nhận: *sửa văn bản*, *chạy lại*, hoặc *chấp nhận và ghi giới hạn*.

## A. Khẳng định trong văn bản M3 so với CSV chính thức

| ID | Nguồn | Khẳng định | Quan sát từ CSV | Kết luận |
|---|---|---|---|---|
| C01 | `reports/m3_hdbscan_temporal.md` | HDBSCAN (mcs=100, ms=10) có Noise Ratio ≈ 10% (10,8%) | metrics chính thức: WEEKDAY_AM 2.1%, WEEKDAY_PM 2.3%, WEEKEND 0.9% | **KHÔNG KHỚP** |
| C02 | `docs/Phan 5/hdbscan_interpretation.md` | HDBSCAN Noise Ratio 9,8%–11,5% | metrics chính thức: 0.9%–2.3% | **KHÔNG KHỚP** |
| C03 | `reports/m3_hdbscan_temporal.md` | mcs=100 cho '4 cụm lớn' (Loop/Near North, O'Hare, Midway, Hyde Park) | bảng cụm chính thức: WEEKDAY_AM 67 cụm, WEEKDAY_PM 63 cụm, WEEKEND 78 cụm | **KHÔNG KHỚP** |
| C04 | `reports/m3_hdbscan_temporal.md` | Silhouette 0,78 và DBI 0,19 cho cấu hình chọn | metrics chính thức: Silhouette 0.981–0.991; DBI 0.180–0.288 | **KHÔNG KHỚP** |
| C05 | `reports/m3_hdbscan_temporal.md` | O'Hare tăng từ 11,5% (sáng) lên 16,8% (chiều) | Σ share cụm khu 76: sáng 15.7% → chiều 20.4% (cụm lớn nhất: 10,6% → 12,8%) | **KHÔNG KHỚP** |
| C06 | `reports/m3_hdbscan_temporal.md` | Tâm cụm trung tâm dịch chuyển 820 m về phía bắc (sáng → chiều); interpretation: 650–950 m | dịch chuyển của các cụm lớn (≥ 2000 chuyến) sáng→chiều: 0 m, 0 m, 0 m, 0 m, 0 m, 0 m, 83 m, 0 m, 0 m; không có cặp nào trong khoảng 650–950 m ở nhóm này | **KHÔNG KHỚP** |
| C07 | `reports/m3_hdbscan_temporal.md` | Hyde Park (khu 41) xuất hiện rõ ở sáng ngày thường (611 chuyến, 1,0%), tan rã chiều/cuối tuần | HDBSCAN khu 41: WEEKDAY_AM 351 chuyến (0.6%), WEEKDAY_PM 607 chuyến (0.7%), WEEKEND 748 chuyến (0.6%). Số 611 chuyến / 1,0% trùng cụm DBSCAN A khu 41: 611 chuyến | **KHÔNG KHỚP** |
| C08 | `reports/m3_hdbscan_temporal.md` | Midway (khu 56) giữ tỷ trọng 4,2%–4,8% ở cả 3 lát cắt | Σ share cụm HDBSCAN khu 56: WEEKDAY_AM 2.7%, WEEKDAY_PM 3.3%, WEEKEND 3.8% | **KHÔNG KHỚP** |
| C09 | `docs/Phan 5/hdbscan_interpretation.md` | DBSCAN Noise Ratio 9,4%–12,6% | dbscan_clusters (A): 9.4%–12.6% | **KHỚP** |
| C10 | `docs/Phan 5/5.5-bien-ban-ban-giao-m3.md` | Bảng H05 gồm đúng 9 dòng (3 K-Means, 3 DBSCAN A, 3 HDBSCAN) | baseline + hdbscan = 9 dòng | **KHỚP** |

Ghi chú C07: số 611 chuyến / 1,0% khu 41 trùng đúng cụm DBSCAN A khu 41 lát cắt sáng, nên văn bản M3 có thể lấy từ kết quả DBSCAN hoặc run cũ. Đây là suy đoán để M3 kiểm tra, không phải kết luận.

## B. Cảnh báo phương pháp (WARN)

| Mã | Phạm vi | Nội dung | Owner |
|---|---|---|---|
| QA-12 | hotspot_tracking | 54% cặp MATCHED có dịch chuyển đúng 0 m (cụm trùng 1 centroid) — giới hạn độ phân giải tọa độ, không nên đọc là 'đứng yên tuyệt đối' | M3 |
| QA-13 | hdbscan_clusters | 63% cụm HDBSCAN chỉ gồm 1 tọa độ duy nhất (bán kính 0) → Silhouette/DBI của HDBSCAN bị thổi phồng, không so trực tiếp với K-Means/DBSCAN | M3 |
| QA-14 | runtime | chế độ fit theo thuật toán: {'dbscan': ['weighted'], 'hdbscan': ['unweighted'], 'kmeans': ['weighted']} → KHÔNG cùng cách fit (weighted trên tọa độ duy nhất vs toàn bộ điểm): runtime không so trực tiếp | M2/M3 |
| QA-15 | environment | phiên bản Python theo thuật toán: {'dbscan': ['3.10.6'], 'hdbscan': ['3.11.9'], 'kmeans': ['3.10.6']} — BA 2.4 yêu cầu ghi/đồng nhất môi trường khi đo runtime | M2/M3 |
| QA-17 | hdbscan_temporal_shift_map.html | thiếu chú thích centroid ≠ GPS trong HTML | M2/M3 |

## C. Đề nghị cụ thể

- **M3:** (1) chỉ rõ run_id đã sinh các con số ở mục A hoặc sửa văn bản theo `hdbscan_metrics.csv`; (2) cho biết lý do 63% cụm chỉ có 1 tọa độ và đề xuất cách báo cáo Silhouette/DBI công bằng; (3) bổ sung chú thích centroid ≠ GPS vào `hdbscan_temporal_shift_map.html`.
- **M2 + M3:** thống nhất cách fit để so runtime (cùng weighted hoặc cùng toàn bộ điểm) và cùng phiên bản Python/numpy khi đo; nếu không đổi, giữ chú thích hiện tại trên mọi hình.
- **M1:** nếu cần heatmap theo lát cắt, xuất tọa độ + số chuyến theo lát cắt (`pickup_coords_by_time_slice.csv` hiện chỉ có thống kê tóm tắt).

Sau khi owner phản hồi, chạy lại `python scripts/run_qa.py`; claim đã sửa sẽ hiển thị `RESOLVED`.
