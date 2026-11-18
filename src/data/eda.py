"""EDA cho du lieu tho Chicago Taxi Trips (M1-03 dinh luong, M1-04 truc quan).

Dau vao la bang da qua extract.parse_types (chua loc dong nao). Cac ham o day KHONG sua
du lieu va KHONG loai dong: chi dem, thong ke va ve. Viec lam sach nam o notebook 02.

Ba nhom ham:
    1. Bang so lieu : add_time_parts, overview, missing_table, numeric_stats, quality_table,
                      counts_*, daily_anomalies, coord_counts, coord_concentration, coords_by_group
    2. Hinh ve      : fig_* (moi ham luu 1 file PNG, tra ve duong dan)
    3. Ghi ket qua  : build_summary, write_tables, write_quality_report

Luu y ve du lieu (phai nho khi doc so):
    - Toa do la TAM census tract / community area, khong phai GPS -> rat it toa do khac nhau.
    - Thoi gian duoc lam tron 15 phut.
    - So luot don (pickup) la NHU CAU taxi, khong phai muc do un tac.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.m2_pilot import BBOX, assign_time_slice

LAT, LON = "pickup_centroid_latitude", "pickup_centroid_longitude"
DLAT, DLON = "dropoff_centroid_latitude", "dropoff_centroid_longitude"
WEEKDAY_VI = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"]
SPEED_MAX_MPH = 80            # nguong co toc do (BA Spec muc 2.2.1)
ANOMALY_DEV = 0.15            # ngay lech > 15% so voi trung vi cung thu -> danh dau

# Mau (bang mau da kiem tra mu mau; 1 mau cho 1 chuoi, cam cho chuoi thu 2)
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
SEQ = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]       # tang dan theo do lon
LANDMARKS = {"O'Hare": (41.98, -87.90), "Midway": (41.785, -87.75), "Loop": (41.88, -87.63)}


# =============================================================================
# 1. BANG SO LIEU
# =============================================================================

def add_time_parts(df: pd.DataFrame, slices: dict[str, Any]) -> pd.DataFrame:
    """Them date, pickup_hour, weekday (0 = Thu 2), is_weekend, time_slice, speed_mph. Khong loai dong."""
    out = df.copy()
    ts = out["trip_start_timestamp"]
    out["date"] = ts.dt.date
    out["pickup_hour"] = ts.dt.hour
    out["weekday"] = ts.dt.dayofweek
    out["is_weekend"] = out["weekday"].isin([5, 6])
    out["time_slice"] = assign_time_slice(out["weekday"], out["pickup_hour"], slices)
    out.loc[ts.isna(), "time_slice"] = None
    secs, miles = out["trip_seconds"], out["trip_miles"]
    out["speed_mph"] = np.where(secs > 0, miles / (secs / 3600.0), np.nan)
    return out


def pct(n: float, total: float) -> float:
    return round(100.0 * n / total, 4) if total else float("nan")


def missing_table(raw: pd.DataFrame) -> pd.DataFrame:
    """So dong thieu va ty le thieu cua TUNG cot (tinh tren file tho)."""
    n = raw.isna().sum()
    return pd.DataFrame({"column": n.index, "n_missing": n.to_numpy(),
                         "missing_pct": (100 * n / len(raw)).round(4).to_numpy()})


def numeric_stats(df: pd.DataFrame, cols: list[str] | None = None) -> pd.DataFrame:
    """min/mean/median/std/Q1/Q3/IQR/p90/p95/p99/max + so gia tri thieu, bang 0, am."""
    cols = cols or ["trip_seconds", "trip_miles", "fare", "tips", "trip_total", "speed_mph"]
    rows = []
    for c in cols:
        s = pd.to_numeric(df[c], errors="coerce")
        v = s.dropna()
        q = v.quantile([0.25, 0.5, 0.75, 0.9, 0.95, 0.99]) if len(v) else pd.Series([np.nan] * 6)
        q1, med, q3, p90, p95, p99 = q.to_numpy()
        rows.append({
            "variable": c, "n": len(v), "n_missing": int(s.isna().sum()),
            "zero_pct": pct((v == 0).sum(), len(s)), "negative_pct": pct((v < 0).sum(), len(s)),
            "min": v.min(), "mean": v.mean(), "median": med, "std": v.std(),
            "q1": q1, "q3": q3, "iqr": q3 - q1, "p90": p90, "p95": p95, "p99": p99, "max": v.max(),
        })
    return pd.DataFrame(rows).round(3)


def in_bbox(lat: pd.Series, lon: pd.Series) -> pd.Series:
    return lat.between(BBOX["lat_min"], BBOX["lat_max"]) & lon.between(BBOX["lon_min"], BBOX["lon_max"])


def quality_table(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """Dem cac truong hop co van de. 'action' la du kien xu ly o notebook 02 (loai / danh dau / giu)."""
    n = len(df)
    ts, te = df["trip_start_timestamp"], df["trip_end_timestamp"]
    lo, hi = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    has_xy = df[LAT].notna() & df[LON].notna()
    secs, miles = df["trip_seconds"], df["trip_miles"]
    speed = df["speed_mph"] if "speed_mph" in df else pd.Series(np.nan, index=df.index)
    rules = [
        ("trip_id thieu", df["trip_id"].isna(), "loai"),
        ("trip_id trung (dong lap lai)", df["trip_id"].duplicated() & df["trip_id"].notna(), "loai"),
        ("thoi diem don thieu / khong doc duoc", ts.isna(), "loai"),
        ("thoi diem don ngoai cua so truy van", ts.notna() & ~((ts >= lo) & (ts < hi)), "loai"),
        ("thieu toa do don", ~has_xy, "loai"),
        ("toa do don ngoai khung Chicago", has_xy & ~in_bbox(df[LAT], df[LON]), "loai"),
        ("co toa do don nhung thieu ma khu (community area)", has_xy & df["pickup_community_area"].isna(), "giu"),
        ("thieu toa do tra", df[DLAT].isna() | df[DLON].isna(), "giu"),
        ("thoi diem tra truoc thoi diem don", te.notna() & ts.notna() & (te < ts), "danh dau"),
        ("trip_seconds thieu", secs.isna(), "danh dau"),
        ("trip_seconds = 0", secs == 0, "danh dau"),
        ("trip_seconds < 0", secs < 0, "danh dau"),
        ("trip_miles thieu", miles.isna(), "danh dau"),
        ("trip_miles = 0", miles == 0, "danh dau"),
        ("trip_miles < 0", miles < 0, "danh dau"),
        (f"toc do > {SPEED_MAX_MPH} mph", speed > SPEED_MAX_MPH, "danh dau"),
        ("fare thieu", df["fare"].isna(), "giu"),
        ("fare < 0", df["fare"] < 0, "danh dau"),
    ]
    return pd.DataFrame([{"rule": r, "n_rows": int(m.sum()), "pct": pct(m.sum(), n), "action": a}
                         for r, m, a in rules])


def counts_by_date(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("date").size().rename("trips").reset_index()
    g["weekday"] = pd.to_datetime(g["date"]).dt.dayofweek
    g["weekday_name"] = g["weekday"].map(dict(enumerate(WEEKDAY_VI)))
    return g


def daily_anomalies(by_date: pd.DataFrame, dev: float = ANOMALY_DEV) -> pd.DataFrame:
    """So moi ngay voi TRUNG VI cua cac ngay cung thu. Lech qua `dev` -> flag = True."""
    out = by_date.copy()
    out["median_same_weekday"] = out.groupby("weekday")["trips"].transform("median")
    out["deviation_pct"] = (100 * (out["trips"] / out["median_same_weekday"] - 1)).round(1)
    out["flag"] = out["deviation_pct"].abs() > 100 * dev
    return out


def missing_dates(df: pd.DataFrame, start: str, end: str) -> list[str]:
    have = set(pd.to_datetime(pd.Series(list(df["date"].dropna().unique()))).dt.strftime("%Y-%m-%d"))
    return [d.strftime("%Y-%m-%d") for d in pd.date_range(start, end) if d.strftime("%Y-%m-%d") not in have]


def counts_by_hour(df: pd.DataFrame) -> pd.DataFrame:
    """So chuyen theo gio, tach ngay thuong / cuoi tuan; kem trung binh moi ngay."""
    n_days = df.groupby("is_weekend")["date"].nunique()
    g = df.groupby(["is_weekend", "pickup_hour"]).size().rename("trips").reset_index()
    g["trips_per_day"] = (g["trips"] / g["is_weekend"].map(n_days)).round(1)
    g["day_type"] = np.where(g["is_weekend"], "cuoi_tuan", "ngay_thuong")
    return g[["day_type", "pickup_hour", "trips", "trips_per_day"]]


def counts_by_weekday(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("weekday").agg(trips=("trip_id", "size"), n_days=("date", "nunique")).reset_index()
    g["trips_per_day"] = (g["trips"] / g["n_days"]).round(1)
    g["weekday_name"] = g["weekday"].map(dict(enumerate(WEEKDAY_VI)))
    return g


def hour_weekday_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Hang = thu (0..6), cot = gio (0..23), gia tri = so chuyen TRUNG BINH moi ngay cua thu do."""
    cnt = df.groupby(["weekday", "pickup_hour"]).size().unstack(fill_value=0)
    cnt = cnt.reindex(index=range(7), columns=range(24), fill_value=0)
    n_days = df.groupby("weekday")["date"].nunique().reindex(range(7)).replace(0, np.nan)
    return cnt.div(n_days, axis=0).round(1)


