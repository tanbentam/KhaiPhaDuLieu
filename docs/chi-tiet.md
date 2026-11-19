# Tóm tắt BA Specification v1.1 – Mobility Demand & Traffic Hotspot Detection

Nguồn gốc: `docs/BA_Specification_Mobility_Traffic_Hotspots_v1.1.docx` (mã DM-ST-BA-01, lập ngày 12/11/2026, nhóm 4 người, kế hoạch 4 tuần).
File này là bản rút gọn để nắm nhanh. Khi cần chi tiết (bảng task đầy đủ, câu trả lời vấn đáp mẫu) thì mở file docx gốc.

## 1. Bài toán trong một đoạn

Phân cụm **các điểm đón khách taxi (pickup events)** ở Chicago để tìm **vùng có nhu cầu đón xe cao (pickup-demand hotspot)**. So sánh 3 thuật toán: K-Means (phân hoạch), DBSCAN (mật độ, một ngưỡng eps), HDBSCAN (mật độ phân cấp). Sau đó chạy riêng trên 3 lát cắt thời gian để xem hotspot dịch chuyển ra sao.

Không gọi hotspot là "điểm ùn tắc": dữ liệu chỉ đo số lượt đón, không có tốc độ hay lưu lượng xe.

## 2. Các quyết định đã chốt

| Hạng mục            | Quyết định                                                                                                                                                            |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Dữ liệu chính      | Chicago Taxi Trips 2013–2023, portal ID `wrvz-psew`, khoảng 212M dòng, 23 cột. https://data.cityofchicago.org/Transportation/Taxi-Trips-2013-2023-/wrvz-psew       |
| Dữ liệu dự phòng  | NYC TLC Yellow Taxi; NYC HVFHV. Cả hai chỉ có Taxi Zone ID, phải join shapefile lấy centroid                                                                        |
| Đơn vị phân tích | 1 lượt pickup. Drop-off chỉ là nhánh đối chiếu, không fit chung với pickup                                                                                     |
| Giới hạn dữ liệu  | Toạ độ là **centroid** của census tract/community area, không phải GPS. Thời gian làm tròn 15 phút                                                      |
| Cửa sổ dữ liệu    | 1 tháng hoặc 4 tuần đủ ngày thường và cuối tuần                                                                                                               |
| Lấy mẫu             | Random hoặc stratified theo weekday x hour, seed 42, lưu `trip_id`. Không lấy N dòng đầu. Mỗi lát cắt nên có ít nhất 20k điểm                          |
| Cỡ mẫu theo RAM     | 8 GB: 30–50k. 16 GB: 100–150k. 32 GB: 200–300k. Pilot trước: 10k, 30k, 50k                                                                                          |
| Hệ toạ độ         | Chiếu WGS84 (EPSG:4326) sang **UTM 16N (EPSG:26916)**, đơn vị mét. Không dùng Euclidean trên độ lat/lon. Haversine chỉ dùng cho phân tích độ nhạy |
| Vector đặc trưng   | **Chỉ `[x_m, y_m]`**. Không đưa giờ, thứ, quãng đường, giá vào khoảng cách                                                                         |
| Lát cắt thời gian  | WEEKDAY_AM (T2–T6, 07:00–09:59), WEEKDAY_PM (T2–T6, 16:00–18:59), WEEKEND (T7–CN, cả ngày). Lọc bên ngoài rồi fit riêng từng lát                           |
| So sánh công bằng  | Cả 3 thuật toán dùng cùng tập `trip_id`, cùng CRS, cùng metric, cùng cách đo runtime                                                                        |
| Kết quả             | Không điền số liệu trước khi chạy notebook. Mọi con số phải truy về một `run_id`                                                                          |
| Ngoài phạm vi       | App web/mobile, dự báo nhu cầu, tính tốc độ giao thông, kết luận ùn tắc, theo dõi cá nhân                                                                 |

## 3. Pipeline (notebook 01 đến 07)

