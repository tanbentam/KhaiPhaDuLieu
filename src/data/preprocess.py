"""Tien xu ly du lieu pickup: lam sach -> chieu toa do -> dac trung thoi gian -> lay mau -> phat hanh.

Task M1-05 .. M1-08. Dau vao la bang da qua extract.parse_types (file tho, chua loc dong nao).

    clean()                -> bang da loai dong + cot co, kem NHAT KY tung quy tac        (M1-05)
    project_coordinates()  -> x_m, y_m (met) tu lon/lat; validate_crs() kiem tra          (M1-06)
    add_features()         -> pickup_hour, weekday, is_weekend, is_weekday, daypart, time_slice (M1-07)
    build_master()         -> gop ba buoc tren thanh bang master, sap theo trip_id
    stratified_sample()    -> mau phan tang weekday x gio, co seed
    release()              -> ghi parquet + manifest (sha256), KHONG ghi de ban da phat hanh (M1-08)
    validate_release()     -> doc lai file da ghi va kiem tra tung dieu kien

Dac trung dua vao mo hinh chi gom [x_m, y_m]. Cac cot thoi gian chi de LOC lat cat, khong vao ma tran khoang cach.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import yaml

from src.m2_pilot import PORTAL_URL, assign_time_slice, sha256, where_clause

RULES_REL = Path("config") / "cleaning_rules.yaml"
LAT, LON = "pickup_centroid_latitude", "pickup_centroid_longitude"
FEATURES = ["x_m", "y_m"]                       # ma tran dac trung cua ca ba mo hinh
STRATA = ["weekday", "pickup_hour"]             # tang lay mau

# Thu tu cot cua file giao (docs/dinh-dang-du-lieu.md muc 2, them daypart / is_weekday / co)
COLUMNS = ["trip_id", "trip_start_timestamp", "x_m", "y_m", "pickup_lat", "pickup_lon",
           "pickup_hour", "weekday", "is_weekend", "is_weekday", "daypart", "time_slice",
           "pickup_community_area", "trip_seconds", "trip_miles"]

FEATURE_DICT = [  # (cot, kieu, don vi, vai tro, mo ta)
    ("trip_id", "string", "-", "khoa", "Ma chuyen di, duy nhat; file sap tang dan theo cot nay"),
    ("trip_start_timestamp", "datetime64[ns]", "gio dia phuong Chicago", "goc", "Thoi diem don, nguon lam tron 15 phut"),
    ("x_m", "float64", "met", "DAC TRUNG", "Toa do dong (easting) cua diem don, EPSG:26916"),
    ("y_m", "float64", "met", "DAC TRUNG", "Toa do bac (northing) cua diem don, EPSG:26916"),
    ("pickup_lat", "float64", "do", "ve ban do", "Vi do WGS84 cua TAM vung don; khong dua vao mo hinh"),
    ("pickup_lon", "float64", "do", "ve ban do", "Kinh do WGS84 cua TAM vung don; khong dua vao mo hinh"),
    ("pickup_hour", "int8", "gio 0-23", "loc / EDA", "Gio bat dau chuyen"),
    ("weekday", "int8", "0-6", "loc / EDA", "0 = thu Hai ... 6 = Chu nhat"),
    ("is_weekend", "bool", "-", "loc", "weekday thuoc {5, 6}"),
    ("is_weekday", "bool", "-", "loc", "weekday thuoc {0..4}"),
    ("daypart", "string", "-", "EDA", "AM_PEAK 07-09h, MIDDAY 10-15h, PM_PEAK 16-18h, NIGHT 19-06h"),
    ("time_slice", "string", "-", "LOC LAT CAT", "WEEKDAY_AM / WEEKDAY_PM / WEEKEND theo config; con lai la OTHER"),
    ("pickup_community_area", "Int16", "ma khu 1-77", "dien giai", "Ma community area; co the rong"),
    ("trip_seconds", "float64", "giay", "kiem tra", "Thoi luong chuyen; khong dua vao mo hinh"),
    ("trip_miles", "float64", "dam", "kiem tra", "Quang duong chuyen; khong dua vao mo hinh"),
]


# =============================================================================
# M1-05  LAM SACH
# =============================================================================

def load_rules(path: str | Path | None = None, root: str | Path | None = None) -> dict[str, Any]:
    if path is None:
        from src.config import find_repo_root
        path = Path(root or find_repo_root()) / RULES_REL
    with open(path, encoding="utf-8") as f:
        rules = yaml.safe_load(f)
    ids_drop, ids_flag = [r["id"] for r in rules["drop"]], [r["id"] for r in rules["flag"]]
    if set(ids_drop) != set(DROP_MASKS) or set(ids_flag) != set(FLAG_MASKS):
        raise ValueError(f"cleaning_rules.yaml khong khop code. drop: {sorted(set(ids_drop) ^ set(DROP_MASKS))}, "
                         f"flag: {sorted(set(ids_flag) ^ set(FLAG_MASKS))}")
    return rules


def speed_mph(df: pd.DataFrame) -> pd.Series:
    """dam / gio; chi tinh khi thoi luong > 0 (tranh chia cho 0)."""
    secs, miles = df["trip_seconds"], df["trip_miles"]
    return pd.Series(np.where(secs > 0, miles / (secs / 3600.0), np.nan), index=df.index)


def _in_bbox(df: pd.DataFrame, b: dict[str, float]) -> pd.Series:
    return df[LAT].between(b["lat_min"], b["lat_max"]) & df[LON].between(b["lon_min"], b["lon_max"])


# Moi ham tra ve mat na True = dong DINH quy tac. ctx: {"lo", "hi", "rules"}
Mask = Callable[[pd.DataFrame, dict[str, Any]], pd.Series]

DROP_MASKS: dict[str, Mask] = {
    "trip_id_null": lambda d, c: d["trip_id"].isna(),
    "trip_id_duplicate": lambda d, c: d["trip_id"].duplicated(keep="first"),
    "start_time_invalid": lambda d, c: d["trip_start_timestamp"].isna(),
    "start_time_outside_window": lambda d, c: ~((d["trip_start_timestamp"] >= c["lo"]) & (d["trip_start_timestamp"] < c["hi"])),
    "pickup_coord_missing": lambda d, c: d[LAT].isna() | d[LON].isna(),
    "pickup_coord_out_of_range": lambda d, c: ~(d[LAT].between(-90, 90) & d[LON].between(-180, 180)),
    "pickup_outside_chicago_bbox": lambda d, c: ~_in_bbox(d, c["rules"]["bbox"]),
}

FLAG_MASKS: dict[str, Mask] = {
    "flag_zero_duration": lambda d, c: ~(d["trip_seconds"] > 0),
    "flag_zero_distance": lambda d, c: ~(d["trip_miles"] > 0),
    "flag_speed_gt_80": lambda d, c: speed_mph(d) > c["rules"]["speed_flag_mph"],
    "flag_end_before_start": lambda d, c: (d["trip_end_timestamp"] < d["trip_start_timestamp"]).fillna(False),
    "flag_missing_area": lambda d, c: d["pickup_community_area"].isna(),
}


def clean(df: pd.DataFrame, rules: dict[str, Any], start: str, end: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Ap quy tac `drop` lan luot roi gan cot co. Tra ve (bang sach, nhat ky).

    Nhat ky: moi quy tac mot dong, co so dong truoc / dinh quy tac / sau. Khong co dong nao bi bo am tham:
    tong `rows_matched` cua cac quy tac drop = so dong tho - so dong sach (ham tu kiem tra).
    """
    ctx = {"lo": pd.Timestamp(start), "hi": pd.Timestamp(end) + pd.Timedelta(days=1), "rules": rules}
    n_raw = len(df)
    out, log = df, []

    def add(step: int, r: dict[str, Any], action: str, before: int, matched: int, after: int) -> None:
        log.append({"step": step, "rule_id": r["id"], "action": action, "condition": r["condition"],
                    "reason": r["reason"], "rows_before": before, "rows_matched": matched, "rows_after": after,
                    "matched_pct_of_raw": round(100.0 * matched / n_raw, 4) if n_raw else 0.0})

    step = 0
    for r in rules["drop"]:
        step += 1
        m = DROP_MASKS[r["id"]](out, ctx).fillna(False).astype(bool)
        before = len(out)
        out = out[~m]
        add(step, r, "drop", before, int(m.sum()), len(out))

    out = out.copy()
    for r in rules["flag"]:
        step += 1
        m = FLAG_MASKS[r["id"]](out, ctx).fillna(False).astype(bool)
        out[r["id"]] = m.to_numpy()
        add(step, r, "flag", len(out), int(m.sum()), len(out))

    log_df = pd.DataFrame(log)
    dropped = int(log_df.loc[log_df["action"] == "drop", "rows_matched"].sum())
    assert dropped == n_raw - len(out), "nhat ky khong khop so dong bi loai"
    return out, log_df


