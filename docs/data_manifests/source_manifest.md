# Nguồn dữ liệu thô (M1-01, M1-02)

File này do `src/data/extract.py` sinh ra khi tải, không sửa tay.

| Hạng mục | Giá trị |
|---|---|
| Bộ dữ liệu | Taxi Trips (2013-2023) (`wrvz-psew`) |
| Trang nguồn | https://data.cityofchicago.org/Transportation/Taxi-Trips-2013-2023-/wrvz-psew |
| Endpoint | https://data.cityofchicago.org/resource/wrvz-psew.json |
| Thời điểm tải (UTC) | 2026-11-18T14:15:48+00:00 |
| Nguồn cập nhật lần cuối (UTC) | 2024-02-07T20:40:12+00:00 |
| Giấy phép | See Terms of Use |
| Cửa sổ thời gian | 2023-04-17 đến 2023-05-14 (trọn ngày) |
| Điều kiện `$where` | `trip_start_timestamp >= '2023-04-17T00:00:00' AND trip_start_timestamp < '2023-05-15T00:00:00'` |
| Sắp xếp khi phân trang | `trip_id` |
| Số dòng server đếm | 554,794 |
| Số dòng tải về | 554,794 |
| Số cột | 17 |
| File | `raw_extract_20230417_20230514.parquet` |
| sha256 | `f249fc450c7d0d3cd9f7ce3a5ccb5d5b8bf251d9bc43e1a2eafe3ca1ceafcaa1` |

Cột đã lấy (`$select`): `trip_id`, `trip_start_timestamp`, `trip_end_timestamp`, `trip_seconds`, `trip_miles`, `pickup_census_tract`, `dropoff_census_tract`, `pickup_community_area`, `dropoff_community_area`, `fare`, `tips`, `trip_total`, `company`, `pickup_centroid_latitude`, `pickup_centroid_longitude`, `dropoff_centroid_latitude`, `dropoff_centroid_longitude`.

## Lưu ý khi dùng

- Toạ độ pickup/dropoff là **tâm của census tract hoặc community area**, không phải GPS. Kết quả chỉ diễn giải ở mức khu vực.
- Thời gian bắt đầu/kết thúc chuyến được nguồn **làm tròn tới 15 phút**. Không phân tích biến động dưới 15 phút.
- Nguồn chỉ gồm các chuyến taxi được báo cáo cho thành phố, không đại diện toàn bộ giao thông Chicago.
- File thô giữ nguyên giá trị dạng chuỗi như API trả về, chưa lọc và chưa ép kiểu. Ép kiểu bằng `parse_types()`.
- Cổng dữ liệu trả 403 khi truy cập từ Việt Nam; việc tải chạy trên Google Colab.
