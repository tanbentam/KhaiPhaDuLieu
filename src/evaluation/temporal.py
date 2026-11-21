"""Phan tich va theo doi su dich chuyen cua cac hotspot theo thoi gian (M3).

Quy tac theo BA Spec v1.1 muc 2.3.5 va 3.4.3:
- Nhan cum 0, 1, 2 giua cac lan fit KHONG co y nghia co dinh.
- Ghep moi cum nguon voi cum dich gan nhat neu khoang cach Euclidean <= threshold_m.
- top_community_area duoc giu trong ket qua de dien giai, khong tham gia quyet dinh ghep.
- Do luong:
  - Delta d: khoang cach dich chuyen cua tam cum (m).
  - Delta share: su thay doi ty trong nhu cau (%).
  - Delta trips: su thay doi so luot don.
- Trang thai ghep: 'MATCHED', 'EMERGING' hoac 'DISSOLVED'; MATCHED khong tu dong co nghia la hotspot da duoc xac nhan persistent.
"""
from __future__ import annotations

import math
from typing import Any

import pandas as pd


def build_time_slice_manifest(
    source_df: pd.DataFrame,
    slice_config: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    """Summarize configured slice exposure and observed pickup counts."""
    required = {"time_slice", "trip_start_timestamp"}
    missing = required - set(source_df.columns)
    if missing:
        raise ValueError(f"source_df is missing required columns: {sorted(missing)}")

    timestamps = pd.to_datetime(source_df["trip_start_timestamp"], errors="raise")
    if timestamps.empty or timestamps.isna().any():
        raise ValueError("trip_start_timestamp must contain non-missing observations.")
    dates = timestamps.dt.normalize()
    study_dates = pd.date_range(dates.min(), dates.max(), freq="D")
    rows = []
    for time_slice, definition in slice_config.items():
        mask = source_df["time_slice"] == time_slice
        n_pickups = int(mask.sum())
        weekdays = set(definition["weekdays"])
        n_days = sum(day.weekday() in weekdays for day in study_dates)
        hours = definition["hours"]
        hours_per_day = 24 if hours == "all" else len(hours)
        if n_pickups == 0 or n_days == 0 or hours_per_day <= 0:
            raise ValueError(f"Time slice {time_slice} has no valid observations or hours.")

        exposure_hours = n_days * hours_per_day
        rows.append({
            "time_slice": time_slice,
            "weekdays": ",".join(map(str, sorted(weekdays))),
            "hours": hours if isinstance(hours, str) else ",".join(map(str, hours)),
            "n_days": n_days,
            "hours_per_day": hours_per_day,
            "exposure_hours": exposure_hours,
            "n_pickups": n_pickups,
            "pickups_per_hour": n_pickups / exposure_hours,
            "first_timestamp": timestamps[mask].min(),
            "last_timestamp": timestamps[mask].max(),
        })
    return pd.DataFrame(rows)


def match_clusters(
    df_from: pd.DataFrame,
    df_to: pd.DataFrame,
    *,
    slice_from_name: str,
    slice_to_name: str,
    max_distance_m: float = 3500.0,
    scaled_min_trips: int | None = None,
) -> pd.DataFrame:
    """Ghep cap hai chieu va phan loai: STABLE, MERGED, SPLIT, EMERGING, DISSOLVED.

    Quy tac theo BA Spec v1.1 va ra soat M3:
    - Khoang cach Euclidean giua hai tam cum <= max_distance_m (mac dinh 3500 m).
    - STABLE (on dinh): Cap cum ghep 1-1 doi xung (mutual nearest centroid).
    - MERGED (gop): Nhieu cum nguon cung ghep vao 1 cum dich.
    - SPLIT (tach): 1 cum nguon phan tach thanh nhieu cum dich.
    - DISSOLVED (mat): Cum nguon khong tim thay cum dich nao trong ban kinh nguong.
    - EMERGING (moi): Cum dich khong co cum nguon nao trong ban kinh nguong.
    """
    from_by_id = {int(r["cluster"]): r for _, r in df_from.iterrows()}
    to_by_id = {int(r["cluster"]): r for _, r in df_to.iterrows()}

    # 1. Chieu thuan (Forward): moi cum from tim cum to gan nhat
    f_best: dict[int, int] = {}
    f_dist: dict[int, float] = {}
    for c_from, r_from in from_by_id.items():
        x1, y1 = float(r_from["center_x_m"]), float(r_from["center_y_m"])
        best_c, min_d = None, float("inf")
        for c_to, r_to in to_by_id.items():
            d = math.hypot(float(r_to["center_x_m"]) - x1, float(r_to["center_y_m"]) - y1)
            if d < min_d:
                min_d = d
                best_c = c_to
        if best_c is not None and min_d <= max_distance_m:
            f_best[c_from] = best_c
            f_dist[c_from] = min_d

    # 2. Chieu nghich (Backward): moi cum to tim cum from gan nhat
    b_best: dict[int, int] = {}
    b_dist: dict[int, float] = {}
    for c_to, r_to in to_by_id.items():
        x2, y2 = float(r_to["center_x_m"]), float(r_to["center_y_m"])
        best_c, min_d = None, float("inf")
        for c_from, r_from in from_by_id.items():
            d = math.hypot(x2 - float(r_from["center_x_m"]), y2 - float(r_from["center_y_m"]))
            if d < min_d:
                min_d = d
                best_c = c_from
        if best_c is not None and min_d <= max_distance_m:
            b_best[c_to] = best_c
            b_dist[c_to] = min_d

    from collections import defaultdict
    dst_sources = defaultdict(list)
    for c_from, c_to in f_best.items():
        dst_sources[c_to].append(c_from)

    src_destinations = defaultdict(list)
    for c_to, c_from in b_best.items():
        src_destinations[c_from].append(c_to)

    rows = []
    matched_pairs: set[tuple[int, int]] = set()

    # 1. Forward edges
    for c_from in sorted(from_by_id.keys()):
        r_from = from_by_id[c_from]
        ca1 = r_from.get("top_community_area", None)
        n_coords_from = int(r_from.get("n_coords", 1))

        if c_from not in f_best:
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
                "n_coords_from": n_coords_from,
                "n_coords_to": None,
                "coord_note": "dissolved_no_target",
                "below_scaled_threshold": False,
                "from_lat": float(r_from["center_lat"]),
                "from_lon": float(r_from["center_lon"]),
                "to_lat": None,
                "to_lon": None,
            })
        else:
            c_to = f_best[c_from]
            r_to = to_by_id[c_to]
            matched_pairs.add((c_from, c_to))
            d_val = f_dist[c_from]
            n_coords_to = int(r_to.get("n_coords", 1))

            is_mutual = (b_best.get(c_to) == c_from)
            n_src = len(dst_sources[c_to])
            n_dst = len(src_destinations[c_from])

            if is_mutual and n_src == 1 and n_dst == 1:
                cat = "STABLE"
            elif n_src > 1:
                cat = "MERGED"
            elif n_dst > 1:
                cat = "SPLIT"
            else:
                cat = "STABLE"

            shift_x = float(r_to["center_x_m"]) - float(r_from["center_x_m"])
            shift_y = float(r_to["center_y_m"]) - float(r_from["center_y_m"])

            coord_note = (
                "single_coord_zero_shift"
                if (round(d_val, 1) == 0.0 and n_coords_from == 1 and n_coords_to == 1)
                else "multi_coord_shift" if round(d_val, 1) > 0.0
                else "same_centroid"
            )

            is_below_scaled = (
                scaled_min_trips is not None and int(r_to["n_trips"]) < scaled_min_trips
            )

            rows.append({
                "transition": f"{slice_from_name} -> {slice_to_name}",
                "status": cat,
                "cluster_from": c_from,
                "cluster_to": c_to,
                "top_area_from": ca1,
                "top_area_to": r_to.get("top_community_area", None),
                "shift_distance_m": round(d_val, 1),
                "shift_dx_m": round(shift_x, 1),
                "shift_dy_m": round(shift_y, 1),
                "trips_from": int(r_from["n_trips"]),
                "trips_to": int(r_to["n_trips"]),
                "delta_trips": int(r_to["n_trips"]) - int(r_from["n_trips"]),
                "share_from": round(float(r_from["share"]) * 100, 2),
                "share_to": round(float(r_to["share"]) * 100, 2),
                "delta_share_pct_points": round((float(r_to["share"]) - float(r_from["share"])) * 100, 2),
                "n_coords_from": n_coords_from,
                "n_coords_to": n_coords_to,
                "coord_note": coord_note,
                "below_scaled_threshold": is_below_scaled,
                "from_lat": float(r_from["center_lat"]),
                "from_lon": float(r_from["center_lon"]),
                "to_lat": float(r_to["center_lat"]),
                "to_lon": float(r_to["center_lon"]),
            })

    # 2. Backward edges for destination clusters not covered by forward edges (SPLIT)
    for c_to in sorted(to_by_id.keys()):
        r_to = to_by_id[c_to]
        n_coords_to = int(r_to.get("n_coords", 1))
        is_below_scaled = (
            scaled_min_trips is not None and int(r_to["n_trips"]) < scaled_min_trips
        )

        if c_to not in b_best:
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
                "n_coords_from": None,
                "n_coords_to": n_coords_to,
                "coord_note": "emerging_no_source",
                "below_scaled_threshold": is_below_scaled,
                "from_lat": None,
                "from_lon": None,
                "to_lat": float(r_to["center_lat"]),
                "to_lon": float(r_to["center_lon"]),
            })
        else:
            c_from = b_best[c_to]
            if (c_from, c_to) not in matched_pairs:
                matched_pairs.add((c_from, c_to))
                r_from = from_by_id[c_from]
                d_val = b_dist[c_to]
                n_coords_from = int(r_from.get("n_coords", 1))
                shift_x = float(r_to["center_x_m"]) - float(r_from["center_x_m"])
                shift_y = float(r_to["center_y_m"]) - float(r_from["center_y_m"])

                coord_note = (
                    "single_coord_zero_shift"
                    if (round(d_val, 1) == 0.0 and n_coords_from == 1 and n_coords_to == 1)
                    else "multi_coord_shift" if round(d_val, 1) > 0.0
                    else "same_centroid"
                )

                rows.append({
                    "transition": f"{slice_from_name} -> {slice_to_name}",
                    "status": "SPLIT",
                    "cluster_from": c_from,
                    "cluster_to": c_to,
                    "top_area_from": r_from.get("top_community_area", None),
                    "top_area_to": r_to.get("top_community_area", None),
                    "shift_distance_m": round(d_val, 1),
                    "shift_dx_m": round(shift_x, 1),
                    "shift_dy_m": round(shift_y, 1),
                    "trips_from": int(r_from["n_trips"]),
                    "trips_to": int(r_to["n_trips"]),
                    "delta_trips": int(r_to["n_trips"]) - int(r_from["n_trips"]),
                    "share_from": round(float(r_from["share"]) * 100, 2),
                    "share_to": round(float(r_to["share"]) * 100, 2),
                    "delta_share_pct_points": round((float(r_to["share"]) - float(r_from["share"])) * 100, 2),
                    "n_coords_from": n_coords_from,
                    "n_coords_to": n_coords_to,
                    "coord_note": coord_note,
                    "below_scaled_threshold": is_below_scaled,
                    "from_lat": float(r_from["center_lat"]),
                    "from_lon": float(r_from["center_lon"]),
                    "to_lat": float(r_to["center_lat"]),
                    "to_lon": float(r_to["center_lon"]),
                })

    return pd.DataFrame(rows)