def counts_by_slice(df: pd.DataFrame) -> pd.DataFrame:
    g = df["time_slice"].value_counts(dropna=False).rename("trips").rename_axis("time_slice").reset_index()
    g["pct"] = (100 * g["trips"] / len(df)).round(2)
    return g.sort_values("time_slice").reset_index(drop=True)


def counts_by_area(df: pd.DataFrame, col: str = "pickup_community_area") -> pd.DataFrame:
    g = df[col].astype("Int64").value_counts(dropna=False).rename("trips").rename_axis(col).reset_index()
    g["pct"] = (100 * g["trips"] / len(df)).round(2)
    g["cum_pct"] = g["pct"].cumsum().round(2)
    return g


def coord_counts(df: pd.DataFrame, lat: str = LAT, lon: str = LON) -> pd.DataFrame:
    """Moi toa do khac nhau: so chuyen, ty trong, ty trong cong don (sap giam dan)."""
    d = df[[lat, lon]].dropna()
    g = d.groupby([lat, lon]).size().rename("trips").reset_index()
    g = g.sort_values(["trips", lat, lon], ascending=[False, True, True]).reset_index(drop=True)
    g["share_pct"] = (100 * g["trips"] / g["trips"].sum()).round(3)
    g["cum_share_pct"] = (100 * g["trips"].cumsum() / g["trips"].sum()).round(3)
    g.insert(0, "rank", np.arange(1, len(g) + 1))
    return g.rename(columns={lat: "lat", lon: "lon"})


