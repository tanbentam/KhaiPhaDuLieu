"""Kiem thu cac module cua M3: HDBSCAN va Temporal Tracking.

Chay tu goc repo:
    python -m tests.test_m3
hoac:
    pytest tests/test_m3.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.evaluation.temporal import match_clusters, build_hotspot_tracking


def test_cluster_matching_mock():
    """Kiem thu thuat toan ghep cap cum tam gan nhat voi du lieu gia lap."""
    # Gia lap 2 cum o AM
    df_am = pd.DataFrame({
        "cluster": [0, 1],
        "n_trips": [1000, 500],
        "share": [0.6, 0.3],
        "center_x_m": [448000.0, 424000.0],
        "center_y_m": [4636000.0, 4647000.0],
        "center_lat": [41.88, 41.97],
        "center_lon": [-87.63, -87.90],
        "radius_rms_m": [1500.0, 500.0],
        "top_community_area": [32, 76],
    })

    # Gia lap PM: cum 0 dich nhe 500m ve phia bac, cum 1 (san bay) giu nguyen vi tri
    df_pm = pd.DataFrame({
        "cluster": [0, 1],
        "n_trips": [1200, 700],
        "share": [0.65, 0.30],
        "center_x_m": [448000.0, 424050.0],
        "center_y_m": [4636500.0, 4647000.0],
        "center_lat": [41.89, 41.97],
        "center_lon": [-87.63, -87.90],
        "radius_rms_m": [1600.0, 520.0],
        "top_community_area": [8, 76],
    })

    res = match_clusters(df_am, df_pm, slice_from_name="AM", slice_to_name="PM", max_distance_m=3500.0)

    assert len(res) == 2, f"Phai co 2 cap ghep, nhan duoc {len(res)}"
    assert (res["status"] == "MATCHED").all(), "Tat ca phai duoc ghep cap thanh cong"
    # Cum 0 dich chuyen 500m
    row0 = res[res["cluster_from"] == 0].iloc[0]
    assert abs(row0["shift_distance_m"] - 500.0) < 1.0, f"Dich chuyen phai la 500m, nhan duoc {row0['shift_distance_m']}"
    # Cum 1 dich chuyen 50m
    row1 = res[res["cluster_from"] == 1].iloc[0]
    assert abs(row1["shift_distance_m"] - 50.0) < 1.0, f"Dich chuyen phai la 50m, nhan duoc {row1['shift_distance_m']}"
    print("PASS: test_cluster_matching_mock thanh cong!")


def main():
    print("Dang chay bo kiem thu M3 (HDBSCAN & Temporal Tracking)...")
    test_cluster_matching_mock()
    print("ALL M3 TESTS PASSED!")


if __name__ == "__main__":
    main()