def speed_sensitivity(clean_df: pd.DataFrame, rules: dict[str, Any]) -> pd.DataFrame:
    """So dong vuot nguong toc do o cac nguong khac (70 / 80 / 90 mph) de bao cao do nhay."""
    sp = speed_mph(clean_df)
    ths = sorted({*rules["speed_sensitivity_mph"], rules["speed_flag_mph"]})
    return pd.DataFrame([{"threshold_mph": t, "rows": int((sp > t).sum()),
                          "pct": round(100.0 * float((sp > t).mean()), 4)} for t in ths])


# =============================================================================
# M1-06  CHIEU TOA DO
# =============================================================================

def project_coordinates(lon, lat, crs: str = "EPSG:26916") -> tuple[np.ndarray, np.ndarray]:
    """WGS84 (kinh do, vi do) -> (x_m, y_m) theo `crs`, don vi met. Ham DUNG CHUNG cho moi notebook."""
    from pyproj import Transformer
    tf = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    x, y = tf.transform(np.asarray(lon, dtype="float64"), np.asarray(lat, dtype="float64"))
    return np.asarray(x, dtype="float64"), np.asarray(y, dtype="float64")


def validate_crs(df: pd.DataFrame, crs: str = "EPSG:26916", n_pairs: int = 2000, seed: int = 42) -> dict[str, Any]:
    """Ba phep kiem tra cho x_m / y_m (df can co pickup_lat, pickup_lon, x_m, y_m):

    1. Vung ap dung cua CRS co phu toan bo diem khong.
    2. Chieu nguoc ve lat/lon lech bao nhieu (met).
    3. Khoang cach Euclid tren x/y lech bao nhieu so voi khoang cach trac dia tren elipxoit.
    """
    from pyproj import CRS, Geod, Transformer
    c = CRS.from_user_input(crs)
    aou = c.area_of_use
    pts = df[["pickup_lat", "pickup_lon", "x_m", "y_m"]].drop_duplicates().reset_index(drop=True)
    lat, lon, x, y = (pts[k].to_numpy() for k in ["pickup_lat", "pickup_lon", "x_m", "y_m"])

    inv = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    lon2, lat2 = inv.transform(x, y)
    geod = Geod(ellps="WGS84")
    _, _, back = geod.inv(lon, lat, lon2, lat2)

    rng = np.random.default_rng(seed)
    i, j = rng.integers(0, len(pts), n_pairs), rng.integers(0, len(pts), n_pairs)
    keep = i != j
    i, j = i[keep], j[keep]
    _, _, g = geod.inv(lon[i], lat[i], lon[j], lat[j])
    e = np.hypot(x[i] - x[j], y[i] - y[j])
    rel = np.abs(e - g) / np.where(g > 0, g, np.nan)
    return {
        "crs": crs, "crs_name": c.name, "unit": c.axis_info[0].unit_name,
        "area_of_use": {"west": aou.west, "south": aou.south, "east": aou.east, "north": aou.north, "name": aou.name},
        "all_points_in_area_of_use": bool(((lon >= aou.west) & (lon <= aou.east) & (lat >= aou.south) & (lat <= aou.north)).all()),
        "unique_points": int(len(pts)),
        "x_min_m": float(x.min()), "x_max_m": float(x.max()), "y_min_m": float(y.min()), "y_max_m": float(y.max()),
        "extent_x_km": round(float(x.max() - x.min()) / 1000, 2), "extent_y_km": round(float(y.max() - y.min()) / 1000, 2),
        "roundtrip_max_error_m": float(np.max(back)),
        "pairs_checked": int(len(i)),
        "distance_max_rel_error_pct": round(100 * float(np.nanmax(rel)), 4),
        "distance_median_rel_error_pct": round(100 * float(np.nanmedian(rel)), 4),
        "distance_max_abs_error_m": round(float(np.max(np.abs(e - g))), 2),
    }