def coord_concentration(cc: pd.DataFrame) -> dict[str, float]:
    """Muc do don ve it toa do: ty trong top 1/2/5/10, trung vi so chuyen moi toa do, so toa do thua."""
    total = cc["trips"].sum()
    top = lambda k: round(100 * cc["trips"].head(k).sum() / total, 2) if total else float("nan")
    return {
        "unique_coords": int(len(cc)), "trips_with_coords": int(total),
        "top1_share_pct": top(1), "top2_share_pct": top(2), "top5_share_pct": top(5), "top10_share_pct": top(10),
        "coords_for_50pct": int((cc["cum_share_pct"] < 50).sum() + 1) if len(cc) else 0,
        "coords_for_80pct": int((cc["cum_share_pct"] < 80).sum() + 1) if len(cc) else 0,
        "median_trips_per_coord": float(cc["trips"].median()) if len(cc) else float("nan"),
        "coords_lt_10_trips": int((cc["trips"] < 10).sum()),
    }


def coords_by_group(df: pd.DataFrame, by: str) -> pd.DataFrame:
    """So chuyen co toa do va so toa do khac nhau theo nhom (time_slice, tuan, ...)."""
    d = df.dropna(subset=[LAT, LON])
    rows = []
    for key, g in d.groupby(by, dropna=False):
        cc = coord_counts(g)
        c = coord_concentration(cc)
        rows.append({by: key, "trips_with_coords": c["trips_with_coords"], "unique_coords": c["unique_coords"],
                     "top2_share_pct": c["top2_share_pct"], "top5_share_pct": c["top5_share_pct"],
                     "median_trips_per_coord": c["median_trips_per_coord"],
                     "coords_lt_10_trips": c["coords_lt_10_trips"]})
    return pd.DataFrame(rows)


def week_start(df: pd.DataFrame) -> pd.Series:
    """Ngay thu Hai cua tuan chua chuyen di (de dem theo tuan)."""
    ts = df["trip_start_timestamp"]
    return (ts.dt.normalize() - pd.to_timedelta(ts.dt.dayofweek, unit="D")).dt.date


def overview(df: pd.DataFrame, raw: pd.DataFrame, file_size_bytes: int | None, start: str, end: str
             ) -> list[tuple[str, str, Any]]:
    """Cac chi so quy mo / thoi gian / khong gian dang (nhom, chi so, gia tri)."""
    ts = df["trip_start_timestamp"]
    n = len(df)
    has_xy = df[LAT].notna() & df[LON].notna()
    by_date = counts_by_date(df)
    n_days_expected = len(pd.date_range(start, end))
    rows: list[tuple[str, str, Any]] = [
        ("quy_mo", "rows", n),
        ("quy_mo", "columns", raw.shape[1]),
        ("quy_mo", "file_size_mb", round(file_size_bytes / 1e6, 2) if file_size_bytes else None),
        ("quy_mo", "unique_trip_id", int(raw["trip_id"].nunique())),
        ("quy_mo", "duplicate_rows", int(raw["trip_id"].duplicated().sum())),
        ("quy_mo", "duplicate_pct", pct(raw["trip_id"].duplicated().sum(), n)),
        ("thoi_gian", "timestamp_min", str(ts.min())),
        ("thoi_gian", "timestamp_max", str(ts.max())),
        ("thoi_gian", "days_expected", n_days_expected),
        ("thoi_gian", "days_present", int(by_date["date"].nunique())),
        ("thoi_gian", "days_missing_pct", pct(len(missing_dates(df, start, end)), n_days_expected)),
        ("thoi_gian", "trips_per_day_mean", round(float(by_date["trips"].mean()), 1)),
        ("thoi_gian", "trips_per_day_median", float(by_date["trips"].median())),
        ("thoi_gian", "trips_per_day_min", int(by_date["trips"].min())),
        ("thoi_gian", "trips_per_day_max", int(by_date["trips"].max())),
        ("thoi_gian", "minute_values", " ".join(str(int(m)) for m in sorted(ts.dt.minute.dropna().unique()))),
        ("khong_gian", "pickup_coords_missing_pct", pct((~has_xy).sum(), n)),
        ("khong_gian", "pickup_lat_min", df[LAT].min()), ("khong_gian", "pickup_lat_max", df[LAT].max()),
        ("khong_gian", "pickup_lon_min", df[LON].min()), ("khong_gian", "pickup_lon_max", df[LON].max()),
        ("khong_gian", "pickup_outside_bbox_pct", pct((has_xy & ~in_bbox(df[LAT], df[LON])).sum(), n)),
        ("khong_gian", "pickup_community_areas", int(df["pickup_community_area"].nunique())),
        ("khong_gian", "pickup_census_tracts", int(df["pickup_census_tract"].nunique())),
        ("khong_gian", "pickup_census_tract_missing_pct", pct(df["pickup_census_tract"].isna().sum(), n)),
    ]
    return rows


