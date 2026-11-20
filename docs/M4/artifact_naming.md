# Quy ước đặt tên artifact và `run_id` (M4-01)

## run_id (do `src/evaluation/runlog.py` sinh, M4 chỉ đọc)
`<algorithm>_<TIME_SLICE>_<YYYYMMDD-HHMMSS>` ví dụ `hdbscan_WEEKEND_20261119-215256`.
Mọi con số trên hình/bảng phải truy về một `run_id` trong `outputs/metrics/metrics_comparison.csv`. Không trộn run khác `sample_id` trên cùng một hình (ví dụ `pilot_m2_v0` với `master_v1`).

## Thuật toán và lát cắt
- `kmeans`, `dbscan`, `hdbscan` (chữ thường). DBSCAN chỉ dùng cấu hình chính A (1%, 1500 m).
- `WEEKDAY_AM`, `WEEKDAY_PM`, `WEEKEND`.

## Tên file M4 (ánh xạ BA)
| BA | File | Ghi chú |
|---|---|---|
| H05 | `outputs/metrics/metrics_comparison.csv` | 9 dòng + 3 cột diễn giải `weighted_fit`, `metric_scope`, `comparable_runtime` |
| M4-03 | `outputs/maps/pickup_demand_heatmap.html`, `outputs/figures/comparison/pickup_demand_heatmap.png` | BA 2.5 gọi `pickup_heatmap.html`; dùng một tên duy nhất |
| M4-04 | `outputs/maps/cluster_map_<algo>.html`, `cluster_map_comparison.html`, `outputs/figures/comparison/algorithm_comparison[_<SLICE>].png` | tâm cụm, cùng extent |
| M4-05 | `outputs/figures/comparison/runtime_noise_comparison.png`, `temporal_hotspot_comparison.png`, `outputs/maps/cluster_comparison.html` | |
| M4-11 | `outputs/maps/<algo>_points_<SLICE>.html` | cấp điểm, cần nhãn |
| QA | `outputs/metrics/qa_checks_m4.csv`, `qa_claim_register.csv`, `outputs/m4_artifact_manifest.csv` | sinh tự động |

Hình/bản đồ do M2/M3 sinh giữ nguyên tên và vị trí cũ (`outputs/figures/`, `outputs/maps/`); M4 không ghi đè. Phiên bản dữ liệu tăng (`master_v2`) → tên file M4 thêm hậu tố `_v2`.

## Git
Nhánh `m<N>/<chu-de>`; commit `feat(m4): ...`, `docs(m4): ...`, `fix(m4): ...`. Tag: `v1.0-tech` (kỹ thuật), `release_v1.0` (cuối).
