"""Dung lai TOAN BO artifact truc quan cua M4 tu CSV da phat hanh (khong can du lieu tho / nhan).

Chay tu goc repo:
    python scripts/build_m4.py            # day du (PNG 300 dpi)
    python scripts/build_m4.py --fast     # PNG 100 dpi de chay thu

Dau vao : outputs/metrics/{baseline_metrics,hdbscan_metrics,*_clusters_master_v1,hotspot_tracking}.csv,
          outputs/metrics/eda/pickup_coords.csv
Dau ra  : xem docs/M4/artifact_naming.md; manifest: outputs/m4_artifact_manifest.csv
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from .comparison import (comparison_plotly, merge_metrics, runtime_noise_figure,
                         temporal_comparison_figure, write_metrics_comparison)
from .m4_maps import (algorithm_comparison_png, cluster_map_algorithm, cluster_map_comparison,
                      _global_nmax, load_cluster_tables, pickup_heatmap, shared_extent)
from .style import ALGO_ORDER

# artifact -> (nguon CSV, ham tao). Dung de ghi manifest truy vet (NFR-03).
SOURCES = {
    "outputs/metrics/metrics_comparison.csv": "baseline_metrics.csv + hdbscan_metrics.csv",
    "outputs/figures/comparison/runtime_noise_comparison.png": "metrics_comparison.csv",
    "outputs/figures/comparison/temporal_hotspot_comparison.png": "hdbscan_clusters_master_v1.csv + hotspot_tracking.csv",
    "outputs/maps/cluster_comparison.html": "metrics_comparison.csv",
    "outputs/maps/pickup_demand_heatmap.html": "eda/pickup_coords.csv",
    "outputs/figures/comparison/pickup_demand_heatmap.png": "eda/pickup_coords.csv",
    "outputs/maps/cluster_map_kmeans.html": "kmeans_clusters_master_v1.csv",
    "outputs/maps/cluster_map_dbscan.html": "dbscan_clusters_master_v1.csv (cau hinh chinh A)",
    "outputs/maps/cluster_map_hdbscan.html": "hdbscan_clusters_master_v1.csv",
    "outputs/maps/cluster_map_comparison.html": "3 bang cum master_v1",
    "outputs/figures/comparison/algorithm_comparison.png": "3 bang cum master_v1",
    "outputs/figures/comparison/algorithm_comparison_WEEKDAY_AM.png": "3 bang cum master_v1",
    "outputs/figures/comparison/algorithm_comparison_WEEKDAY_PM.png": "3 bang cum master_v1",
    "outputs/figures/comparison/algorithm_comparison_WEEKEND.png": "3 bang cum master_v1",
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_all(root: str | Path = ".", dpi: int = 300) -> pd.DataFrame:
    root = Path(root)
    out = {}
    # H05: bang gop
    write_metrics_comparison(root)
    df = merge_metrics(root)
    # Bieu do metrics + temporal (PNG)
    fig_dir = root / "outputs" / "figures" / "comparison"
    runtime_noise_figure(df, fig_dir / "runtime_noise_comparison.png", dpi=dpi)
    clusters = pd.read_csv(root / "outputs" / "metrics" / "hdbscan_clusters_master_v1.csv")
    tracking = pd.read_csv(root / "outputs" / "metrics" / "hotspot_tracking.csv")
    temporal_comparison_figure(clusters, tracking, fig_dir / "temporal_hotspot_comparison.png", dpi=dpi)
    comparison_plotly(df, root / "outputs" / "maps" / "cluster_comparison.html")
    # Ban do
    pickup_heatmap(root)
    tables = load_cluster_tables(root)
    pc = pd.read_csv(root / "outputs" / "metrics" / "eda" / "pickup_coords.csv")
    extent = shared_extent(tables, pc)
    n_max = _global_nmax(tables)
    for a in ALGO_ORDER:
        cluster_map_algorithm(a, tables[a], extent, n_max, root / "outputs" / "maps" / f"cluster_map_{a}.html")
    cluster_map_comparison(tables, extent, n_max, root / "outputs" / "maps" / "cluster_map_comparison.html")
    algorithm_comparison_png(tables, extent, n_max, fig_dir, dpi=dpi)
    # Manifest
    rows = []
    for rel, src in SOURCES.items():
        p = root / rel
        rows.append(dict(artifact=rel, source=src, size_kb=round(p.stat().st_size / 1024, 1),
                         sha256=sha256(p), generated_by="scripts/build_m4.py", owner="M4"))
    man = pd.DataFrame(rows)
    man.to_csv(root / "outputs" / "m4_artifact_manifest.csv", index=False)
    return man
