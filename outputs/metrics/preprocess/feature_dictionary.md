# Từ điển đặc trưng của file giao cho M2, M3

Ma trận đặc trưng của cả ba mô hình **chỉ gồm `x_m`, `y_m`**. Các cột thời gian dùng để lọc lát cắt trước khi phân cụm, không đưa vào khoảng cách.

| Cột | Kiểu | Đơn vị | Vai trò | Mô tả |
|---|---|---|---|---|
| `trip_id` | string | - | khoa | Ma chuyen di, duy nhat; file sap tang dan theo cot nay |
| `trip_start_timestamp` | datetime64[ns] | gio dia phuong Chicago | goc | Thoi diem don, nguon lam tron 15 phut |
| `x_m` | float64 | met | DAC TRUNG | Toa do dong (easting) cua diem don, EPSG:26916 |
| `y_m` | float64 | met | DAC TRUNG | Toa do bac (northing) cua diem don, EPSG:26916 |
| `pickup_lat` | float64 | do | ve ban do | Vi do WGS84 cua TAM vung don; khong dua vao mo hinh |
| `pickup_lon` | float64 | do | ve ban do | Kinh do WGS84 cua TAM vung don; khong dua vao mo hinh |
| `pickup_hour` | int8 | gio 0-23 | loc / EDA | Gio bat dau chuyen |
| `weekday` | int8 | 0-6 | loc / EDA | 0 = thu Hai ... 6 = Chu nhat |
| `is_weekend` | bool | - | loc | weekday thuoc {5, 6} |
| `is_weekday` | bool | - | loc | weekday thuoc {0..4} |
| `daypart` | string | - | EDA | AM_PEAK 07-09h, MIDDAY 10-15h, PM_PEAK 16-18h, NIGHT 19-06h |
| `time_slice` | string | - | LOC LAT CAT | WEEKDAY_AM / WEEKDAY_PM / WEEKEND theo config; con lai la OTHER |
| `pickup_community_area` | Int16 | ma khu 1-77 | dien giai | Ma community area; co the rong |
| `trip_seconds` | float64 | giay | kiem tra | Thoi luong chuyen; khong dua vao mo hinh |
| `trip_miles` | float64 | dam | kiem tra | Quang duong chuyen; khong dua vao mo hinh |
| `flag_zero_duration` | bool | - | co chat luong | trip_seconds <= 0 hoac rong |
| `flag_zero_distance` | bool | - | co chat luong | trip_miles <= 0 hoac rong |
| `flag_speed_gt_80` | bool | - | co chat luong | trip_miles / (trip_seconds / 3600) > speed_flag_mph |
| `flag_end_before_start` | bool | - | co chat luong | trip_end_timestamp < trip_start_timestamp |
| `flag_missing_area` | bool | - | co chat luong | pickup_community_area rong (van co toa do) |
