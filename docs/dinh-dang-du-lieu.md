# Định dạng dữ liệu và log kết quả dùng chung

Trạng thái: **ĐỀ XUẤT của M2 (Tân), chờ M1 và M3 xác nhận.** Ngày soạn: 13/11/2026.
Căn cứ: BA Spec v1.1 (`docs/chi-tiet.md`). Những chỗ spec chưa nói rõ hoặc nói chưa thống nhất được đánh dấu **[cần chốt]**.

Mục đích: M2 và M3 đọc cùng một file đầu vào và ghi kết quả theo cùng một khuôn. Nhờ vậy M4 ghép bảng so sánh mà không phải sửa số liệu, và so sánh 3 thuật toán là công bằng.

## 1. Quy ước chung

- Mọi đường dẫn đều tương đối so với gốc repo, không dùng `D:\...`, để chạy được cả trên Colab.
- File dữ liệu lớn không commit lên Git. Ai cần thì tải từ link chung (Drive) hoặc tự tạo lại bằng notebook của M1.
- Định dạng bảng là Parquet. Riêng bảng tổng hợp nhỏ dùng CSV (UTF-8, dấu phẩy, dấu chấm thập phân).
- Seed mặc định là 42.

## 2. Đầu vào M1 giao cho M2 và M3

File: `data/processed/model_input.parquet`, kèm `data/manifests/model_input_manifest.json`.

| Cột | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `trip_id` | string | Có | Duy nhất, không null. File sắp xếp tăng dần theo cột này |
| `trip_start_timestamp` | datetime64 | Có | Giờ địa phương Chicago, làm tròn 15 phút như nguồn gốc |
| `x_m` | float64 | Có | Toạ độ EPSG:26916, đơn vị mét, không null |
| `y_m` | float64 | Có | Như trên |
| `pickup_lat` | float64 | Có | WGS84, chỉ dùng để vẽ bản đồ, không đưa vào mô hình |
| `pickup_lon` | float64 | Có | Như trên |
| `pickup_hour` | int8 | Có | 0–23 |
| `weekday` | int8 | Có | 0 = thứ Hai … 6 = Chủ nhật |
| `is_weekend` | bool | Có | `weekday` thuộc {5, 6} |
| `time_slice` | string | Có | `WEEKDAY_AM`, `WEEKDAY_PM`, `WEEKEND` hoặc `OTHER` (dòng không thuộc lát cắt nào) **[cần chốt]** |
| `pickup_community_area` | int16 | Không | Dùng để diễn giải cụm nằm ở khu nào |
| `flag_*` | bool | Không | Cờ chất lượng của M1, ví dụ `flag_speed_gt_80`, `flag_zero_distance` |

Nội dung manifest:

```json
{
  "sample_id": "sample_v1",
  "created_at": "2026-11-20T10:00:00",
  "created_by": "M1",
  "source": "https://data.cityofchicago.org/... (wrvz-psew)",
  "query_where": "trip_start_timestamp between ... and ...",
  "date_window": ["2023-..-..", "2023-..-.."],
  "crs": "EPSG:26916",
  "seed": 42,
  "rows_raw": 0,
  "rows_after_cleaning": 0,
  "rows_in_sample": 0,
  "rows_by_time_slice": {"WEEKDAY_AM": 0, "WEEKDAY_PM": 0, "WEEKEND": 0, "OTHER": 0},
  "sha256": "..."
}
```

Các số trong mẫu trên chỉ là chỗ trống, M1 điền khi phát hành. Khi M1 đổi mẫu thì tăng phiên bản (`sample_v2`…), không ghi đè file cũ.

Cách M2 và M3 lấy dữ liệu cho một lát cắt:

```python
df = pd.read_parquet("data/processed/model_input.parquet")
part = df[df["time_slice"] == "WEEKDAY_AM"]   # giữ nguyên thứ tự trip_id
X = part[["x_m", "y_m"]].to_numpy(dtype="float64")
```

## 3. Nhãn cụm (M2 và M3 ghi)

File: `outputs/labels/<run_id>.parquet`

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `trip_id` | string | Cùng thứ tự với đầu vào |
| `label` | int32 | -1 là nhiễu (K-Means không có -1) |
| `probability` | float32 | Chỉ HDBSCAN có (`probabilities_`), thuật toán khác để null |

## 4. Log mỗi lần chạy (M2 và M3 dùng chung một file)

File: `outputs/metrics/run_log.csv`. Mỗi lần fit ghi thêm một dòng, không sửa dòng cũ.

`run_id` = `<thuat_toan>_<time_slice>_<YYYYMMDD-HHMMSS>`, ví dụ `dbscan_WEEKDAY_AM_20261120-143005`.

| Cột | Ý nghĩa |
|---|---|
| `run_id` | Mã lần chạy, trùng với tên file nhãn |
| `timestamp` | Thời điểm chạy |
| `member` | M2 hoặc M3 |
| `algorithm` | `kmeans`, `dbscan`, `hdbscan` |
| `time_slice` | Lát cắt đã chạy |
| `sample_id` | Lấy từ manifest, để biết chạy trên mẫu nào |
| `n_points` | Số điểm đưa vào fit |
| `params` | JSON tham số, ví dụ `{"eps": 350, "min_samples": 10}` |
| `n_clusters` | Số cụm, không tính nhiễu |
| `n_noise`, `noise_ratio`, `coverage` | Theo công thức trong spec |
| `size_min`, `size_median`, `size_max`, `largest_share` | Phân bố kích thước cụm |
| `silhouette`, `davies_bouldin`, `calinski_harabasz` | Chỉ tính trên điểm có cụm; để trống nếu có ít hơn 2 cụm |
| `n_points_metric` | Số điểm dùng để tính 3 chỉ số trên |
| `silhouette_sample` | Cỡ mẫu con dùng cho Silhouette (tối đa 20000) |
| `runtime_fit_sec` | Chỉ tính thời gian fit, không tính đọc file |
| `peak_mem_mb` | RAM đỉnh khi fit; đo không được thì để trống |
| `machine` | Ví dụ `Tan-R7-7840H-16GB` hoặc `colab` |
| `lib_versions` | Phiên bản sklearn và hdbscan |
| `git_commit` | Mã commit lúc chạy, nếu có |
| `note` | Ghi chú tự do |

M2 viết sẵn hàm `log_run(...)` và các hàm tính chỉ số trong `src/evaluation/` (mục 2.2–2.3 của checklist M2) để M3 gọi lại, khỏi phải tự viết.

## 5. Những điểm cần chốt

1. Dòng không thuộc 3 lát cắt: giữ lại trong file với `time_slice = "OTHER"`, hay M1 bỏ hẳn?
2. Tên file log: spec chỗ ghi `runs/baseline_run_log.csv`, chỗ ghi `logs/experiment_runs.csv`. Đề xuất dùng một file duy nhất `outputs/metrics/run_log.csv` cho cả M2 và M3.
3. Thư mục `data/`, `outputs/` theo mục 5.3 của spec. Cấu trúc repo thuộc phần M4/M1, cần họ đồng ý.
4. Nơi chia sẻ file dữ liệu lớn (Google Drive?) để thành viên khác và Colab tải về.
5. Bảng tổng hợp cuối `baseline_metrics.csv` (M2) và `hdbscan_metrics.csv` (M3): đề xuất chỉ cần lọc từ `run_log.csv` những `run_id` được chọn, cùng một bộ cột.
