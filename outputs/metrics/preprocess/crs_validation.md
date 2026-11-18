# Kiểm tra hệ toạ độ (M1-06)

- Hệ chiếu: **EPSG:26916** (NAD83 / UTM zone 16N), đơn vị trục: metre.
- Vùng áp dụng của hệ chiếu: kinh độ -90.0 đến -84.0, vĩ độ 23.97 đến 84.0 (North America - between 90°W and 84°W - onshore and offshore. Canada - Manitoba; Nunavut; Ontario. United States (USA) - Alabama; Arkansas; Florida; Georgia; Indiana; Illinois; Kentucky; Louisiana; Michigan; Minnesota; Mississippi; Missouri; North Carolina; Ohio; Tennessee; Wisconsin.).
- Mọi điểm nằm trong vùng áp dụng: **có** (304 toạ độ khác nhau).
- Phạm vi sau khi chiếu: x từ 424312 đến 455498 m, y từ 4612218 đến 4651790 m (rộng 31.19 km, dài 39.57 km).
- Chiếu ngược về lat/lon: lệch lớn nhất **2.47e-09 m**.
- Khoảng cách Euclid trên x/y so với khoảng cách trắc địa, 1990 cặp điểm ngẫu nhiên: lệch tương đối lớn nhất **0.0375%**, trung vị 0.0363%, lệch tuyệt đối lớn nhất 14.09 m.

Kết luận dùng cho mô hình: khoảng cách Euclid trên `[x_m, y_m]` là khoảng cách mét; `eps` của DBSCAN và các ngưỡng khoảng cách khác đặt trực tiếp bằng mét. Không tính Euclid trên độ lat/lon.
