"""Ban do chuan hoa cua M4 (M4-03, M4-04): heatmap pickup va ban do so sanh 3 thuat toan.

Nguyen tac (BA 2.5, 2.4):
- CUNG extent, CUNG zoom, CUNG thang kich thuoc cham cho moi ban do thuat toan.
- Noise khong ve thanh hotspot (xam, ghi bang chu giai); chi ve tam cum.
- Tam cum (marker +) khac diem quan sat; vong tron = ban kinh RMS quanh tam, KHONG phai ranh gioi cum.
- Tien de: dung bang cum do M2/M3 phat hanh (*_clusters_master_v1.csv). M4 khong gan lai nhan.
  Ban do cap diem (tung toa do) can outputs/labels/*.parquet (khong commit) -> xem ban do goc cua M2/M3.
"""
from __future__ import annotations

import html
from pathlib import Path

import numpy as np
import pandas as pd

from .style import (ALGO_COLOR, ALGO_ORDER, CENTROID_CAVEAT, NOISE_COLOR, SLICE_LABEL, SLICE_ORDER,
                    SLICE_SHORT, SOURCE_NOTE, algo_label, apply_matplotlib_style, fmt_int, fmt_pct)

METRICS_DIR = Path("outputs") / "metrics"
MAP_DIR = Path("outputs") / "maps"
FIG_DIR = Path("outputs") / "figures" / "comparison"

# Bbox Chicago (theo config/cleaning_rules.yaml: lat 41.64-42.05, lon -87.94..-87.52) — dung de loai diem ngoai pham vi
BBOX = dict(lat_min=41.64, lat_max=42.05, lon_min=-87.94, lon_max=-87.52)


def load_cluster_tables(root: str | Path = ".") -> dict[str, pd.DataFrame]:
    """Doc 3 bang cum (M2/M3) ve cung schema toi thieu; them cot algorithm."""
    root = Path(root)
    out = {}
    for a in ALGO_ORDER:
        df = pd.read_csv(root / METRICS_DIR / f"{a}_clusters_master_v1.csv")
        if a == "dbscan" and "role" in df.columns:
            df = df[df["role"].astype(str).str.contains("chinh")].copy()   # chi cau hinh chinh (A)
        df["algorithm"] = a
        if "noise_trips" not in df.columns:
            df["noise_trips"] = 0
            df["noise_share"] = 0.0
        out[a] = df
    return out


def shared_extent(tables: dict[str, pd.DataFrame], extra_coords: pd.DataFrame | None = None,
                  pad: float = 0.03) -> tuple[float, float, float, float]:
    """(lat_min, lon_min, lat_max, lon_max) chung cho moi ban do; gom ca toa do EDA neu co."""
    lat = pd.concat([t["center_lat"] for t in tables.values()] + ([extra_coords["lat"]] if extra_coords is not None else []))
    lon = pd.concat([t["center_lon"] for t in tables.values()] + ([extra_coords["lon"]] if extra_coords is not None else []))
    return (float(lat.min() - pad), float(lon.min() - pad), float(lat.max() + pad), float(lon.max() + pad))


def check_in_bbox(df: pd.DataFrame, lat: str, lon: str) -> pd.DataFrame:
    """Giu lai cac dong trong bbox Chicago; tra ve phan bi loai (de ghi log, khong ve)."""
    ok = df[lat].between(BBOX["lat_min"], BBOX["lat_max"]) & df[lon].between(BBOX["lon_min"], BBOX["lon_max"])
    return df[ok].copy(), df[~ok].copy()


# ------------------------------------------------------------------------- heatmap

