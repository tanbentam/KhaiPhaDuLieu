"""Bo kiem thu doc lap cho cac module cua M2 (K-Means, DBSCAN, evaluation, maps).

Chay bang: python -m tests.test_m2
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics import adjusted_rand_score

from src.evaluation.hotspots import cluster_table, relabel_by_size
from src.evaluation.metrics import evaluate
from src.models.dbscan import (
    estimate_full_neighbors,
    fit_weighted as dbscan_fit_weighted,
    k_distance_curve,
    knee_eps,
    min_samples_from_frac,
    scan_grid,
    weighted_k_distance,
)
from src.models.kmeans import aggregate_unique, elbow, fit_weighted as kmeans_fit_weighted, knee_point, scan_k
from src.visualization.maps import NOISE_COLOR, PALETTE, cluster_map


def _make_centroid_data(seed: int = 42) -> np.ndarray:
    """Tao du lieu gia lap dang centroid: 24 toa do trung lap thanh nhieu chuyen, chia 3 cum + 2 diem nhieu."""
    rng = np.random.default_rng(seed)
    centers = [(448000.0, 4637000.0), (425000.0, 4647000.0), (438000.0, 4626000.0)]
    coords = []
    weights = []
    for cx, cy in centers:
        for _ in range(8):
            coords.append([cx + rng.normal(0, 250), cy + rng.normal(0, 250)])
            weights.append(int(rng.integers(40, 120)))
    # 2 diem nhieu xa cum
    coords.extend([[460000.0, 4610000.0], [410000.0, 4615000.0]])
    weights.extend([3, 2])
    return np.repeat(np.asarray(coords, dtype=np.float64), weights, axis=0)


def test_aggregate_and_kmeans_weighted_equals_full() -> None:
    X = _make_centroid_data()
    Xu, w, inv = aggregate_unique(X)
    assert len(Xu) == 26
    assert int(w.sum()) == len(X)
    assert np.allclose(Xu[inv], X)

    lw, kmw = kmeans_fit_weighted(X, k=3, n_init=20, seed=42)
    kmf = KMeans(n_clusters=3, init="k-means++", n_init=20, max_iter=300, random_state=42).fit(X)
    assert adjusted_rand_score(kmf.labels_, lw) == 1.0
    assert np.isclose(kmw.inertia_, kmf.inertia_, rtol=1e-6)

    # K > n_distinct phai bao loi
    try:
        kmeans_fit_weighted(X, k=len(Xu) + 1)
        raise AssertionError("Phai bao ValueError khi k > n_distinct")
    except ValueError:
        pass


def test_kmeans_elbow_scan_and_knee() -> None:
    X = _make_centroid_data()
    Xu, w, _ = aggregate_unique(X)
    eb = elbow(Xu, k_min=2, k_max=6, n_init=10, seed=42, sample_weight=w)
    assert list(eb["k"]) == [2, 3, 4, 5, 6]
    assert eb["converged"].all()
    assert np.all(np.diff(eb["inertia"].to_numpy()) <= 1e-6)
    assert knee_point(eb["k"], eb["inertia"]) == 3

    ks = scan_k(X, [2, 3, 4], n_init=10, seed=42, silhouette_max_sample=1000)
    assert list(ks["k"]) == [2, 3, 4]
    assert int(ks.loc[ks["silhouette"].idxmax(), "k"]) == 3
    assert ks["silhouette_unique"].notna().all()


def test_dbscan_weighted_and_kdistance() -> None:
    X = _make_centroid_data()
    Xu, w, _ = aggregate_unique(X)

    assert min_samples_from_frac(60498, 0.01) == 605
    assert min_samples_from_frac(10, 0.01) == 2

    k = 100
    kd = weighted_k_distance(Xu, w, k=k)
    assert np.all(np.isfinite(kd))
    # Kiem tra dung nguong core: dat eps = kd[i] -> tong trong so trong ban kinh >= k
    for i in range(len(Xu)):
        d = np.linalg.norm(Xu - Xu[i], axis=1)
        assert w[d <= kd[i] + 1e-2].sum() >= k - 1e-9
        if kd[i] > 1e-1:
            assert w[d <= kd[i] - 1e-2].sum() < k

    share, dist = k_distance_curve(X, k=k)
    assert np.isclose(share[-1], 1.0)
    assert np.all(np.diff(dist) >= -1e-9)
    assert knee_eps(share, dist) > 0

    # estimate_full_neighbors khop chinh xac voi dem truc tiep
    eps = 1000.0
    est = estimate_full_neighbors(X, eps)
    # Tinh truc tiep tren Xu*w: sum_i w_i * sum_{j: d(i,j)<=eps} w_j
    from sklearn.neighbors import NearestNeighbors
    nb = NearestNeighbors(radius=eps).fit(X).radius_neighbors(X, return_distance=False)
    exact = sum(len(idx) for idx in nb)
    assert est == exact

    # fit_weighted trung khop hoan toan voi DBSCAN full
    ms = 50
    lw, _ = dbscan_fit_weighted(X, eps=eps, min_samples=ms)
    lf = DBSCAN(eps=eps, min_samples=ms).fit_predict(X)
    assert adjusted_rand_score(lf, lw) == 1.0
    assert np.array_equal(lf == -1, lw == -1)

    grid = scan_grid(X, [1000.0, 2000.0], [("spec 50", 50)], seed=42, silhouette_max_sample=1000)
    assert len(grid) == 2
    assert (grid["n_points"] == len(X)).all()


def test_evaluation_edge_cases_and_hotspots() -> None:
    X = _make_centroid_data()
    # Toan bo la nhieu -> metrics = None
    r_noise = evaluate(X, np.full(len(X), -1))
    assert r_noise["n_clusters"] == 0
    assert r_noise["noise_ratio"] == 1.0
    assert r_noise["silhouette"] is None

    # Chi co 1 cum -> metrics = None
    r_one = evaluate(X, np.zeros(len(X), dtype=int))
    assert r_one["n_clusters"] == 1
    assert r_one["silhouette"] is None

    # relabel_by_size: cum lon nhat = 0, nhieu giu -1
    raw = np.array([5, 5, 2, 2, 2, -1])
    rel = relabel_by_size(raw)
    assert list(rel) == [1, 1, 0, 0, 0, -1]

    # cluster_table
    df = pd.DataFrame({"x_m": X[:, 0], "y_m": X[:, 1], "pickup_community_area": pd.Series([32] * len(X), dtype="Int16")})
    lw, _ = kmeans_fit_weighted(X, k=3, n_init=10, seed=42)
    ct = cluster_table(df, relabel_by_size(lw))
    assert len(ct) == 3
    assert int(ct["n_trips"].sum()) == len(X)
    assert np.isclose(ct["share"].sum(), 1.0)
    assert ct["center_lat"].between(41.0, 43.0).all()


def test_maps_palette_and_xss_escape() -> None:
    assert len(PALETTE) >= 20
    assert len(set(PALETTE)) == len(PALETTE)
    assert NOISE_COLOR not in PALETTE
    # Khong co mau xam trung lap (R == G == B) trong PALETTE
    for hx in PALETTE:
        r, g, b = int(hx[1:3], 16), int(hx[3:5], 16), int(hx[5:7], 16)
        assert not (abs(r - g) <= 10 and abs(g - b) <= 10), f"Mau qua gan xam: {hx}"

    df = pd.DataFrame({
        "x_m": [448000.0, 448100.0, 425000.0],
        "y_m": [4637000.0, 4637100.0, 4647000.0],
        "pickup_lat": [41.88, 41.881, 41.97],
        "pickup_lon": [-87.63, -87.629, -87.90],
    })
    labels = np.array([0, 0, -1])
    ct = cluster_table(df, labels)
    with tempfile.TemporaryDirectory() as td:
        out = cluster_map({"<script>alert(1)</script>": (df, labels, ct)}, Path(td) / "m.html",
                          title="<b>Test</b>", note="<img onerror=1>")
        html_txt = out.read_text(encoding="utf-8")
        assert "<script>alert(1)</script>" not in html_txt
        assert "&lt;b&gt;Test&lt;/b&gt;" in html_txt
        assert "&lt;img onerror=1&gt;" in html_txt
        assert "centroid" in html_txt.lower()


def main() -> None:
    tests = [
        test_aggregate_and_kmeans_weighted_equals_full,
        test_kmeans_elbow_scan_and_knee,
        test_dbscan_weighted_and_kdistance,
        test_evaluation_edge_cases_and_hotspots,
        test_maps_palette_and_xss_escape,
    ]
    for fn in tests:
        fn()
        print(f"PASS: {fn.__name__}")
    print(f"\n{len(tests)} PASS, 0 FAIL")


if __name__ == "__main__":
    main()