| Notebook                   | Nội dung                                                                  | Đầu ra chính                                                                                |
| -------------------------- | -------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| 01_data_acquisition_eda    | Tải qua API (`$select`, `$where`, phân trang), kiểm tra schema, EDA | `raw_extract.parquet`, `schema_snapshot.json`, `eda_summary.csv`, ít nhất 6 biểu đồ |
| 02_preprocessing_features  | Làm sạch, tạo đặc trưng thời gian, lấy mẫu, chiếu toạ độ      | `sample_master.parquet`, `model_input.parquet`, `cleaning_log.csv`, manifest             |
| 03_kmeans_baseline         | Elbow, Silhouette, chọn K                                                 | labels, `kmeans_tuning.csv`, bản đồ                                                       |
| 04_dbscan_tuning           | Đồ thị k-distance, lưới eps/min_samples                               | labels, `dbscan_tuning.csv`, bản đồ                                                       |
| 05_hdbscan_tuning          | Tune min_cluster_size và min_samples, stability                           | labels, `hdbscan_run_log.csv`, condensed tree                                                |
| 06_temporal_comparison     | Chạy 3 lát cắt, ghép cụm giữa các lát, đo dịch chuyển (mét)    | `hotspot_tracking.csv`, bản đồ dịch chuyển                                              |
| 07_visualization_reporting | Bản đồ Folium/Plotly, biểu đồ so sánh, PNG cho báo cáo            | các file HTML, PNG 300 dpi                                                                    |

Các bước tiền xử lý P01–P08: load và chuẩn hoá tên cột → parse thời gian, kiểm tra toạ độ → lọc không gian (bbox thô lat 41.64–42.05, lon -87.94 đến -87.52, sau đó dùng polygon) → kiểm tra trùng lặp và logic chuyến → tạo đặc trưng → lấy mẫu phân tầng → chiếu sang EPSG:26916 → tách theo lát cắt.

Quy tắc làm sạch đáng nhớ:

- Thiếu toạ độ: loại khỏi nhánh clustering.
- Duration hoặc distance bằng 0: **gắn cờ**, không tự động loại khỏi clustering.
- Tốc độ trên 80 mph: gắn cờ, thử độ nhạy với ngưỡng 70 và 90 mph.
- Fare hoặc distance quá lớn: gắn cờ bằng IQR hoặc p99.
- Mọi quy tắc phải ghi số dòng trước và sau. Không xoá âm thầm.

Đặc trưng thời gian: `pickup_hour`, `weekday` (0 = thứ Hai), `is_weekend`, `daypart` (AM_PEAK 07–09:59, MIDDAY 10–15:59, PM_PEAK 16–18:59, NIGHT 19–06:59), `time_slice`, `date`.

## 4. Cấu hình khởi điểm (không phải kết quả)

| Thuật toán | Tham số thử                                                                             | Cách chọn                                                                                                                           |
| ------------ | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| K-Means      | K từ 2 đến 15, `k-means++`, n_init 10, max_iter 300, random_state 42                 | Elbow, Silhouette (mẫu con 10–20k điểm), bản đồ, kích thước cụm                                                            |
| DBSCAN       | eps 150, 250, 350, 500, 700, 1000 m (điều chỉnh quanh knee); min_samples 5, 10, 15, 20 | Đồ thị k-distance với k = min_samples. Lưu ý nhiều toạ độ centroid trùng nhau sẽ tạo đoạn phẳng hoặc khoảng cách 0 |
| HDBSCAN      | min_cluster_size 30, 50, 100, 200; min_samples 5, 10, 20; `eom` (thử `leaf` phụ)    | **Đặt min_samples tường minh** và giữ cố định khi tune min_cluster_size                                                |

## 5. Đánh giá

- Silhouette, Davies-Bouldin, Calinski-Harabasz: tính trên các điểm đã được gán cụm, luôn ghi kèm số điểm dùng, Noise Ratio và coverage.
- Noise Ratio = số điểm nhãn -1 / tổng số điểm. K-Means có Noise Ratio = 0 do thiết kế, không phải ưu điểm.
- Báo cáo thêm: số cụm, phân bố kích thước cụm, runtime, bộ nhớ đỉnh (`psutil`, không đo được thì ghi N/A), độ ổn định qua 2–3 lần lấy mẫu.
- DBCV là tuỳ chọn nếu còn thời gian.
- Không xếp hạng mô hình bằng một chỉ số duy nhất. Phải có bản đồ cùng extent cho cả 3 mô hình.
- So sánh giữa các lát cắt: ghép cụm theo khoảng cách centroid, không so nhãn 0/1/2.

