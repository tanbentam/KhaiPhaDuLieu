"""M1 - Xac minh nguon va trich xuat du lieu tho Chicago Taxi Trips (task M1-01, M1-02).

Cong du lieu tra 403 tu may o Viet Nam -> chay tren Google Colab
(notebooks/01_data_acquisition_eda.ipynb).

Cac buoc cua build_raw_extract:
  1. doc metadata that cua cong du lieu, doi chieu ten cot (khong tin tai lieu cu);
  2. luu schema_snapshot.json va data_dictionary.csv;
  3. dem so dong tren server theo dieu kien $where;
  4. tai theo trang, moi trang luu thanh 1 file (checkpoint) de chay lai khong mat cong;
  5. ghep, doi chieu so dong voi server, luu raw_extract_<start>_<end>.parquet;
  6. ghi manifest (JSON, co sha256) va source_manifest.md.

File tho la BAT BIEN: gia tri giu nguyen dang chuoi nhu API tra ve, khong loc, khong sua.
Neu file da ton tai thi bao loi, khong ghi de. Ep kieu dung parse_types() o buoc sau.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
try:
    import pyarrow.parquet as pq
except ImportError:
    pq = None

# Dung lai phan goi API da kiem thu cua M2 (thu lai khi 429/5xx, where tron ngay, sha256)
from src.m2_pilot import (DATASET_ID, METADATA_URL, PAGE_SIZE, PORTAL_URL, RESOURCE_URL,
                          Fetcher, _default_fetch, sha256, where_clause)

# fieldName tren cong du lieu -> (ten noi bo, don vi, vai tro trong do an)
FIELDS: dict[str, tuple[str, str, str]] = {
    "trip_id": ("trip_id", "", "Khoa chuyen di; dung de tai lap mau"),
    "trip_start_timestamp": ("trip_start_timestamp", "gio dia phuong Chicago, lam tron 15 phut",
                             "Thoi diem don; tao pickup_hour, weekday, time_slice"),
    "trip_end_timestamp": ("trip_end_timestamp", "gio dia phuong Chicago, lam tron 15 phut",
                           "Kiem tra end < start"),
    "trip_seconds": ("trip_seconds", "giay", "EDA va co chat luong; KHONG dua vao mo hinh"),
    "trip_miles": ("trip_miles", "dam (mile)", "EDA va co chat luong; KHONG dua vao mo hinh"),
    "pickup_census_tract": ("pickup_census_tract", "ma census tract", "EDA khong gian; co the bi an"),
    "dropoff_census_tract": ("dropoff_census_tract", "ma census tract", "EDA khong gian; co the bi an"),
    "pickup_community_area": ("pickup_community_area", "ma khu 1-77", "Dien giai cum nam o khu nao"),
    "dropoff_community_area": ("dropoff_community_area", "ma khu 1-77", "Nhanh doi chieu drop-off"),
    "fare": ("fare", "USD", "EDA; KHONG dua vao mo hinh"),
    "tips": ("tips", "USD", "EDA; KHONG dua vao mo hinh"),
    "trip_total": ("trip_total", "USD", "EDA; KHONG dua vao mo hinh"),
    "company": ("company", "", "EDA phan khuc"),
    "pickup_centroid_latitude": ("pickup_lat", "do (WGS84), tam vung, khong phai GPS",
                                 "Toa do don -> chieu sang x_m, y_m"),
    "pickup_centroid_longitude": ("pickup_lon", "do (WGS84), tam vung, khong phai GPS",
                                  "Toa do don -> chieu sang x_m, y_m"),
    "dropoff_centroid_latitude": ("dropoff_lat", "do (WGS84), tam vung, khong phai GPS",
                                  "Nhanh doi chieu drop-off"),
    "dropoff_centroid_longitude": ("dropoff_lon", "do (WGS84), tam vung, khong phai GPS",
                                   "Nhanh doi chieu drop-off"),
}
COLUMNS = list(FIELDS)

TIMESTAMP_COLS = ["trip_start_timestamp", "trip_end_timestamp"]
FLOAT_COLS = ["trip_seconds", "trip_miles", "fare", "tips", "trip_total",
              "pickup_centroid_latitude", "pickup_centroid_longitude",
              "dropoff_centroid_latitude", "dropoff_centroid_longitude"]
AREA_COLS = ["pickup_community_area", "dropoff_community_area"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _epoch_to_iso(v: Any) -> str | None:
    try:
        return datetime.fromtimestamp(int(v), timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------ M1-01: nguon va schema

def fetch_metadata(fetch: Fetcher = _default_fetch) -> dict[str, Any]:
    return fetch(METADATA_URL, {})


def check_columns(meta: dict[str, Any], columns: list[str] = COLUMNS) -> list[str]:
    """Doi chieu cot can lay voi metadata that. Thieu cot thi bao loi, tra ve moi cot hien co."""
    names = [c.get("fieldName") for c in meta.get("columns", [])]
    missing = [c for c in columns if c not in names]
    if missing:
        raise ValueError(f"Metadata khong co cot: {missing}. Cot hien co: {names}")
    return names


def schema_snapshot(meta: dict[str, Any]) -> dict[str, Any]:
    """Anh chup schema tai thoi diem tai (chi giu phan can de truy nguon)."""
    cols = [c for c in meta.get("columns", []) if not str(c.get("fieldName", "")).startswith(":")]
    return {
        "dataset_id": DATASET_ID,
        "name": meta.get("name"),
        "portal_url": PORTAL_URL,
        "metadata_url": METADATA_URL,
        "retrieved_at_utc": _now(),
        "rows_updated_at_utc": _epoch_to_iso(meta.get("rowsUpdatedAt")),
        "view_last_modified_utc": _epoch_to_iso(meta.get("viewLastModified")),
        "license": (meta.get("license") or {}).get("name"),
        "attribution": meta.get("attribution"),
        "n_columns": len(cols),
        "columns": [{"fieldName": c.get("fieldName"), "name": c.get("name"),
                     "dataTypeName": c.get("dataTypeName"),
                     "description": c.get("description")} for c in cols],
    }


def data_dictionary(snapshot: dict[str, Any]) -> pd.DataFrame:
    """Bang moi cot cua nguon: ten that, kieu, mo ta goc; cot M1 dung thi co ten noi bo, don vi, vai tro."""
    rows = []
    for c in snapshot["columns"]:
        name = c["fieldName"]
        internal, unit, role = FIELDS.get(name, ("", "", ""))
        rows.append({"field_name": name, "display_name": c["name"], "source_type": c["dataTypeName"],
                     "used_by_m1": name in FIELDS, "internal_name": internal, "unit": unit,
                     "role": role, "source_description": c["description"]})
    return pd.DataFrame(rows)


def server_count(where: str, fetch: Fetcher = _default_fetch) -> int:
    res = fetch(RESOURCE_URL, {"$select": "count(*) AS n", "$where": where})
    return int(res[0]["n"])


def download_pages(where: str, parts_dir: str | Path, columns: list[str] = COLUMNS,
                   fetch: Fetcher = _default_fetch, page_size: int = PAGE_SIZE,
                   progress: bool = True) -> int:
    """Tai theo trang (sap theo trip_id), moi trang ghi 1 file part_XXXXX.parquet. Tra ve tong so dong.

    Chay lai sau khi bi ngat thi tiep tuc tu cho da tai. Chi dung khi gap trang rong
    (server co the tu gioi han so dong moi trang thap hon so xin).
    """
    parts_dir = Path(parts_dir)
    parts_dir.mkdir(parents=True, exist_ok=True)
    query = {"where": where, "columns": columns, "order": "trip_id"}
    qfile = parts_dir / "_query.json"
    if qfile.exists():
        if json.loads(qfile.read_text(encoding="utf-8")) != query:
            raise RuntimeError(f"{parts_dir} chua cac trang cua mot truy van KHAC. "
                               "Xoa thu muc nay (sau khi kiem tra) roi chay lai.")
    else:
        qfile.write_text(json.dumps(query), encoding="utf-8")

    parts = sorted(parts_dir.glob("part_*.parquet"))
    if pq is not None:
        offset = sum(pq.read_metadata(p).num_rows for p in parts)
    else:
        import fastparquet
        offset = sum(fastparquet.ParquetFile(str(p)).count() for p in parts)
    if parts and progress:
        print(f"  tiep tuc tu {offset:,} dong da tai ({len(parts)} trang)")
    idx = len(parts)
    while True:
        page = fetch(RESOURCE_URL, {
            "$select": ",".join(columns), "$where": where, "$order": "trip_id",
            "$limit": str(page_size), "$offset": str(offset),
        })
        if not page:
            break
        # cot null toan bo khong xuat hien trong JSON -> reindex; ep 'string' de schema cac trang giong nhau
        df = pd.DataFrame(page, dtype="object").reindex(columns=columns).astype("string")
        tmp = parts_dir / f"part_{idx:05d}.tmp"
        df.to_parquet(tmp, index=False)
        tmp.rename(parts_dir / f"part_{idx:05d}.parquet")   # doi ten sau khi ghi xong -> khong co trang do dang
        offset += len(df)
        idx += 1
        if progress:
            print(f"  da tai {offset:,} dong")
    return offset


def parse_types(raw: pd.DataFrame) -> pd.DataFrame:
    """Ep kieu ban sao cua bang tho (khong loc dong nao). Gia tri hong thanh NaT/NaN de EDA dem."""
    df = raw.copy()
    for c in TIMESTAMP_COLS:
        if c in df:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    for c in FLOAT_COLS:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")
    for c in AREA_COLS:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int16")
    return df


def raw_name(start: str, end: str) -> str:
    return f"raw_extract_{start.replace('-', '')}_{end.replace('-', '')}"


def _source_manifest_md(m: dict[str, Any]) -> str:
    return f"""# Nguồn dữ liệu thô (M1-01, M1-02)

