"""Kiem thu cac module cua M3: HDBSCAN va Temporal Tracking.

Chay tu goc repo:
    python -m tests.test_m3
hoac:
    pytest tests/test_m3.py
"""
from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.evaluation.temporal import build_time_slice_manifest, match_clusters
from src.models.hdbscan import fit_hdbscan, get_cluster_persistence_table


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


def test_cluster_persistence_tracks_size_relabeling():
    clusterer = SimpleNamespace(
        labels_=np.array([0, 0, 1, 1, 1, -1]),
        cluster_persistence_=np.array([0.25, 0.75]),
    )

    result = get_cluster_persistence_table(clusterer)

    assert result["cluster"].tolist() == [0, 1]
    assert result["cluster_original"].tolist() == [1, 0]
    assert result["cluster_size"].tolist() == [3, 2]
    assert result["persistence"].tolist() == [0.75, 0.25]


def test_cluster_persistence_rejects_missing_backend_output():
    clusterer = SimpleNamespace(labels_=np.array([0, 0, 1, 1]))

    try:
        get_cluster_persistence_table(clusterer)
    except RuntimeError as exc:
        assert "cluster_persistence_" in str(exc)
    else:
        raise AssertionError("Missing persistence data must not be silently accepted")


def test_fit_hdbscan_requires_stability_outputs():
    class FakeHDBSCAN:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def fit(self, X):
            self.labels_ = np.array([0, 0, 1, 1])
            self.probabilities_ = np.ones(len(X))
            self.cluster_persistence_ = np.array([0.4, 0.8])
            self.condensed_tree_ = object()

    module = SimpleNamespace(HDBSCAN=FakeHDBSCAN)
    X = np.array([[0.0, 0.0], [0.1, 0.0], [2.0, 2.0], [2.1, 2.0]])

    with patch.dict(sys.modules, {"hdbscan": module}):
        labels, probabilities, clusterer = fit_hdbscan(X, min_cluster_size=2, min_samples=1)

    assert labels.tolist() == [0, 0, 1, 1]
    assert probabilities.tolist() == [1.0, 1.0, 1.0, 1.0]
    assert clusterer.kwargs["min_samples"] == 1
    assert clusterer.kwargs["gen_min_span_tree"] is False


def test_time_slice_manifest_normalizes_by_exposure_hours():
    source = pd.DataFrame({
        "time_slice": ["WEEKDAY_AM", "WEEKDAY_AM", "WEEKDAY_AM", "WEEKEND", "OTHER"],
        "trip_start_timestamp": [
            "2023-04-17 07:10:00",
            "2023-04-17 08:00:00",
            "2023-04-18 07:30:00",
            "2023-04-22 12:00:00",
            "2023-04-23 12:00:00",
        ],
    })
    config = {
        "WEEKDAY_AM": {"weekdays": [0, 1, 2, 3, 4], "hours": [7, 8, 9]},
        "WEEKEND": {"weekdays": [5, 6], "hours": "all"},
    }

    result = build_time_slice_manifest(source, config).set_index("time_slice")

    assert result.loc["WEEKDAY_AM", "n_pickups"] == 3
    assert result.loc["WEEKDAY_AM", "exposure_hours"] == 15
    assert result.loc["WEEKDAY_AM", "pickups_per_hour"] == 0.2
    assert result.loc["WEEKEND", "exposure_hours"] == 48


def main():
    print("Dang chay bo kiem thu M3 (HDBSCAN & Temporal Tracking)...")
    test_cluster_matching_mock()
    test_cluster_persistence_tracks_size_relabeling()
    test_cluster_persistence_rejects_missing_backend_output()
    test_fit_hdbscan_requires_stability_outputs()
    test_time_slice_manifest_normalizes_by_exposure_hours()
    print("ALL M3 TESTS PASSED!")


if __name__ == "__main__":
    main()
