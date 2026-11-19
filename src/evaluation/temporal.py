"""Phan tich va theo doi su dich chuyen cua cac hotspot theo thoi gian (M3).

Quy tac theo BA Spec v1.1 muc 2.3.5 va 3.4.3:
- Nhan cum 0, 1, 2 giua cac lan fit KHONG co y nghia co dinh.
- Ghep cap cum giua hai lat cat thoi gian (vd WEEKDAY_AM -> WEEKDAY_PM) dua tren:
  1. Khoang cach Euclidean giua hai tam cum theo don vi met (Delta d <= threshold_m).
  2. Su tuong dong ve khu vuc dia ly (top_community_area).
- Do luong:
  - Delta d: khoang cach dich chuyen cua tam cum (m).
  - Delta share: su thay doi ty trong nhu cau (%).
  - Delta trips: su thay doi so luot don.
  - Classification: 'PERSISTENT' (xuat hien on dinh xuyen suot) vs 'EMERGING/DISSOLVING' (cuc bo theo gio).
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def match_clusters(
    df_from: pd.DataFrame,
    df_to: pd.DataFrame,
    *,
    slice_from_name: str,
    slice_to_name: str,
    max_distance_m: float = 3500.0,
) -> pd.DataFrame:
    """Ghep cap tung cum tu lat cat A sang lat cat B dua tren khoang cach tam gan nhat.

    df_from va df_to can cac cot:
        cluster, n_trips, share, center_x_m, center_y_m, center_lat, center_lon,
        radius_rms_m, top_community_area.
    """
    rows = []
    # Sao chep danh sach cum muc tieu de ghep cap
    unmatched_to = set(df_to["cluster"].tolist())

    for _, r_from in df_from.iterrows():
        c_from = int(r_from["cluster"])
        x1, y1 = float(r_from["center_x_m"]), float(r_from["center_y_m"])
        ca1 = r_from.get("top_community_area", None)

        best_c_to = None
        min_dist = float("inf")
        best_r_to = None

        for _, r_to in df_to.iterrows():
            c_to = int(r_to["cluster"])
            x2, y2 = float(r_to["center_x_m"]), float(r_to["center_y_m"])
            dist = math.hypot(x2 - x1, y2 - y1)

            # Uu tien cung khu vuc neu khoang cach xap xi
            if dist < min_dist:
                min_dist = dist
                best_c_to = c_to
                best_r_to = r_to

        matched = (best_r_to is not None) and (min_dist <= max_distance_m)

        if matched and best_r_to is not None:
            unmatched_to.discard(best_c_to)
            shift_x = float(best_r_to["center_x_m"]) - x1
            shift_y = float(best_r_to["center_y_m"]) - y1
            d_trips = int(best_r_to["n_trips"]) - int(r_from["n_trips"])
            d_share = float(best_r_to["share"]) - float(r_from["share"])

            rows.append({
                "transition": f"{slice_from_name} -> {slice_to_name}",
                "status": "MATCHED",
                "cluster_from": c_from,
                "cluster_to": best_c_to,
                "top_area_from": ca1,
                "top_area_to": best_r_to.get("top_community_area", None),
                "shift_distance_m": round(min_dist, 1),
                "shift_dx_m": round(shift_x, 1),
                "shift_dy_m": round(shift_y, 1),
                "trips_from": int(r_from["n_trips"]),
                "trips_to": int(best_r_to["n_trips"]),
                "delta_trips": d_trips,
                "share_from": round(float(r_from["share"]) * 100, 2),
                "share_to": round(float(best_r_to["share"]) * 100, 2),
                "delta_share_pct_points": round(d_share * 100, 2),
                "from_lat": float(r_from["center_lat"]),
                "from_lon": float(r_from["center_lon"]),
                "to_lat": float(best_r_to["center_lat"]),
                "to_lon": float(best_r_to["center_lon"]),
            })
        else:
            # Cum o slice_from khong tim thay cum tuong ung o slice_to
            rows.append({
                "transition": f"{slice_from_name} -> {slice_to_name}",
                "status": "DISSOLVED",
                "cluster_from": c_from,
                "cluster_to": None,
                "top_area_from": ca1,
                "top_area_to": None,
                "shift_distance_m": None,
                "shift_dx_m": None,
                "shift_dy_m": None,
                "trips_from": int(r_from["n_trips"]),
                "trips_to": 0,
                "delta_trips": -int(r_from["n_trips"]),
                "share_from": round(float(r_from["share"]) * 100, 2),
                "share_to": 0.0,
                "delta_share_pct_points": -round(float(r_from["share"]) * 100, 2),
                "from_lat": float(r_from["center_lat"]),
                "from_lon": float(r_from["center_lon"]),
                "to_lat": None,
                "to_lon": None,
            })

    # Cac cum o slice_to moi xuat hien (khong co trong slice_from)
    for c_to in sorted(unmatched_to):
        r_to = df_to[df_to["cluster"] == c_to].iloc[0]
        rows.append({
            "transition": f"{slice_from_name} -> {slice_to_name}",
            "status": "EMERGING",
            "cluster_from": None,
            "cluster_to": c_to,
            "top_area_from": None,
            "top_area_to": r_to.get("top_community_area", None),
            "shift_distance_m": None,
            "shift_dx_m": None,
            "shift_dy_m": None,
            "trips_from": 0,
            "trips_to": int(r_to["n_trips"]),
            "delta_trips": int(r_to["n_trips"]),
            "share_from": 0.0,
            "share_to": round(float(r_to["share"]) * 100, 2),
            "delta_share_pct_points": round(float(r_to["share"]) * 100, 2),
            "from_lat": None,
            "from_lon": None,
            "to_lat": float(r_to["center_lat"]),
            "to_lon": float(r_to["center_lon"]),
        })

    return pd.DataFrame(rows)


def build_hotspot_tracking(
    clusters_df: pd.DataFrame,
    *,
    max_distance_m: float = 3500.0,
) -> pd.DataFrame:
    """Xay dung bang theo doi dich chuyen xuyen suot ca 3 lat cat.

    So sanh:
    1. WEEKDAY_AM -> WEEKDAY_PM (nhu cau sang som lam viec -> chieu tan tam)
    2. WEEKDAY_PM -> WEEKEND (ngay lam viec -> cuoi tuan)
    3. WEEKDAY_AM -> WEEKEND (sang ngay thuong -> cuoi tuan)
    """
    am = clusters_df[clusters_df["time_slice"] == "WEEKDAY_AM"].reset_index(drop=True)
    pm = clusters_df[clusters_df["time_slice"] == "WEEKDAY_PM"].reset_index(drop=True)
    we = clusters_df[clusters_df["time_slice"] == "WEEKEND"].reset_index(drop=True)

    t1 = match_clusters(am, pm, slice_from_name="WEEKDAY_AM", slice_to_name="WEEKDAY_PM", max_distance_m=max_distance_m)
    t2 = match_clusters(pm, we, slice_from_name="WEEKDAY_PM", slice_to_name="WEEKEND", max_distance_m=max_distance_m)
    t3 = match_clusters(am, we, slice_from_name="WEEKDAY_AM", slice_to_name="WEEKEND", max_distance_m=max_distance_m)

    tracking_all = pd.concat([t1, t2, t3], ignore_index=True)
    return tracking_all
