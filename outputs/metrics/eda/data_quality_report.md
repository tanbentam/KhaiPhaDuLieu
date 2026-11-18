# Báo cáo chất lượng dữ liệu thô (M1-03)

Nguồn: Chicago Data Portal, Taxi Trips (wrvz-psew), 2023-04-17 đến 2023-05-14. Toạ độ là tâm vùng; thời gian làm tròn 15 phút.

Số dòng thô: **554,794**. File này do `src/data/eda.py` sinh ra từ file thô, chỉ gồm số liệu; không sửa tay. Chạy lại notebook 01 để cập nhật.

## 1. Tỷ lệ thiếu theo cột

| column | n_missing | missing_pct |
|---|---|---|
| trip_id | 0 | 0.0 |
| trip_start_timestamp | 0 | 0.0 |
| trip_end_timestamp | 6 | 0.0011 |
| trip_seconds | 86 | 0.0155 |
| trip_miles | 1 | 0.0002 |
| pickup_census_tract | 287373 | 51.7981 |
| dropoff_census_tract | 294967 | 53.1669 |
| pickup_community_area | 19888 | 3.5848 |
| dropoff_community_area | 54303 | 9.788 |
| fare | 737 | 0.1328 |
| tips | 737 | 0.1328 |
| trip_total | 737 | 0.1328 |
| company | 0 | 0.0 |
| pickup_centroid_latitude | 19627 | 3.5377 |
| pickup_centroid_longitude | 19627 | 3.5377 |
| dropoff_centroid_latitude | 50550 | 9.1115 |
| dropoff_centroid_longitude | 50550 | 9.1115 |

## 2. Các kiểm tra chất lượng

Cột `action` là cách xử lý **dự kiến** ở bước làm sạch (notebook 02): `loai` = bỏ dòng, `danh dau` = giữ dòng và gắn cờ, `giu` = giữ nguyên. Một dòng có thể dính nhiều quy tắc, nên không cộng dồn các tỷ lệ.

| rule | n_rows | pct | action |
|---|---|---|---|
| trip_id thieu | 0 | 0.0 | loai |
| trip_id trung (dong lap lai) | 0 | 0.0 | loai |
| thoi diem don thieu / khong doc duoc | 0 | 0.0 | loai |
| thoi diem don ngoai cua so truy van | 0 | 0.0 | loai |
| thieu toa do don | 19627 | 3.5377 | loai |
| toa do don ngoai khung Chicago | 0 | 0.0 | loai |
| co toa do don nhung thieu ma khu (community area) | 261 | 0.047 | giu |
| thieu toa do tra | 50550 | 9.1115 | giu |
| thoi diem tra truoc thoi diem don | 7 | 0.0013 | danh dau |
| trip_seconds thieu | 86 | 0.0155 | danh dau |
| trip_seconds = 0 | 11033 | 1.9887 | danh dau |
| trip_seconds < 0 | 0 | 0.0 | danh dau |
| trip_miles thieu | 1 | 0.0002 | danh dau |
| trip_miles = 0 | 57545 | 10.3723 | danh dau |
| trip_miles < 0 | 0 | 0.0 | danh dau |
| toc do > 80 mph | 412 | 0.0743 | danh dau |
| fare thieu | 737 | 0.1328 | giu |
| fare < 0 | 0 | 0.0 | danh dau |

Các quy tắc `loai` cộng lại nhiều nhất là 19,627 dòng (3.54%); số chính xác sau khi loại nằm trong cleaning log của notebook 02.

## 3. Ngày có số chuyến lệch so với các ngày cùng thứ

Ngưỡng: lệch quá 15% so với trung vị của các ngày cùng thứ trong cửa sổ.

| date | weekday_name | trips | median_same_weekday | deviation_pct |
|---|---|---|---|---|
| 2023-05-13 | Thứ 7 | 13302 | 16177.5 | -17.8 |
| 2023-05-14 | CN | 12909 | 15614.5 | -17.3 |

## 4. Giới hạn của dữ liệu cần nêu khi diễn giải

- Toạ độ là tâm census tract hoặc community area, không phải GPS.
- Thời gian được làm tròn về bội số 15 phút.
- Mã census tract bị ẩn ở một phần chuyến đi; khi đó toạ độ là tâm community area.
- Số lượt đón phản ánh nhu cầu taxi, không đo mức độ ùn tắc.
