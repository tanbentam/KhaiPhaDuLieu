"""Ban do Folium cho ket qua phan cum (dung chung K-Means, DBSCAN, HDBSCAN).

Moi lop (layer) la mot lan fit, vi du mot lat cat thoi gian. Moi cham la mot toa do
centroid, kich thuoc ~ can bac hai so chuyen, mau = cum, nhieu (-1) mau xam.
Tam cum ve bang dau cong den, popup ghi so chuyen va ty trong.
Moi lop dung cung khung nhin (extent) de so sanh cong bang (BA Spec muc 2.5).
"""
from __future__ import annotations

import html
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
           "#8c564b", "#e377c2", "#bcbd22", "#17becf", "#7f7f7f"]
NOISE_COLOR = "#b0b0b0"
CHICAGO_CENTER = (41.88, -87.70)


def _color(label: int) -> str:
    return NOISE_COLOR if label < 0 else PALETTE[label % len(PALETTE)]


def cluster_map(layers: dict[str, tuple[pd.DataFrame, Any, pd.DataFrame]], out_html: str | Path,
                title: str, note: str = "") -> Path:
    """layers: {ten_lop: (df co pickup_lat/pickup_lon, labels, cluster_table)}.

    Lop dau tien hien san; cac lop khac bat/tat trong LayerControl.
    Chuoi hien thi (ten lop, tieu de, ghi chu) duoc escape HTML.
    """
    import folium

    # Nen OpenStreetMap: mien phi, khong can API key (CartoDB nay doi key). Can Internet khi mo file.
    m = folium.Map(location=CHICAGO_CENTER, zoom_start=10, tiles="OpenStreetMap", control_scale=True)
    all_lat, all_lon = [], []
    for i, (name, (df, labels, ctab)) in enumerate(layers.items()):
        lab = np.asarray(labels)
        if len(lab) != len(df):
            raise ValueError(f"Lop {name}: so nhan ({len(lab)}) khac so dong ({len(df)})")
        fg = folium.FeatureGroup(name=html.escape(str(name)), show=(i == 0))
        pts = (df.assign(cluster_label=lab)
                 .groupby(["pickup_lat", "pickup_lon", "cluster_label"]).size().rename("n").reset_index())
        n_max = max(int(pts["n"].max()), 1)
        for r in pts.itertuples(index=False):
            lbl = int(r.cluster_label)
            txt = "nhieu" if lbl < 0 else f"cum {lbl}"
            folium.CircleMarker(
                location=(float(r.pickup_lat), float(r.pickup_lon)),
                radius=float(2 + 18 * np.sqrt(r.n / n_max)),
                color=_color(lbl), weight=0.5, fill=True, fill_color=_color(lbl), fill_opacity=0.65,
                tooltip=f"{txt} | {int(r.n):,} chuyen",
            ).add_to(fg)
        for c in ctab.itertuples(index=False):
            folium.Marker(
                location=(float(c.center_lat), float(c.center_lon)),
                icon=folium.DivIcon(html=f'<div style="font:bold 16px sans-serif;color:#000;'
                                         f'transform:translate(-5px,-11px)">+{int(c.cluster)}</div>'),
                tooltip=(f"tam cum {int(c.cluster)} | {int(c.n_trips):,} chuyen | "
                         f"{c.share * 100:.1f}% | ban kinh RMS {c.radius_rms_m / 1000:.1f} km"),
            ).add_to(fg)
        fg.add_to(m)
        all_lat += pts["pickup_lat"].tolist(); all_lon += pts["pickup_lon"].tolist()
    if all_lat:
        m.fit_bounds([[min(all_lat), min(all_lon)], [max(all_lat), max(all_lon)]])
    folium.LayerControl(collapsed=False).add_to(m)
    # Dat o goc duoi ben trai (tren thuoc ty le) de khong che bang chon lop o goc tren ben phai,
    # ke ca tren man hinh dien thoai 375px.
    head = (f'<div style="position:fixed;bottom:48px;left:10px;z-index:9999;background:rgba(255,255,255,.92);'
            f'padding:6px 10px;border:1px solid #999;font:12px/1.35 sans-serif;'
            f'max-width:min(460px, calc(100% - 20px));box-sizing:border-box">'
            f'<b>{html.escape(title)}</b><br>{html.escape(note)}<br>'
            f'Cham = toa do centroid (khong phai GPS), kich thuoc ~ so chuyen; xam = nhieu; +n = tam cum n.<br>'
            f'<i>Luu y nghiep vu: Hotspot la diem tap trung nhu cau don xe, khong phai diem un tac giao thong.</i></div>')
    m.get_root().html.add_child(folium.Element(head))
    out_html = Path(out_html)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(out_html))
    return out_html


