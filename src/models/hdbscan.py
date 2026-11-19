"""HDBSCAN cho M3 tren du lieu Chicago Taxi (theo BA Spec v1.1 muc 2.3.4 va 3.4.3).

HDBSCAN xay dung phan cap mat do dua tren khoang cach tiep can tuong ho (mutual reachability distance)
va do ben vung cua cum (cluster stability), giup nhan dien cac vung mat do khac nhau
(nhu Trung tam Loop day dac va cac vung phu can thua hon) tot hon DBSCAN voi mot nguong eps co dinh.

Luu y ve trien khai:
- Thu vien hdbscan khong ho tro truc tiep sample_weight nhu scikit-learn DBSCAN/KMeans.
  Do do HDBSCAN duoc fit truc tiep tren mang X [x_m, y_m].
- De kiem soat doc lap tac dong cua kich thuoc cum va muc do bao thu mat do,
  min_samples luon duoc dat tuong minh (tranh gia tri mac dinh ngam phu thuoc vao min_cluster_size).
"""
from __future__ import annotations

import time
from typing import Any

import numpy as np
import pandas as pd


def fit_hdbscan(
    X: Any,
    min_cluster_size: int = 100,
    min_samples: int | None = 10,
    *,
    metric: str = "euclidean",
    cluster_selection_method: str = "eom",
    cluster_selection_epsilon: float = 0.0,
    gen_min_span_tree: bool = False,
    approx_min_span_tree: bool = True,
    core_dist_n_jobs: int = -1,
) -> tuple[np.ndarray, np.ndarray, Any]:
    """Fit mo hinh HDBSCAN tren mang toa do X.

    Tra ve:
        (labels, probabilities, clusterer)
        - labels: mang int32 (-1 la nhieu/noise).
        - probabilities: mang float32, xac suat diem thuoc ve cum duoc gan.
        - clusterer: doi tuong HDBSCAN da fit (chua cluster_persistence_, condensed_tree_...).
    """
    import hdbscan

    X = np.asarray(X, dtype=np.float64)
    if X.ndim != 2 or X.shape[1] != 2:
        raise ValueError(f"X phai co kich thuoc (n, 2), nhan duoc shape {X.shape}")
    if min_cluster_size < 2:
        raise ValueError(f"min_cluster_size phai >= 2, nhan duoc {min_cluster_size}")

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=int(min_cluster_size),
        min_samples=int(min_samples) if min_samples is not None else None,
        metric=metric,
        cluster_selection_method=cluster_selection_method,
        cluster_selection_epsilon=float(cluster_selection_epsilon),
        gen_min_span_tree=gen_min_span_tree,
        approx_min_span_tree=approx_min_span_tree,
        core_dist_n_jobs=core_dist_n_jobs,
    )
    clusterer.fit(X)
    labels = clusterer.labels_.astype(np.int32)
    probabilities = clusterer.probabilities_.astype(np.float32)
    return labels, probabilities, clusterer


def hdbscan_fit_predict(
    X: Any,
    min_cluster_size: int = 100,
    min_samples: int | None = 10,
    *,
    metric: str = "euclidean",
    cluster_selection_method: str = "eom",
    cluster_selection_epsilon: float = 0.0,
    core_dist_n_jobs: int = -1,
) -> tuple[np.ndarray, np.ndarray]:
    """Ham wrapper tra ve (labels, probabilities) phu hop cho run_and_log cua src.evaluation."""
    labels, probabilities, _ = fit_hdbscan(
        X,
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric=metric,
        cluster_selection_method=cluster_selection_method,
        cluster_selection_epsilon=cluster_selection_epsilon,
        gen_min_span_tree=False,
        core_dist_n_jobs=core_dist_n_jobs,
    )
    return labels, probabilities


def scan_min_cluster_size(
    X: Any,
    mcs_candidates: list[int],
    *,
    min_samples: int = 10,
    metric: str = "euclidean",
    cluster_selection_method: str = "eom",
    seed: int = 42,
    silhouette_max_sample: int = 20000,
) -> pd.DataFrame:
    """Khao sat tac dong cua min_cluster_size khi giu co dinh min_samples.

    Giu co dinh min_samples giup tach biet anh huong cua quy mo cum toi thieu
    khoi muc do bao thu ve mat do loi (theo canh bao R05 trong BA Spec).
    """
    from src.evaluation import evaluate, measure

    X = np.asarray(X, dtype=np.float64)
    rows = []
    for mcs in mcs_candidates:
        def _run() -> tuple[np.ndarray, np.ndarray, Any]:
            return fit_hdbscan(
                X,
                min_cluster_size=mcs,
                min_samples=min_samples,
                metric=metric,
                cluster_selection_method=cluster_selection_method,
            )

        (labels, prob, clusterer), sec, peak_mb, delta_mb = measure(_run)
        metrics = evaluate(X, labels, silhouette_max_sample=silhouette_max_sample, seed=seed)

        # Do ben vung trung binh cua cac cum (cluster persistence)
        pers = getattr(clusterer, "cluster_persistence_", None)
        mean_persistence = float(np.mean(pers)) if pers is not None and len(pers) > 0 else None

        row = {
            "min_cluster_size": int(mcs),
            "min_samples": int(min_samples),
            "cluster_selection_method": cluster_selection_method,
            "mean_persistence": mean_persistence,
            "runtime_sec": round(sec, 4),
            "peak_mem_mb": round(peak_mb, 1),
            "mem_delta_mb": round(delta_mb, 1),
            **metrics,
        }
        rows.append(row)

    return pd.DataFrame(rows)


def scan_min_samples(
    X: Any,
    ms_candidates: list[int],
    *,
    min_cluster_size: int = 100,
    metric: str = "euclidean",
    cluster_selection_method: str = "eom",
    seed: int = 42,
    silhouette_max_sample: int = 20000,
) -> pd.DataFrame:
    """Khao sat muc do bao thu qua tham so min_samples voi min_cluster_size co dinh."""
    from src.evaluation import evaluate, measure

    X = np.asarray(X, dtype=np.float64)
    rows = []
    for ms in ms_candidates:
        def _run() -> tuple[np.ndarray, np.ndarray, Any]:
            return fit_hdbscan(
                X,
                min_cluster_size=min_cluster_size,
                min_samples=ms,
                metric=metric,
                cluster_selection_method=cluster_selection_method,
            )

        (labels, prob, clusterer), sec, peak_mb, delta_mb = measure(_run)
        metrics = evaluate(X, labels, silhouette_max_sample=silhouette_max_sample, seed=seed)

        pers = getattr(clusterer, "cluster_persistence_", None)
        mean_persistence = float(np.mean(pers)) if pers is not None and len(pers) > 0 else None

        row = {
            "min_cluster_size": int(min_cluster_size),
            "min_samples": int(ms),
            "cluster_selection_method": cluster_selection_method,
            "mean_persistence": mean_persistence,
            "runtime_sec": round(sec, 4),
            "peak_mem_mb": round(peak_mb, 1),
            "mem_delta_mb": round(delta_mb, 1),
            **metrics,
        }
        rows.append(row)

    return pd.DataFrame(rows)


def get_cluster_persistence_table(clusterer: Any) -> pd.DataFrame:
    """Xuat bang do ben vung cua tung cum (cluster persistence / stability)."""
    pers = getattr(clusterer, "cluster_persistence_", None)
    if pers is None:
        return pd.DataFrame(columns=["cluster", "persistence"])
    return pd.DataFrame({
        "cluster": np.arange(len(pers)),
        "persistence": pers.astype(float),
    }).sort_values("persistence", ascending=False).reset_index(drop=True)