# =============================================================================
# M1-07  DAC TRUNG THOI GIAN
# =============================================================================

def daypart(hour: pd.Series) -> pd.Series:
    """AM_PEAK 07:00-09:59, MIDDAY 10:00-15:59, PM_PEAK 16:00-18:59, NIGHT 19:00-06:59 (BA Spec 2.2.2)."""
    h = hour.to_numpy()
    out = np.full(len(h), "NIGHT", dtype=object)
    out[(h >= 7) & (h <= 9)] = "AM_PEAK"
    out[(h >= 10) & (h <= 15)] = "MIDDAY"
    out[(h >= 16) & (h <= 18)] = "PM_PEAK"
    return pd.Series(out, index=hour.index)


def add_features(df: pd.DataFrame, slices: dict[str, Any]) -> pd.DataFrame:
    """Them pickup_hour, weekday, is_weekend, is_weekday, daypart, time_slice. Giu nguyen timestamp goc."""
    out = df.copy()
    ts = out["trip_start_timestamp"]
    out["pickup_hour"] = ts.dt.hour.astype("int8")
    out["weekday"] = ts.dt.dayofweek.astype("int8")          # 0 = thu Hai
    out["is_weekend"] = out["weekday"].isin([5, 6])
    out["is_weekday"] = ~out["is_weekend"]
    out["daypart"] = daypart(out["pickup_hour"])
    out["time_slice"] = assign_time_slice(out["weekday"], out["pickup_hour"], slices)
    return out