def build_summary(df: pd.DataFrame, raw: pd.DataFrame, file_size_bytes: int | None, start: str, end: str
                  ) -> pd.DataFrame:
    """eda_summary.csv: bang dai (group, metric, value) gom moi chi so chinh de bao cao lay so."""
    rows = overview(df, raw, file_size_bytes, start, end)
    rows += [("toa_do_don", k, v) for k, v in coord_concentration(coord_counts(df)).items()]
    rows += [("lat_cat", f"{r.time_slice}_trips", r.trips) for r in counts_by_slice(df).itertuples()]
    rows += [("lat_cat", f"{r.time_slice}_pct", r.pct) for r in counts_by_slice(df).itertuples()]
    for r in numeric_stats(df).itertuples():
        for k in ["median", "mean", "std", "iqr", "p90", "p95", "max", "zero_pct", "negative_pct"]:
            rows.append(("chuyen_di", f"{r.variable}_{k}", getattr(r, k)))
    rows += [("chat_luong", r.rule, r.pct) for r in quality_table(df, start, end).itertuples()]
    return pd.DataFrame(rows, columns=["group", "metric", "value"])


def write_tables(df: pd.DataFrame, raw: pd.DataFrame, out_dir: str | Path, file_size_bytes: int | None,
                 start: str, end: str) -> dict[str, Path]:
    """Ghi eda_summary.csv vao out_dir va cac bang chi tiet vao out_dir/eda/. Tra ve {ten: duong dan}."""
    out_dir = Path(out_dir); sub = out_dir / "eda"; sub.mkdir(parents=True, exist_ok=True)
    by_date = counts_by_date(df)
    wk = df.assign(week_start=week_start(df))
    tables = {
        "missing_by_column": missing_table(raw),
        "numeric_stats": numeric_stats(df),
        "quality_checks": quality_table(df, start, end),
        "trips_by_date": daily_anomalies(by_date),
        "trips_by_hour": counts_by_hour(df),
        "trips_by_weekday": counts_by_weekday(df),
        "trips_hour_x_weekday": hour_weekday_matrix(df).rename_axis("weekday").reset_index(),
        "trips_by_time_slice": counts_by_slice(df),
        "trips_by_pickup_area": counts_by_area(df),
        "pickup_coords": coord_counts(df),
        "pickup_coords_by_time_slice": coords_by_group(df, "time_slice"),
        "pickup_coords_by_week": coords_by_group(wk, "week_start"),
    }
    paths = {"eda_summary": out_dir / "eda_summary.csv"}
    build_summary(df, raw, file_size_bytes, start, end).to_csv(paths["eda_summary"], index=False)
    for name, t in tables.items():
        paths[name] = sub / f"{name}.csv"
        t.to_csv(paths[name], index=False)
    return paths


def write_quality_report(df: pd.DataFrame, raw: pd.DataFrame, out_md: str | Path, start: str, end: str,
                         source_note: str) -> Path:
    """data_quality_report.md: chi gom SO LIEU. Phan nhan xet do M1 viet trong notebook / bao cao."""
    q = quality_table(df, start, end)
    miss = missing_table(raw)
    anom = daily_anomalies(counts_by_date(df))
    anom = anom[anom["flag"]]
    n = len(df)

    def md(t: pd.DataFrame) -> str:
        head = "| " + " | ".join(t.columns) + " |\n|" + "---|" * len(t.columns) + "\n"
        return head + "\n".join("| " + " | ".join(str(v) for v in row) + " |" for row in t.to_numpy()) + "\n"

    drop = q[q["action"] == "loai"]
    text = [
        "# Báo cáo chất lượng dữ liệu thô (M1-03)\n",
        f"{source_note}\n",
        f"Số dòng thô: **{n:,}**. File này do `src/data/eda.py` sinh ra từ file thô, chỉ gồm số liệu; "
        "không sửa tay. Chạy lại notebook 01 để cập nhật.\n",
        "## 1. Tỷ lệ thiếu theo cột\n", md(miss),
        "## 2. Các kiểm tra chất lượng\n",
        "Cột `action` là cách xử lý **dự kiến** ở bước làm sạch (notebook 02): `loai` = bỏ dòng, "
        "`danh dau` = giữ dòng và gắn cờ, `giu` = giữ nguyên. Một dòng có thể dính nhiều quy tắc, "
        "nên không cộng dồn các tỷ lệ.\n", md(q),
        f"Các quy tắc `loai` cộng lại nhiều nhất là {int(drop['n_rows'].sum()):,} dòng "
        f"({pct(drop['n_rows'].sum(), n):.2f}%); số chính xác sau khi loại nằm trong cleaning log của notebook 02.\n",
        "## 3. Ngày có số chuyến lệch so với các ngày cùng thứ\n",
        f"Ngưỡng: lệch quá {int(100 * ANOMALY_DEV)}% so với trung vị của các ngày cùng thứ trong cửa sổ.\n",
        md(anom[["date", "weekday_name", "trips", "median_same_weekday", "deviation_pct"]]) if len(anom)
        else "Không có ngày nào vượt ngưỡng.\n",
        "## 4. Giới hạn của dữ liệu cần nêu khi diễn giải\n",
        "- Toạ độ là tâm census tract hoặc community area, không phải GPS.\n"
        "- Thời gian được làm tròn về bội số 15 phút.\n"
        "- Mã census tract bị ẩn ở một phần chuyến đi; khi đó toạ độ là tâm community area.\n"
        "- Số lượt đón phản ánh nhu cầu taxi, không đo mức độ ùn tắc.\n",
    ]
    out_md = Path(out_md); out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(text), encoding="utf-8")
    return out_md


