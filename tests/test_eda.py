"""Kiem thu src/data/eda.py bang du lieu GIA (khong can file tho, khong goi mang).

Chay:  python -m tests.test_eda            (tu goc repo)
       python -m tests.test_eda <thu_muc>  (giu lai bang va hinh trong <thu_muc> de xem)
Du lieu gia co trip_id tien to TEST_, chi de kiem tra code; KHONG dua so nao vao bao cao.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import load_config
from src.data import eda as A
from src.data import extract as E

START, END = "2023-04-17", "2023-05-14"
N = 40_000


def make_raw(n: int = N, seed: int = 0) -> pd.DataFrame:
    """Bang tho gia: moi cot la chuoi nhu file tho that. Co cai san vai loi biet truoc so luong."""
    rng = np.random.default_rng(seed)
    days = pd.date_range(START, END)
    day_w = np.where(days.dayofweek >= 5, 0.7, 1.0)
    day_w[-1] = 0.35                                            # ngay cuoi thap bat thuong (co y)
    d = rng.choice(len(days), n, p=day_w / day_w.sum())
    hour_w = np.array([2, 1, 1, 1, 1, 2, 4, 7, 8, 8, 8, 9, 9, 9, 9, 10, 11, 12, 11, 9, 7, 6, 5, 3], float)
    h = rng.choice(24, n, p=hour_w / hour_w.sum())
    start = days[d] + pd.to_timedelta(h, unit="h") + pd.to_timedelta(rng.choice([0, 15, 30, 45], n), unit="m")
    secs = np.round(rng.lognormal(6.6, 0.8, n)).astype(int)
    miles = np.round(rng.lognormal(1.0, 1.0, n), 2)

    k = 300                                                     # 300 toa do, 2 toa do dau chiem ~23%
    lat = np.round(rng.uniform(41.66, 42.02, k), 6); lon = np.round(rng.uniform(-87.90, -87.55, k), 6)
    lat[:2], lon[:2] = [41.980264, 41.979071], [-87.913625, -87.903040]
    w = 1 / np.arange(1, k + 1) ** 1.1; w[:2] = [0.17 * w[2:].sum() / 0.77, 0.06 * w[2:].sum() / 0.77]
    pu = rng.choice(k, n, p=w / w.sum()); do = rng.choice(k, n, p=w[::-1] / w.sum())

    df = pd.DataFrame({
        "trip_id": [f"TEST_{i:06d}" for i in range(n)],
        "trip_start_timestamp": start.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "trip_end_timestamp": (start + pd.to_timedelta(secs, unit="s")).strftime("%Y-%m-%dT%H:%M:%S.000"),
        "trip_seconds": secs.astype(str), "trip_miles": miles.astype(str),
        "pickup_census_tract": None, "dropoff_census_tract": None,
        "pickup_community_area": (pu % 77 + 1).astype(str), "dropoff_community_area": (do % 77 + 1).astype(str),
        "fare": np.round(3.25 + 2.5 * miles, 2).astype(str), "tips": "0", "trip_total": "10", "company": "Test Co",
        "pickup_centroid_latitude": lat[pu].astype(str), "pickup_centroid_longitude": lon[pu].astype(str),
        "dropoff_centroid_latitude": lat[do].astype(str), "dropoff_centroid_longitude": lon[do].astype(str),
    })[E.COLUMNS].astype("object")
    df.loc[:1399, ["pickup_centroid_latitude", "pickup_centroid_longitude"]] = None     # 1400 dong thieu toa do don
    df.loc[1400:1404, "pickup_centroid_latitude"] = "45.0"                               # 5 dong ngoai khung
    df.loc[2000:2099, "trip_seconds"] = "0"                                              # 100 dong thoi luong 0
    df.loc[3000:3049, "trip_miles"] = "0"                                                # 50 dong quang duong 0
    df.loc[4000:4009, ["trip_seconds", "trip_miles"]] = ["60", "5"]                      # 10 dong 300 mph
    df.loc[5000:5019, "pickup_community_area"] = None                                    # 20 dong co toa do, thieu ma khu
    return df


def test_all(keep_dir: str | None = None) -> int:
    passed = 0

    def ok(cond, msg):
        nonlocal passed
        assert cond, msg
        passed += 1
        print("PASS", msg)

    cfg = load_config()
    raw = make_raw()
    df = A.add_time_parts(E.parse_types(raw), cfg["time_slices"])

    # 1. dac trung thoi gian
    ok(len(df) == N, "add_time_parts khong lam mat dong")
    mon8 = df[(df.weekday == 0) & (df.pickup_hour == 8)]
    sat8 = df[(df.weekday == 5) & (df.pickup_hour == 8)]
    tue12 = df[(df.weekday == 1) & (df.pickup_hour == 12)]
    ok((mon8.time_slice == "WEEKDAY_AM").all() and (sat8.time_slice == "WEEKEND").all()
       and (tue12.time_slice == "OTHER").all(), "time_slice: T2 8h = AM, T7 = WEEKEND, T3 12h = OTHER")
    ok(pd.Timestamp("2023-04-17").dayofweek == 0 and df.weekday.min() == 0, "weekday 0 = Thu 2")
    sl = A.counts_by_slice(df)
    ok(sl.trips.sum() == N and abs(sl.pct.sum() - 100) < 0.05, "cac lat cat cong lai du 100%")

    # 2. chat luong: dung cac loi da cai
    q = A.quality_table(df, START, END).set_index("rule")
    ok(q.loc["thieu toa do don", "n_rows"] == 1400, "dem dung 1400 dong thieu toa do don")
    ok(q.loc["toa do don ngoai khung Chicago", "n_rows"] == 5, "dem dung 5 dong ngoai khung")
    ok(q.loc["trip_seconds = 0", "n_rows"] == 100 and q.loc["trip_miles = 0", "n_rows"] == 50, "dem dung gia tri 0")
    ok(q.loc[f"toc do > {A.SPEED_MAX_MPH} mph", "n_rows"] >= 10, "bat duoc 10 dong 300 mph")
    ok(q.loc["co toa do don nhung thieu ma khu (community area)", "n_rows"] == 20, "20 dong thieu ma khu")
    ok(q.loc["trip_id trung (dong lap lai)", "n_rows"] == 0 and q.loc["thoi diem don ngoai cua so truy van", "n_rows"] == 0,
       "khong co trung, khong co dong ngoai cua so")
    dup = pd.concat([df, df.iloc[:7]])
    ok(A.quality_table(dup, START, END).set_index("rule").loc["trip_id trung (dong lap lai)", "n_rows"] == 7,
       "them 7 dong lap -> dem dung 7")

    # 3. thieu, thong ke
    miss = A.missing_table(raw).set_index("column")
    ok(miss.loc["pickup_centroid_latitude", "n_missing"] == 1400 and miss.loc["pickup_census_tract", "missing_pct"] == 100,
       "missing_table tinh tren file tho")
    ok(len(miss) == 17, "missing_table co du 17 cot")
    st = A.numeric_stats(df).set_index("variable")
    s = df.trip_seconds
    ok(abs(st.loc["trip_seconds", "median"] - s.median()) < 1e-6
       and abs(st.loc["trip_seconds", "iqr"] - (s.quantile(.75) - s.quantile(.25))) < 1e-6
       and abs(st.loc["trip_seconds", "p95"] - s.quantile(.95)) < 1e-6, "median / IQR / p95 khop pandas")
    ok(abs(st.loc["trip_seconds", "zero_pct"] - 100 * 100 / N) < 1e-3, "zero_pct = 100 / N")
    ok(df.loc[df.trip_seconds == 0, "speed_mph"].isna().all(), "thoi luong 0 -> toc do NaN, khong phai vo cuc")

    # 4. thoi gian
    bd = A.counts_by_date(df)
    ok(len(bd) == 28 and bd.trips.sum() == N, "28 ngay, tong = N")
    an = A.daily_anomalies(bd)
    ok(str(an.loc[an.flag, "date"].max()) == END and an.loc[an.date.astype(str) == END, "deviation_pct"].iloc[0] < -15,
       "ngay cuoi (co y cho thap) bi danh dau")
    ok(A.missing_dates(df, START, END) == [] and
       A.missing_dates(df[df.date.astype(str) != "2023-05-01"], START, END) == ["2023-05-01"], "phat hien ngay bi thieu")
    hw = A.hour_weekday_matrix(df)
    ok(hw.shape == (7, 24) and abs(float((hw * 4).to_numpy().sum()) - N) < 30, "ma tran 7 x 24, x 4 ngay = N")
    bh = A.counts_by_hour(df)
    ok(bh.trips.sum() == N and set(bh.day_type) == {"ngay_thuong", "cuoi_tuan"}, "theo gio: tong = N, du 2 loai ngay")
    ok(A.counts_by_weekday(df).n_days.tolist() == [4] * 7, "moi thu co 4 ngay")

    # 5. toa do
    cc = A.coord_counts(df)
    c = A.coord_concentration(cc)
    ok(c["trips_with_coords"] == N - 1400 and cc.trips.is_monotonic_decreasing, "toa do: bo dong thieu, sap giam dan")
    ok(abs(cc.cum_share_pct.iloc[-1] - 100) < 1e-6 and c["unique_coords"] == len(cc), "ty trong cong don = 100%")
    ok(15 < c["top2_share_pct"] < 30 and c["top1_share_pct"] < c["top2_share_pct"] < c["top5_share_pct"],
       "top 2 toa do chiem ty trong lon nhu da cai")
    by = A.coords_by_group(df, "time_slice")
    ok(by.trips_with_coords.sum() == N - 1400 and (by.unique_coords <= c["unique_coords"]).all(),
       "toa do theo lat cat: tong khop, khong vuot tong")
    ok(len(A.coords_by_group(df.assign(week_start=A.week_start(df)), "week_start")) == 4, "4 tuan")

    # 6. ghi file
    with tempfile.TemporaryDirectory() as td:
        out = Path(keep_dir) if keep_dir else Path(td)
        paths = A.write_tables(df, raw, out / "metrics", 12_345_678, START, END)
        summ = pd.read_csv(paths["eda_summary"])
        get = lambda m: summ.loc[summ.metric == m, "value"].iloc[0]
        ok(int(float(get("rows"))) == N and float(get("file_size_mb")) == 12.35 and int(float(get("days_present"))) == 28,
           "eda_summary.csv: rows, dung luong, so ngay")
        ok(summ.metric.is_unique and len(paths) == 13 and all(p.exists() for p in paths.values()),
           "13 file bang, ten chi so khong trung")
        md = A.write_quality_report(df, raw, out / "data_quality_report.md", START, END, "Nguon: TEST").read_text("utf-8")
        ok("1,400" not in md and "| thieu toa do don | 1400 | 3.5 | loai |" in md and "14/05" not in md and END in md,
           "data_quality_report.md co bang kiem tra va ngay bat thuong")
        figs = A.write_figures(df, out / "figures", "Nguon: du lieu GIA de kiem thu", cfg["time_slices"])
        ok(len(figs) == 10 and all(p.stat().st_size > 20_000 for p in figs.values()), "ve du 10 hinh PNG")
        # bang rong / thieu du lieu khong lam sap ham ve
        tiny = df[df.weekday < 5].head(200)
        A.write_figures(tiny, out / "figures_tiny", "TEST", cfg["time_slices"])
        ok(True, "ve duoc khi khong co ngay cuoi tuan")

    print(f"\n{passed} PASS, 0 FAIL")
    return passed


if __name__ == "__main__":
    test_all(sys.argv[1] if len(sys.argv) > 1 else None)
