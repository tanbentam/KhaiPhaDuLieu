"""Chi so danh gia phan cum dung chung cho M2 (K-Means, DBSCAN) va M3 (HDBSCAN).

Quy tac (theo BA Spec v1.1, muc 2.4):
- Nhan -1 la nhieu (noise). K-Means khong co -1 nen Noise Ratio = 0 theo thiet ke.
- Silhouette, Davies-Bouldin, Calinski-Harabasz chi tinh tren diem DA DUOC GAN CUM
  (bo nhieu), luon tra kem so diem dung de tinh (n_points_metric).
- Silhouette tinh tren mau con toi da `silhouette_max_sample` diem, chon ngau nhien co seed.
- Khi khong tinh duoc (it hon 2 cum, ...) thi tra ve None -> ghi N/A / o trong trong CSV.

Vi du:
    from src.evaluation import evaluate
    res = evaluate(X, labels, silhouette_max_sample=20000, seed=42)
"""
from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score

NOISE = -1


def _check_inputs(X: np.ndarray | None, labels: Any) -> tuple[np.ndarray | None, np.ndarray]:
    lab = np.asarray(labels)
    if lab.ndim != 1:
        raise ValueError("labels phai la mang 1 chieu")
    if lab.size and not np.issubdtype(lab.dtype, np.integer):
        raise ValueError(f"labels phai la so nguyen, nhan duoc kieu {lab.dtype}")
    if X is None:
        return None, lab.astype(np.int64, copy=False)
    X = np.asarray(X, dtype=np.float64)
    if X.ndim != 2:
        raise ValueError("X phai la mang 2 chieu (n_diem, n_dac_trung)")
    if X.shape[0] != lab.shape[0]:
        raise ValueError(f"So diem X ({X.shape[0]}) khac so nhan ({lab.shape[0]})")
    if not np.isfinite(X).all():
        raise ValueError("X co gia tri NaN hoac vo cuc")
    return X, lab.astype(np.int64, copy=False)


def cluster_summary(labels: Any) -> dict[str, Any]:
    """So cum, nhieu va phan bo kich thuoc cum.

    largest_share = kich thuoc cum lon nhat / TONG so diem dau vao (ke ca nhieu).
    """
    _, lab = _check_inputs(None, labels)
    n = int(lab.size)
    n_noise = int((lab == NOISE).sum())
    clustered = lab[lab != NOISE]
    sizes = np.bincount(np.unique(clustered, return_inverse=True)[1]) if clustered.size else np.array([], int)
    out: dict[str, Any] = {
        "n_points": n,
        "n_clusters": int(sizes.size),
        "n_noise": n_noise,
        "noise_ratio": (n_noise / n) if n else None,
        "coverage": (1 - n_noise / n) if n else None,
        "size_min": int(sizes.min()) if sizes.size else None,
        "size_median": float(np.median(sizes)) if sizes.size else None,
        "size_max": int(sizes.max()) if sizes.size else None,
        "largest_share": (int(sizes.max()) / n) if sizes.size else None,
    }
    return out


def internal_metrics(
    X: Any,
    labels: Any,
    silhouette_max_sample: int = 20000,
    min_clusters: int = 2,
    seed: int = 42,
) -> dict[str, Any]:
    """Silhouette / DBI / CH tren cac diem co cum (bo nhieu)."""
    X, lab = _check_inputs(X, labels)
    mask = lab != NOISE
    Xc, lc = X[mask], lab[mask]
    n_c = int(lc.size)
    k = int(np.unique(lc).size)
    out: dict[str, Any] = {
        "silhouette": None,
        "davies_bouldin": None,
        "calinski_harabasz": None,
        "n_points_metric": n_c,
        "silhouette_sample": None,
    }
    # sklearn yeu cau 2 <= so cum <= so diem - 1
    if k < max(2, min_clusters) or k > n_c - 1:
        return out

    out["davies_bouldin"] = float(davies_bouldin_score(Xc, lc))
    out["calinski_harabasz"] = float(calinski_harabasz_score(Xc, lc))

    # Silhouette: mau con ngau nhien co seed de tiet kiem bo nho (O(n^2))
    if n_c > silhouette_max_sample:
        idx = np.random.default_rng(seed).choice(n_c, size=silhouette_max_sample, replace=False)
        Xs, ls = Xc[idx], lc[idx]
    else:
        Xs, ls = Xc, lc
    ks = int(np.unique(ls).size)
    if 2 <= ks <= ls.size - 1:
        out["silhouette"] = float(silhouette_score(Xs, ls))
        out["silhouette_sample"] = int(ls.size)
    return out


def evaluate(
    X: Any,
    labels: Any,
    silhouette_max_sample: int = 20000,
    min_clusters: int = 2,
    seed: int = 42,
) -> dict[str, Any]:
    """Gop cluster_summary + internal_metrics thanh mot dict (cac cot cua run_log.csv)."""
    res = cluster_summary(labels)
    res.update(internal_metrics(X, labels, silhouette_max_sample, min_clusters, seed))
    return res
