"""Kiem thu src/data/extract.py bang server GIA (khong goi mang).

Chay:  python -m tests.test_extract      (tu goc repo)
Du lieu gia co trip_id tien to TEST_, chi ton tai trong thu muc tam.
"""
from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from src.data import extract as E
from src.m2_pilot import METADATA_URL, sha256

N = 237


def make_rows(n: int = N) -> list[dict]:
    rows = []
    t0 = datetime(2023, 4, 17)
    for i in range(n):
        ts = t0 + timedelta(minutes=15 * i)
        r = {
            "trip_id": f"TEST_{(i * 7919) % n:05d}",          # thu tu xao tron, van duy nhat
            "trip_start_timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "trip_end_timestamp": (ts + timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%S.000"),
            "trip_seconds": str(600 + i), "trip_miles": "2.5",
            "pickup_community_area": "8", "dropoff_community_area": "32",
            "fare": "12.5", "tips": "0", "trip_total": "12.5", "company": "Test Co",
            "pickup_centroid_latitude": "41.8789", "pickup_centroid_longitude": "-87.6359",
            "dropoff_centroid_latitude": "41.9", "dropoff_centroid_longitude": "-87.63",
        }
        if i % 10 == 0:                                        # thieu toa do pickup -> khoa vang trong JSON
            del r["pickup_centroid_latitude"], r["pickup_centroid_longitude"]
        rows.append(r)                                         # census tract luon vang (bi an)
    return sorted(rows, key=lambda r: r["trip_id"])


def make_meta(drop: str | None = None) -> dict:
    cols = [{"fieldName": c, "name": c.replace("_", " ").title(), "dataTypeName": "text",
             "description": f"mo ta {c}"} for c in [*E.COLUMNS, "taxi_id", "payment_type"] if c != drop]
    return {"name": "Taxi Trips TEST", "rowsUpdatedAt": 1700000000, "license": {"name": "Test"},
            "columns": cols}


