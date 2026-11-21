"""Hop nhat metrics va ve bieu do so sanh (M4-05, H05).

M4 CHI hop nhat va the hien: khong tinh lai, khong noi suy. Moi gia tri truy ve
mot run_id trong CSV nguon (baseline_metrics.csv cua M2, hdbscan_metrics.csv cua M3).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .style import (ALGO_COLOR, ALGO_ORDER, SLICE_COLOR, SLICE_ORDER, SLICE_SHORT, SLICE_LABEL,
                    SOURCE_NOTE, CENTROID_CAVEAT, algo_label, apply_matplotlib_style, fmt_int, plotly_layout)

METRICS_DIR = Path("outputs") / "metrics"
FIG_DIR = Path("outputs") / "figures" / "comparison"
MAP_DIR = Path("outputs") / "maps"

# Cot bat buoc cua bang H05 (28 cot RUN_LOG_COLUMNS) — kiem tra schema truoc khi concat.
REQUIRED_COLS = [
    "run_id", "member", "algorithm", "time_slice", "sample_id", "n_points", "params",
    "n_clusters", "n_noise", "noise_ratio", "coverage", "size_min", "size_median", "size_max",
    "largest_share", "silhouette", "davies_bouldin", "calinski_harabasz", "n_points_metric",
    "runtime_fit_sec", "peak_mem_mb",
]


def merge_metrics(root: str | Path = ".") -> pd.DataFrame:
    """H05: noi baseline_metrics.csv (M2) + hdbscan_metrics.csv (M3) -> metrics_comparison.csv.

    Kiem tra: cung schema, cung sample_id, cung n_points theo lat cat (cung tap trip_id),
    khong trung run_id. Neu sai thi bao loi — KHONG tu sua gia tri (tra ve cho M2/M3).
    Ghi them 3 cot dien giai (khong thay gia tri goc): `weighted_fit`, `metric_scope`, `comparable_runtime`.
    """
    root = Path(root)
    base = pd.read_csv(root / METRICS_DIR / "baseline_metrics.csv")
    hdb = pd.read_csv(root / METRICS_DIR / "hdbscan_metrics.csv")
    if list(base.columns) != list(hdb.columns):
        raise ValueError("baseline_metrics.csv va hdbscan_metrics.csv khac schema; tra ve M2/M3.")
    miss = [c for c in REQUIRED_COLS if c not in base.columns]
    if miss:
        raise ValueError(f"Thieu cot bat buoc: {miss}")
    df = pd.concat([base, hdb], ignore_index=True)
    if df["run_id"].duplicated().any():
        raise ValueError("run_id bi trung trong bang gop.")
    if df["sample_id"].nunique() != 1:
        raise ValueError(f"Nhieu sample_id trong bang chinh: {df['sample_id'].unique()}")
    npts = df.groupby("time_slice")["n_points"].nunique()
    if (npts > 1).any():
        raise ValueError(f"n_points khac nhau giua thuat toan trong cung lat cat:\n{npts}")

    def _weighted(p: str) -> str:
        try:
            return str(json.loads(p).get("mode", "unweighted"))
        except Exception:  # noqa: BLE001
            return "unknown"

    df["weighted_fit"] = df["params"].map(_weighted)          # weighted = fit tren toa do duy nhat
    df["metric_scope"] = np.where(df["noise_ratio"] > 0, "clustered_only", "all_points")
    # Runtime chi so sanh truc tiep duoc khi cung che do fit (BA 2.4: cung sample, cung cach do).
    df["comparable_runtime"] = df.groupby("time_slice")["weighted_fit"].transform("nunique").eq(1)
    df["algorithm"] = pd.Categorical(df["algorithm"], ALGO_ORDER, ordered=True)
    df["time_slice"] = pd.Categorical(df["time_slice"], SLICE_ORDER, ordered=True)
    df = df.sort_values(["time_slice", "algorithm"]).reset_index(drop=True)
    df["algorithm"] = df["algorithm"].astype(str)
    df["time_slice"] = df["time_slice"].astype(str)
    return df


def write_metrics_comparison(root: str | Path = ".") -> Path:
    df = merge_metrics(root)
    out = Path(root) / METRICS_DIR / "metrics_comparison.csv"
    df.to_csv(out, index=False)
    return out


# --------------------------------------------------------------------------- PNG

def _footer(fig, text: str) -> None:
    fig.text(0.01, -0.02, text, fontsize=8.5, color="#555555", ha="left", va="top", wrap=True)


def runtime_noise_figure(df: pd.DataFrame, out_png: str | Path, dpi: int = 300) -> Path:
    """Small multiples: Runtime | Noise Ratio | So cum | Silhouette (clustered-only) + Coverage."""
    import matplotlib.pyplot as plt

    apply_matplotlib_style()
    fig, axes = plt.subplots(1, 5, figsize=(21, 5.2))
    algos = [a for a in ALGO_ORDER if a in set(df["algorithm"])]
    x = np.arange(len(SLICE_ORDER))
    w = 0.8 / len(algos)

    def bars(ax, col, scale=1.0, log=False, fmt="{:.1f}", title="", ylabel=""):
        for i, a in enumerate(algos):
            vals = [df[(df.algorithm == a) & (df.time_slice == s)][col].iloc[0] * scale for s in SLICE_ORDER]
            b = ax.bar(x + (i - (len(algos) - 1) / 2) * w, vals, w * 0.92, color=ALGO_COLOR[a],
                       label=algo_label(a))
            for rect, v in zip(b, vals):
                ax.annotate(fmt.format(v), (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                            ha="center", va="bottom", fontsize=8, xytext=(0, 2), textcoords="offset points")
        ax.set_xticks(x, [SLICE_SHORT[s] for s in SLICE_ORDER])
        ax.set_title(title, fontsize=12)
        ax.set_ylabel(ylabel)
        if log:
            ax.set_yscale("log")
        ax.margins(y=0.15)

    bars(axes[0], "runtime_fit_sec", log=True, fmt="{:.2f}", title="Runtime fit (log)", ylabel="giây")
    bars(axes[1], "noise_ratio", scale=100, fmt="{:.1f}", title="Noise Ratio", ylabel="% điểm nhãn −1")
    bars(axes[2], "n_clusters", fmt="{:.0f}", title="Số cụm", ylabel="cụm")
    bars(axes[3], "silhouette", fmt="{:.2f}", title="Silhouette (chỉ điểm có nhãn)", ylabel="[−1, 1]")
    axes[3].set_ylim(0, 1.15)
    bars(axes[4], "coverage", scale=100, fmt="{:.1f}", title="Coverage = 1 − Noise Ratio", ylabel="% điểm có nhãn cụm")
    axes[4].set_ylim(0, 112)
    axes[0].legend(loc="upper left", ncol=1)
    fig.suptitle("So sánh 3 thuật toán trên master_v1 — runtime, noise, số cụm, Silhouette",
                 x=0.01, ha="left", fontsize=14, fontweight="bold")
    _footer(fig, (SOURCE_NOTE + ". Cùng tập trip_id mỗi lát cắt (n = " +
                  ", ".join(f"{SLICE_SHORT[s]} {fmt_int(df[df.time_slice == s].n_points.iloc[0])}" for s in SLICE_ORDER) +
                  ").\nK-Means: Noise = 0 theo thiết kế (ép mọi điểm vào cụm), KHÔNG phải ưu điểm. "
                  "Silhouette chỉ tính trên điểm có nhãn → đọc cùng Coverage (ô bên phải).\n"
                  "Runtime: K-Means/DBSCAN fit weighted trên tọa độ duy nhất; HDBSCAN fit trên toàn bộ điểm "
                  "(thư viện không hỗ trợ sample_weight) → chênh lệch phản ánh cách fit, không chỉ thuật toán.\n"
                  "Nguồn số liệu: outputs/metrics/metrics_comparison.csv (9 run_id)."))
    fig.tight_layout(rect=(0, 0.0, 1, 0.94))
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=dpi)
    plt.close(fig)
    return out_png


def temporal_comparison_figure(clusters: pd.DataFrame, tracking: pd.DataFrame, out_png: str | Path,
                               dpi: int = 300) -> Path:
    """HDBSCAN: (a) so cum + (b) cum lon nhat theo lat cat, (c) phan bo khoang dich chuyen cua cac cap MATCHED.

    Chi the hien bang M3 da phat hanh (hdbscan_clusters_master_v1.csv, hotspot_tracking.csv).
    """
    import matplotlib.pyplot as plt

    apply_matplotlib_style()
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.2))
    g = clusters.groupby("time_slice")
    # (a) so cum va tong chuyen thuoc cum
    ax = axes[0]
    ncl = [int(g.get_group(s)["cluster"].nunique()) for s in SLICE_ORDER]
    bars = ax.bar([SLICE_SHORT[s] for s in SLICE_ORDER], ncl, color=[SLICE_COLOR[s] for s in SLICE_ORDER])
    for r, v in zip(bars, ncl):
        ax.annotate(str(v), (r.get_x() + r.get_width() / 2, v), ha="center", va="bottom", xytext=(0, 2),
                    textcoords="offset points")
    ax.set_title("Số cụm HDBSCAN theo lát cắt")
    ax.set_ylabel("cụm")
    ax.margins(y=0.15)
    # (b) top-5 cum: share theo lat cat (khong ghep nhan; chi dung hotspot_tracking de ghep)
    ax = axes[1]
    top = []
    for s in SLICE_ORDER:
        sub = g.get_group(s).nlargest(5, "n_trips")
        top.append(sub["share"].sum() * 100)
    bars = ax.bar([SLICE_SHORT[s] for s in SLICE_ORDER], top, color=[SLICE_COLOR[s] for s in SLICE_ORDER])
    for r, v in zip(bars, top):
        ax.annotate(f"{v:.1f}%", (r.get_x() + r.get_width() / 2, v), ha="center", va="bottom",
                    xytext=(0, 2), textcoords="offset points")
    ax.set_title("Tỷ trọng 5 cụm lớn nhất")
    ax.set_ylabel("% tổng chuyến của lát cắt")
    ax.margins(y=0.15)
    # (c) phan bo khoang dich chuyen (MATCHED): 0 m / <=200 m / 200-1000 m / >1000 m
    ax = axes[2]
    matched = tracking[tracking["status"] == "MATCHED"]
    trans = [t for t in ["WEEKDAY_AM -> WEEKDAY_PM", "WEEKDAY_PM -> WEEKEND", "WEEKDAY_AM -> WEEKEND"]
             if t in set(matched["transition"])]
    bins = [("= 0 m (cùng centroid)", lambda d: d == 0, "#BBBBBB"),
            ("0–200 m", lambda d: (d > 0) & (d <= 200), "#9ECAE1"),
            ("200–1000 m", lambda d: (d > 200) & (d <= 1000), "#4292C6"),
            ("> 1000 m", lambda d: d > 1000, "#08519C")]
    bottom = np.zeros(len(trans))
    for name, fn, colr in bins:
        vals = np.array([fn(matched[matched.transition == t]["shift_distance_m"].to_numpy()).mean() * 100
                         for t in trans])
        ax.bar(range(len(trans)), vals, bottom=bottom, color=colr, label=name, edgecolor="white")
        for i, (v, b0) in enumerate(zip(vals, bottom)):
            if v >= 6:
                ax.text(i, b0 + v / 2, f"{v:.0f}%", ha="center", va="center", fontsize=9,
                        color="white" if colr in ("#4292C6", "#08519C") else "#222")
        bottom += vals
    ax.set_xticks(range(len(trans)), [f"{t.replace(' -> ', ' → ').replace('WEEKDAY_', '')}\n(n={int((matched.transition == t).sum())} cặp)"
                                      for t in trans])
    ax.set_ylim(0, 100)
    ax.set_title("Dịch chuyển tâm cụm (cặp MATCHED)")
    ax.set_ylabel("% số cặp")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, fontsize=8.5)
    fig.suptitle("HDBSCAN theo lát cắt thời gian — quy mô và dịch chuyển hotspot", x=0.01, ha="left",
                 fontsize=14, fontweight="bold")
    _footer(fig, (SOURCE_NOTE + ". Ghép cụm giữa các lát cắt theo khoảng cách centroid (không so nhãn 0/1/2).\n"
                  "Hơn nửa số cặp có dịch chuyển = 0 m vì cụm HDBSCAN thường trùng đúng 1 tọa độ centroid "
                  "(tọa độ rời rạc) → '0 m' là giới hạn độ phân giải, không phải bằng chứng hotspot đứng yên tuyệt đối.\n"
                  "Dịch chuyển là mô tả vị trí tâm cụm, không phải nguyên nhân hay mức ùn tắc. "
                  "Nguồn: hdbscan_clusters_master_v1.csv, hotspot_tracking.csv."))
    fig.tight_layout(rect=(0, 0.0, 1, 0.94))
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=dpi)
    plt.close(fig)
    return out_png


# --------------------------------------------------------------------------- Plotly

def comparison_plotly(df: pd.DataFrame, out_html: str | Path) -> Path:
    """cluster_comparison.html: 4 bieu do tuong tac (hover co run_id)."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    algos = [a for a in ALGO_ORDER if a in set(df["algorithm"])]
    specs = [("runtime_fit_sec", "Runtime fit (giây, log)", True, 1.0),
             ("noise_ratio", "Noise Ratio (%)", False, 100.0),
             ("n_clusters", "Số cụm", False, 1.0),
             ("silhouette", "Silhouette (chỉ điểm có nhãn)", False, 1.0)]
    fig = make_subplots(rows=2, cols=2, subplot_titles=[s[1] for s in specs], vertical_spacing=0.18)
    for k, (col, _title, log, scale) in enumerate(specs):
        r, c = divmod(k, 2)
        for a in algos:
            sub = df[df.algorithm == a].set_index("time_slice").reindex(SLICE_ORDER)
            fig.add_trace(go.Bar(
                x=[SLICE_SHORT[s] for s in SLICE_ORDER], y=sub[col] * scale, name=algo_label(a),
                marker_color=ALGO_COLOR[a], legendgroup=a, showlegend=(k == 0),
                customdata=np.stack([sub["run_id"], sub["coverage"] * 100, sub["n_points_metric"]], axis=-1),
                hovertemplate=("%{x}<br>" + algo_label(a) + ": %{y:.3g}<br>coverage %{customdata[1]:.1f}%"
                               "<br>n điểm tính metric: %{customdata[2]:,}<br>run_id: %{customdata[0]}<extra></extra>"),
            ), row=r + 1, col=c + 1)
        if log:
            fig.update_yaxes(type="log", row=r + 1, col=c + 1)
    lay = plotly_layout("So sánh 3 thuật toán trên master_v1",
                        "Cùng tập trip_id mỗi lát cắt · Silhouette chỉ tính trên điểm có nhãn, đọc cùng coverage "
                        "(hover) · K-Means noise = 0 là do thiết kế")
    fig.update_layout(barmode="group", height=760, **lay)
    fig.add_annotation(text=(SOURCE_NOTE + ". " + CENTROID_CAVEAT +
                             " Runtime: HDBSCAN fit trên toàn bộ điểm, K-Means/DBSCAN fit weighted "
                             "trên tọa độ duy nhất → không so trực tiếp. Nguồn: metrics_comparison.csv."),
                       xref="paper", yref="paper", x=0, y=-0.14, showarrow=False, align="left",
                       font=dict(size=10, color="#555"))
    out_html = Path(out_html)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out_html), include_plotlyjs=True, full_html=True)
    return out_html
