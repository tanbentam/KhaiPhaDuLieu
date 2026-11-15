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