def pickup_heatmap(root: str | Path = ".", out_html: str | Path | None = None) -> dict[str, Path]:
    """pickup_demand_heatmap.html (Folium HeatMap, trong so = so chuyen/centroid) + PNG tinh du phong.

    Nguon: outputs/metrics/eda/pickup_coords.csv (nhu cau TONG, 304 toa do). Chua co heatmap theo lat cat vi
    EDA khong phat hanh toa do kem lat cat (de xuat M1 bo sung, xem docs/M4).
    """
    import folium
    from folium.plugins import HeatMap
    import matplotlib.pyplot as plt

    root = Path(root)
    pc = pd.read_csv(root / METRICS_DIR / "eda" / "pickup_coords.csv")
    pc, dropped = check_in_bbox(pc, "lat", "lon")
    total = int(pc["trips"].sum())
    tables = load_cluster_tables(root)
    lat0, lon0, lat1, lon1 = shared_extent(tables, pc)

    m = folium.Map(location=[(lat0 + lat1) / 2, (lon0 + lon1) / 2], zoom_start=10, tiles=None, control_scale=True)
    folium.TileLayer("OpenStreetMap", name="Nền OSM (cần Internet)", show=True).add_to(m)
    folium.TileLayer(tiles="", attr="không nền (offline)", name="Không nền (offline)", show=False).add_to(m)
    heat = folium.FeatureGroup(name="Heatmap nhu cầu đón (theo số chuyến)", show=True)
    HeatMap(pc[["lat", "lon", "trips"]].values.tolist(), radius=18, blur=22, min_opacity=0.25,
            max_zoom=12).add_to(heat)
    heat.add_to(m)
    pts = folium.FeatureGroup(name="Centroid pickup (top 15)", show=False)
    for r in pc.nlargest(15, "trips").itertuples(index=False):
        folium.CircleMarker((r.lat, r.lon), radius=4 + 14 * np.sqrt(r.trips / pc["trips"].max()),
                            color="#333", weight=1, fill=True, fill_color="#d62728", fill_opacity=0.5,
                            tooltip=f"hạng {int(r.rank)} · {int(r.trips):,} chuyến · {r.share_pct:.1f}%").add_to(pts)
    pts.add_to(m)
    m.fit_bounds([[lat0, lon0], [lat1, lon1]])
    folium.LayerControl(collapsed=False).add_to(m)
    title = "Chicago — nhu cầu đón xe taxi theo centroid (toàn bộ master_v1, 17/04–14/05/2023)"
    note = (f"Cường độ = số chuyến tại mỗi centroid (n = {fmt_int(total)} chuyến, {len(pc)} tọa độ). "
            "Nhu cầu ĐÓN khách, không phải ùn tắc. " + CENTROID_CAVEAT)
    m.get_root().html.add_child(folium.Element(
        f'<div style="position:fixed;bottom:48px;left:10px;z-index:9999;background:rgba(255,255,255,.94);'
        f'padding:6px 10px;border:1px solid #999;font:12px/1.35 sans-serif;'
        f'max-width:min(480px,calc(100% - 20px));box-sizing:border-box"><b>{html.escape(title)}</b><br>'
        f'{html.escape(note)}<br><i>{html.escape(SOURCE_NOTE)}</i></div>'))
    out_html = Path(out_html or root / MAP_DIR / "pickup_demand_heatmap.html")
    out_html.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(out_html))

    # PNG tinh du phong (khong can Internet)
    apply_matplotlib_style()
    fig, ax = plt.subplots(figsize=(8, 9))
    pcs = pc.sort_values("trips")
    sc = ax.scatter(pcs["lon"], pcs["lat"], s=8 + 900 * (pcs["trips"] / pcs["trips"].max()) ** 1.0,
                    c=np.log10(pcs["trips"]), cmap="YlOrRd", alpha=0.75, edgecolor="#555", linewidth=0.3)
    cb = fig.colorbar(sc, ax=ax, shrink=0.6)
    cb.set_label("log10(số chuyến tại centroid)")
    ax.set_xlim(lon0, lon1); ax.set_ylim(lat0, lat1)
    ax.set_aspect(1 / np.cos(np.radians(41.88)))
    ax.set_xlabel("Kinh độ (WGS84)"); ax.set_ylabel("Vĩ độ (WGS84)")
    ax.set_title("Nhu cầu đón taxi theo centroid — Chicago, master_v1", loc="left")
    ax.set_xticks(np.arange(-87.9, -87.5, 0.1))
    offs = [(18, 22), (-30, -34), (22, 14), (28, -4), (22, -22)]   # tranh chong nhan #1/#2 va #4/#5
    for r, off in zip(pc.nlargest(5, "trips").itertuples(index=False), offs):
        ax.annotate(f"#{int(r.rank)} ({r.share_pct:.1f}%)", (r.lon, r.lat), fontsize=8.5, xytext=off,
                    textcoords="offset points", arrowprops=dict(arrowstyle="-", color="#555", lw=0.6))
    fig.text(0.01, -0.01, f"Kích thước/màu ∝ số chuyến (n = {fmt_int(total)}). {CENTROID_CAVEAT}\n"
             f"Không có nền bản đồ (bản dự phòng offline). {SOURCE_NOTE}", fontsize=8, va="top", color="#555")
    png = Path(root / FIG_DIR / "pickup_demand_heatmap.png")
    png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png, dpi=300)
    plt.close(fig)
    return {"html": out_html, "png": png, "dropped_rows": len(dropped)}


