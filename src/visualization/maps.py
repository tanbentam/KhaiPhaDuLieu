"""Ban do Folium cho ket qua phan cum (dung chung K-Means, DBSCAN, HDBSCAN).

Moi lop (layer) la mot lan fit, vi du mot lat cat thoi gian. Moi cham la mot toa do
centroid, kich thuoc ~ can bac hai so chuyen, mau = cum, nhieu (-1) mau xam.
Tam cum ve bang dau cong den, popup ghi so chuyen va ty trong.
Moi lop dung cung khung nhin (extent) de so sanh cong bang (BA Spec muc 2.5).
"""
from __future__ import annotations

import html
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
            f'Cham = toa do centroid (khong phai GPS), kich thuoc ~ so chuyen; xam = nhieu; +n = tam cum n.</div>')
    m.get_root().html.add_child(folium.Element(head))
    out_html = Path(out_html)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(out_html))
    return out_html
