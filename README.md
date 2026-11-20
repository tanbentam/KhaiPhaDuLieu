# Phân tích nhu cầu di chuyển và phát hiện điểm nóng giao thông (Chicago Taxi)

Đồ án Khai phá dữ liệu — nhóm 4 người. Phân cụm **điểm đón khách taxi** ở Chicago để tìm vùng có **nhu cầu đón cao (pickup-demand hotspot)**, so sánh K-Means, DBSCAN, HDBSCAN trên 3 lát cắt thời gian (ngày thường sáng / chiều, cuối tuần). Đặc tả: `docs/BA_Specification_Mobility_Traffic_Hotspots_v1.1.docx`.

> Hotspot ở đây là nhu cầu **đón khách**, không phải ùn tắc. Tọa độ là **centroid** của census tract/community area, **không phải GPS**; thời gian làm tròn 15 phút.

## Sơ đồ chạy
```
01 tải + EDA → 02 tiền xử lý (EPSG:26916) → 03 K-Means → 04 DBSCAN → 05 HDBSCAN → 06 so sánh theo thời gian → 07 trực quan hóa & đóng gói
   (M1)            (M1)                      (M2)        (M2)         (M3)             (M3)                      (M4)
```

## Dữ liệu
- Nguồn: Chicago Taxi Trips 2013–2023, portal ID `wrvz-psew` — https://data.cityofchicago.org/Transportation/Taxi-Trips-2013-2023-/wrvz-psew (dữ liệu mở của Thành phố Chicago; xem điều khoản trên portal).
- Cửa sổ: 17/04/2023–14/05/2023 (4 tuần). Bản phát hành `master_v1`: 535.167 dòng, 304 tọa độ duy nhất, CRS `EPSG:26916` (UTM 16N, mét); đặc trưng phân cụm chỉ gồm `[x_m, y_m]`.
- `data/` **không** nằm trong Git. Tạo lại bằng notebook 01–02 hoặc lấy từ link Drive chung của nhóm, đặt vào `data/raw`, `data/processed`, `data/manifests` (đường dẫn khai báo ở `config/experiment.yaml`).
- Giới hạn: centroid thay vì GPS; chỉ điểm đón (drop-off là nhánh đối chiếu); 1 tháng nên không kết luận theo mùa.

## Môi trường
- Python 3.10–3.13; RAM khuyến nghị 16 GB nếu chạy lại HDBSCAN trên toàn bộ điểm (phần M4 chỉ cần < 1 GB).
```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (Linux/macOS: source .venv/bin/activate)
python -m pip install -r requirements.txt
pip install notebook              # nếu chạy notebook trên máy cá nhân (Colab đã có sẵn)
```
Colab: xem `docs/Phan 2/2.4-chay-tren-colab.md`.

## Thứ tự chạy
| Bước | Notebook | Cần `data/` | Đầu ra chính |
|---|---|---|---|
| 1–2 | `01_data_acquisition_eda`, `02_preprocessing_features` | tải API | `data/processed/*`, `outputs/metrics/eda/`, `preprocess/` |
| 3 | `03_kmeans_baseline` | có | `kmeans_*`, nhãn, bản đồ |
| 4 | `04_dbscan_tuning` | có | `dbscan_*`, nhãn, bản đồ |
| 5 | `05_hdbscan_tuning` | có | `hdbscan_*`, nhãn |
| 6 | `06_temporal_comparison` | có | `hotspot_tracking.csv`, bản đồ dịch chuyển |
| 7 | `07_visualization_reporting` | **không** | `metrics_comparison.csv`, `outputs/figures/comparison/`, bản đồ chuẩn hóa |

Tái tạo riêng phần trực quan (không cần dữ liệu thô) và kiểm tra:
```bash
python scripts/build_m4.py      # 14 artifact + outputs/m4_artifact_manifest.csv (thêm --fast để chạy thử)
python scripts/run_qa.py        # kiểm tra nhất quán số liệu + đối chiếu văn bản với CSV
python scripts/check_repo.py    # repo sạch: không dữ liệu lớn, secret, đường dẫn cá nhân
python -m pytest -q tests
```
Cấu hình (seed 42, CRS, lát cắt, tham số mô hình): `config/experiment.yaml`, `config/cleaning_rules.yaml`.

## Kết quả kỳ vọng (tên file)
- `outputs/metrics/`: `baseline_metrics.csv` (M2), `hdbscan_metrics.csv` (M3), **`metrics_comparison.csv`** (9 dòng gộp), `*_clusters_master_v1.csv`, `hotspot_tracking.csv`, `run_log.csv`, `qa_*.csv`.
- `outputs/figures/comparison/`: `runtime_noise_comparison.png`, `temporal_hotspot_comparison.png`, `algorithm_comparison*.png`, `pickup_demand_heatmap.png` (300 dpi, bản dự phòng offline).
- `outputs/maps/`: `pickup_demand_heatmap.html`, `cluster_map_{kmeans,dbscan,hdbscan,comparison}.html`, `cluster_comparison.html` (Plotly) cùng các bản đồ của M2/M3.
- Nhãn cụm `-1` = **noise** (không thuộc cụm nào). K-Means không có noise do thiết kế, không phải ưu điểm. Silhouette/DBI/CH chỉ tính trên điểm có nhãn; luôn đọc cùng `coverage = 1 − noise_ratio`. Không ghi giá trị metric cố định ở đây — mở file CSV.

## Quy ước và tài liệu
`CONTRIBUTING.md`, `docs/M4/` (phân công, quy ước tên, style, QA, ghi nhận trả về owner), `docs/checklist-m2.md`, `docs/checklist-m3.md`.

## Khắc phục lỗi thường gặp
| Lỗi | Cách xử lý |
|---|---|
| `ModuleNotFoundError: folium/plotly/...` | `pip install -r requirements.txt` trong đúng venv |
| `UnicodeDecodeError` khi cài trên Windows | giữ `requirements.txt` chỉ ký tự ASCII |
| `MemoryError` khi chạy HDBSCAN | giảm mẫu / dùng Colab; xem `config/experiment.yaml` (`evaluation.ram_stop_ratio`) |
| `FileNotFoundError: data/...` | chưa có dữ liệu; chạy notebook 01–02 hoặc tải từ Drive nhóm |
| Bản đồ HTML trống / `L is not defined` | cần Internet (Leaflet, nền OSM); dùng PNG trong `outputs/figures/comparison/` |
| API Socrata timeout | chạy lại notebook 01 (tải theo từng khoảng ngày, có phân trang) |
| CRS mismatch / điểm ngoài Chicago | kiểm tra thứ tự lat/lon; `python scripts/run_qa.py` (QA-09/10) |
| `git status` báo hàng trăm file đổi | khác biệt CRLF/LF; `.gitattributes` đã chuẩn hóa — commit riêng |