# ------------------------------------------------------------------ cluster maps

def _radius_px(n: pd.Series | float, n_max: float, lo: float = 4.0, hi: float = 26.0) -> pd.Series | float:
    return lo + (hi - lo) * np.sqrt(np.asarray(n, dtype=float) / n_max)


def _global_nmax(tables: dict[str, pd.DataFrame]) -> float:
    return float(max(t["n_trips"].max() for t in tables.values()))


def cluster_map_algorithm(algo: str, table: pd.DataFrame, extent: tuple, n_max: float,
                          out_html: str | Path, slices: list[str] | None = None) -> Path:
    """cluster_map_<algo>.html: 3 lop lat cat; cung extent + thang kich thuoc."""
    import folium

    slices = slices or SLICE_ORDER
    lat0, lon0, lat1, lon1 = extent
    m = folium.Map(location=[(lat0 + lat1) / 2, (lon0 + lon1) / 2], zoom_start=10, tiles=None, control_scale=True)
    folium.TileLayer("OpenStreetMap", name="Nền OSM (cần Internet)", show=True).add_to(m)
    folium.TileLayer(tiles="", attr="không nền (offline)", name="Không nền (offline)", show=False).add_to(m)
    col = ALGO_COLOR[algo]
    for i, s in enumerate(slices):
        sub = table[table["time_slice"] == s].sort_values("n_trips", ascending=False).reset_index(drop=True)
        if sub.empty:
            continue
        noise = int(sub["noise_trips"].iloc[0]); nshare = float(sub["noise_share"].iloc[0])
        fg = folium.FeatureGroup(name=f"{SLICE_SHORT[s]} — {len(sub)} cụm · noise {fmt_pct(nshare)}", show=(i == 0))
        for rank, r in enumerate(sub.itertuples(index=False), start=1):
            rad_m = float(r.radius_rms_m)
            if rad_m > 0:   # vong ban kinh RMS (don vi met) — KHONG phai ranh gioi cum
                folium.Circle((r.center_lat, r.center_lon), radius=rad_m, color=col, weight=1, fill=False,
                              dash_array="4,4", opacity=0.6).add_to(fg)
            folium.CircleMarker(
                (r.center_lat, r.center_lon), radius=float(_radius_px(r.n_trips, n_max)),
                color="#222", weight=0.8, fill=True, fill_color=col, fill_opacity=0.55,
                tooltip=(f"{algo_label(algo)} · {SLICE_SHORT[s]} · cụm {int(r.cluster)} (hạng {rank}) · "
                         f"{int(r.n_trips):,} chuyến · {r.share * 100:.1f}% · BK RMS {rad_m / 1000:.2f} km · "
                         f"khu vực {r.top_community_area}")).add_to(fg)
            if rank <= 8 or len(sub) <= 8:
                folium.Marker((r.center_lat, r.center_lon), icon=folium.DivIcon(
                    html=f'<div style="font:bold 14px sans-serif;color:#000;transform:translate(-5px,-9px)">+</div>'),
                    tooltip=f"tâm cụm {int(r.cluster)}").add_to(fg)
        fg.add_to(m)
    m.fit_bounds([[lat0, lon0], [lat1, lon1]])
    folium.LayerControl(collapsed=False).add_to(m)
    legend = (f"<b>{algo_label(algo)} — hotspot nhu cầu đón, master_v1</b><br>"
              f"Chấm = tâm cụm (centroid), diện tích ∝ số chuyến; <b>+</b> = tâm cụm (8 cụm lớn nhất); "
              f"vòng nét đứt = bán kính RMS quanh tâm (không phải ranh giới cụm).<br>"
              f"Điểm nhiễu (nhãn −1) KHÔNG được vẽ là hotspot; tỷ lệ noise ghi ở tên lớp. "
              f"{CENTROID_CAVEAT}<br><i>{SOURCE_NOTE}</i>")
    m.get_root().html.add_child(folium.Element(
        f'<div style="position:fixed;bottom:48px;left:10px;z-index:9999;background:rgba(255,255,255,.94);'
        f'padding:6px 10px;border:1px solid #999;font:12px/1.35 sans-serif;'
        f'max-width:min(520px,calc(100% - 20px));box-sizing:border-box">{legend}</div>'))
    out_html = Path(out_html)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(out_html))
    return out_html


