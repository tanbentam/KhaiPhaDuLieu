# Định dạng dữ liệu và log kết quả dùng chung

Trạng thái: **Phần đầu vào (mục 2) ĐÃ CHỐT theo bản phát hành v1 của M1 – Hoàng Thị Ngọc (19/11/2026); phần nhãn và log chạy chung (mục 3–4) đang chờ M3 – Hoàng Tuấn Bảo xác nhận.**
Ngày soạn ban đầu: 13/11/2026. Cập nhật theo M1 v1: 19/11/2026.
Căn cứ: BA Spec v1.1 (`docs/chi-tiet.md`), `docs/CHANGELOG_DATA.md` và `outputs/metrics/preprocess/feature_dictionary.md`.

Mục đích: M2 và M3 đọc cùng nguồn dữ liệu đầu vào do M1 phát hành và ghi kết quả theo cùng một khuôn. Nhờ vậy M4 ghép bảng so sánh mà không phải sửa số liệu, và so sánh 3 thuật toán là công bằng.

## 1. Quy ước chung

- Mọi đường dẫn đều tương đối so với gốc repo, không dùng `D:\...`, để chạy được cả trên Colab.
- File dữ liệu lớn nằm trong `/data/` (không commit lên Git; chỉ ignore `/data/` ở gốc repo để giữ code `src/data/`). Lấy từ Google Drive chung `KhaiPhaDuLieu/data` (`processed/` và `manifests/`), hoặc tái tạo bằng `notebooks/02_preprocessing_features.ipynb`.
- Định dạng bảng là Parquet. Riêng bảng tổng hợp nhỏ dùng CSV (UTF-8, dấu phẩy, dấu chấm thập phân).
- Seed mặc định là 42.

## 2. Đầu vào M1 giao cho M2 và M3 (đã chốt – v1, 19/11/2026)

M1 phát hành 2 file không ghi đè (khi đổi dữ liệu/quy tắc sẽ tăng `release.version` trong `config/experiment.yaml` lên `v2`, ...). Cửa sổ dữ liệu: `2023-04-17` đến `2023-05-14` (4 tuần, 554.794 dòng thô, 535.167 dòng sau làm sạch).

| Bản | File dữ liệu (`paths.*` trong config) | Manifest | `sample_id` | Tổng dòng | 3 lát cắt (AM / PM / WE) | Toạ độ duy nhất | `sha256` (16 ký tự đầu) |
|---|---|---|---|---:|---|---:|---|
| Đầy đủ (M2 dùng) | `data/processed/master_pickups_v1.parquet` (`paths.master`) | `data/manifests/master_pickups_v1_manifest.json` (`paths.master_manifest`) | `master_v1` | 535.167 | 60.498 / 86.617 / 120.571 | 304 | `7459bd276a0b77c3` |
| Mẫu phân tầng 100k | `data/processed/model_input_sample_v1.parquet` (`paths.model_input`) | `data/manifests/model_input_sample_v1_manifest.json` (`paths.manifest`) | `sample_v1` | 100.000 | 11.304 / 16.185 / 22.530 | 222 | `1165613449110766` |

Lưu ý cỡ mẫu: theo đề xuất của M1, M2 chạy trên bản đầy đủ `master_v1` (vì mẫu 100k mất 82/304 toạ độ ít chuyến và hai lát cắt ngày thường dưới 20k dòng). Cần chốt với M3 (Hoàng Tuấn Bảo) xem HDBSCAN chạy được trên `master_v1` hay cần đối chiếu thêm trên cùng tập `sample_v1`.

Cấu trúc 20 cột của cả hai file (đúng thứ tự thực tế):

