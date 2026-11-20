"""Kiem thu phan M4: bang gop H05, tinh nhat quan, extent chung, QA (chay: pytest tests/test_m4.py)."""
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))

from src.qa.consistency import (check_cluster_tables, check_crs, check_schema_and_samples,  # noqa: E402
                                check_tracking, claim_register)
from src.visualization.comparison import merge_metrics  # noqa: E402
from src.visualization.m4_maps import check_in_bbox, load_cluster_tables, shared_extent  # noqa: E402
from src.visualization.style import ALGO_COLOR, NOISE_COLOR, fmt_int, fmt_pct  # noqa: E402


def test_merge_has_9_rows_and_same_sample():
    df = merge_metrics(ROOT)
    assert len(df) == 9 and df["sample_id"].nunique() == 1
    assert set(df.algorithm) == {"kmeans", "dbscan", "hdbscan"}
    # gia tri goc khong bi sua
    hd = pd.read_csv(ROOT / "outputs/metrics/hdbscan_metrics.csv")
    m = df[df.algorithm == "hdbscan"].set_index("run_id")
    for r in hd.itertuples():
        assert m.loc[r.run_id, "silhouette"] == pytest.approx(r.silhouette)


def test_merge_rejects_schema_mismatch(tmp_path):
    (tmp_path / "outputs/metrics").mkdir(parents=True)
    pd.DataFrame({"run_id": ["a"], "x": [1]}).to_csv(tmp_path / "outputs/metrics/baseline_metrics.csv", index=False)
    pd.DataFrame({"run_id": ["b"], "y": [1]}).to_csv(tmp_path / "outputs/metrics/hdbscan_metrics.csv", index=False)
    with pytest.raises(ValueError):
        merge_metrics(tmp_path)


def test_qa_core_checks_pass():
    for fn in (check_schema_and_samples, check_cluster_tables, check_crs):
        assert all(r.status != "FAIL" for r in fn(ROOT)), fn.__name__
    assert all(r.status != "FAIL" for r in check_tracking(ROOT))


def test_shared_extent_covers_all_centroids():
    t = load_cluster_tables(ROOT)
    lat0, lon0, lat1, lon1 = shared_extent(t)
    for df in t.values():
        assert df.center_lat.between(lat0, lat1).all() and df.center_lon.between(lon0, lon1).all()
    # dbscan chi giu cau hinh chinh
    assert t["dbscan"]["run_id"].nunique() == 3


def test_bbox_filter_drops_out_of_range():
    df = pd.DataFrame({"lat": [41.88, 0.0, -87.6], "lon": [-87.63, -87.6, 41.8]})  # dong 3 dao lat/lon
    ok, bad = check_in_bbox(df, "lat", "lon")
    assert len(ok) == 1 and len(bad) == 2


def test_claim_register_flags_known_mismatch():
    cl = claim_register(ROOT).set_index("claim_id")
    assert cl.loc["C10", "verdict"] in ("KHỚP", "RESOLVED")
    assert cl.loc["C01", "verdict"] in ("KHÔNG KHỚP", "RESOLVED")


def test_style_conventions():
    assert NOISE_COLOR not in ALGO_COLOR.values() and len(set(ALGO_COLOR.values())) == 3
    assert fmt_int(60498) == "60.498" and fmt_pct(0.1264) == "12,6%"
