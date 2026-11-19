# Nhật ký phiên bản dữ liệu (M1)

File dữ liệu đã phát hành không bị ghi đè. Mỗi lần đổi dữ liệu, quy tắc làm sạch, cỡ mẫu hoặc seed, M1 tăng `release.version` trong `config/experiment.yaml`, phát hành file mới và thêm một mục vào đây.

## v1 – 19/11/2026

**Trạng thái:** đã tạo và kiểm tra trên máy M1; chờ nhóm chốt cỡ mẫu trước khi M2, M3 dùng cho kết quả cuối.

| | |
|---|---|
| Nguồn | Chicago Data Portal, Taxi Trips (`wrvz-psew`), 17/04/2023–14/05/2023 |
| File thô | `raw_extract_20230417_20230514.parquet`, 554.794 dòng |
| Sau làm sạch | 535.167 dòng (loại 19.627 dòng thiếu toạ độ đón, 3,54%) |
| Hệ toạ độ | EPSG:26916, đơn vị mét |
| Seed | 42 |

| File | Số dòng | sha256 (16 ký tự đầu) |
|---|---|---|
| `data/processed/model_input_sample_v1.parquet` | 100.000 | `1165613449110766` |
| `data/processed/master_pickups_v1.parquet` | 535.167 | `7459bd276a0b77c3` |

Mã sha256 đầy đủ nằm trong hai file manifest ở `data/manifests/`.

Số dòng và số toạ độ khác nhau theo lát cắt:

| Lát cắt | Master: dòng | Master: toạ độ | Mẫu: dòng | Mẫu: toạ độ |
|---|---|---|---|---|
| WEEKDAY_AM | 60.498 | 165 | 11.304 | 142 |
| WEEKDAY_PM | 86.617 | 188 | 16.185 | 152 |
| WEEKEND | 120.571 | 189 | 22.530 | 154 |
| OTHER | 267.481 | 249 | 49.981 | 190 |
| Tất cả | 535.167 | 304 | 100.000 | 222 |

Mẫu phân tầng theo thứ × giờ; mỗi tầng lệch không quá một dòng so với tỷ lệ trong master.

**Cách dùng (M2, M3):**

1. Lấy nhánh có `config/experiment.yaml` mới (`paths.model_input`, `paths.manifest` đã trỏ tới bản v1).
2. Lấy hai thư mục `processed/` và `manifests/` từ Drive `KhaiPhaDuLieu/data` về `data/` của repo (trên Colab thì đã nối sẵn).
3. Trong notebook mô hình, đặt `DATA_KEY = "model_input"`.
4. Đối chiếu `sha256` của file với manifest trước khi chạy kết quả cuối.

**Lưu ý khi dùng:**

- Ma trận đặc trưng chỉ gồm `[x_m, y_m]`. Cột thời gian chỉ để lọc lát cắt.
- Toạ độ là tâm census tract hoặc community area, không phải GPS; rất nhiều dòng trùng toạ độ.
- Mẫu 100.000 dòng **mất 82 trong 304 toạ độ** (các toạ độ rất ít chuyến). Nếu thuật toán chạy được trên toàn bộ dữ liệu hoặc theo kiểu có trọng số thì nên dùng master.
- Các cột `flag_*` chỉ đánh dấu, không dòng nào bị loại vì chúng. Chi tiết ở `outputs/metrics/preprocess/cleaning_log.csv`.

**Tái tạo:** chạy `notebooks/02_preprocessing_features.ipynb` với file thô và config của phiên bản này. Notebook tự đối chiếu kết quả với file đã phát hành và báo lỗi nếu khác.