# =============================================================================
# 2. HINH VE
# =============================================================================

def _plt():
    import matplotlib
    import matplotlib.pyplot as plt
    matplotlib.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "text.color": INK,
        "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK2, "ytick.labelcolor": INK2,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
        "axes.spines.top": False, "axes.spines.right": False, "font.size": 10,
        "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
    })
    return plt


def _cmap():
    from matplotlib.colors import LinearSegmentedColormap
    return LinearSegmentedColormap.from_list("kpdl_blue", SEQ)


def _save(fig, out_png: str | Path, note: str) -> Path:
    """Ghi chu nguon + co mau o chan hinh, luu PNG 200 dpi."""
    plt = _plt()
    fig.text(0.01, -0.02, note, ha="left", va="top", fontsize=8, color=MUTED)   # nam duoi khung, khong de nhan truc
    out_png = Path(out_png); out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out_png


def _n(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _hist(values: pd.Series, out_png, note, title, xlabel, unit, bins: int = 60) -> Path:
    """Histogram cat o p99 (duoi dai lam mat hinh); ve duong trung vi va p95; ghi ty le bang 0."""
    plt = _plt()
    v = pd.to_numeric(values, errors="coerce").dropna()
    p50, p95, p99 = v.quantile([0.5, 0.95, 0.99]).to_numpy()
    shown = v[(v >= 0) & (v <= p99)]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.hist(shown, bins=bins, color=BLUE, edgecolor=SURFACE, linewidth=0.6)
    ax.grid(axis="x", visible=False)
    top = ax.get_ylim()[1]
    for x, lab, ha in [(p50, f"trung vị {p50:.1f} {unit}", "left"), (p95, f"p95 {p95:.1f} {unit}", "left")]:
        ax.axvline(x, color=INK2, linewidth=1, linestyle="--")
        ax.text(x, top * 0.97, " " + lab, ha=ha, va="top", fontsize=9, color=INK2)
    ax.set_title(title)
    ax.set_xlabel(f"{xlabel} (trục cắt tại p99 = {p99:.1f} {unit})")
    ax.set_ylabel("Số chuyến")
    extra = f"n = {_n(len(v))} chuyến có giá trị; {100 * (v == 0).mean():.1f}% bằng 0; lớn nhất {v.max():,.0f} {unit}."
    return _save(fig, out_png, f"{extra}\n{note}")


def fig_trip_duration(df: pd.DataFrame, out_png, note: str) -> Path:
    return _hist(df["trip_seconds"] / 60.0, out_png, note, "Phân phối thời lượng chuyến đi",
                 "Thời lượng (phút)", "phút")


def fig_trip_distance(df: pd.DataFrame, out_png, note: str) -> Path:
    return _hist(df["trip_miles"], out_png, note, "Phân phối quãng đường chuyến đi",
                 "Quãng đường (dặm)", "dặm")


def fig_boxplots(df: pd.DataFrame, out_png, note: str) -> Path:
    """Boxplot tren truc log cho 3 bien lech phai; moi bien 1 o rieng vi khac don vi."""
    plt = _plt()
    import matplotlib.ticker as mticker
    items = [("trip_seconds", "Thời lượng (giây)"), ("trip_miles", "Quãng đường (dặm)"), ("fare", "Cước (USD)")]
    fig, axes = plt.subplots(3, 1, figsize=(8, 5.2))
    for ax, (c, lab) in zip(axes, items):
        v = pd.to_numeric(df[c], errors="coerce").dropna()
        pos = v[v > 0]
        ax.boxplot(pos, vert=False, widths=0.6, whis=(5, 95), showfliers=False, patch_artist=True,
                   boxprops=dict(facecolor="#9ec5f4", edgecolor=BLUE), medianprops=dict(color=INK, linewidth=1.5),
                   whiskerprops=dict(color=BLUE), capprops=dict(color=BLUE))
        ax.set_xscale("log"); ax.set_yticks([]); ax.grid(axis="y", visible=False)
        # moc 1-2-5 viet bang so thuong (khong dung 10^3) de doc duoc gia tri tren truc log
        ax.xaxis.set_major_locator(mticker.LogLocator(base=10, subs=(1, 2, 5), numticks=15))
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.10g}".translate(str.maketrans(",.", ".,"))))   # 1.000 va 0,5 kieu Viet
        ax.xaxis.set_minor_formatter(mticker.NullFormatter())
        ax.set_xlabel(f"{lab}, thang log – n = {_n(len(pos))} giá trị > 0 "
                      f"(bỏ {_n(len(v) - len(pos))} giá trị ≤ 0)", fontsize=9)
    axes[0].set_title("Thời lượng, quãng đường và cước: hộp = Q1–Q3, vạch = trung vị, râu = p5–p95")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    return _save(fig, out_png, note)


