"""Script thuc thi tron goi quy trinh HDBSCAN cho M3 (Giai doan 2).

Chuc nang:
1. Doc du lieu master_v1 va kiem tra ma bam SHA256 voi manifest.
2. Khao sat luoi tham so min_cluster_size va min_samples tren lat cat WEEKDAY_AM.
3. Xuat bang metrics tuning va ve bieu do phan tich outputs/figures/hdbscan_tuning_master_v1.png.
4. Chot cau hinh chinh thuc va fit tren ca 3 lat cat: WEEKDAY_AM, WEEKDAY_PM, WEEKEND.
5. Luu nhan (kem xac suat) vao outputs/labels/<run_id>.parquet.
6. Ghi 3 dong log vao outputs/metrics/run_log.csv theo chuan 28 cot dung chung.
7. Xuat bang metrics chinh thuc outputs/metrics/hdbscan_metrics.csv (dong nhat voi baseline_metrics.csv).
8. Lap bang chi tiet cac cum outputs/metrics/hdbscan_clusters_master_v1.csv.
9. Xuat ban do Folium tuong tac outputs/maps/hdbscan_map_master_v1.html.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_config, resolve_path
from src.evaluation.hotspots import cluster_table, relabel_by_size
from src.evaluation.runlog import export_metrics_table, run_and_log
from src.models.hdbscan import (
    fit_hdbscan,
    scan_min_cluster_size,
    scan_min_samples,
)
from src.visualization.maps import cluster_map


def main() -> None:
    t_start = time.perf_counter()
    print("=" * 70, flush=True)
    print("M3 - ADVANCED MODELING & TEMPORAL LEAD: HDBSCAN EXPERIMENTS", flush=True)
    print("=" * 70, flush=True)

    cfg = load_config()
    DATA_KEY = "master"
    data_path = resolve_path(cfg, DATA_KEY)
    man_path = resolve_path(cfg, "master_manifest")
    manifest = json.loads(man_path.read_text(encoding="utf-8"))

    # 1. Kiem tra tinh toan ven SHA256
    print(f"\n[1/6] Doc du lieu {data_path.name} va kiem tra SHA256...", flush=True)
    file_bytes = data_path.read_bytes()
    calc_sha = hashlib.sha256(file_bytes).hexdigest()
    assert calc_sha == manifest["sha256"], f"SHA256 khong khop! ({calc_sha} != {manifest['sha256']})"
    print(f" -> SHA256 khop 100%: {calc_sha[:16]}... (Tong so dong: {manifest['rows_in_sample']:,})", flush=True)

    df = pd.read_parquet(data_path)
    sample_id = manifest["sample_id"]
    slices = list(cfg["time_slices"])

    # 2. Khao sat tham so tren WEEKDAY_AM (60.498 dong)
    print("\n[2/6] Khao sat tham so HDBSCAN tren WEEKDAY_AM...", flush=True)
    am_df = df[df.time_slice == "WEEKDAY_AM"].reset_index(drop=True)
    X_am = am_df[["x_m", "y_m"]].to_numpy(dtype="float64")

    # Dải tuning tinh gọn, đại diện cao
    mcs_list = [50, 100, 200]
    ms_default = 10

    print(f" -> Buoc 2.1: Quet min_cluster_size trong {mcs_list} (co dinh min_samples={ms_default})...", flush=True)
    df_mcs = scan_min_cluster_size(
        X_am,
        mcs_list,
        min_samples=ms_default,
        metric="euclidean",
        cluster_selection_method="eom",
        seed=cfg["project"]["seed"],
        silhouette_max_sample=cfg["evaluation"]["silhouette_max_sample"],
    )
    mcs_csv = resolve_path(cfg, "run_log").parent / f"hdbscan_mcs_tuning_{sample_id}.csv"
    df_mcs.to_csv(mcs_csv, index=False)
    print(f"    Da luu: {mcs_csv.relative_to(ROOT)}", flush=True)
    for _, r in df_mcs.iterrows():
        print(f"    mcs={int(r['min_cluster_size']):3d} | Cum: {int(r['n_clusters']):2d} | "
              f"Noise: {r['noise_ratio']:.1%} | Silh: {r['silhouette'] if r['silhouette'] is not None else -1:.3f} | "
              f"DBI: {r['davies_bouldin'] if r['davies_bouldin'] is not None else -1:.3f} | "
              f"Fit: {r['runtime_sec']:.2f}s | RAM+: {r['mem_delta_mb']:.1f}MB", flush=True)

    chosen_mcs = 100
    ms_list = [5, 10, 20]
    print(f"\n -> Buoc 2.2: Quet min_samples trong {ms_list} (co dinh min_cluster_size={chosen_mcs})...", flush=True)
    df_ms = scan_min_samples(
        X_am,
        ms_list,
        min_cluster_size=chosen_mcs,
        metric="euclidean",
        cluster_selection_method="eom",
        seed=cfg["project"]["seed"],
        silhouette_max_sample=cfg["evaluation"]["silhouette_max_sample"],
    )
    ms_csv = resolve_path(cfg, "run_log").parent / f"hdbscan_ms_tuning_{sample_id}.csv"
    df_ms.to_csv(ms_csv, index=False)
    print(f"    Da luu: {ms_csv.relative_to(ROOT)}", flush=True)
    for _, r in df_ms.iterrows():
        print(f"    ms={int(r['min_samples']):2d} | Cum: {int(r['n_clusters']):2d} | "
              f"Noise: {r['noise_ratio']:.1%} | Silh: {r['silhouette'] if r['silhouette'] is not None else -1:.3f} | "
              f"DBI: {r['davies_bouldin'] if r['davies_bouldin'] is not None else -1:.3f} | "
              f"Fit: {r['runtime_sec']:.2f}s", flush=True)

    # 3. Ve bieu do tuning
    print("\n[3/6] Ve bieu do tuning HDBSCAN...", flush=True)
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    # Subplot 1: mcs
    ax1 = axes[0]
    ax1.plot(df_mcs["min_cluster_size"], df_mcs["n_clusters"], "o-", color="#1f77b4", label="So cum")
    ax1.set_xlabel("min_cluster_size (min_samples = 10)")
    ax1.set_ylabel("So cum", color="#1f77b4")
    ax1.tick_params(axis="y", labelcolor="#1f77b4")
    ax1.grid(alpha=0.3)
    ax1_twin = ax1.twinx()
    ax1_twin.plot(df_mcs["min_cluster_size"], df_mcs["noise_ratio"] * 100, "s--", color="#d62728", label="Noise ratio (%)")
    ax1_twin.set_ylabel("Noise ratio (%)", color="#d62728")
    ax1_twin.tick_params(axis="y", labelcolor="#d62728")
    ax1.set_title("Anh huong cua min_cluster_size (WEEKDAY_AM)")

    # Subplot 2: ms
    ax2 = axes[1]
    ax2.plot(df_ms["min_samples"], df_ms["noise_ratio"] * 100, "s-", color="#d62728", label="Noise ratio (%)")
    ax2.set_xlabel(f"min_samples (min_cluster_size = {chosen_mcs})")
    ax2.set_ylabel("Noise ratio (%)", color="#d62728")
    ax2.grid(alpha=0.3)
    ax2_twin = ax2.twinx()
    ax2_twin.plot(df_ms["min_samples"], df_ms["silhouette"], "^-", color="#2ca02c", label="Silhouette")
    ax2_twin.set_ylabel("Silhouette", color="#2ca02c")
    ax2_twin.tick_params(axis="y", labelcolor="#2ca02c")
    ax2.set_title("Anh huong cua min_samples (Do bao thu mat do)")

    fig.suptitle(f"HDBSCAN Hyperparameter Tuning - {sample_id}", fontsize=13, y=1.02)
    fig.tight_layout()
    fig_path = resolve_path(cfg, "figures_dir") / f"hdbscan_tuning_{sample_id}.png"
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f" -> Da luu bieu do: {fig_path.relative_to(ROOT)}", flush=True)

    # 4. Chot cau hinh va fit tren ca 3 lat cat
    final_mcs = 100
    final_ms = 10
    final_method = "eom"
    print(f"\n[4/6] Fit HDBSCAN chinh thuc (mcs={final_mcs}, ms={final_ms}) tren 3 lat cat...", flush=True)

    final_hdb = {}
    final_run_ids = []

    for s in slices:
        part = df[df.time_slice == s].reset_index(drop=True)
        X = part[["x_m", "y_m"]].to_numpy(dtype="float64")
        params = {
            "min_cluster_size": final_mcs,
            "min_samples": final_ms,
            "cluster_selection_method": final_method,
            "metric": "euclidean",
            "cluster_selection_epsilon": 0.0,
        }

        print(f" -> Dang fit {s} (n={len(X):,})...", end="", flush=True)
        def _fit_fn(X_arr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
            lab, prob, _ = fit_hdbscan(
                X_arr,
                min_cluster_size=final_mcs,
                min_samples=final_ms,
                cluster_selection_method=final_method,
            )
            return relabel_by_size(lab), prob

        row = run_and_log(
            cfg,
            algorithm="hdbscan",
            fit_fn=_fit_fn,
            X=X,
            trip_ids=part["trip_id"].to_numpy(),
            member="M3",
            time_slice=s,
            sample_id=sample_id,
            params=params,
            note=f"du lieu M1 {sample_id}; cau hinh chinh thuc chot o Giai doan 2",
        )
        final_run_ids.append(row["run_id"])

        lab_df = pd.read_parquet(resolve_path(cfg, "labels_dir") / f"{row['run_id']}.parquet")
        assert (lab_df["trip_id"].values == part["trip_id"].values).all(), "trip_id khong khop!"
        final_hdb[s] = (part, lab_df["label"].to_numpy(), row)

        print(f" Xong! ({row['runtime_fit_sec']:.2f}s) | Cum: {row['n_clusters']} | "
              f"Noise: {row['noise_ratio']:.1%} | Silh: {row['silhouette']:.3f} | DBI: {row['davies_bouldin']:.3f}", flush=True)

    # 5. Xuat hdbscan_metrics.csv va bang chi tiet cum
    print("\n[5/6] Xuat bang metrics va bang chi tiet cum...", flush=True)
    out_metrics_path = resolve_path(cfg, "run_log").parent / "hdbscan_metrics.csv"
    export_metrics_table(
        resolve_path(cfg, "run_log"),
        out_metrics_path,
        final_run_ids,
        require_same_sample=True,
    )
    print(f" -> Da xuat bang chi so chinh thuc: {out_metrics_path.relative_to(ROOT)} (3 dong, bo 28 cot)", flush=True)

    cluster_tabs = []
    for s, (part, lab, row) in final_hdb.items():
        ct = cluster_table(part, lab, crs=cfg["project"]["crs"])
        ct = ct.assign(
            time_slice=s,
            run_id=row["run_id"],
            sample_id=sample_id,
            noise_trips=int((lab == -1).sum()),
            noise_share=float((lab == -1).mean()),
        )
        cluster_tabs.append(ct)

    hdb_clusters = pd.concat(cluster_tabs, ignore_index=True)
    clp = resolve_path(cfg, "run_log").parent / f"hdbscan_clusters_{sample_id}.csv"
    hdb_clusters.to_csv(clp, index=False)
    print(f" -> Da luu bang cum: {clp.relative_to(ROOT)}", flush=True)

    # 6. Tao ban do Folium HTML
    print("\n[6/6] Tao ban do Folium HTML cho HDBSCAN...", flush=True)
    map_path = resolve_path(cfg, "maps_dir") / f"hdbscan_map_{sample_id}.html"
    layers = {}
    for s, (part, lab, row) in final_hdb.items():
        ct_sub = hdb_clusters[hdb_clusters.time_slice == s]
        layers[f"HDBSCAN {s} (mcs={final_mcs}, ms={final_ms})"] = (part, lab, ct_sub)

    cluster_map(
        layers,
        map_path,
        title=f"HDBSCAN - {sample_id}",
        note=f"Cau hinh: min_cluster_size={final_mcs}, min_samples={final_ms}, method={final_method}. Du lieu chinh thuc M1 ({sample_id}).",
    )
    print(f" -> Da luu ban do Folium: {map_path.relative_to(ROOT)} ({map_path.stat().st_size / 1024:.0f} KB)", flush=True)

    total_sec = time.perf_counter() - t_start
    print("\n" + "=" * 70, flush=True)
    print(f"HOAN THANH HDBSCAN PIPELINE TRONG {total_sec:.1f} GIAY!", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    main()