def build_master(typed: pd.DataFrame, rules: dict[str, Any], slices: dict[str, Any], start: str, end: str,
                 crs: str = "EPSG:26916") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Bang tho da ep kieu -> (master, nhat ky lam sach). Master: moi dong sach, du cot, sap theo trip_id."""
    cl, log = clean(typed, rules, start, end)
    cl = add_features(cl, slices)
    cl["x_m"], cl["y_m"] = project_coordinates(cl[LON], cl[LAT], crs)
    cl = cl.rename(columns={LAT: "pickup_lat", LON: "pickup_lon"})
    flags = [r["id"] for r in rules["flag"]]
    out = cl[COLUMNS + flags].sort_values("trip_id", kind="stable").reset_index(drop=True)
    out["trip_id"] = out["trip_id"].astype(str)
    out["pickup_community_area"] = out["pickup_community_area"].astype("Int16")
    return out, log


# =============================================================================
# LAY MAU PHAN TANG
# =============================================================================

def allocate(counts: pd.Series, n: int) -> pd.Series:
    """Chia n cho cac tang theo ty le so dong, lam tron bang phuong phap SO DU LON NHAT (tong dung bang n)."""
    total = int(counts.sum())
    if n >= total:
        return counts.astype(int)
    exact = counts * n / total
    base = np.floor(exact).astype(int)
    rest = n - int(base.sum())
    frac = (exact - base).sort_values(ascending=False, kind="stable")
    base.loc[frac.index[:rest]] += 1
    return base


def stratified_sample(master: pd.DataFrame, n: int, seed: int = 42, by: list[str] = STRATA) -> pd.DataFrame:
    """Mau n dong, phan tang theo `by` (mac dinh thu x gio), ty le giu nguyen nhu tong the.

    Tai lap duoc: master phai sap theo trip_id; cac tang duoc duyet theo thu tu khoa; mot bo sinh so
    ngau nhien duy nhat khoi tao tu `seed`. Cung master + cung n + cung seed -> cung tap trip_id.
    """
    if n >= len(master):
        return master.copy()
    assert master["trip_id"].is_monotonic_increasing, "master phai sap theo trip_id truoc khi lay mau"
    groups = master.groupby(by, sort=True).indices                # {khoa tang: vi tri dong}
    counts = pd.Series({k: len(v) for k, v in groups.items()})
    alloc = allocate(counts, n)
    rng = np.random.default_rng(seed)
    pick = [rng.choice(groups[k], size=int(alloc[k]), replace=False) for k in sorted(groups)]
    idx = np.sort(np.concatenate(pick))
    return master.iloc[idx].reset_index(drop=True)


def sample_check(master: pd.DataFrame, sample: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """So ty trong tung nhom trong mau voi tong the (diem phan tram)."""
    p = master.groupby(by).size().rename("population")
    s = sample.groupby(by).size().rename("sample")
    t = pd.concat([p, s], axis=1).fillna(0).astype(int).reset_index()
    t["population_pct"] = (100 * t["population"] / len(master)).round(4)
    t["sample_pct"] = (100 * t["sample"] / len(sample)).round(4)
    t["diff_pp"] = (t["sample_pct"] - t["population_pct"]).round(4)
    return t


def coord_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Theo lat cat: so dong, so toa do khac nhau, ty trong 2 toa do dong nhat (M2 / M3 can de chon tham so)."""
    rows = []
    for name, g in [("ALL", df), *df.groupby("time_slice")]:
        vc = g.groupby(FEATURES).size().sort_values(ascending=False)
        rows.append({"time_slice": name, "rows": len(g), "unique_coords": len(vc),
                     "top2_share_pct": round(100 * float(vc.head(2).sum()) / len(g), 2),
                     "median_rows_per_coord": float(vc.median())})
    return pd.DataFrame(rows)


