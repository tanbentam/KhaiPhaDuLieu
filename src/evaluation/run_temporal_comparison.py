"""Script chay phan tich lat cat thoi gian va theo doi dich chuyen hotspot (M3 - Giai doan 3).

Chuc nang:
1. Doc ket qua cum da fit cho sample hien tai.
2. Thuc hien ghep cap cum (Cluster Matching) giua AM -> PM, PM -> Weekend va AM -> Weekend.
3. Tinh toan khoang cach dich chuyen Delta d (met), bien dong so chuyen va ty trong.
4. Xuat bang tracking va manifest/counts cho cac lat cat.
5. Ve bieu do so sanh su thay doi hotspot outputs/figures/temporal_hotspot_shifts.png.
6. Tao ban do Folium vector dich chuyen outputs/maps/hdbscan_temporal_shift_map.html.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Them goc repo vao sys.path neu can
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_config, resolve_path
from src.evaluation.temporal import build_hotspot_tracking, build_time_slice_manifest
from src.visualization.maps import temporal_shift_map


def main() -> None:
    t_start = time.perf_counter()
    print("=" * 70)
    print("M3 - ADVANCED MODELING & TEMPORAL LEAD: TEMPORAL TRACKING (GIAI DOAN 3)")
    print("=" * 70)

    cfg = load_config()
    data_path = resolve_path(cfg, "master")
    manifest_path = resolve_path(cfg, "master_manifest")
    data_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sample_id = data_manifest["sample_id"]
    metrics_dir = resolve_path(cfg, "run_log").parent
    clusters_path = metrics_dir / f"hdbscan_clusters_{sample_id}.csv"
    metrics_path = metrics_dir / "hdbscan_metrics.csv"

    if not clusters_path.exists():
        raise FileNotFoundError(f"Vui long chay buoc 2 (run_hdbscan) truoc de tao {clusters_path}")
    if not metrics_path.exists():
        raise FileNotFoundError(f"Vui long chay buoc 2 (run_hdbscan) truoc de tao {metrics_path}")

    print(f"\n[1/4] Doc ket qua cum tu {clusters_path.name}...")
    clusters_df = pd.read_csv(clusters_path)
    print(f" -> Da doc {len(clusters_df)} dong cum tren 3 lat cat: {clusters_df['time_slice'].unique().tolist()}")

    metrics_df = pd.read_csv(metrics_path)
    required_metric_columns = [
        "time_slice", "run_id", "n_points", "n_noise", "noise_ratio", "coverage", "n_clusters"
    ]
    missing_metrics = {"sample_id", *required_metric_columns} - set(metrics_df.columns)
    if missing_metrics:
        raise ValueError(f"{metrics_path.name} is missing columns: {sorted(missing_metrics)}")
    if set(metrics_df["sample_id"]) != {sample_id}:
        raise ValueError(f"{metrics_path.name} does not match master sample {sample_id}.")
    required_cluster_columns = {"time_slice", "run_id"}
    missing_cluster_columns = required_cluster_columns - set(clusters_df.columns)
    if missing_cluster_columns:
        raise ValueError(f"{clusters_path.name} is missing columns: {sorted(missing_cluster_columns)}")
    expected_slices = set(cfg["time_slices"])
    if set(clusters_df["time_slice"]) != expected_slices:
        raise ValueError(f"{clusters_path.name} does not contain all configured time slices.")

    source_df = pd.read_parquet(data_path, columns=["time_slice", "trip_start_timestamp"])
    slice_manifest = build_time_slice_manifest(source_df, cfg["time_slices"])
    slice_manifest["sample_id"] = sample_id
    slice_manifest["crs"] = cfg["project"]["crs"]
    count_summary = slice_manifest.merge(
        metrics_df[required_metric_columns],
        on="time_slice",
        how="left",
        validate="one_to_one",
    )
    if count_summary["run_id"].isna().any():
        raise ValueError("hdbscan_metrics.csv is missing one or more configured time slices.")
    if not np.array_equal(count_summary["n_pickups"].to_numpy(), count_summary["n_points"].to_numpy()):
        raise ValueError("M1 slice counts do not match the HDBSCAN run metrics.")
    count_summary["n_clustered"] = count_summary["n_points"] - count_summary["n_noise"]
    count_summary["clustered_pickups_per_hour"] = (
        count_summary["n_clustered"] / count_summary["exposure_hours"]
    )
    for time_slice, slice_clusters in clusters_df.groupby("time_slice"):
        matching_run = count_summary.loc[count_summary["time_slice"] == time_slice, "run_id"]
        if matching_run.empty or set(slice_clusters["run_id"]) != {matching_run.iloc[0]}:
            raise ValueError(f"Cluster details and metrics have different runs for {time_slice}.")

    slice_manifest_path = metrics_dir / "time_slice_manifest.csv"
    slice_manifest.to_csv(slice_manifest_path, index=False)
    counts_path = metrics_dir / "temporal_sample_counts.csv"
    count_summary.to_csv(counts_path, index=False)
    print(f" -> Da luu manifest/counters: {slice_manifest_path.name}, {counts_path.name}")

    # 2. Xay dung bang tracking
    print("\n[2/4] Thuc hien thuat toan ghep cap cum giua cac lat cat (Cluster Matching)...")
    tracking_df = build_hotspot_tracking(clusters_df, max_distance_m=3500.0)
    out_tracking_path = resolve_path(cfg, "run_log").parent / "hotspot_tracking.csv"
    tracking_df.to_csv(out_tracking_path, index=False)
    print(f" -> Da luu bang theo doi hotspot: {out_tracking_path.relative_to(ROOT)} ({len(tracking_df)} cap ghep)")

    # In cac cap MATCHED noi bat
    matched = tracking_df[tracking_df["status"] == "MATCHED"]
    print("\n   --- Top cac cap ghep thanh cong giua AM -> PM ---")
    am_pm = matched[matched["transition"] == "WEEKDAY_AM -> WEEKDAY_PM"]
    for _, r in am_pm.iterrows():
        print(f"   Cum AM {int(r['cluster_from'])} (Khu {r['top_area_from']}) -> "
              f"Cum PM {int(r['cluster_to'])} (Khu {r['top_area_to']}) | "
              f"Dich chuyen: {r['shift_distance_m']:,.0f} m | "
              f"Ty trong: {r['share_from']:.1f}% -> {r['share_to']:.1f}% ({r['delta_share_pct_points']:+.1f}%)")

    # 3. Ve bieu do truc quan hoa su bien dong cua cac hotspot
    print("\n[3/4] Ve bieu do phan tich su bien dong quy mo & ty trong cua cac hotspot...")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Biểu đồ 1: Số chuyến theo cụm ở từng lát cắt
    ax1 = axes[0]
    pivot_trips = clusters_df.pivot(index="cluster", columns="time_slice", values="n_trips").fillna(0)
    pivot_trips.plot(kind="bar", ax=ax1, width=0.8, colormap="tab10")
    ax1.set_title("Quy mo so luot don (trips) theo cum qua cac lat cat", fontsize=11)
    ax1.set_xlabel("Cum (Cluster ID)")
    ax1.set_ylabel("So luot don (pickups)")
    ax1.grid(axis="y", alpha=0.3)
    ax1.legend(title="Lat cat thoi gian")

    # Biểu đồ 2: Tỷ trọng (%) của từng cụm
    ax2 = axes[1]
    pivot_share = (clusters_df.pivot(index="cluster", columns="time_slice", values="share").fillna(0) * 100)
    pivot_share.plot(kind="bar", ax=ax2, width=0.8, colormap="tab10")
    ax2.set_title("Ty trong nhu cau (%) cua tung cum qua cac lat cat", fontsize=11)
    ax2.set_xlabel("Cum (Cluster ID)")
    ax2.set_ylabel("Ty trong (%)")
    ax2.grid(axis="y", alpha=0.3)
    ax2.legend(title="Lat cat thoi gian")

    fig.suptitle("HDBSCAN: Phan tich bien dong nhu cau Hotspot theo thoi gian (Temporal Analysis)", fontsize=13, y=1.02)
    fig.tight_layout()
    fig_path = resolve_path(cfg, "figures_dir") / "temporal_hotspot_shifts.png"
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f" -> Da luu bieu do: {fig_path.relative_to(ROOT)}")

    # 4. Tao ban do Folium vector dich chuyen
    print("\n[4/4] Tao ban do Folium vector dich chuyen khong gian - thoi gian...")
    map_shift_path = resolve_path(cfg, "maps_dir") / "hdbscan_temporal_shift_map.html"
    temporal_shift_map(
        clusters_df,
        tracking_df,
        map_shift_path,
        title="HDBSCAN - Ban do dich chuyen Hotspot khong gian - thoi gian (Chicago)",
        note="Duong noi the hien su dich chuyen tam cum tu AM -> PM va PM -> Weekend. Du lieu master_v1.",
    )
    print(f" -> Da luu ban do Folium: {map_shift_path.relative_to(ROOT)} ({map_shift_path.stat().st_size / 1024:.0f} KB)")

    total_sec = time.perf_counter() - t_start
    print("\n" + "=" * 70)
    print(f"HOAN THANH GIAI DOAN 3 TRONG {total_sec:.1f} GIAY! SAN SANG CHO TONG HOP BÁO CÁO (M4).")
    print("=" * 70)


if __name__ == "__main__":
    main()
