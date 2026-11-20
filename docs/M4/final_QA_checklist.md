# Checklist QA kỹ thuật (M4-09) — chưa gồm rehearsal/Q&A

Chạy: `python scripts/run_qa.py && python scripts/check_repo.py && python -m pytest -q tests`

- [x] Schema 28 cột `RUN_LOG_COLUMNS` ở `baseline_metrics.csv`, `hdbscan_metrics.csv` (QA-01)
- [x] Cùng `sample_id`, cùng `n_points` theo lát cắt, 9 run_id duy nhất (QA-02..04)
- [x] `n_points_metric = n_points − n_noise`; K-Means noise = 0 (QA-05/06)
- [x] Bảng cụm khớp metrics: số cụm, Σ chuyến + noise (QA-07/08)
- [x] CRS: x,y (EPSG:26916) ↔ lat,lon sai số < 1 m; trong bbox Chicago (QA-09/10)
- [x] `hotspot_tracking.csv` khớp bảng cụm (QA-11)
- [x] 15/15 artifact M4 tồn tại, manifest SHA-256 (QA-16)
- [x] Chú thích centroid ≠ GPS trong HTML của M4 (QA-17)
- [ ] **Mở — chờ owner:** văn bản M3 lệch CSV (claim C01–C08), cách fit khác nhau (QA-14), môi trường khác nhau (QA-15), Silhouette HDBSCAN (QA-13), dịch chuyển 0 m (QA-12), chú thích trong `hdbscan_temporal_shift_map.html` (QA-17)
- [ ] Mở nhờ máy có dữ liệu: bản đồ cấp điểm (M4-11)
- [ ] Mỗi bản đồ HTML mở được khi có Internet; đã thử PNG dự phòng khi offline (người review ký)
- [ ] Ít nhất một thành viên khác review từng artifact (BA 3.8) — ghi vào `project_board.csv`