def cluster_map_comparison(tables: dict[str, pd.DataFrame], extent: tuple, n_max: float, out_html: str | Path,
                           time_slice: str = "WEEKDAY_PM") -> Path:
    """Mot ban do, 3 lop (K-Means / DBSCAN / HDBSCAN) cung lat cat, bat/tat bang LayerControl."""
    import folium

    lat0, lon0, lat1, lon1 = extent
    m = folium.Map(location=[(lat0 + lat1) / 2, (lon0 + lon1) / 2], zoom_start=10, tiles=None, control_scale=True)
    folium.TileLayer("OpenStreetMap", name="Nền OSM (cần Internet)", show=True).add_to(m)
    folium.TileLayer(tiles="", attr="không nền (offline)", name="Không nền (offline)", show=False).add_to(m)
    for i, a in enumerate(ALGO_ORDER):
        sub = tables[a][tables[a]["time_slice"] == time_slice]
        fg = folium.FeatureGroup(name=f"{algo_label(a)} — {len(sub)} cụm", show=True)
        for r in sub.sort_values("n_trips", ascending=False).itertuples(index=False):
            folium.CircleMarker(
                (r.center_lat, r.center_lon), radius=float(_radius_px(r.n_trips, n_max)),
                color=ALGO_COLOR[a], weight=1.6, fill=True, fill_color=ALGO_COLOR[a], fill_opacity=0.28,
                tooltip=(f"{algo_label(a)} · cụm {int(r.cluster)} · {int(r.n_trips):,} chuyến · "
                         f"{r.share * 100:.1f}% · BK RMS {float(r.radius_rms_m) / 1000:.2f} km")).add_to(fg)
        fg.add_to(m)
    m.fit_bounds([[lat0, lon0], [lat1, lon1]])
    folium.LayerControl(collapsed=False).add_to(m)
    swatch = "".join(f'<span style="color:{ALGO_COLOR[a]}">●</span> {algo_label(a)} &nbsp;' for a in ALGO_ORDER)
    legend = (f"<b>So sánh tâm cụm 3 thuật toán — {SLICE_LABEL[time_slice]}</b><br>{swatch}<br>"
              f"Cùng tập chuyến, cùng extent, cùng thang diện tích (∝ số chuyến). Bật/tắt lớp ở góc trên phải để xem "
              f"nơi 3 thuật toán đồng thuận (tâm cụm trùng nhau) hoặc khác biệt. "
              f"Noise không được vẽ. {CENTROID_CAVEAT}<br><i>{SOURCE_NOTE}</i>")
    m.get_root().html.add_child(folium.Element(
        f'<div style="position:fixed;bottom:48px;left:10px;z-index:9999;background:rgba(255,255,255,.94);'
        f'padding:6px 10px;border:1px solid #999;font:12px/1.35 sans-serif;'
        f'max-width:min(520px,calc(100% - 20px));box-sizing:border-box">{legend}</div>'))
    out_html = Path(out_html)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(out_html))
    return out_html


