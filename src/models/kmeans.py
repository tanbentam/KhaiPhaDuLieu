"""K-Means cho M2: Elbow, gop toa do trung, tim diem khuyu.

Du lieu Chicago la toa do centroid (rat nhieu diem trung nhau). K-Means voi
sample_weight tren cac toa do duy nhat toi uu cung ham muc tieu (tong binh phuong
khoang cach co trong so) nhu khi chay tren tung chuyen, nhung nhanh hon nhieu.
"""
from __future__ import annotations

import time
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans


def aggregate_unique(X: Any) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Gop diem trung toa do. Tra ve (X_unique, weight = so diem, inverse).

    X_unique[inverse] == X, nen nhan cua tung chuyen = labels_unique[inverse].
    """
    X = np.asarray(X, dtype=np.float64)
    Xu, inverse, counts = np.unique(X, axis=0, return_inverse=True, return_counts=True)
    return Xu, counts.astype(np.float64), inverse.reshape(-1)


def elbow(
    X: Any,
    k_min: int = 2,
    k_max: int = 15,
    *,
    init: str = "k-means++",
    n_init: int = 10,
    max_iter: int = 300,
    seed: int = 42,
    sample_weight: Any = None,
) -> pd.DataFrame:
    """Chay K-Means cho K = k_min..k_max. Moi dong: k, inertia, n_iter, converged, runtime_sec.

    inertia = tong binh phuong khoang cach (co trong so neu truyen sample_weight), don vi m^2.
    converged = n_iter < max_iter (sklearn dung som khi tam khong doi).
    """
    X = np.asarray(X, dtype=np.float64)
    n_distinct = np.unique(X, axis=0).shape[0]
    if k_min < 1 or k_max < k_min:
        raise ValueError("Can 1 <= k_min <= k_max")
    if k_max > n_distinct:
        raise ValueError(f"k_max = {k_max} lon hon so toa do khac nhau ({n_distinct})")
    rows = []
    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, init=init, n_init=n_init, max_iter=max_iter, random_state=seed)
        t0 = time.perf_counter()
        km.fit(X, sample_weight=sample_weight)
        rows.append({
            "k": k,
            "inertia": float(km.inertia_),
            "n_iter": int(km.n_iter_),
            "converged": bool(km.n_iter_ < max_iter),
            "runtime_sec": time.perf_counter() - t0,
        })
    return pd.DataFrame(rows)


def fit_weighted(X: Any, k: int, *, init: str = "k-means++", n_init: int = 50,
                 max_iter: int = 300, seed: int = 42) -> tuple[np.ndarray, KMeans]:
    """Fit K-Means tren toa do duy nhat (sample_weight = so chuyen), tra nhan cho TUNG chuyen."""
    Xu, w, inv = aggregate_unique(X)
    if k > len(Xu):
        raise ValueError(f"k = {k} lon hon so toa do khac nhau ({len(Xu)})")
    km = KMeans(n_clusters=k, init=init, n_init=n_init, max_iter=max_iter, random_state=seed)
    km.fit(Xu, sample_weight=w)
    return km.labels_[inv], km


def scan_k(X: Any, k_values: Any, *, init: str = "k-means++", n_init: int = 50,
           max_iter: int = 300, seed: int = 42, silhouette_max_sample: int = 20000) -> pd.DataFrame:
    """Voi moi K: fit_weighted roi tinh chi so tren tung chuyen bang src.evaluation.evaluate.

    Them `silhouette_unique`: Silhouette tren cac toa do duy nhat (khong trong so) de doi chieu,
    vi Silhouette tren tung chuyen bi keo len do rat nhieu chuyen trung toa do (khoang cach 0).
    """
    from sklearn.metrics import silhouette_score

    from src.evaluation import evaluate

    X = np.asarray(X, dtype=np.float64)
    Xu, w, inv = aggregate_unique(X)
    rows = []
    for k in k_values:
        t0 = time.perf_counter()
        labels, km = fit_weighted(X, int(k), init=init, n_init=n_init, max_iter=max_iter, seed=seed)
        fit_sec = time.perf_counter() - t0
        r = evaluate(X, labels, silhouette_max_sample=silhouette_max_sample, seed=seed)
        lu = km.labels_
        r["silhouette_unique"] = (float(silhouette_score(Xu, lu))
                                  if 2 <= np.unique(lu).size <= len(Xu) - 1 else None)
        r.update({"k": int(k), "inertia": float(km.inertia_), "n_iter": int(km.n_iter_),
                  "n_unique": int(len(Xu)), "fit_sec": fit_sec,
                  "smallest_share": r["size_min"] / r["n_points"] if r["size_min"] else None})
        rows.append(r)
    cols = ["k", "inertia", "silhouette", "silhouette_unique", "davies_bouldin", "calinski_harabasz",
            "size_min", "size_median", "size_max", "largest_share", "smallest_share",
            "n_points", "n_unique", "silhouette_sample", "n_iter", "fit_sec"]
    return pd.DataFrame(rows)[cols]


def knee_point(ks: Any, values: Any) -> int:
    """Diem khuyu theo cach 'khoang cach lon nhat toi day cung' (giong Kneedle don gian).

    Chuan hoa ca hai truc ve [0, 1], ve doan thang noi diem dau va diem cuoi cua
    duong cong giam dan; diem xa doan thang nhat la khuyu. Chi la GOI Y de doi chieu
    voi Silhouette va ban do o muc 3.2, khong tu dong chon K.
    """
    k = np.asarray(ks, dtype=float)
    v = np.asarray(values, dtype=float)
    if k.size < 3:
        raise ValueError("Can it nhat 3 gia tri K")
    kn = (k - k.min()) / (k.max() - k.min())
    vr = v.max() - v.min()
    vn = (v - v.min()) / vr if vr > 0 else np.zeros_like(v)
    # duong thang tu (0, vn[0]) toi (1, vn[-1]); khoang cach vuong goc
    x0, y0, x1, y1 = kn[0], vn[0], kn[-1], vn[-1]
    dist = np.abs((y1 - y0) * kn - (x1 - x0) * vn + x1 * y0 - y1 * x0) / np.hypot(y1 - y0, x1 - x0)
    return int(k[int(np.argmax(dist))])