| STT | Cột | Kiểu | Vai trò | Ghi chú |
|---:|---|---|---|---|
| 1 | `trip_id` | string | Khoá | Duy nhất, không null. File sắp xếp tăng dần theo cột này |
| 2 | `trip_start_timestamp` | datetime64[ns] | Gốc | Giờ địa phương Chicago, làm tròn 15 phút như nguồn gốc |
| 3 | `x_m` | float64 | Đặc trưng | Toạ độ đông EPSG:26916, đơn vị mét, không null |
| 4 | `y_m` | float64 | Đặc trưng | Toạ độ bắc EPSG:26916, đơn vị mét, không null |
| 5 | `pickup_lat` | float64 | Vẽ bản đồ | WGS84 của tâm vùng đón, không đưa vào mô hình |
| 6 | `pickup_lon` | float64 | Vẽ bản đồ | Như trên |
| 7 | `pickup_hour` | int8 | Lọc / EDA | 0–23 |
| 8 | `weekday` | int8 | Lọc / EDA | 0 = thứ Hai … 6 = Chủ nhật |
| 9 | `is_weekend` | bool | Lọc | `weekday` thuộc {5, 6} |
| 10 | `is_weekday` | bool | Lọc | `weekday` thuộc {0..4} |
| 11 | `daypart` | string | EDA | `AM_PEAK`, `MIDDAY`, `PM_PEAK`, `NIGHT` |
| 12 | `time_slice` | string | Lọc lát cắt | `WEEKDAY_AM`, `WEEKDAY_PM`, `WEEKEND`, hoặc `OTHER` (giữ lại, chiếm ~50%) |
| 13 | `pickup_community_area` | Int16 | Diễn giải | Mã khu vực 1–77, có thể rỗng |
| 14 | `trip_seconds` | float64 | Kiểm tra | Thời lượng chuyến (giây), không đưa vào mô hình |
| 15 | `trip_miles` | float64 | Kiểm tra | Quãng đường chuyến (dặm), không đưa vào mô hình |
| 16–20 | `flag_zero_duration`, `flag_zero_distance`, `flag_speed_gt_80`, `flag_end_before_start`, `flag_missing_area` | bool | Cờ chất lượng | Không null; chỉ đánh dấu, không loại dòng |

Nội dung manifest thực tế (`master_pickups_v1_manifest.json`; bản mẫu có thêm mục `sampling`):

```json
{
  "sample_id": "master_v1",
  "file": "master_pickups_v1.parquet",
  "created_at": "2026-11-18T17:45:48+00:00",
  "created_by": "M1",
  "source": "https://data.cityofchicago.org/Transportation/Taxi-Trips-2013-2023-/wrvz-psew",
  "query_where": "trip_start_timestamp >= '2023-04-17T00:00:00' AND trip_start_timestamp < '2023-05-15T00:00:00'",
  "date_window": ["2023-04-17", "2023-05-14"],
  "raw_file": "raw_extract_20230417_20230514.parquet",
  "raw_sha256": "f249fc450c7d0d3cd9f7ce3a5ccb5d5b8bf251d9bc43e1a2eafe3ca1ceafcaa1",
  "crs": "EPSG:26916",
  "features": ["x_m", "y_m"],
  "seed": 42,
  "rows_raw": 554794,
  "rows_after_cleaning": 535167,
  "rows_in_sample": 535167,
  "rows_by_time_slice": {"OTHER": 267481, "WEEKDAY_AM": 60498, "WEEKDAY_PM": 86617, "WEEKEND": 120571},
  "unique_pickup_coords": 304,
  "sha256": "7459bd276a0b77c32d905d9f4bc7165c1c77594e8b92ae5925173d069079da51"
}
```

Cách M2 (và M3) lấy dữ liệu cho một lát cắt:

```python
from src.config import load_config, resolve_path

cfg = load_config()
df = pd.read_parquet(resolve_path(cfg, "master"))     # hoac "model_input" cho sample_v1
part = df[df["time_slice"] == "WEEKDAY_AM"]           # giu nguyen thu tu trip_id
X = part[["x_m", "y_m"]].to_numpy(dtype="float64")
```

Trước khi chạy kết quả cuối, đối chiếu `sha256` của file parquet với trường `"sha256"` trong manifest tương ứng.

## 3. Nhãn cụm (M2 và M3 ghi) [chờ M3 xác nhận]