def fig_by_hour(df: pd.DataFrame, out_png, note: str, slices: dict[str, Any] | None = None) -> Path:
    """So chuyen trung binh moi ngay theo gio, tach ngay thuong / cuoi tuan; to nen khung gio cao diem."""
    plt = _plt()
    h = counts_by_hour(df)
    fig, ax = plt.subplots(figsize=(9, 4.8))
    for name, sc in (slices or {}).items():              # khung gio cua cac lat cat ngay thuong
        if sc.get("hours") != "all":
            lo, hi = min(sc["hours"]), max(sc["hours"])
            ax.axvspan(lo - 0.5, hi + 0.5, color=GRID, alpha=0.6, zorder=0)
            ax.text((lo + hi) / 2, 1.0, name, transform=ax.get_xaxis_transform(), ha="center", va="bottom",
                    fontsize=8, color=MUTED)
    for key, lab, col, mk in [("ngay_thuong", "Ngày thường (T2–T6)", BLUE, "o"),
                              ("cuoi_tuan", "Cuối tuần (T7, CN)", ORANGE, "s")]:
        d = h[h["day_type"] == key].sort_values("pickup_hour")
        if len(d):
            ax.plot(d["pickup_hour"], d["trips_per_day"], color=col, linewidth=2, marker=mk, markersize=5, label=lab)
            last = d.iloc[-1]
            ax.text(23.4, last["trips_per_day"], lab.split(" (")[0], color=INK2, fontsize=9, va="center")
    ax.set_xlim(-0.5, 26.5); ax.set_xticks(range(24)); ax.set_ylim(bottom=0)
    ax.grid(axis="x", visible=False)
    ax.set_title("Nhu cầu đón theo giờ trong ngày", pad=16)
    ax.set_xlabel("Giờ bắt đầu chuyến (0–23)"); ax.set_ylabel("Số chuyến trung bình mỗi ngày")
    ax.legend(frameon=False, loc="upper left")
    return _save(fig, out_png, f"n = {_n(len(df))} chuyến. Vùng xám: khung giờ của các lát cắt ngày thường.\n{note}")


def fig_by_weekday(df: pd.DataFrame, out_png, note: str) -> Path:
    plt = _plt()
    w = counts_by_weekday(df).set_index("weekday").reindex(range(7))
    fig, ax = plt.subplots(figsize=(8, 4.6))
    bars = ax.bar(range(7), w["trips_per_day"].fillna(0), color=BLUE, width=0.62)
    for b, v in zip(bars, w["trips_per_day"]):
        if pd.notna(v):
            ax.text(b.get_x() + b.get_width() / 2, v, f"{v:,.0f}".replace(",", "."), ha="center", va="bottom",
                    fontsize=9, color=INK2)
    ax.set_xticks(range(7)); ax.set_xticklabels(WEEKDAY_VI); ax.grid(axis="x", visible=False)
    ax.set_title("Nhu cầu đón theo thứ trong tuần")
    ax.set_xlabel("Thứ"); ax.set_ylabel("Số chuyến trung bình mỗi ngày")
    days = ", ".join(f"{WEEKDAY_VI[i]}: {int(n)}" for i, n in w["n_days"].dropna().items())
    return _save(fig, out_png, f"n = {_n(len(df))} chuyến. Số ngày của mỗi thứ – {days}.\n{note}")