def build_hotspot_tracking(
    clusters_df: pd.DataFrame,
    *,
    max_distance_m: float = 3500.0,
) -> pd.DataFrame:
    """Xay dung bang theo doi dich chuyen xuyen suot ca 3 lat cat (Hai chieu & phan loai)."""
    am = clusters_df[clusters_df["time_slice"] == "WEEKDAY_AM"].reset_index(drop=True)
    pm = clusters_df[clusters_df["time_slice"] == "WEEKDAY_PM"].reset_index(drop=True)
    we = clusters_df[clusters_df["time_slice"] == "WEEKEND"].reset_index(drop=True)

    # Scaled min trips cho Weekend theo ty le kich thuoc lat cat so voi AM (100 chuyen / 60.498 dong -> 199 chuyen / 120.571 dong)
    t1 = match_clusters(am, pm, slice_from_name="WEEKDAY_AM", slice_to_name="WEEKDAY_PM", max_distance_m=max_distance_m)
    t2 = match_clusters(pm, we, slice_from_name="WEEKDAY_PM", slice_to_name="WEEKEND", max_distance_m=max_distance_m, scaled_min_trips=199)
    t3 = match_clusters(am, we, slice_from_name="WEEKDAY_AM", slice_to_name="WEEKEND", max_distance_m=max_distance_m, scaled_min_trips=199)

    tracking_all = pd.concat([t1, t2, t3], ignore_index=True)
    return tracking_all
