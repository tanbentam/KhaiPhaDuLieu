# Hướng dẫn style trực quan (M4-02)

Mã nguồn: `src/visualization/style.py`. Gọi `apply_matplotlib_style()` đầu mỗi notebook/script.

| Yếu tố | Quy ước |
|---|---|
| Màu thuật toán | K-Means `#0072B2`, DBSCAN `#E69F00`, HDBSCAN `#009E73` (Okabe-Ito, an toàn mù màu), **giống nhau ở mọi hình** |
| Màu lát cắt | AM `#56B4E9`, PM `#D55E00`, Cuối tuần `#CC79A7` (khác họ màu thuật toán để khỏi nhầm) |
| Noise (nhãn −1) | xám `#B0B0B0`, **không bao giờ** tô như hotspot; thường chỉ ghi tỷ lệ trong tiêu đề ô/tên lớp |
| Tiêu đề | nêu đối tượng + lát cắt/thuật toán + bộ dữ liệu (`master_v1`) |
| Chú thích chân hình | nguồn dữ liệu, n, giới hạn (centroid ≠ GPS), nguồn CSV |
| Xuất | PNG 300 dpi cho báo cáo/slide; HTML kèm PNG dự phòng |
| Thang | cột đo cùng đơn vị cùng trục; runtime dùng log và ghi rõ; Silhouette luôn đi kèm Coverage |
| Bản đồ | cùng `shared_extent`, cùng thang diện tích (∝ √ hoặc ∝ số chuyến ở mọi bản đồ so sánh), tâm cụm = `+`, vòng nét đứt = bán kính RMS (không phải ranh giới) |
| Số | dấu chấm ngăn nghìn (`60.498`), dấu phẩy thập phân (`12,6%`) |

## Điều không được làm
- Gọi hotspot là "điểm ùn tắc" (dữ liệu chỉ đo lượt đón).
- Dùng K-Means Noise = 0 để kết luận "bao phủ tốt hơn".
- Xếp hạng bằng một chỉ số duy nhất; so Silhouette khi Coverage khác nhau mà không ghi.
- Đặt hai run khác `sample_id` hoặc khác lát cắt trên cùng hình mà không chú thích.
- Đọc "dịch chuyển 0 m" là "đứng yên tuyệt đối" (giới hạn độ phân giải centroid).
- Hình M2/M3 cũ (ví dụ `temporal_hotspot_shifts.png`, 150 dpi, màu khác) vẫn hợp lệ làm nguồn tham chiếu; sản phẩm cuối dùng bản chuẩn trong `outputs/figures/comparison/`.
