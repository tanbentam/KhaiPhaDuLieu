"""Kiem tra nhat quan so lieu giua cac artifact (M4-09, H05/H06).

M4 KHONG sua so lieu: moi check chi doc CSV/van ban va bao PASS / WARN / FAIL.
FAIL/WARN duoc tra ve cho owner (M1/M2/M3) xac minh.

Chay:   python scripts/run_qa.py
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd

MET = Path("outputs") / "metrics"
FIG = Path("outputs") / "figures"
MAP = Path("outputs") / "maps"
BBOX = dict(lat_min=41.64, lat_max=42.05, lon_min=-87.94, lon_max=-87.52)


@dataclass
class Result:
    check_id: str
    scope: str
    status: str      # PASS | WARN | FAIL
    detail: str
    owner: str = ""  # M1 / M2 / M3 / M4


def _read(root: Path, rel: Path) -> pd.DataFrame:
    return pd.read_csv(root / rel)


# --------------------------------------------------------------------------- checks

def check_schema_and_samples(root: Path) -> list[Result]:
    from src.evaluation.runlog import RUN_LOG_COLUMNS

    res: list[Result] = []
    base = _read(root, MET / "baseline_metrics.csv")
    hdb = _read(root, MET / "hdbscan_metrics.csv")
    for name, df, owner in (("baseline_metrics.csv", base, "M2"), ("hdbscan_metrics.csv", hdb, "M3")):
        ok = list(df.columns) == RUN_LOG_COLUMNS
        res.append(Result("QA-01", name, "PASS" if ok else "FAIL",
                          f"schema {'khớp' if ok else 'KHÁC'} RUN_LOG_COLUMNS ({len(df.columns)} cột)", owner))
    both = pd.concat([base, hdb])
    res.append(Result("QA-02", "H05", "PASS" if both["sample_id"].nunique() == 1 else "FAIL",
                      f"sample_id = {sorted(both['sample_id'].unique())}", "M2/M3"))
    npts = both.groupby("time_slice")["n_points"].nunique()
    res.append(Result("QA-03", "H05", "PASS" if (npts == 1).all() else "FAIL",
                      "cùng n_points giữa 3 thuật toán theo lát cắt: " +
                      ", ".join(f"{s}={both[both.time_slice == s].n_points.iloc[0]:,}" for s in npts.index), "M2/M3"))
    cnt = both.groupby(["algorithm", "time_slice"]).size()
    res.append(Result("QA-04", "H05", "PASS" if (cnt == 1).all() and len(cnt) == 9 else "FAIL",
                      f"{len(cnt)} cặp (thuật toán × lát cắt), mỗi cặp 1 run_id", "M2/M3"))
    # Silhouette co dung n_points_metric = n_points - n_noise
    exp = both["n_points"] - both["n_noise"]
    ok = (exp == both["n_points_metric"]).all()
    res.append(Result("QA-05", "metrics", "PASS" if ok else "FAIL",
                      "n_points_metric = n_points − n_noise (metric chỉ trên điểm có nhãn)", "M2/M3"))
    km = both[both.algorithm == "kmeans"]
    res.append(Result("QA-06", "metrics", "PASS" if (km["noise_ratio"] == 0).all() else "FAIL",
                      "K-Means Noise Ratio = 0 (theo thiết kế, không phải ưu điểm)", "M2"))
    return res


def check_cluster_tables(root: Path) -> list[Result]:
    res: list[Result] = []
    met = pd.concat([_read(root, MET / "baseline_metrics.csv"), _read(root, MET / "hdbscan_metrics.csv")])
    met = met.set_index("run_id")
    for algo, owner in (("kmeans", "M2"), ("dbscan", "M2"), ("hdbscan", "M3")):
        t = _read(root, MET / f"{algo}_clusters_master_v1.csv")
        if algo == "dbscan" and "role" in t.columns:
            t = t[t["role"].astype(str).str.contains("chinh")]
        runs = set(t["run_id"])
        ok = runs <= set(met.index)
        res.append(Result("QA-07", f"{algo}_clusters", "PASS" if ok else "FAIL",
                          f"{len(runs)} run_id đều có trong metrics" if ok else f"run_id lạ: {runs - set(met.index)}", owner))
        bad = []
        for rid, g in t.groupby("run_id"):
            m = met.loc[rid]
            noise = int(g["noise_trips"].iloc[0]) if "noise_trips" in g.columns else 0
            if len(g) != int(m["n_clusters"]):
                bad.append(f"{rid}: {len(g)} cụm vs metrics {int(m['n_clusters'])}")
            if int(g["n_trips"].sum()) + noise != int(m["n_points"]):
                bad.append(f"{rid}: Σtrips+noise={int(g['n_trips'].sum()) + noise} vs n_points={int(m['n_points'])}")
        res.append(Result("QA-08", f"{algo}_clusters", "PASS" if not bad else "FAIL",
                          "số cụm và Σ(chuyến)+noise khớp metrics" if not bad else "; ".join(bad), owner))
    return res


def check_crs(root: Path) -> list[Result]:
    """center_x_m/y_m (EPSG:26916) phai khop center_lat/lon (EPSG:4326) — bat loi dao lat/lon (R06)."""
    from pyproj import Transformer

    tr = Transformer.from_crs("EPSG:4326", "EPSG:26916", always_xy=True)
    res: list[Result] = []
    for algo, owner in (("kmeans", "M2"), ("dbscan", "M2"), ("hdbscan", "M3")):
        t = _read(root, MET / f"{algo}_clusters_master_v1.csv")
        x, y = tr.transform(t["center_lon"].to_numpy(), t["center_lat"].to_numpy())
        err = np.hypot(x - t["center_x_m"].to_numpy(), y - t["center_y_m"].to_numpy())
        inb = (t["center_lat"].between(BBOX["lat_min"], BBOX["lat_max"]) &
               t["center_lon"].between(BBOX["lon_min"], BBOX["lon_max"])).all()
        ok = float(err.max()) < 1.0 and inb
        res.append(Result("QA-09", f"{algo}_clusters", "PASS" if ok else "FAIL",
                          f"x,y ↔ lat,lon sai số lớn nhất {err.max():.3f} m; trong bbox Chicago: {inb}", owner))
    pc = _read(root, MET / "eda" / "pickup_coords.csv")
    inb = (pc["lat"].between(BBOX["lat_min"], BBOX["lat_max"]) & pc["lon"].between(BBOX["lon_min"], BBOX["lon_max"]))
    res.append(Result("QA-10", "pickup_coords", "PASS" if inb.all() else "WARN",
                      f"{int(inb.sum())}/{len(pc)} tọa độ trong bbox Chicago", "M1"))
    return res


def check_tracking(root: Path) -> list[Result]:
    res: list[Result] = []
    tr = _read(root, MET / "hotspot_tracking.csv")
    hc = _read(root, MET / "hdbscan_clusters_master_v1.csv")
    sl = {s: g.set_index("cluster") for s, g in hc.groupby("time_slice")}
    bad = 0
    matched_mask = tr["status"].isin({"MATCHED", "STABLE", "MERGED", "SPLIT"})
    for r in tr[matched_mask].itertuples(index=False):
        a, b = r.transition.split(" -> ")
        if int(sl[a].loc[int(r.cluster_from), "n_trips"]) != int(r.trips_from) or \
           int(sl[b].loc[int(r.cluster_to), "n_trips"]) != int(r.trips_to):
            bad += 1
    res.append(Result("QA-11", "hotspot_tracking", "PASS" if bad == 0 else "FAIL",
                      f"trips_from/trips_to khớp hdbscan_clusters ({bad} dòng lệch)", "M3"))
    m = tr[matched_mask]
    zero = float((m["shift_distance_m"] == 0).mean())
    res.append(Result("QA-12", "hotspot_tracking",
                      "WARN" if zero > 0.5 else "PASS",
                      f"{zero * 100:.0f}% cặp ghép (STABLE/MERGED/SPLIT) có dịch chuyển đúng 0 m (cụm trùng 1 centroid) — "
                      "giới hạn độ phân giải tọa độ, không nên đọc là 'đứng yên tuyệt đối'", "M3"))
    single = float((hc["n_coords"] == 1).mean())
    res.append(Result("QA-13", "hdbscan_clusters", "WARN" if single > 0.4 else "PASS",
                      f"{single * 100:.0f}% cụm HDBSCAN chỉ gồm 1 tọa độ duy nhất (bán kính 0) → "
                      "Silhouette/DBI của HDBSCAN bị thổi phồng, không so trực tiếp với K-Means/DBSCAN", "M3"))
    return res


def check_fit_mode(root: Path) -> list[Result]:
    both = pd.concat([_read(root, MET / "baseline_metrics.csv"), _read(root, MET / "hdbscan_metrics.csv")])
    modes = {a: sorted({str(json.loads(p).get("mode", "unweighted")) for p in g["params"]})
             for a, g in both.groupby("algorithm")}
    same = len({tuple(v) for v in modes.values()}) == 1
    libs = both.groupby("algorithm")["lib_versions"].apply(lambda s: sorted({json.loads(x).get("python", "?") for x in s}))
    return [
        Result("QA-14", "runtime", "PASS" if same else "WARN",
               f"chế độ fit theo thuật toán: {modes} → " + ("cùng cách fit" if same else
               "KHÔNG cùng cách fit (weighted trên tọa độ duy nhất vs toàn bộ điểm): runtime không so trực tiếp"), "M2/M3"),
        Result("QA-15", "environment", "WARN" if len({tuple(v) for v in libs}) > 1 else "PASS",
               f"phiên bản Python theo thuật toán: {libs.to_dict()} — BA 2.4 yêu cầu ghi/đồng nhất môi trường khi đo runtime",
               "M2/M3"),
    ]


def check_artifacts(root: Path, required: list[str]) -> list[Result]:
    miss = [p for p in required if not (root / p).is_file() or (root / p).stat().st_size == 0]
    return [Result("QA-16", "artifacts", "PASS" if not miss else "FAIL",
                   f"{len(required) - len(miss)}/{len(required)} artifact tồn tại và không rỗng" +
                   (f"; thiếu: {miss}" if miss else ""), "M4")]


def check_html_maps(root: Path) -> list[Result]:
    """Moi HTML map phai co legend/tieu de va nhac den centroid khong phai GPS."""
    res: list[Result] = []
    for p in sorted((root / MAP).glob("*.html")):
        if p.name == "cluster_comparison.html":   # bieu do Plotly, khong phai ban do
            continue
        txt = p.read_text(encoding="utf-8", errors="ignore")
        has_caveat = bool(re.search(r"khong phai GPS|không phải GPS|KHÔNG phải GPS|không phải vị trí GPS", txt, re.I))
        res.append(Result("QA-17", p.name, "PASS" if has_caveat else "WARN",
                          "có chú thích centroid ≠ GPS" if has_caveat else "thiếu chú thích centroid ≠ GPS trong HTML",
                          "M4" if p.name in M4_MAPS else "M2/M3"))
    return res


M4_MAPS = {"pickup_demand_heatmap.html", "cluster_map_kmeans.html", "cluster_map_dbscan.html",
           "cluster_map_hdbscan.html", "cluster_map_comparison.html"}


# ---------------------------------------------------------------- claim register

def claim_register(root: Path) -> pd.DataFrame:
    """So khop cac khang dinh trong van ban M3 voi CSV da phat hanh.

    Moi dong: claim (trich tu van ban), nguon (file), observed (tinh tu CSV), verdict. Neu van ban duoc sua
    va khang dinh khong con xuat hien thi dong duoc danh dau RESOLVED.
    """
    hm = _read(root, MET / "hdbscan_metrics.csv")
    hc = _read(root, MET / "hdbscan_clusters_master_v1.csv")
    dc = _read(root, MET / "dbscan_clusters_master_v1.csv")
    dc = dc[dc["role"].astype(str).str.contains("chinh")]
    tr = _read(root, MET / "hotspot_tracking.csv")
    src_report = Path("reports") / "m3_hdbscan_temporal.md"
    src_interp = Path("docs") / "Phan 5" / "hdbscan_interpretation.md"
    src_handoff = Path("docs") / "Phan 5" / "5.5-bien-ban-ban-giao-m3.md"
    txt = {p: (root / p).read_text(encoding="utf-8") if (root / p).exists() else "" for p in (src_report, src_interp, src_handoff)}

    def present(p: Path, pat: str) -> bool:
        return bool(re.search(pat, txt[p]))

    def share_area(area: int, s: str) -> float:
        return float(hc[(hc.top_community_area == area) & (hc.time_slice == s)]["share"].sum())

    rows = []

    def add(cid, p, pat, claim, observed, ok):
        found = present(p, pat)
        rows.append(dict(claim_id=cid, source=str(p).replace("\\", "/"), claim=claim, observed=observed,
                         verdict=("RESOLVED" if not found else ("KHỚP" if ok else "KHÔNG KHỚP")), owner="M3"))

    nz = hm.set_index("time_slice")
    add("C01", src_report, r"10,8\\%|quanh \$10\\%\$",
        "HDBSCAN (mcs=100, ms=10) có Noise Ratio ≈ 10% (10,8%)",
        "metrics chính thức: " + ", ".join(f"{s} {nz.loc[s, 'noise_ratio'] * 100:.1f}%" for s in nz.index), False)
    add("C02", src_interp, r"9,8\\% - 11,5\\%",
        "HDBSCAN Noise Ratio 9,8%–11,5%",
        f"metrics chính thức: {hm.noise_ratio.min() * 100:.1f}%–{hm.noise_ratio.max() * 100:.1f}%", False)
    add("C03", src_report, r"4 cụm lớn ổn định",
        "mcs=100 cho '4 cụm lớn' (Loop/Near North, O'Hare, Midway, Hyde Park)",
        "bảng cụm chính thức: " + ", ".join(f"{s} {int(nz.loc[s, 'n_clusters'])} cụm" for s in nz.index), False)
    add("C04", src_report, r"Silhouette đạt \$0,78\$",
        "Silhouette 0,78 và DBI 0,19 cho cấu hình chọn",
        f"metrics chính thức: Silhouette {hm.silhouette.min():.3f}–{hm.silhouette.max():.3f}; "
        f"DBI {hm.davies_bouldin.min():.3f}–{hm.davies_bouldin.max():.3f}", False)
    # O'Hare share
    oh_am, oh_pm = share_area(76, "WEEKDAY_AM"), share_area(76, "WEEKDAY_PM")
    add("C05", src_report, r"11,5\\%\$ tổng số chuyến",
        "O'Hare tăng từ 11,5% (sáng) lên 16,8% (chiều)",
        f"Σ share cụm khu 76: sáng {oh_am * 100:.1f}% → chiều {oh_pm * 100:.1f}% "
        f"(cụm lớn nhất: 10,6% → 12,8%)", abs(oh_am - 0.115) < 0.005 and abs(oh_pm - 0.168) < 0.005)
    # Loop -> Near North 820 m
    matched_statuses = {"MATCHED", "STABLE", "MERGED", "SPLIT"}
    big = tr[(tr.transition == "WEEKDAY_AM -> WEEKDAY_PM") & (tr.status.isin(matched_statuses)) &
             (tr.trips_from >= 2000)]
    add("C06", src_report, r"820",
        "Tâm cụm trung tâm dịch chuyển 820 m về phía bắc (sáng → chiều); interpretation: 650–950 m",
        "dịch chuyển của các cụm lớn (≥ 2000 chuyến) sáng→chiều: " +
        ", ".join(f"{d:.0f} m" for d in big["shift_distance_m"].tolist()) +
        "; không có cặp nào trong khoảng 650–950 m ở nhóm này",
        bool(((big.shift_distance_m > 650) & (big.shift_distance_m < 950)).any()))
    # Hyde Park
    hp = hc[hc.top_community_area == 41]
    add("C07", src_report, r"611\$ chuyến",
        "Hyde Park (khu 41) xuất hiện rõ ở sáng ngày thường (611 chuyến, 1,0%), tan rã chiều/cuối tuần",
        "HDBSCAN khu 41: " + ", ".join(f"{s} {int(g.n_trips.sum())} chuyến ({g.share.sum() * 100:.1f}%)"
                                         for s, g in hp.groupby("time_slice")) +
        f". Số 611 chuyến / 1,0% trùng cụm DBSCAN A khu 41: {int(dc[(dc.top_community_area == 41) & (dc.time_slice == 'WEEKDAY_AM')].n_trips.sum())} chuyến", False)
    # Midway 4.2-4.8
    mw = {s: share_area(56, s) for s in ("WEEKDAY_AM", "WEEKDAY_PM", "WEEKEND")}
    add("C08", src_report, r"4,2\\% - 4,8\\%",
        "Midway (khu 56) giữ tỷ trọng 4,2%–4,8% ở cả 3 lát cắt",
        "Σ share cụm HDBSCAN khu 56: " + ", ".join(f"{s} {v * 100:.1f}%" for s, v in mw.items()),
        all(0.042 <= v <= 0.048 for v in mw.values()))
    # DBSCAN noise range (khop)
    dn = dc.groupby("time_slice")["noise_share"].first()
    add("C09", src_interp, r"9,4\\% - 12,6\\%",
        "DBSCAN Noise Ratio 9,4%–12,6%",
        f"dbscan_clusters (A): {dn.min() * 100:.1f}%–{dn.max() * 100:.1f}%",
        abs(dn.min() - 0.094) < 0.001 and abs(dn.max() - 0.126) < 0.001)
    # Handoff: bang tong hop 9 dong
    both = pd.concat([_read(root, MET / "baseline_metrics.csv"), hm])
    add("C10", src_handoff, r"đúng 9 dòng",
        "Bảng H05 gồm đúng 9 dòng (3 K-Means, 3 DBSCAN A, 3 HDBSCAN)", f"baseline + hdbscan = {len(both)} dòng", len(both) == 9)
    return pd.DataFrame(rows)


def run_all(root: str | Path = ".", required_artifacts: list[str] | None = None) -> pd.DataFrame:
    root = Path(root)
    results: list[Result] = []
    for fn in (check_schema_and_samples, check_cluster_tables, check_crs, check_tracking, check_fit_mode,
               check_html_maps):
        results += fn(root)
    if required_artifacts:
        results += check_artifacts(root, required_artifacts)
    return pd.DataFrame([asdict(r) for r in results])