## 6. Phân vai M1–M4 (chưa gán tên thật)

Tài liệu dùng mã M1–M4 và để nhóm tự gán tên. Thành viên trong `plan.md`: Chu Thành Tân, Hoàng Thị Ngọc, Hà Xuân Đại, Hoàng Tuấn Bảo.

Đã chốt:
- **Chu Thành Tân nhận M2** (K-Means, DBSCAN, chốt ngày 13/11/2026).
- **Hoàng Thị Ngọc nhận M1** (Data Engineer & EDA Lead, chốt ngày 17/11/2026).
- **Hoàng Tuấn Bảo nhận M3** (Advanced Modeling & Temporal Lead, cập nhật ngày 19/11/2026).
- M4 (Visualization, Report & Pitch Lead) còn lại cho Hà Xuân Đại (chờ xác nhận).
Đề xuất kèm theo, chưa được nhóm duyệt: máy của Tân (RAM 16 GB, RTX 4060) chạy benchmark chính thức cho cả 3 thuật toán, để runtime và bộ nhớ được đo trên cùng phần cứng.

| Mã | Vai trò                           | Sở hữu                                                               | Notebook |
| --- | ---------------------------------- | ---------------------------------------------------------------------- | -------- |
| M1  | Data Engineer & EDA Lead           | Nguồn dữ liệu, schema, EDA, làm sạch, CRS, lấy mẫu, manifest    | 01, 02   |
| M2  | Baseline Modeling Lead             | K-Means, DBSCAN, file log và hàm đánh giá dùng chung             | 03, 04   |
| M3  | Advanced Modeling & Temporal Lead  | HDBSCAN, stability, 3 lát cắt, dịch chuyển hotspot                 | 05, 06   |
| M4  | Visualization, Report & Pitch Lead | Bản đồ, biểu đồ, Word, slide, README, QA, điều phối rehearsal | 07       |

Nguyên tắc: người viết phần kỹ thuật là người xác nhận số liệu và trả lời chính khi bị hỏi. M4 chỉ biên tập, không tự sửa số liệu. Review chéo M2 với M3, M1 với M4. Có một buổi teach-back nội bộ.

Thứ tự bàn giao: H01 data contract (M1 → mọi người) → H02 EDA → H03 baseline (M2) → H04 HDBSCAN (M3) → H05 bảng so sánh chung → H06 gói hình ảnh → H07 các phần báo cáo → H08 bản final.

## 7. Lịch 4 tuần

| Tuần | Việc chính                                                                                                                 | Mốc                                                                         |
| ----- | ---------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| 1     | Chốt dataset và câu hỏi nghiên cứu, kiểm tra schema, viết script tải, mẫu pilot, EDA, duyệt quy tắc lọc và CRS | MS1: dataset chốt, báo cáo EDA, quy tắc tiền xử lý được duyệt     |
| 2     | Pipeline tiền xử lý; K-Means, DBSCAN, HDBSCAN trên pilot; chốt lưới tham số                                          | MS2: 3 mô hình chạy trên cùng mẫu 50k, có log runtime và Noise Ratio |
| 3     | Chạy mẫu chính thức trên 3 lát cắt, tính chỉ số, bản đồ, báo cáo nháp v0.8                                   | MS3: bảng so sánh, bản đồ AM/PM/weekend                                 |
| 4     | Clean-run trên môi trường sạch, hoàn thiện Word, slide, README, 2 lần rehearsal                                      | MS4: bản final có tag, rehearsal 10–15 phút                              |

Không được bỏ: pilot HDBSCAN, đánh giá noise, rehearsal. Đổi dataset, CRS hoặc cách lấy mẫu sau tuần 2 phải mở issue và đánh giá tác động.

## 8. Sản phẩm nộp