def temporal_shift_map(
    clusters_df: pd.DataFrame,
    tracking_df: pd.DataFrame,
    out_html: str | Path,
    title: str = "HDBSCAN - Spatial-Temporal Hotspot Shifts",
    note: str = "",
) -> Path:
    """Ban do Folium the hien su dich chuyen cua cac hotspot giua AM, PM va Weekend (M3).

    Moi lat cat dung mot mau dac trung cho tam cum:
    - WEEKDAY_AM: Xanh lam (#1f77b4)
    - WEEKDAY_PM: Do cam (#d62728)
    - WEEKEND: Xanh la (#2ca02c)

    Duong mui ten noi hai tam the hien huong va khoang cach dich chuyen (m).
    """
    import folium

    m = folium.Map(location=CHICAGO_CENTER, zoom_start=11, tiles="OpenStreetMap", control_scale=True)
    slice_colors = {
        "WEEKDAY_AM": "#1f77b4",
        "WEEKDAY_PM": "#d62728",
        "WEEKEND": "#2ca02c",
    }

    # 1. Ve cac tam cum theo tung lat cat
    for s_name, col in slice_colors.items():
        sub = clusters_df[clusters_df["time_slice"] == s_name]
        fg = folium.FeatureGroup(name=f"Tam cum {s_name}", show=True)
        for r in sub.itertuples(index=False):
            rad = max(4.0, min(18.0, 4.0 + 12.0 * math.sqrt(float(r.share))))
            tip = (f"[{s_name}] Cum {int(r.cluster)}: {int(r.n_trips):,} chuyen ({float(r.share)*100:.1f}%) | "
                   f"Khu vuc: {r.top_community_area} | BK RMS: {float(r.radius_rms_m)/1000:.1f} km")
            folium.CircleMarker(
                location=(float(r.center_lat), float(r.center_lon)),
                radius=rad,
                color=col,
                weight=2.0,
                fill=True,
                fill_color=col,
                fill_opacity=0.75,
                tooltip=tip,
            ).add_to(fg)
            folium.Marker(
                location=(float(r.center_lat), float(r.center_lon)),
                icon=folium.DivIcon(html=f'<div style="font:bold 12px sans-serif;color:{col};'
                                         f'transform:translate(8px,-8px)">{s_name[:2]}-C{int(r.cluster)}</div>'),
            ).add_to(fg)
        fg.add_to(m)

    # 2. Ve cac vector dich chuyen cho cac cap ghep MATCHED
    transitions = tracking_df["transition"].unique()
    line_styles = {
        "WEEKDAY_AM -> WEEKDAY_PM": {"color": "#ff7f0e", "dash": "5, 5", "weight": 2.5},
        "WEEKDAY_PM -> WEEKEND": {"color": "#9467bd", "dash": "2, 4", "weight": 2.0},
        "WEEKDAY_AM -> WEEKEND": {"color": "#8c564b", "dash": "1, 5", "weight": 1.5},
    }

    for trans in transitions:
        sub_tr = tracking_df[(tracking_df["transition"] == trans) & (tracking_df["status"] == "MATCHED")]
        style = line_styles.get(trans, {"color": "#333", "dash": "3, 3", "weight": 2})
        fg_lines = folium.FeatureGroup(name=f"Dich chuyen {trans}", show=(trans == "WEEKDAY_AM -> WEEKDAY_PM"))

        for r in sub_tr.itertuples(index=False):
            p1 = (float(r.from_lat), float(r.from_lon))
            p2 = (float(r.to_lat), float(r.to_lon))
            tip = (f"Dich chuyen: {trans} | Cum {int(r.cluster_from)} -> {int(r.cluster_to)} | "
                   f"Khoang cach: {float(r.shift_distance_m):,.0f} m | "
                   f"Thay doi ty trong: {float(r.delta_share_pct_points):+.2f}%")
            folium.PolyLine(
                locations=[p1, p2],
                color=style["color"],
                weight=style["weight"],
                dash_array=style["dash"],
                tooltip=tip,
            ).add_to(fg_lines)

        fg_lines.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    info_box = (
        f'<div style="position:fixed;bottom:48px;left:10px;z-index:9999;background:rgba(255,255,255,.94);'
        f'padding:8px 12px;border:1px solid #999;border-radius:4px;font:12px/1.4 sans-serif;'
        f'max-width:min(480px, calc(100% - 20px));box-sizing:border-box">'
        f'<b>{html.escape(title)}</b><br>{html.escape(note)}<br>'
        f'<span style="color:#1f77b4">● AM (Sang ngay thuong)</span> | '
        f'<span style="color:#d62728">● PM (Chieu ngay thuong)</span> | '
        f'<span style="color:#2ca02c">● WE (Cuoi tuan)</span><br>'
        f'Duong noi: Vector dich chuyen giua cac tam hotspot.<br>'
        f'<i>Luu y nghiep vu: Toa do la centroid khu vuc hanh chinh (khong phai GPS); Hotspot la diem tap trung nhu cau don xe, khong phai diem un tac giao thong.</i></div>'
    )
    m.get_root().html.add_child(folium.Element(info_box))

    out_html = Path(out_html)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(out_html))
    return out_html

