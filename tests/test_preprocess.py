"""Kiem thu src/data/preprocess.py bang du lieu GIA (khong can file tho, khong goi mang).

Chay:  python -m tests.test_preprocess      (tu goc repo)
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import load_config
from src.data import extract as E
from src.data import preprocess as P
from tests.test_eda import END, N, START, make_raw


def expect(exc, fn):
    try:
        fn()
    except exc as e:
        return e
    raise AssertionError(f"khong bao {exc.__name__}")


def test_all() -> int:
    passed = 0

    def ok(cond, msg):
        nonlocal passed
        assert cond, msg
        passed += 1
        print("PASS", msg)

    cfg = load_config()
    slices, crs = cfg["time_slices"], cfg["project"]["crs"]
    rules = P.load_rules()
    raw = make_raw()                      # 1400 thieu toa do, 5 ngoai khung, 100 thoi luong 0, 50 quang duong 0, ...
    extra = raw.iloc[[10_000, 10_001, 10_002]].copy()                      # 3 dong lap trip_id
    bad_ts = raw.iloc[[20_000]].copy(); bad_ts["trip_id"] = "TEST_BADTS"; bad_ts["trip_start_timestamp"] = "khong phai ngay"
    out_win = raw.iloc[[20_001]].copy(); out_win["trip_id"] = "TEST_OUTWIN"; out_win["trip_start_timestamp"] = "2023-05-15T00:00:00.000"
    no_id = raw.iloc[[20_002]].copy(); no_id["trip_id"] = None
    end_lt = raw.index[30_000]; raw.loc[end_lt, "trip_end_timestamp"] = "2023-04-01T00:00:00.000"
    raw2 = pd.concat([raw, extra, bad_ts, out_win, no_id], ignore_index=True)
    typed = E.parse_types(raw2)

    # 1. lam sach: tung quy tac dem dung, khong mat dong am tham
    master, log = P.build_master(typed, rules, slices, START, END, crs)
    L = log.set_index("rule_id")
    ok(L.loc["trip_id_null", "rows_matched"] == 1 and L.loc["trip_id_duplicate", "rows_matched"] == 3, "loai 1 trip_id rong, 3 trip_id lap")
    ok(L.loc["start_time_invalid", "rows_matched"] == 1 and L.loc["start_time_outside_window", "rows_matched"] == 1,
       "loai 1 timestamp hong, 1 ngoai cua so (00:00 ngay sau ngay cuoi)")
    ok(L.loc["pickup_coord_missing", "rows_matched"] == 1400 and L.loc["pickup_outside_chicago_bbox", "rows_matched"] == 5
       and L.loc["pickup_coord_out_of_range", "rows_matched"] == 0, "loai 1400 thieu toa do, 5 ngoai khung")
    d = log[log.action == "drop"]
    ok(d.rows_matched.sum() == len(raw2) - len(master) == 1411 and len(master) == N - 1405,
       "tong so dong bi loai = tong cac quy tac (khong mat dong am tham)")
    ok((d.rows_before.iloc[1:].to_numpy() == d.rows_after.iloc[:-1].to_numpy()).all() and d.rows_before.iloc[0] == len(raw2),
       "nhat ky noi tiep: sau quy tac truoc = truoc quy tac sau")
    ok(list(log.rule_id) == [r["id"] for r in rules["drop"] + rules["flag"]] and log.reason.str.len().min() > 5,
       "nhat ky co du 12 quy tac, dung thu tu, co ly do")
    ok(L.loc["flag_zero_duration", "rows_matched"] == master.flag_zero_duration.sum() == 100, "co thoi luong 0: 100 dong, khong loai")
    ok(master.flag_zero_distance.sum() == 50 and master.flag_speed_gt_80.sum() >= 10, "co quang duong 0: 50; co toc do > 80: du 10 dong cai")
    ok(master.flag_end_before_start.sum() == 1 and master.flag_missing_area.sum() == 20, "co tra-truoc-don: 1; co thieu ma khu: 20")
    ok(not master.loc[master.flag_zero_duration, "flag_speed_gt_80"].any(), "thoi luong 0 khong bi tinh la toc do vo cuc")
    sens = P.speed_sensitivity(master, rules).set_index("threshold_mph")
    ok(list(sens.index) == [70, 80, 90] and sens.rows.is_monotonic_decreasing and sens.loc[80, "rows"] == master.flag_speed_gt_80.sum(),
       "do nhay toc do 70/80/90: giam dan, nguong 80 khop cot co")
    bad = dict(rules, drop=rules["drop"][:-1])
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "r.yaml"; f.write_text(__import__("yaml").safe_dump(bad), encoding="utf-8")
        ok("pickup_outside_chicago_bbox" in str(expect(ValueError, lambda: P.load_rules(f))), "yaml thieu quy tac so voi code -> bao loi")

    # 2. master: schema
    ok(list(master.columns) == P.COLUMNS + [r["id"] for r in rules["flag"]], "master du cot, dung thu tu")
    ok(master.trip_id.is_unique and master.trip_id.is_monotonic_increasing and master[P.FEATURES].notna().all().all(),
       "master: trip_id duy nhat, tang dan; x_m, y_m khong rong")
    ok(str(master.pickup_hour.dtype) == "int8" and str(master.weekday.dtype) == "int8" and str(master.x_m.dtype) == "float64"
       and str(master.pickup_community_area.dtype) == "Int16", "kieu du lieu dung dinh dang da thong nhat")

    # 3. chieu toa do
    x, y = P.project_coordinates([-87.6298], [41.8781])                     # trung tam Chicago
    ok(440_000 < x[0] < 455_000 and 4_630_000 < y[0] < 4_645_000, "trung tam Chicago -> x ~ 448 km, y ~ 4.637 km (UTM 16N)")
    x2, y2 = P.project_coordinates([-87.6298, -87.6298], [41.8781, 41.8871])  # 0,009 do vi do ~ 1 km
    ok(abs(np.hypot(x2[1] - x2[0], y2[1] - y2[0]) - 1000) < 5, "0,009 do vi do ~ 1.000 m tren x/y")
    v = P.validate_crs(master, crs)
    ok(v["all_points_in_area_of_use"] and v["unit"] == "metre", "CRS: don vi met, moi diem trong vung ap dung")
    ok(v["roundtrip_max_error_m"] < 0.01 and v["distance_max_rel_error_pct"] < 0.1, "chieu nguoc lech < 1 cm; khoang cach lech < 0,1%")

    # 4. dac trung thoi gian: cac ca bien cua spec
    def feat(ts: str) -> pd.Series:
        return P.add_features(pd.DataFrame({"trip_start_timestamp": [pd.Timestamp(ts)]}), slices).iloc[0]
    f = {k: feat(v) for k, v in {
        "fri0659": "2023-04-21 06:59", "fri0700": "2023-04-21 07:00", "fri0959": "2023-04-21 09:59", "fri1000": "2023-04-21 10:00",
        "fri1559": "2023-04-21 15:59", "fri1600": "2023-04-21 16:00", "fri1859": "2023-04-21 18:59", "fri1900": "2023-04-21 19:00",
        "fri2359": "2023-04-21 23:59", "sat0000": "2023-04-22 00:00", "sat0800": "2023-04-22 08:00", "sun2345": "2023-04-23 23:45",
        "mon0000": "2023-04-24 00:00"}.items()}
    ok(f["fri0659"].time_slice == "OTHER" and f["fri0700"].time_slice == "WEEKDAY_AM"
       and f["fri0959"].time_slice == "WEEKDAY_AM" and f["fri1000"].time_slice == "OTHER", "bien sang: 06:59 OTHER | 07:00, 09:59 AM | 10:00 OTHER")
    ok(f["fri1559"].time_slice == "OTHER" and f["fri1600"].time_slice == "WEEKDAY_PM"
       and f["fri1859"].time_slice == "WEEKDAY_PM" and f["fri1900"].time_slice == "OTHER", "bien chieu: 15:59 OTHER | 16:00, 18:59 PM | 19:00 OTHER")
    ok(f["fri2359"].time_slice == "OTHER" and not f["fri2359"].is_weekend and f["sat0000"].time_slice == "WEEKEND"
       and f["sat0800"].time_slice == "WEEKEND" and f["sun2345"].time_slice == "WEEKEND" and f["mon0000"].time_slice == "OTHER",
       "bien tuan: thu Sau 23:59 chua la cuoi tuan; thu Bay 00:00 la WEEKEND; thu Hai 00:00 het WEEKEND")
    ok([f[k].daypart for k in ["fri0659", "fri0700", "fri0959", "fri1000", "fri1559", "fri1600", "fri1859", "fri1900"]]
       == ["NIGHT", "AM_PEAK", "AM_PEAK", "MIDDAY", "MIDDAY", "PM_PEAK", "PM_PEAK", "NIGHT"], "daypart dung o 8 moc bien")
    ok(f["fri0700"].weekday == 4 and f["sat0000"].weekday == 5 and f["sat0800"].daypart == "AM_PEAK" and f["sat0000"].is_weekday == False,  # noqa: E712
       "weekday: thu Sau = 4, thu Bay = 5; daypart khong phu thuoc thu")

    # 5. lay mau phan tang
    n = 5000
    s1 = P.stratified_sample(master, n, seed=42)
    s2 = P.stratified_sample(master, n, seed=42)
    s3 = P.stratified_sample(master, n, seed=7)
    ok(len(s1) == n and s1.trip_id.is_unique and s1.trip_id.is_monotonic_increasing and s1.trip_id.isin(master.trip_id).all(),
       "mau dung n dong, khong lap, sap theo trip_id, nam trong master")
    ok(s1.trip_id.equals(s2.trip_id) and not s1.trip_id.equals(s3.trip_id), "cung seed -> cung mau; khac seed -> khac mau")
    sc = P.sample_check(master, s1, P.STRATA)
    ok(len(sc) == master.groupby(P.STRATA).ngroups and sc["sample"].min() >= 0
       and (sc["sample"] - sc["population"] * n / len(master)).abs().max() < 1, "moi tang lech khong qua 1 dong so voi ty le")
    ok(P.sample_check(master, s1, ["time_slice"]).diff_pp.abs().max() < 0.5, "ty trong lat cat cua mau lech tong the < 0,5 diem % (mau thu nho)")
    a = P.allocate(pd.Series([1, 1, 1, 7]), 5)
    ok(a.sum() == 5 and a.iloc[3] >= 3 and P.allocate(pd.Series([3, 4]), 100).tolist() == [3, 4], "allocate: tong dung n; n > tong -> lay het")
    ok(len(P.stratified_sample(master, 10**9)) == len(master), "n lon hon master -> tra ve ca master")
    shuffled = master.sample(frac=1, random_state=0)
    expect(AssertionError, lambda: P.stratified_sample(shuffled, n))
    ok(True, "master chua sap theo trip_id -> tu choi lay mau (bao ve tinh tai lap)")

    # 6. phat hanh + kiem tra
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        raw_man = {"file": "raw_TEST.parquet", "sha256": "abc", "rows_raw": len(raw2)}
        kw = dict(processed_dir=td / "processed", manifests_dir=td / "manifests", version="v1", seed=42, crs=crs,
                  start=START, end=END, sample_target=n)
        m = P.release(master, s1, log, raw_man, **kw)
        nm = P.release_names("v1")
        fs, fm, fman = td / "processed" / nm["sample"], td / "processed" / nm["master"], td / "manifests" / nm["manifest"]
        man = json.loads(fman.read_text(encoding="utf-8"))
        ok(man["sample_id"] == "sample_v1" and man["rows_raw"] == len(raw2) and man["rows_after_cleaning"] == len(master)
           and man["rows_in_sample"] == n and man["seed"] == 42 and man["crs"] == crs and man["date_window"] == [START, END],
           "manifest co du truong da thong nhat voi M2")
        ok(sum(man["rows_by_time_slice"].values()) == n and set(man["rows_by_time_slice"]) == {"WEEKDAY_AM", "WEEKDAY_PM", "WEEKEND", "OTHER"},
           "manifest: so dong theo 4 lat cat cong lai = n")
        ok(man["sha256"] == P.sha256(fs) and man["sampling"]["master_sha256"] == P.sha256(fm) == m["master"]["sha256"]
           and man["rows_dropped_by_rule"]["pickup_coord_missing"] == 1400, "manifest: sha256 khop file; ghi so dong loai theo quy tac")
        back = pd.read_parquet(fs)
        ok(back.trip_id.equals(s1.trip_id) and np.array_equal(back[P.FEATURES].to_numpy(), s1[P.FEATURES].to_numpy())
           and str(back.pickup_hour.dtype) == "int8", "doc lai parquet: giong het bang trong bo nho, giu kieu")
        part = back[back.time_slice == "WEEKDAY_AM"]
        X = part[["x_m", "y_m"]].to_numpy(dtype="float64")
        ok(X.shape == (man["rows_by_time_slice"]["WEEKDAY_AM"], 2) and np.isfinite(X).all(), "cach doc cua M2/M3 (loc lat cat -> X) chay duoc")
        expect(FileExistsError, lambda: P.release(master, s1, log, raw_man, **kw))
        ok(P.sha256(fs) == man["sha256"], "phat hanh lai cung phien ban -> FileExistsError, file cu nguyen ven")
        P.release(master, s3, log, raw_man, **{**kw, "version": "v2", "seed": 7})
        ok((td / "processed" / "model_input_sample_v2.parquet").exists() and fs.exists(), "phien ban v2 nam canh v1")

        qa = P.validate_release(fs, fman, slices, master_path=fm, crs=crs, bbox=rules["bbox"])
        ok(qa.ok.all() and len(qa) >= 20, f"validate_release: {len(qa)} kiem tra deu dat tren file vua phat hanh")
        broken = back.copy(); broken.loc[0, "x_m"] += 50.0; broken.loc[1, "time_slice"] = "WEEKEND" if broken.loc[1, "time_slice"] != "WEEKEND" else "OTHER"
        fb = td / "broken.parquet"; broken.to_parquet(fb, index=False)
        qb = P.validate_release(fb, fman, slices, crs=crs).set_index("check").ok
        ok(not qb["sha256 khop manifest"] and not qb["x_m, y_m dung bang phep chieu tu lat/lon"] and not qb["time_slice khop config"],
           "file bi sua (x_m lech 50 m, sai 1 nhan lat cat) -> validate_release bat duoc ca ba loi")

        rep = P.write_reports(td / "rep", log, rules, master, s1, v, qa)
        ok(len(rep) == 9 and all(p.stat().st_size > 50 for p in rep.values()), "ghi du 9 file bao cao")
        fd = rep["feature_dictionary"].read_text(encoding="utf-8")
        ok(all(f"`{c}`" in fd for c in master.columns) and "chỉ gồm `x_m`, `y_m`" in fd, "feature dictionary co du moi cot cua file giao")
        ok("EPSG:26916" in rep["crs_validation"].read_text(encoding="utf-8"), "crs_validation.md ghi he chieu")

    print(f"\n{passed} PASS, 0 FAIL")
    return passed


if __name__ == "__main__":
    test_all()
