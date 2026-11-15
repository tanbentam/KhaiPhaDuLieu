"""DBSCAN cho M2 tren du lieu centroid (xem docs/Phan 4/4.0-quyet-dinh-dbscan.md).

- Fit tren toa do duy nhat voi sample_weight = so chuyen: tuong duong chinh xac fit tren
  tung chuyen (sklearn: diem la core khi TONG TRONG SO trong ban kinh eps, tinh ca chinh no,
  >= min_samples), nhung khong bi tran RAM.
- k-distance co trong so: voi moi toa do, khoang cach nho nhat de gom du k chuyen
  = nguong eps de toa do do tro thanh core.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
from sklearn.metrics import pairwise_distances

from src.models.kmeans import aggregate_unique

MAX_PAIRWISE = 20000   # so toa do duy nhat toi da de tinh ma tran khoang cach day du


def min_samples_from_frac(n_trips: int, frac: float) -> int:
    """min_samples = ceil(frac * so chuyen cua lat cat), toi thieu 2."""
    if not 0 < frac < 1:
        raise ValueError("frac phai trong (0, 1)")
    return max(2, math.ceil(frac * n_trips))


def weighted_k_distance(Xu: Any, w: Any, k: float) -> np.ndarray:
    """Khoang cach nho nhat d de tong trong so cac diem trong ban kinh d (tinh ca chinh no) >= k.

    Toa do co trong so >= k thi bang 0. Neu tong trong so ca tap < k thi bang +inf.
    """
    Xu = np.asarray(Xu, dtype=np.float64)
    w = np.asarray(w, dtype=np.float64)
    if Xu.ndim != 2 or len(Xu) != len(w):
        raise ValueError("Xu phai 2 chieu va cung do dai voi w")
    if len(Xu) > MAX_PAIRWISE:
        raise ValueError(f"Qua nhieu toa do duy nhat ({len(Xu)} > {MAX_PAIRWISE}) de tinh ma tran khoang cach")
    if k <= 0:
        raise ValueError("k phai > 0")
    D = pairwise_distances(Xu)
    order = np.argsort(D, axis=1, kind="stable")
    d_sorted = np.take_along_axis(D, order, axis=1)
    cw = np.cumsum(w[order], axis=1)
    reach = cw >= k - 1e-9
    has = reach.any(axis=1)
    idx = np.argmax(reach, axis=1)
    out = np.full(len(Xu), np.inf)
    out[has] = d_sorted[has, idx[has]]
    return out


def k_distance_curve(X: Any, k: float) -> tuple[np.ndarray, np.ndarray]:
    """Duong k-distance theo TUNG CHUYEN: (ty le chuyen tich luy 0-1, k-distance tang dan).

    Moi toa do dong gop so chuyen cua no; tuong ung voi do thi k-distance thong thuong
    ve tren tung chuyen, nhung tinh dung voi diem trung toa do.
    """
    Xu, w, _ = aggregate_unique(X)
    kd = weighted_k_distance(Xu, w, k)
    o = np.argsort(kd, kind="stable")
    share = np.cumsum(w[o]) / w.sum()
    return share, kd[o]


def knee_eps(share: Any, dist: Any) -> float:
    """Diem gay cua duong k-distance tang dan (ty le chuyen -> khoang cach).

    Chuan hoa 2 truc ve [0, 1], lay diem nam DUOI day cung (noi diem dau va cuoi) xa nhat:
    do la cho duong cong bat dau dung len. Bo qua gia tri inf va gia tri 0 (toa do tu la core
    o moi eps, neu giu lai thi diem gay luon roi vao 0). Chi la GOI Y eps.
    """
    x = np.asarray(share, dtype=float)
    y = np.asarray(dist, dtype=float)
    m = np.isfinite(y) & (y > 0)
    x, y = x[m], y[m]
    if x.size < 3 or y.max() == y.min():
        raise ValueError("Duong k-distance qua ngan hoac phang, khong tim duoc diem gay")
    xn = (x - x.min()) / (x.max() - x.min())
    yn = (y - y.min()) / (y.max() - y.min())
    chord = yn[0] + (yn[-1] - yn[0]) * (xn - xn[0]) / (xn[-1] - xn[0])
    below = chord - yn          # khoang cach theo truc dung tu day cung xuong duong cong
    return float(y[int(np.argmax(below))])


def estimate_full_neighbors(X: Any, eps: float) -> int:
    """Uoc tinh tong so cap lang gieng (tinh ca chinh no) ma DBSCAN tren TUNG CHUYEN phai luu.

    sklearn DBSCAN luu danh sach lang gieng trong ban kinh eps cho moi diem, nen bo nho
    ~ tong so cap x 8 byte (int64). Tinh nhanh tren toa do duy nhat:
    sum_i w_i * (tong trong so trong ban kinh eps cua toa do i).
    Dung de BO QUA lan chay day du truoc khi no lam tran RAM.
    """
    from sklearn.neighbors import NearestNeighbors

    Xu, w, _ = aggregate_unique(X)
    nb = NearestNeighbors(radius=eps).fit(Xu).radius_neighbors(Xu, return_distance=False)
    return int(sum(w[i] * w[idx].sum() for i, idx in enumerate(nb)))


def fit_weighted(X: Any, eps: float, min_samples: int, *, metric: str = "euclidean",
                 algorithm: str = "auto", n_jobs: int | None = None) -> tuple[np.ndarray, Any]:
    """DBSCAN tren toa do duy nhat (sample_weight = so chuyen), tra nhan cho TUNG chuyen."""
    from sklearn.cluster import DBSCAN

    Xu, w, inv = aggregate_unique(X)
    db = DBSCAN(eps=eps, min_samples=min_samples, metric=metric, algorithm=algorithm, n_jobs=n_jobs)
    db.fit(Xu, sample_weight=w)
    return db.labels_[inv], db