File này do `src/data/extract.py` sinh ra khi tải, không sửa tay.

| Hạng mục | Giá trị |
|---|---|
| Bộ dữ liệu | {m['dataset_name']} (`{DATASET_ID}`) |
| Trang nguồn | {PORTAL_URL} |
| Endpoint | {RESOURCE_URL} |
| Thời điểm tải (UTC) | {m['retrieved_at_utc']} |
| Nguồn cập nhật lần cuối (UTC) | {m['rows_updated_at_utc']} |
| Giấy phép | {m['license']} |
| Cửa sổ thời gian | {m['date_window'][0]} đến {m['date_window'][1]} (trọn ngày) |
| Điều kiện `$where` | `{m['query_where']}` |
| Sắp xếp khi phân trang | `trip_id` |
| Số dòng server đếm | {m['rows_server_count']:,} |
| Số dòng tải về | {m['rows_raw']:,} |
| Số cột | {len(m['columns'])} |
| File | `{m['file']}` |
| sha256 | `{m['sha256']}` |

Cột đã lấy (`$select`): {", ".join(f"`{c}`" for c in m['columns'])}.

## Lưu ý khi dùng

- Toạ độ pickup/dropoff là **tâm của census tract hoặc community area**, không phải GPS. Kết quả chỉ diễn giải ở mức khu vực.
- Thời gian bắt đầu/kết thúc chuyến được nguồn **làm tròn tới 15 phút**. Không phân tích biến động dưới 15 phút.
- Nguồn chỉ gồm các chuyến taxi được báo cáo cho thành phố, không đại diện toàn bộ giao thông Chicago.
- File thô giữ nguyên giá trị dạng chuỗi như API trả về, chưa lọc và chưa ép kiểu. Ép kiểu bằng `parse_types()`.
- Cổng dữ liệu trả 403 khi truy cập từ Việt Nam; việc tải chạy trên Google Colab.
"""


def build_raw_extract(start: str, end: str, raw_dir: str | Path, manifests_dir: str | Path,
                      fetch: Fetcher = _default_fetch, page_size: int = PAGE_SIZE,
                      progress: bool = True) -> dict[str, Any]:
    """Chay tron goi M1-01 + M1-02, tra ve manifest. Bao loi neu so dong tai ve khac so server dem."""
    raw_dir, manifests_dir = Path(raw_dir), Path(manifests_dir)
    name = raw_name(start, end)
    out = raw_dir / f"{name}.parquet"
    if out.exists():
        raise FileExistsError(f"{out} da ton tai. File tho la bat bien, khong ghi de.")
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)

    meta = fetch_metadata(fetch)
    check_columns(meta)
    snap = schema_snapshot(meta)
    (manifests_dir / "schema_snapshot.json").write_text(
        json.dumps(snap, indent=2, ensure_ascii=False), encoding="utf-8")
    data_dictionary(snap).to_csv(manifests_dir / "data_dictionary.csv", index=False, encoding="utf-8")

    where = where_clause(start, end)
    expected = server_count(where, fetch)
    if progress:
        print(f"Server bao {expected:,} chuyen trong {start} .. {end}")
    parts_dir = raw_dir / f"_parts_{name}"
    got = download_pages(where, parts_dir, COLUMNS, fetch, page_size, progress)
    if got != expected:
        raise RuntimeError(f"Tai thieu/du: server {expected}, tai ve {got}. "
                           f"Cac trang van nam o {parts_dir} de kiem tra.")

    parts = sorted(parts_dir.glob("part_*.parquet"))
    df = (pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True) if parts
          else pd.DataFrame(columns=COLUMNS, dtype="string"))
    df = df.sort_values("trip_id", kind="stable").reset_index(drop=True)
    df.to_parquet(out, index=False)
    shutil.rmtree(parts_dir)        # chi xoa thu muc trang tam do chinh ham nay tao

    manifest = {
        "file": out.name,
        "created_by": "M1",
        "dataset_name": snap["name"],
        "source": PORTAL_URL,
        "endpoint": RESOURCE_URL,
        "retrieved_at_utc": _now(),
        "rows_updated_at_utc": snap["rows_updated_at_utc"],
        "license": snap["license"],
        "query_select": ",".join(COLUMNS),
        "query_where": where,
        "query_order": "trip_id",
        "date_window": [start, end],
        "columns": COLUMNS,
        "rows_server_count": expected,
        "rows_raw": len(df),
        "file_size_bytes": out.stat().st_size,
        "sha256": sha256(out),
    }
    (manifests_dir / f"{name}_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (manifests_dir / "source_manifest.md").write_text(_source_manifest_md(manifest), encoding="utf-8")
    return manifest
