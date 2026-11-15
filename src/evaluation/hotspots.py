"""Bang mo ta tung cum (hotspot) dung chung cho M2 va M3.

Moi cum: so chuyen, ty trong, so toa do khac nhau, tam cum (trung binh x/y theo tung
chuyen = tam co trong so), toa do tam doi nguoc ve lat/lon, ban kinh RMS (m),
community area xuat hien nhieu nhat. Nhieu (-1) khong phai hotspot: chi bao so luong.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

NOISE = -1


def relabel_by_size(labels: Any) -> np.ndarray:
    """Danh so lai cum theo kich thuoc giam dan: cum lon nhat = 0. Nhieu giu -1.

    Nhan 0/1/2 cua cac lan fit khac nhau khong co nghia co dinh; danh so theo kich thuoc
    giup bang va ban do de doc hon (khong dung de ghep cum giua cac lat cat).
    """
    lab = np.asarray(labels).astype(np.int64)
    ids, counts = np.unique(lab[lab != NOISE], return_counts=True)
    order = ids[np.argsort(-counts, kind="stable")]
    mapping = {old: new for new, old in enumerate(order)}
    return np.array([mapping.get(v, NOISE) for v in lab], dtype=np.int64)


def cluster_table(df: pd.DataFrame, labels: Any, crs: str = "EPSG:26916") -> pd.DataFrame:
    """df can cot x_m, y_m (va tuy chon pickup_lat, pickup_lon, pickup_community_area)."""
    from pyproj import Transformer

    lab = np.asarray(labels)
    if len(lab) != len(df):
        raise ValueError(f"So nhan ({len(lab)}) khac so dong ({len(df)})")
    d = df.assign(_label=lab)
    d = d[d["_label"] != NOISE]
    n_total = len(df)
    if d.empty:
        return pd.DataFrame(columns=["cluster", "n_trips", "share", "n_coords", "center_x_m", "center_y_m",
                                     "center_lat", "center_lon", "radius_rms_m", "top_community_area"])
    g = d.groupby("_label")
    out = pd.DataFrame({
        "n_trips": g.size(),
        "center_x_m": g["x_m"].mean(),
        "center_y_m": g["y_m"].mean(),
        "n_coords": d.drop_duplicates(["_label", "x_m", "y_m"]).groupby("_label").size(),
    })
    out["share"] = out["n_trips"] / n_total
    cx = d["_label"].map(out["center_x_m"]); cy = d["_label"].map(out["center_y_m"])
    sq = (d["x_m"] - cx) ** 2 + (d["y_m"] - cy) ** 2
    out["radius_rms_m"] = np.sqrt(sq.groupby(d["_label"]).mean())
    tf = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    lon, lat = tf.transform(out["center_x_m"].to_numpy(), out["center_y_m"].to_numpy())
    out["center_lat"], out["center_lon"] = lat, lon
    if "pickup_community_area" in d.columns:
        out["top_community_area"] = g["pickup_community_area"].agg(
            lambda s: s.mode().iloc[0] if s.notna().any() else pd.NA)
    else:
        out["top_community_area"] = pd.NA
    out = out.reset_index().rename(columns={"_label": "cluster"}).sort_values("n_trips", ascending=False)
    return out[["cluster", "n_trips", "share", "n_coords", "center_x_m", "center_y_m",
                "center_lat", "center_lon", "radius_rms_m", "top_community_area"]].reset_index(drop=True)