class FakeServer:
    def __init__(self, rows, cap=None, count=None, fail_at_call=None, meta=None):
        self.rows, self.cap, self.count = rows, cap, count
        self.fail_at_call, self.meta = fail_at_call, meta or make_meta()
        self.page_calls = 0

    def __call__(self, url, params):
        if url == METADATA_URL:
            return self.meta
        if params.get("$select", "").startswith("count("):
            return [{"n": str(self.count if self.count is not None else len(self.rows))}]
        self.page_calls += 1
        if self.fail_at_call == self.page_calls:
            raise RuntimeError("HTTP 503 (loi co y)")
        assert params["$order"] == "trip_id"
        lim, off = int(params["$limit"]), int(params["$offset"])
        if self.cap:
            lim = min(lim, self.cap)
        return self.rows[off:off + lim]


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

    rows = make_rows()
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)

        # 1. duong chay binh thuong
        srv = FakeServer(rows)
        m = E.build_raw_extract("2023-04-17", "2023-04-23", td / "raw", td / "man", fetch=srv,
                                page_size=50, progress=False)
        out = td / "raw" / "raw_extract_20230417_20230423.parquet"
        df = pd.read_parquet(out)
        ok(srv.page_calls == 6, "237 dong, trang 50 -> 6 lan goi (lan cuoi rong)")
        ok(len(df) == N == m["rows_raw"] == m["rows_server_count"], "so dong = so server dem")
        ok(list(df.columns) == E.COLUMNS, "du 17 cot, dung thu tu")
        ok(df.trip_id.is_unique and df.trip_id.is_monotonic_increasing, "trip_id duy nhat, tang dan")
        ok(all(str(t) in ("string", "str") or "string" in str(t) for t in df.dtypes), "file tho giu dang chuoi")
        ok(df.pickup_census_tract.isna().all(), "cot vang toan bo van co mat, toan null")
        ok(df.pickup_centroid_latitude.isna().sum() == 24, "24 dong thieu toa do duoc giu lai (khong loc)")
        ok(m["sha256"] == sha256(out), "sha256 khop file")
        ok(not (td / "raw" / "_parts_raw_extract_20230417_20230423").exists(), "thu muc trang tam da don")
        ok("2023-04-17T00:00:00" in m["query_where"] and "2023-04-24T00:00:00" in m["query_where"],
           "where lay tron ngay cuoi")

        # 2. cac file M1-01
        snap = json.loads((td / "man" / "schema_snapshot.json").read_text(encoding="utf-8"))
        dd = pd.read_csv(td / "man" / "data_dictionary.csv")
        md = (td / "man" / "source_manifest.md").read_text(encoding="utf-8")
        ok(snap["n_columns"] == 19 and snap["rows_updated_at_utc"].startswith("2023-11-14"), "schema snapshot")
        ok(len(dd) == 19 and dd.used_by_m1.sum() == 17, "data dictionary: 19 cot nguon, 17 cot dung")
        ok(dd.set_index("field_name").loc["pickup_centroid_latitude", "internal_name"] == "pickup_lat",
           "mapping ten that -> ten noi bo")
        ok(not dd.set_index("field_name").loc["taxi_id", "used_by_m1"], "khong lay taxi_id")
        ok("237" in md and "15 phút" in md and m["sha256"] in md, "source_manifest.md co so dong, caveat, sha256")

        # 3. khong ghi de file tho
        expect(FileExistsError, lambda: E.build_raw_extract(
            "2023-04-17", "2023-04-23", td / "raw", td / "man", fetch=FakeServer(rows), progress=False))
        ok(True, "file tho da co -> FileExistsError, khong ghi de")

        # 4. server tu gioi han 30 dong/trang
        srv = FakeServer(rows, cap=30)
        m2 = E.build_raw_extract("2023-04-17", "2023-04-23", td / "raw2", td / "man2", fetch=srv,
                                 page_size=50, progress=False)
        ok(m2["rows_raw"] == N and srv.page_calls == 9, "server gioi han 30 dong/trang van tai du")
        ok(m2["sha256"] == m["sha256"], "cung du lieu -> cung sha256 du phan trang khac nhau")

        # 5. bi ngat giua chung roi chay lai
        srv = FakeServer(rows, fail_at_call=3)
        expect(RuntimeError, lambda: E.build_raw_extract(
            "2023-04-17", "2023-04-23", td / "raw3", td / "man3", fetch=srv, page_size=50, progress=False))
        parts = td / "raw3" / "_parts_raw_extract_20230417_20230423"
        ok(len(list(parts.glob("part_*.parquet"))) == 2 and not list(parts.glob("*.tmp")),
           "ngat o trang 3: con 2 trang hoan chinh, khong co trang do dang")
        ok(not (td / "raw3" / "raw_extract_20230417_20230423.parquet").exists(), "chua ghi file tho khi loi")
        srv = FakeServer(rows)
        m3 = E.build_raw_extract("2023-04-17", "2023-04-23", td / "raw3", td / "man3", fetch=srv,
                                 page_size=50, progress=False)
        ok(srv.page_calls == 4 and m3["rows_raw"] == N, "chay lai: tiep tuc tu trang 3 (4 lan goi), du 237 dong")
        ok(m3["sha256"] == m["sha256"], "ket qua sau khi chay lai giong het lan chay lien mach")

        # 6. trang tam cua truy van khac
        E.download_pages("where A", td / "p", fetch=FakeServer(rows), page_size=50, progress=False)
        e = expect(RuntimeError, lambda: E.download_pages(
            "where B", td / "p", fetch=FakeServer(rows), page_size=50, progress=False))
        ok("KHAC" in str(e), "thu muc trang cua truy van khac -> bao loi, khong tron")

        # 7. so dong lech
        e = expect(RuntimeError, lambda: E.build_raw_extract(
            "2023-04-17", "2023-04-23", td / "raw4", td / "man4", fetch=FakeServer(rows, count=N + 5),
            page_size=50, progress=False))
        ok("Tai thieu/du" in str(e) and not list((td / "raw4").glob("*.parquet")),
           "server dem khac so tai ve -> RuntimeError, khong ghi file")

        # 8. metadata thieu cot
        e = expect(ValueError, lambda: E.build_raw_extract(
            "2023-04-17", "2023-04-23", td / "raw5", td / "man5",
            fetch=FakeServer(rows, meta=make_meta(drop="trip_miles")), progress=False))
        ok("trip_miles" in str(e), "metadata thieu cot -> ValueError neu ten cot")

        # 9. parse_types
        raw = df.copy()
        raw.loc[0, "trip_seconds"] = "abc"
        t = E.parse_types(raw)
        ok(len(t) == N and str(t.trip_start_timestamp.dtype).startswith("datetime64"), "parse_types: datetime, khong mat dong")
        ok(t.trip_seconds.isna().sum() == 1 and t.fare.dtype == "float64", "gia tri hong -> NaN, so -> float64")
        ok(str(t.pickup_community_area.dtype) == "Int16" and raw.loc[0, "trip_seconds"] == "abc",
           "community area Int16; bang goc khong bi sua")
        ok(set(t.trip_start_timestamp.dt.minute.unique()) <= {0, 15, 30, 45}, "phut chi co 0/15/30/45")

    print(f"\n{passed} PASS, 0 FAIL")
    return passed


if __name__ == "__main__":
    test_all()