File: `outputs/labels/<run_id>.parquet`

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `trip_id` | string | Cùng thứ tự với đầu vào |
| `label` | int32 | -1 là nhiễu (K-Means không có -1) |
| `probability` | float32 | Chỉ HDBSCAN có (`probabilities_`), thuật toán khác để null |

## 4. Log mỗi lần chạy (M2 và M3 dùng chung một file) [chờ M3 xác nhận]

File: `outputs/metrics/run_log.csv`. Mỗi lần fit ghi thêm một dòng, không sửa dòng cũ. Thứ tự cột chuẩn nằm trong `RUN_LOG_COLUMNS` (`src/evaluation/runlog.py`, 28 cột).

`run_id` = `<thuat_toan>_<time_slice>_<YYYYMMDD-HHMMSS>`, ví dụ `dbscan_WEEKDAY_AM_20261120-143005`.

| Cột | Ý nghĩa |
|---|---|
| `run_id` | Mã lần chạy, trùng với tên file nhãn |
| `timestamp` | Thời điểm chạy |
| `member` | M2 hoặc M3 |
| `algorithm` | `kmeans`, `dbscan`, `hdbscan` |
| `time_slice` | Lát cắt đã chạy |
| `sample_id` | Lấy từ manifest (`master_v1`, `sample_v1`, ...), để biết chạy trên mẫu nào |
| `n_points` | Số điểm đưa vào fit |
| `params` | JSON tham số, ví dụ `{"eps_m": 2000.0, "min_samples": 605}` |
| `n_clusters` | Số cụm, không tính nhiễu |
| `n_noise`, `noise_ratio`, `coverage` | Theo công thức trong spec |
| `size_min`, `size_median`, `size_max`, `largest_share` | Phân bố kích thước cụm |
| `silhouette`, `davies_bouldin`, `calinski_harabasz` | Chỉ tính trên điểm có cụm; để trống nếu có ít hơn 2 cụm |
| `n_points_metric` | Số điểm dùng để tính 3 chỉ số trên |
| `silhouette_sample` | Cỡ mẫu con dùng cho Silhouette (tối đa 20000) |
| `runtime_fit_sec` | Chỉ tính thời gian fit, không tính đọc file |
| `peak_mem_mb` | RAM đỉnh (RSS) của tiến trình khi fit; đo không được thì để trống |
| `mem_delta_mb` | Phần RAM fit dùng thêm = đỉnh trừ RSS trước khi fit. Dùng cột này để so sánh RAM giữa các thuật toán (bổ sung ở mục 2.3) |
| `machine` | Ví dụ `Tan-R7-7840H-16GB` hoặc `colab` |
| `lib_versions` | Phiên bản python, numpy, sklearn và hdbscan |
| `git_commit` | Mã commit lúc chạy, nếu có |
| `note` | Ghi chú tự do |

M2 đã viết sẵn hàm `run_and_log(...)` và các hàm tính chỉ số trong `src/evaluation/` để M3 gọi lại, không phải tự viết.

## 5. Trạng thái các điểm cần chốt

1. **Dòng không thuộc 3 lát cắt**: Đã chốt với M1 (19/11/2026) — giữ lại trong file với `time_slice = "OTHER"`.
2. **Tên file log chung (`outputs/metrics/run_log.csv`)**: Chờ M3 (Hoàng Tuấn Bảo) xác nhận.
3. **Thư mục `/data/`, `outputs/`**: Đã chốt theo nhánh M1 (19/11/2026); `.gitignore` chỉ bỏ qua `/data/` ở gốc repo.
4. **Nơi chia sẻ file dữ liệu lớn**: Đã chốt — Google Drive `KhaiPhaDuLieu/data` (`processed/`, `manifests/`).
5. **Bảng tổng hợp cuối (`baseline_metrics.csv`, `hdbscan_metrics.csv`) và cỡ mẫu chung**: Đề xuất lọc trực tiếp các `run_id` chốt từ `run_log.csv` (cùng 28 cột); chờ M3 (Hoàng Tuấn Bảo) xác nhận định dạng và khả năng chạy HDBSCAN trên `master_v1`.