def fig_heatmap(df: pd.DataFrame, out_png, note: str) -> Path:
    plt = _plt()
    m = hour_weekday_matrix(df)
    fig, ax = plt.subplots(figsize=(10, 3.9))
    im = ax.imshow(m.to_numpy(dtype=float), aspect="auto", cmap=_cmap(), vmin=0)
    ax.set_xticks(range(24)); ax.set_yticks(range(7)); ax.set_yticklabels(WEEKDAY_VI)
    ax.set_xticks(np.arange(-0.5, 24), minor=True); ax.set_yticks(np.arange(-0.5, 7), minor=True)
    ax.grid(False); ax.grid(which="minor", color=SURFACE, linewidth=1.5)
    ax.tick_params(which="both", length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("Nhu cầu đón theo giờ × thứ")
    ax.set_xlabel("Giờ bắt đầu chuyến (0–23)")
    cb = fig.colorbar(im, ax=ax, pad=0.015); cb.set_label("Số chuyến trung bình mỗi giờ"); cb.outline.set_visible(False)
    return _save(fig, out_png, f"n = {_n(len(df))} chuyến. Mỗi ô = trung bình các ngày cùng thứ trong cửa sổ.\n{note}")


def fig_daily(df: pd.DataFrame, out_png, note: str) -> Path:
    """So chuyen moi ngay; khoanh cac ngay lech > nguong so voi trung vi cung thu."""
    plt = _plt()
    d = daily_anomalies(counts_by_date(df))
    x = pd.to_datetime(d["date"])
    fig, ax = plt.subplots(figsize=(10, 4.4))
    ax.plot(x, d["trips"], color=BLUE, linewidth=2, marker="o", markersize=4)
    we = d["weekday"] >= 5
    ax.scatter(x[we], d.loc[we, "trips"], s=42, color=ORANGE, zorder=3, label="Thứ 7, Chủ nhật")
    fl = d[d["flag"]]
    ax.scatter(pd.to_datetime(fl["date"]), fl["trips"], s=170, facecolors="none", edgecolors=INK, linewidths=1.2,
               zorder=4, label=f"Lệch > {int(100 * ANOMALY_DEV)}% so với trung vị cùng thứ")
    for r in fl.itertuples():
        ax.annotate(f"{pd.Timestamp(r.date):%d/%m}: {r.deviation_pct:+.0f}%", (pd.Timestamp(r.date), r.trips),
                    textcoords="offset points", xytext=(0, -16), ha="center", fontsize=8, color=INK2)
    ax.set_ylim(bottom=0); ax.grid(axis="x", visible=False)
    ax.set_title("Số chuyến mỗi ngày trong cửa sổ dữ liệu")
    ax.set_xlabel("Ngày"); ax.set_ylabel("Số chuyến")
    ax.xaxis.set_major_formatter(__import__("matplotlib.dates", fromlist=["x"]).DateFormatter("%d/%m"))
    ax.legend(frameon=False, loc="lower left")
    return _save(fig, out_png, f"n = {_n(len(df))} chuyến, {d['date'].nunique()} ngày.\n{note}")


def _map_axes(ax, title: str) -> None:
    ax.set_xlim(BBOX["lon_min"] - 0.02, BBOX["lon_max"] + 0.02)
    ax.set_ylim(BBOX["lat_min"] - 0.01, BBOX["lat_max"] + 0.01)
    ax.set_aspect(1 / np.cos(np.deg2rad(41.88)))       # 1 do kinh ~ 0,74 do vi o vi do Chicago
    ax.set_title(title); ax.set_xlabel("Kinh độ (°)"); ax.set_ylabel("Vĩ độ (°)")
    for name, (la, lo) in LANDMARKS.items():
        ax.annotate(name, (lo, la), textcoords="offset points", xytext=(7, 7), fontsize=8, color=INK2)


def _bubbles(ax, cc: pd.DataFrame, norm, smax: float):
    """Moi toa do 1 cham: dien tich va mau deu theo so chuyen. Ve cham lon truoc de cham nho khong bi che."""
    cc = cc.sort_values("trips", ascending=False)
    return ax.scatter(cc["lon"], cc["lat"], s=12 + 900 * cc["trips"] / smax, c=cc["trips"], cmap=_cmap(),
                      norm=norm, edgecolors=SURFACE, linewidths=0.8, alpha=0.95)


def fig_pickup_map(df: pd.DataFrame, out_png, note: str) -> Path:
    """Ban do diem don: 1 cham = 1 TOA DO KHAC NHAU (tam vung), khong phai 1 chuyen."""
    plt = _plt()
    from matplotlib.colors import LogNorm
    cc = coord_counts(df)
    fig, ax = plt.subplots(figsize=(7.6, 8))
    if len(cc):
        sc = _bubbles(ax, cc, LogNorm(vmin=1, vmax=max(cc["trips"].max(), 2)), cc["trips"].max())
        cb = fig.colorbar(sc, ax=ax, shrink=0.7, pad=0.02); cb.set_label("Số chuyến tại toạ độ (thang log)")
        cb.outline.set_visible(False)
    _map_axes(ax, "Mật độ điểm đón theo toạ độ")
    c = coord_concentration(cc)
    extra = (f"n = {_n(c['trips_with_coords'])} chuyến có toạ độ, dồn vào {_n(c['unique_coords'])} toạ độ khác nhau "
             f"(tâm vùng, không phải GPS). Diện tích và màu chấm theo số chuyến.")
    return _save(fig, out_png, f"{extra}\n{note}")


def fig_pickup_vs_dropoff(df: pd.DataFrame, out_png, note: str) -> Path:
    """Hai ban do cung khung, cung thang mau va cung thang kich thuoc."""
    plt = _plt()
    from matplotlib.colors import LogNorm
    pu, do = coord_counts(df), coord_counts(df, DLAT, DLON)
    vmax = max(pu["trips"].max() if len(pu) else 2, do["trips"].max() if len(do) else 2, 2)
    norm = LogNorm(vmin=1, vmax=vmax)
    fig, axes = plt.subplots(1, 2, figsize=(13, 7.4), sharex=True, sharey=True)
    sc = None
    for ax, cc, t in [(axes[0], pu, "Điểm đón"), (axes[1], do, "Điểm trả")]:
        if len(cc):
            sc = _bubbles(ax, cc, norm, vmax)
        _map_axes(ax, f"{t}: {_n(int(cc['trips'].sum()))} chuyến, {_n(len(cc))} toạ độ")
    axes[1].set_ylabel("")
    if sc is not None:
        cb = fig.colorbar(sc, ax=axes, shrink=0.6, pad=0.015)
        cb.set_label("Số chuyến tại toạ độ (thang log, chung cho hai bản đồ)"); cb.outline.set_visible(False)
    return _save(fig, out_png, f"Hai bản đồ cùng khung toạ độ, cùng thang màu và thang kích thước.\n{note}")


def fig_coord_concentration(df: pd.DataFrame, out_png, note: str) -> Path:
    """Duong cong ty trong cong don: bao nhieu toa do thi gom duoc bao nhieu % so chuyen."""
    plt = _plt()
    cc = coord_counts(df)
    c = coord_concentration(cc)
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.plot(cc["rank"], cc["cum_share_pct"], color=BLUE, linewidth=2)
    for k in (2, 10):
        if len(cc) >= k:
            y = cc["cum_share_pct"].iloc[k - 1]
            ax.scatter([k], [y], s=40, color=BLUE, zorder=3, edgecolors=SURFACE, linewidths=1.5)
            ax.annotate(f"{k} toạ độ đầu: {y:.1f}%", (k, y), textcoords="offset points", xytext=(10, -4),
                        fontsize=9, color=INK2)
    ax.set_xscale("log"); ax.set_ylim(0, 102); ax.set_xlim(left=0.9)
    ax.set_title("Mức độ dồn chuyến vào ít toạ độ đón")
    ax.set_xlabel("Số toạ độ, xếp từ nhiều chuyến nhất (thang log)")
    ax.set_ylabel("Tỷ trọng cộng dồn số chuyến (%)")
    extra = (f"n = {_n(c['trips_with_coords'])} chuyến có toạ độ, {_n(c['unique_coords'])} toạ độ khác nhau; "
             f"trung vị {c['median_trips_per_coord']:.0f} chuyến mỗi toạ độ; "
             f"{c['coords_lt_10_trips']} toạ độ có dưới 10 chuyến.")
    return _save(fig, out_png, f"{extra}\n{note}")


FIGURES = [
    ("01_trip_duration_hist", fig_trip_duration),
    ("02_trip_distance_hist", fig_trip_distance),
    ("03_pickups_by_hour", fig_by_hour),
    ("04_pickups_by_weekday", fig_by_weekday),
    ("05_hour_weekday_heatmap", fig_heatmap),
    ("06_pickup_density_map", fig_pickup_map),
    ("07_pickup_vs_dropoff_map", fig_pickup_vs_dropoff),
    ("08_boxplots_log", fig_boxplots),
    ("09_trips_by_date", fig_daily),
    ("10_pickup_coord_concentration", fig_coord_concentration),
]


def write_figures(df: pd.DataFrame, out_dir: str | Path, note: str, slices: dict[str, Any] | None = None
                  ) -> dict[str, Path]:
    """Ve du 10 hinh vao out_dir (PNG). Tra ve {ten: duong dan}."""
    out_dir = Path(out_dir)
    paths = {}
    for name, fn in FIGURES:
        kw = {"slices": slices} if fn is fig_by_hour else {}
        paths[name] = fn(df, out_dir / f"{name}.png", note, **kw)
    return paths


# Bo cuc hien thi trong notebook: moi nhom 1 tieu de, cac hinh cung nhom dat canh nhau de so sanh.
# "span" = so cot hinh chiem (luoi 2 cot); "rows" = so hang hinh chiem.
GRID_LAYOUT = [
    ("Chuyến đi: thời lượng và quãng đường", [("01_trip_duration_hist", {}), ("02_trip_distance_hist", {})]),
    ("Thời gian: theo giờ và theo thứ", [("03_pickups_by_hour", {}), ("04_pickups_by_weekday", {})]),
    ("Thời gian: giờ × thứ và từng ngày", [("05_hour_weekday_heatmap", {}), ("09_trips_by_date", {})]),
    ("Không gian: toạ độ đón và mức dồn chuyến",
     [("06_pickup_density_map", {"rows": 2}), ("10_pickup_coord_concentration", {}), ("08_boxplots_log", {})]),
    ("Không gian: điểm đón so với điểm trả", [("07_pickup_vs_dropoff_map", {"span": 2})]),
]


def figure_grid_html(figs: dict[str, Path], max_width: int = 1080, layout=GRID_LAYOUT) -> str:
    """HTML xep cac hinh thanh luoi 2 cot (anh nhung base64 nen hien duoc ca tren Colab).

    Chi doi cach HIEN THI; file PNG goc van giu nguyen kich thuoc de dua vao bao cao.
    Bam vao hinh de mo ban day du o tab moi.
    """
    import base64

    out = [f'<div style="max-width:{max_width}px">']
    for title, items in layout:
        items = [(n, o) for n, o in items if n in figs]
        if not items:
            continue
        out.append(f'<div style="font:600 14px sans-serif;margin:14px 0 6px">{title}</div>')
        out.append('<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;align-items:start">')
        for name, opt in items:
            b64 = base64.b64encode(Path(figs[name]).read_bytes()).decode("ascii")
            src = f"data:image/png;base64,{b64}"
            style = f"grid-column:span {opt.get('span', 1)};grid-row:span {opt.get('rows', 1)}"
            out.append(f'<a href="{src}" target="_blank" title="{name}.png" style="{style}">'
                       f'<img src="{src}" alt="{name}" style="width:100%;display:block;'
                       f'border:1px solid {GRID};border-radius:4px"></a>')
        out.append("</div>")
    out.append("</div>")
    return "\n".join(out)