# =============================================================================
# M1-08  PHAT HANH + KIEM TRA
# =============================================================================

def release_names(version: str) -> dict[str, str]:
    return {"master": f"master_pickups_{version}.parquet",
            "sample": f"model_input_sample_{version}.parquet",
            "manifest": f"model_input_sample_{version}_manifest.json",
            "master_manifest": f"master_pickups_{version}_manifest.json"}


def _slice_counts(df: pd.DataFrame) -> dict[str, int]:
    return {k: int(v) for k, v in df["time_slice"].value_counts().sort_index().items()}


def release(master: pd.DataFrame, sample: pd.DataFrame, log: pd.DataFrame, raw_manifest: dict[str, Any],
            processed_dir: str | Path, manifests_dir: str | Path, version: str, seed: int, crs: str,
            start: str, end: str, sample_target: int) -> dict[str, Any]:
    """Ghi master + mau + 2 manifest. Bao FileExistsError neu phien ban nay da duoc ghi (khong ghi de)."""
    processed_dir, manifests_dir = Path(processed_dir), Path(manifests_dir)
    names = release_names(version)
    targets = [processed_dir / names["master"], processed_dir / names["sample"],
               manifests_dir / names["manifest"], manifests_dir / names["master_manifest"]]
    exist = [str(p) for p in targets if p.exists()]
    if exist:
        raise FileExistsError(f"Phien ban {version} da duoc phat hanh, khong ghi de: {exist}. "
                              "Muon doi du lieu thi tang release.version trong config.")
    processed_dir.mkdir(parents=True, exist_ok=True); manifests_dir.mkdir(parents=True, exist_ok=True)

    def write(df: pd.DataFrame, path: Path) -> None:
        tmp = path.with_suffix(".tmp")
        df.to_parquet(tmp, index=False)
        tmp.rename(path)

    write(master, targets[0]); write(sample, targets[1])
    drops = log[log["action"] == "drop"]
    common = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "created_by": "M1",
        "source": PORTAL_URL,
        "query_where": where_clause(start, end),
        "date_window": [start, end],
        "raw_file": raw_manifest.get("file"), "raw_sha256": raw_manifest.get("sha256"),
        "crs": crs, "features": FEATURES, "seed": seed,
        "rows_raw": int(raw_manifest["rows_raw"]),
        "rows_after_cleaning": int(len(master)),
        "rows_dropped_by_rule": {r.rule_id: int(r.rows_matched) for r in drops.itertuples()},
        "columns": list(master.columns),
        "notes": ["Toa do la tam census tract / community area, khong phai GPS.",
                  "Thoi gian lam tron 15 phut.",
                  "Mo hinh chi dung [x_m, y_m]; cot thoi gian chi de loc lat cat."],
    }
    m_master = {"sample_id": f"master_{version}", "file": names["master"], **common,
                "rows_in_sample": int(len(master)), "rows_by_time_slice": _slice_counts(master),
                "unique_pickup_coords": int(master[FEATURES].drop_duplicates().shape[0]),
                "sha256": sha256(targets[0])}
    m_sample = {"sample_id": f"sample_{version}", "file": names["sample"], **common,
                "sampling": {"method": "phan tang theo ty le, so du lon nhat", "strata": STRATA,
                             "target_size": int(sample_target), "from": names["master"],
                             "master_sha256": m_master["sha256"]},
                "rows_in_sample": int(len(sample)), "rows_by_time_slice": _slice_counts(sample),
                "unique_pickup_coords": int(sample[FEATURES].drop_duplicates().shape[0]),
                "sha256": sha256(targets[1])}
    targets[2].write_text(json.dumps(m_sample, indent=2, ensure_ascii=False), encoding="utf-8")
    targets[3].write_text(json.dumps(m_master, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"sample": m_sample, "master": m_master}


def validate_release(data_path: str | Path, manifest_path: str | Path, slices: dict[str, Any],
                     master_path: str | Path | None = None, crs: str = "EPSG:26916",
                     bbox: dict[str, float] | None = None) -> pd.DataFrame:
    """Doc LAI file tu dia va kiem tra tung dieu kien nghiem thu. Tra ve bang (check, ok, detail)."""
    df = pd.read_parquet(data_path)
    man = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    out: list[dict[str, Any]] = []

    def chk(name: str, ok: Any, detail: Any = "") -> None:
        out.append({"check": name, "ok": bool(ok), "detail": str(detail)})

    need = COLUMNS
    chk("du cot bat buoc, dung thu tu", list(df.columns[:len(need)]) == need, f"{df.shape[1]} cot")
    chk("sha256 khop manifest", sha256(data_path) == man["sha256"], man["sha256"][:16] + "...")
    chk("so dong khop manifest", len(df) == man["rows_in_sample"], f"{len(df):,}")
    chk("trip_id khong rong, duy nhat", df["trip_id"].notna().all() and df["trip_id"].is_unique)
    chk("sap tang dan theo trip_id", df["trip_id"].is_monotonic_increasing)
    req = [c for c in need if c != "pickup_community_area" and c not in ("trip_seconds", "trip_miles")]
    nulls = df[req].isna().sum()
    chk("cot bat buoc khong co gia tri rong", int(nulls.sum()) == 0, dict(nulls[nulls > 0]))
    kinds = {"x_m": "float64", "y_m": "float64", "pickup_lat": "float64", "pickup_lon": "float64",
             "pickup_hour": "int8", "weekday": "int8", "is_weekend": "bool", "is_weekday": "bool"}
    bad = {c: str(df[c].dtype) for c, t in kinds.items() if str(df[c].dtype) != t}
    chk("kieu du lieu dung", not bad and str(df["trip_start_timestamp"].dtype).startswith("datetime64"), bad)
    chk("x_m, y_m huu han", np.isfinite(df[FEATURES].to_numpy()).all())
    x, y = project_coordinates(df["pickup_lon"], df["pickup_lat"], crs)
    err = float(np.max(np.hypot(x - df["x_m"], y - df["y_m"]))) if len(df) else 0.0
    chk("x_m, y_m dung bang phep chieu tu lat/lon", err < 1e-6, f"lech lon nhat {err:.2e} m")
    if bbox:
        inb = df["pickup_lat"].between(bbox["lat_min"], bbox["lat_max"]) & df["pickup_lon"].between(bbox["lon_min"], bbox["lon_max"])
        chk("moi diem nam trong khung Chicago", inb.all(), f"{int((~inb).sum())} diem ngoai")
    lo, hi = pd.Timestamp(man["date_window"][0]), pd.Timestamp(man["date_window"][1]) + pd.Timedelta(days=1)
    ts = df["trip_start_timestamp"]
    chk("thoi gian nam trong cua so", ((ts >= lo) & (ts < hi)).all(), f"{ts.min()} .. {ts.max()}")
    chk("pickup_hour 0-23, weekday 0-6", df["pickup_hour"].between(0, 23).all() and df["weekday"].between(0, 6).all())
    chk("gio / thu khop timestamp", (df["pickup_hour"] == ts.dt.hour).all() and (df["weekday"] == ts.dt.dayofweek).all())
    chk("is_weekend khop weekday", (df["is_weekend"] == df["weekday"].isin([5, 6])).all()
        and (df["is_weekday"] == ~df["is_weekend"]).all())
    chk("time_slice khop config", (df["time_slice"] == assign_time_slice(df["weekday"], df["pickup_hour"], slices)).all())
    chk("daypart dung dinh nghia", (df["daypart"] == daypart(df["pickup_hour"])).all())
    chk("so dong theo lat cat khop manifest", _slice_counts(df) == man["rows_by_time_slice"], _slice_counts(df))
    flags = [c for c in df.columns if c.startswith("flag_")]
    chk("cot co la bool, khong rong", all(str(df[c].dtype) == "bool" for c in flags), flags)
    chk("dac trung chi gom x_m, y_m", man["features"] == FEATURES, man["features"])
    if master_path is not None:
        ms = pd.read_parquet(master_path, columns=["trip_id", *STRATA, "x_m", "y_m"])
        chk("moi trip_id cua mau deu co trong master", df["trip_id"].isin(ms["trip_id"]).all())
        chk("master khop sha256 ghi trong manifest mau", sha256(master_path) == man["sampling"]["master_sha256"])
        if len(df) < len(ms):
            sc = sample_check(ms, df, STRATA)
            d = (sc["sample"] - sc["population"] * len(df) / len(ms)).abs().max()
            chk("moi tang thu x gio lech khong qua 1 dong so voi ty le", d < 1, f"lech lon nhat {d:.2f} dong")
    return pd.DataFrame(out)


# =============================================================================
# GHI BAO CAO
# =============================================================================

def feature_dictionary_md(flag_rules: list[dict[str, str]]) -> str:
    rows = ["# Từ điển đặc trưng của file giao cho M2, M3\n",
            "Ma trận đặc trưng của cả ba mô hình **chỉ gồm `x_m`, `y_m`**. Các cột thời gian dùng để lọc lát cắt "
            "trước khi phân cụm, không đưa vào khoảng cách.\n",
            "| Cột | Kiểu | Đơn vị | Vai trò | Mô tả |", "|---|---|---|---|---|"]
    rows += [f"| `{c}` | {t} | {u} | {r} | {d} |" for c, t, u, r, d in FEATURE_DICT]
    rows += [f"| `{r['id']}` | bool | - | co chat luong | {r['condition']} |" for r in flag_rules]
    return "\n".join(rows) + "\n"


def crs_validation_md(v: dict[str, Any]) -> str:
    a = v["area_of_use"]
    return "\n".join([
        "# Kiểm tra hệ toạ độ (M1-06)\n",
        f"- Hệ chiếu: **{v['crs']}** ({v['crs_name']}), đơn vị trục: {v['unit']}.",
        f"- Vùng áp dụng của hệ chiếu: kinh độ {a['west']} đến {a['east']}, vĩ độ {a['south']} đến {a['north']} ({a['name']}).",
        f"- Mọi điểm nằm trong vùng áp dụng: **{'có' if v['all_points_in_area_of_use'] else 'KHÔNG'}** "
        f"({v['unique_points']} toạ độ khác nhau).",
        f"- Phạm vi sau khi chiếu: x từ {v['x_min_m']:.0f} đến {v['x_max_m']:.0f} m, "
        f"y từ {v['y_min_m']:.0f} đến {v['y_max_m']:.0f} m "
        f"(rộng {v['extent_x_km']} km, dài {v['extent_y_km']} km).",
        f"- Chiếu ngược về lat/lon: lệch lớn nhất **{v['roundtrip_max_error_m']:.2e} m**.",
        f"- Khoảng cách Euclid trên x/y so với khoảng cách trắc địa, {v['pairs_checked']} cặp điểm ngẫu nhiên: "
        f"lệch tương đối lớn nhất **{v['distance_max_rel_error_pct']}%**, trung vị {v['distance_median_rel_error_pct']}%, "
        f"lệch tuyệt đối lớn nhất {v['distance_max_abs_error_m']} m.\n",
        "Kết luận dùng cho mô hình: khoảng cách Euclid trên `[x_m, y_m]` là khoảng cách mét; "
        "`eps` của DBSCAN và các ngưỡng khoảng cách khác đặt trực tiếp bằng mét. "
        "Không tính Euclid trên độ lat/lon.\n",
    ])


def write_reports(out_dir: str | Path, log: pd.DataFrame, rules: dict[str, Any], master: pd.DataFrame,
                  sample: pd.DataFrame, crs_info: dict[str, Any], qa: pd.DataFrame | None = None) -> dict[str, Path]:
    """Ghi cac file bao cao tien xu ly (nho, commit duoc) vao out_dir. Tra ve {ten: duong dan}."""
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    p = {k: out_dir / v for k, v in {
        "cleaning_log": "cleaning_log.csv", "speed_sensitivity": "speed_sensitivity.csv",
        "crs_validation": "crs_validation.md", "feature_dictionary": "feature_dictionary.md",
        "sample_vs_master_by_slice": "sample_vs_master_by_time_slice.csv",
        "sample_vs_master_by_strata": "sample_vs_master_by_weekday_hour.csv",
        "coords_master": "coords_by_time_slice_master.csv", "coords_sample": "coords_by_time_slice_sample.csv",
    }.items()}
    log.to_csv(p["cleaning_log"], index=False)
    speed_sensitivity(master, rules).to_csv(p["speed_sensitivity"], index=False)
    p["crs_validation"].write_text(crs_validation_md(crs_info), encoding="utf-8")
    p["feature_dictionary"].write_text(feature_dictionary_md(rules["flag"]), encoding="utf-8")
    sample_check(master, sample, ["time_slice"]).to_csv(p["sample_vs_master_by_slice"], index=False)
    sample_check(master, sample, STRATA).to_csv(p["sample_vs_master_by_strata"], index=False)
    coord_summary(master).to_csv(p["coords_master"], index=False)
    coord_summary(sample).to_csv(p["coords_sample"], index=False)
    if qa is not None:
        p["qa_checks"] = out_dir / "qa_checks.csv"
        qa.to_csv(p["qa_checks"], index=False)
    return p