- **Báo cáo Word:** gồm tóm tắt và các chương 1 Giới thiệu, 2 Dữ liệu và EDA, 3 Tiền xử lý, 4 Cơ sở lý thuyết, 5 Thực nghiệm, 6 Kết quả và thảo luận, 7 Kết luận, kèm tài liệu tham khảo và phụ lục.
- **Slide:** khoảng 12 slide trong 12 phút, chia khung 1–2p (slide 1–2), 2p (3–4), 3–4p (5–7), 3–4p (8–10), 1–2p (11–12). Chuẩn bị PNG offline dự phòng.
- **Repo:** `config/`, `data/{raw,interim,processed,manifests}` (không commit dữ liệu thô), `notebooks/01–07`, `src/{data,preprocessing,models,evaluation,visualization}`, `outputs/{metrics,labels,figures,maps}`, `reports/`, `logs/`.
- **README:** nguồn và link dữ liệu, cách tải, môi trường, thứ tự chạy 01→07, các lỗi thường gặp.

## 9. Rủi ro chính và cách xử lý dự phòng

- R01: DBSCAN tràn RAM (bộ nhớ O(n^2) trong trường hợp xấu).
- R02: HDBSCAN chạy chậm.
- R03: hiểu nhầm centroid là GPS.
- R06: sai CRS hoặc đảo thứ tự lat/lon.
- R09: chỉ số thiên vị K-Means.
- R11: gọi nhầm hotspot là "ùn tắc".

Cách xử lý dự phòng: tăng dần cỡ mẫu 10k → 30k → 50k → 100k, dừng khi RAM vượt 80–85%. Nếu HDBSCAN không chạy nổi 100k thì dùng chung mẫu 50k cho bảng so sánh chính. Không bao giờ so sánh kết quả chạy trên các mẫu khác nhau.

## 10. Vấn đáp: 10 câu cần chuẩn bị (câu trả lời mẫu nằm ở Phần 7 file docx)

1. Vì sao chọn dataset này, nó có đại diện cho toàn bộ giao thông không? (M1)
2. Centroid khác GPS ra sao? (M1)
3. Vì sao không đưa quãng đường, thời lượng, giờ vào vector? (M2)
4. K-Means tối ưu gì, vì sao chia sai cụm dọc tuyến đường? (M2)
5. Core, border và noise trong DBSCAN? (M2)
6. Chọn eps thế nào, đơn vị là gì? (M2)
7. HDBSCAN khác DBSCAN ở đâu, có luôn tốt hơn không? (M3)
8. Ý nghĩa min_cluster_size và min_samples? (M3)
9. Silhouette cao nhất có phải mô hình tốt nhất không? (M2, M3)
10. Có gọi hotspot là điểm ùn tắc được không? (M4)

Cấu trúc trả lời: định nghĩa → quyết định của nhóm → bằng chứng (bảng, run_id) → giới hạn.

## 11. Điểm còn mở hoặc cần lưu ý

- Bảng quản lý tài liệu ghi phiên bản 1.0, tiêu đề ghi 1.1.
- Mới gán M2 (Tân); M1, M3, M4 chưa gán.
- Đề bài yêu cầu "so sánh với phương pháp hiện đại". Spec coi HDBSCAN là đại diện cải tiến và để dự báo nhu cầu ngoài phạm vi. Cần nhóm xác nhận như vậy là đủ hay bổ sung thêm phương pháp.
- Tên cột Chicago phải kiểm tra lại bằng `df.columns` khi tải, không hard-code theo tài liệu.

## 12. Tài liệu tham khảo (link)

- [1] Chicago Taxi Trips: https://data.cityofchicago.org/Transportation/Taxi-Trips-2013-2023-/wrvz-psew
- [2] Schema tham khảo: https://www.johnsnowlabs.com/marketplace/chicago-taxi-trips/
- [3] NYC TLC: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
- [4] Yellow dictionary: https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf
- [5] HVFHV dictionary: https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_hvfhs.pdf
- [6] HDBSCAN chọn tham số: https://hdbscan.readthedocs.io/en/latest/parameter_selection.html
- [7] K-Means: https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html
- [8] DBSCAN: https://scikit-learn.org/stable/modules/generated/sklearn.cluster.DBSCAN.html
- [9] HDBSCAN API: https://hdbscan.readthedocs.io/en/latest/api.html
- [10] Đánh giá phân cụm: https://scikit-learn.org/stable/modules/clustering.html
- [11] Plotly heatmap: https://plotly.com/python/heatmaps/
