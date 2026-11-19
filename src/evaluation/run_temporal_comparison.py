"""Script chay phan tich lat cat thoi gian va theo doi dich chuyen hotspot (M3 - Giai doan 3).

Chuc nang:
1. Doc ket qua cum tu outputs/metrics/hdbscan_clusters_master_v1.csv.
2. Thuc hien ghep cap cum (Cluster Matching) giua AM -> PM, PM -> Weekend va AM -> Weekend.
3. Tinh toan khoang cach dich chuyen Delta d (met), bien dong so chuyen va ty trong.
4. Xuat bang ket qua outputs/metrics/hotspot_tracking.csv.
5. Ve bieu do so sanh su thay doi hotspot outputs/figures/temporal_hotspot_shifts.png.
6. Tao ban do Folium vector dich chuyen outputs/maps/hdbscan_temporal_shift_map.html.
"""
from __future__ import annotations

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
from src.evaluation.temporal import build_hotspot_tracking
from src.visualization.maps import temporal_shift_map


def main() -> None:
    t_start = time.perf_counter()
    print("=" * 70)
    print("M3 - ADVANCED MODELING & TEMPORAL LEAD: TEMPORAL TRACKING (GIAI DOAN 3)")
    print("=" * 70)

    cfg = load_config()
    DATA_KEY = "master"
    clusters_path = resolve_path(cfg, "run_log").parent / "hdbscan_clusters_master_v1.csv"

    # Neu chua co file hdbscan_clusters_master_v1.csv, kiem tra tu dbscan_clusters de lam mau hoac thong bao
    if not clusters_path.exists():
        print(f"[!] Khong tim thay {clusters_path.name}. Dang su dung du lieu cluster hdbscan du kien...")
        # Tao placeholder hoac load tu du lieu da fit
        raise FileNotFoundError(f"Vui long chay buoc 2 (run_hdbscan) truoc de tao {clusters_path}")

    print(f"\n[1/4] Doc ket qua cum tu {clusters_path.name}...")
    clusters_df = pd.read_csv(clusters_path)
    print(f" -> Da doc {len(clusters_df)} dong cum tren 3 lat cat: {clusters_df['time_slice'].unique().tolist()}")

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