def _draw_panel(ax, table: pd.DataFrame, algo: str, s: str, lon_lim, lat_lim, n_max: float) -> None:
    from matplotlib.lines import Line2D  # noqa: F401

    sub = table[table["time_slice"] == s]
    col = ALGO_COLOR[algo]
    sub = sub.sort_values("n_trips", ascending=False)
    ax.scatter(sub["center_lon"], sub["center_lat"], s=20 + 900 * (sub["n_trips"] / n_max), c=col, alpha=0.5,
               edgecolor="#222", linewidth=0.6, zorder=3)
    ax.scatter(sub["center_lon"].head(8), sub["center_lat"].head(8), marker="+", s=60, c="#000", linewidth=1.2, zorder=4)
    ax.set_xlim(*lon_lim); ax.set_ylim(*lat_lim)
    ax.set_aspect(1 / np.cos(np.radians(41.88)))
    nshare = float(sub["noise_share"].iloc[0]) if len(sub) else 0.0
    ax.set_title(f"{algo_label(algo)} · {SLICE_SHORT[s]}\n{len(sub)} cụm · noise {fmt_pct(nshare)}", fontsize=11)
    ax.tick_params(labelsize=7)


def algorithm_comparison_png(tables: dict[str, pd.DataFrame], extent: tuple, n_max: float,
                             out_dir: str | Path, dpi: int = 300) -> list[Path]:
    """PNG tinh: algorithm_comparison.png (luoi 3x3) va algorithm_comparison_<slice>.png (1x3)."""
    import matplotlib.pyplot as plt

    apply_matplotlib_style()
    lat0, lon0, lat1, lon1 = extent
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    foot = (f"{SOURCE_NOTE}. Chấm = tâm cụm (centroid), diện tích ∝ số chuyến (cùng thang ở mọi ô); + = 8 cụm lớn nhất. "
            f"Noise không vẽ.\n{CENTROID_CAVEAT} Không nền bản đồ (bản offline); cùng extent mọi ô.")
    fig, axes = plt.subplots(3, 3, figsize=(15, 16))
    for i, s in enumerate(SLICE_ORDER):
        for j, a in enumerate(ALGO_ORDER):
            _draw_panel(axes[i, j], tables[a], a, s, (lon0, lon1), (lat0, lat1), n_max)
            if j > 0:
                axes[i, j].set_yticklabels([])
    fig.suptitle("Tâm cụm hotspot theo thuật toán × lát cắt — Chicago, master_v1", x=0.01, ha="left",
                 fontsize=15, fontweight="bold")
    fig.text(0.01, 0.0, foot, fontsize=9, color="#555", va="top")
    fig.tight_layout(rect=(0, 0.0, 1, 0.97))
    p = out_dir / "algorithm_comparison.png"
    fig.savefig(p, dpi=dpi); plt.close(fig); paths.append(p)
    for s in SLICE_ORDER:
        fig, axes = plt.subplots(1, 3, figsize=(17, 6.6))
        for j, a in enumerate(ALGO_ORDER):
            _draw_panel(axes[j], tables[a], a, s, (lon0, lon1), (lat0, lat1), n_max)
            if j > 0:
                axes[j].set_yticklabels([])
        fig.suptitle(f"So sánh tâm cụm 3 thuật toán — {SLICE_LABEL[s]}", x=0.01, ha="left", fontsize=14,
                     fontweight="bold")
        fig.text(0.01, 0.0, foot, fontsize=8.5, color="#555", va="top")
        fig.tight_layout(rect=(0, 0.04, 1, 0.94))
        p = out_dir / f"algorithm_comparison_{s}.png"
        fig.savefig(p, dpi=dpi); plt.close(fig); paths.append(p)
    return paths
