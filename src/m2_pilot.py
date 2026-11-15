"""Mau pilot TAM cua M2 (Chicago Taxi Trips) de chay thu K-Means/DBSCAN khi chua co du lieu cua M1.

KHONG thay the du lieu chinh thuc cua M1 va KHONG dung cho ket qua cuoi.
Ten file rieng (pilot_m2_v0) de khong lan voi data/processed/model_input.parquet.

Cong du lieu thanh pho tra 403 tu may o Viet Nam (15/11/2026) -> chay notebook
notebooks/m2_pilot_tam.ipynb tren Colab roi tai file ve.

Cac buoc: kiem tra cot trong metadata -> dem so dong tren server -> tai theo trang
-> doi chieu so dong -> lam sach toi thieu -> gan time_slice -> chieu sang EPSG:26916
-> luu parquet + manifest (co sha256).
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

DATASET_ID = "wrvz-psew"
BASE = "https://data.cityofchicago.org"
RESOURCE_URL = f"{BASE}/resource/{DATASET_ID}.json"
METADATA_URL = f"{BASE}/api/views/{DATASET_ID}.json"
PORTAL_URL = f"{BASE}/Transportation/Taxi-Trips-2013-2023-/{DATASET_ID}"

COLUMNS = [
    "trip_id", "trip_start_timestamp", "trip_seconds", "trip_miles",
    "pickup_community_area", "pickup_centroid_latitude", "pickup_centroid_longitude",
]
# Khung toa do tho cua Chicago (BA Spec muc 2.2.1)
BBOX = {"lat_min": 41.64, "lat_max": 42.05, "lon_min": -87.94, "lon_max": -87.52}
PAGE_SIZE = 50000

Fetcher = Callable[[str, dict[str, str]], Any]   # (url, params) -> JSON da parse


def _default_fetch(url: str, params: dict[str, str]) -> Any:
    import requests
    for attempt in range(4):
        r = requests.get(url, params=params, timeout=120,
                         headers={"User-Agent": "KPDL-student-project/0.1"})
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 500, 502, 503, 504) and attempt < 3:
            time.sleep(5 * (attempt + 1))
            continue
        raise RuntimeError(f"HTTP {r.status_code} khi goi {url}: {r.text[:200]}")
    raise RuntimeError("Het so lan thu lai")


def where_clause(start: str, end: str) -> str:
    """start/end dang YYYY-MM-DD, lay tron ngay: [start 00:00, end+1 00:00)."""
    s = pd.Timestamp(start)
    e = pd.Timestamp(end) + pd.Timedelta(days=1)
    return (f"trip_start_timestamp >= '{s:%Y-%m-%dT%H:%M:%S}' "
            f"AND trip_start_timestamp < '{e:%Y-%m-%dT%H:%M:%S}'")


def check_columns(fetch: Fetcher = _default_fetch) -> list[str]:
    """Doi chieu COLUMNS voi metadata that cua cong du lieu. Bao loi neu thieu cot."""
    meta = fetch(METADATA_URL, {})
    names = [c.get("fieldName") for c in meta.get("columns", [])]
    missing = [c for c in COLUMNS if c not in names]
    if missing:
        raise ValueError(f"Metadata khong co cot: {missing}. Cot hien co: {names}")
    return names


def server_count(where: str, fetch: Fetcher = _default_fetch) -> int:
    res = fetch(RESOURCE_URL, {"$select": "count(*) AS n", "$where": where})
    return int(res[0]["n"])


def download(where: str, fetch: Fetcher = _default_fetch, page_size: int = PAGE_SIZE,
             progress: bool = True) -> pd.DataFrame:
    """Tai theo trang, sap xep theo trip_id de phan trang on dinh.

    Chi dung khi gap trang rong (khong dung khi trang < page_size), vi server co the
    tu gioi han so dong moi trang thap hon so xin. Ton them 1 request nhung khong tai thieu.
    """
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = fetch(RESOURCE_URL, {
            "$select": ",".join(COLUMNS), "$where": where, "$order": "trip_id",
            "$limit": str(page_size), "$offset": str(offset),
        })
        if not page:
            break
        rows.extend(page)
        if progress:
            print(f"  da tai {len(rows):,} dong")
        offset += len(page)
    df = pd.DataFrame(rows)
    for c in COLUMNS:          # cot null toan bo co the khong xuat hien trong JSON
        if c not in df.columns:
            df[c] = None
    return df[COLUMNS]


def assign_time_slice(weekday: pd.Series, hour: pd.Series, slices: dict[str, Any]) -> pd.Series:
    """Gan WEEKDAY_AM / WEEKDAY_PM / WEEKEND theo config; khong thuoc lat nao -> OTHER."""
    out = pd.Series("OTHER", index=weekday.index, dtype="object")
    for name, sc in slices.items():
        hours = range(24) if sc["hours"] == "all" else sc["hours"]
        out[weekday.isin(sc["weekdays"]) & hour.isin(list(hours))] = name
    return out


def clean(raw: pd.DataFrame, slices: dict[str, Any], crs: str = "EPSG:26916"
          ) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Lam sach toi thieu + dac trung + chieu toa do. Tra ve (df, nhat ky tung buoc)."""
    from pyproj import Transformer

    steps: list[dict[str, Any]] = []
    df = raw.copy()

    def log(rule: str, before: int) -> None:
        steps.append({"rule": rule, "before": before, "after": len(df), "removed": before - len(df)})

    df["trip_start_timestamp"] = pd.to_datetime(df["trip_start_timestamp"], errors="coerce")
    for c in ["pickup_centroid_latitude", "pickup_centroid_longitude", "trip_seconds", "trip_miles"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    n = len(df); df = df[df["trip_id"].notna()]; log("trip_id null", n)
    n = len(df); df = df.drop_duplicates("trip_id"); log("trip_id trung", n)
    n = len(df); df = df[df["trip_start_timestamp"].notna()]; log("timestamp null / khong parse duoc", n)
    n = len(df)
    df = df[df["pickup_centroid_latitude"].notna() & df["pickup_centroid_longitude"].notna()]
    log("thieu toa do pickup", n)
    n = len(df)
    lat, lon = df["pickup_centroid_latitude"], df["pickup_centroid_longitude"]
    df = df[lat.between(BBOX["lat_min"], BBOX["lat_max"]) & lon.between(BBOX["lon_min"], BBOX["lon_max"])]
    log("ngoai khung toa do Chicago", n)

    ts = df["trip_start_timestamp"]
    df = df.assign(
        pickup_hour=ts.dt.hour.astype("int8"),
        weekday=ts.dt.dayofweek.astype("int8"),
    )
    df["is_weekend"] = df["weekday"].isin([5, 6])
    df["time_slice"] = assign_time_slice(df["weekday"], df["pickup_hour"], slices)

    tf = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    x, y = tf.transform(df["pickup_centroid_longitude"].to_numpy(), df["pickup_centroid_latitude"].to_numpy())
    df["x_m"], df["y_m"] = np.asarray(x, dtype="float64"), np.asarray(y, dtype="float64")

    # Co chat luong (khong loai, chi danh dau) theo BA Spec muc 2.2.1
    secs, miles = df["trip_seconds"], df["trip_miles"]
    speed = np.where(secs > 0, miles / (secs / 3600.0), np.nan)
    df["flag_zero_duration"] = ~(secs > 0)
    df["flag_zero_distance"] = ~(miles > 0)
    df["flag_speed_gt_80"] = speed > 80

    df = df.rename(columns={"pickup_centroid_latitude": "pickup_lat",
                            "pickup_centroid_longitude": "pickup_lon"})
    cols = ["trip_id", "trip_start_timestamp", "x_m", "y_m", "pickup_lat", "pickup_lon",
            "pickup_hour", "weekday", "is_weekend", "time_slice", "pickup_community_area",
            "trip_seconds", "trip_miles", "flag_zero_duration", "flag_zero_distance", "flag_speed_gt_80"]
    df = df[cols].sort_values("trip_id").reset_index(drop=True)
    df["trip_id"] = df["trip_id"].astype(str)
    df["pickup_community_area"] = pd.to_numeric(df["pickup_community_area"], errors="coerce").astype("Int16")
    return df, steps


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_pilot(start: str, end: str, slices: dict[str, Any], out_parquet: str | Path,
                out_manifest: str | Path, seed: int = 42, crs: str = "EPSG:26916",
                fetch: Fetcher = _default_fetch, page_size: int = PAGE_SIZE) -> dict[str, Any]:
    """Chay tron goi, tra ve manifest. Bao loi neu so dong tai ve khac so dong tren server."""
    where = where_clause(start, end)
    check_columns(fetch)
    expected = server_count(where, fetch)
    print(f"Server bao {expected:,} chuyen trong {start} .. {end}")
    raw = download(where, fetch, page_size=page_size)
    if len(raw) != expected:
        raise RuntimeError(f"Tai thieu/du: server {expected}, tai ve {len(raw)}")
    df, steps = clean(raw, slices, crs)

    out_parquet = Path(out_parquet); out_parquet.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_parquet, index=False)
    manifest = {
        "sample_id": out_parquet.stem,
        "purpose": "MAU TAM cua M2 de chay thu code; khong phai du lieu chinh thuc cua M1",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "created_by": "M2",
        "source": PORTAL_URL,
        "endpoint": RESOURCE_URL,
        "query_select": ",".join(COLUMNS),
        "query_where": where,
        "date_window": [start, end],
        "crs": crs,
        "seed": seed,
        "rows_server_count": expected,
        "rows_raw": len(raw),
        "rows_after_cleaning": len(df),
        "rows_in_sample": len(df),
        "rows_by_time_slice": {k: int(v) for k, v in df["time_slice"].value_counts().sort_index().items()},
        "cleaning_steps": steps,
        "unique_pickup_coords": int(df[["pickup_lat", "pickup_lon"]].drop_duplicates().shape[0]),
        "sha256": sha256(out_parquet),
    }
    Path(out_manifest).write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def subsample(df: pd.DataFrame, n: int, seed: int = 42) -> pd.DataFrame:
    """Lay ngau nhien n dong (co seed), giu thu tu trip_id. n >= len(df) thi tra ve ca bang."""
    if n >= len(df):
        return df
    return df.sample(n=n, random_state=seed).sort_values("trip_id").reset_index(drop=True)
