"""Bo style chung cho moi bieu do / ban do cua nhom (M4-02).

Chi dinh nghia mau, ten hien thi va ham dung chung. Khong tinh lai so lieu.
Quy uoc day du: docs/M4/visual_style_guide.md.

- Mau thuat toan: Okabe-Ito (an toan cho nguoi mu mau), cung mau o MOI hinh.
- Nhieu / noise: luon xam trung tinh, khong bao gio duoc to mau hotspot.
- Mau lat cat thoi gian khac ho mau thuat toan de khong nham hai khai niem.
"""
from __future__ import annotations

from typing import Iterable

ALGO_ORDER = ["kmeans", "dbscan", "hdbscan"]
ALGO_LABEL = {"kmeans": "K-Means", "dbscan": "DBSCAN", "hdbscan": "HDBSCAN"}
ALGO_COLOR = {"kmeans": "#0072B2", "dbscan": "#E69F00", "hdbscan": "#009E73"}

SLICE_ORDER = ["WEEKDAY_AM", "WEEKDAY_PM", "WEEKEND"]
SLICE_LABEL = {
    "WEEKDAY_AM": "Ngày thường sáng (T2–T6, 07–09h)",
    "WEEKDAY_PM": "Ngày thường chiều (T2–T6, 16–18h)",
    "WEEKEND": "Cuối tuần (T7–CN, cả ngày)",
}
SLICE_SHORT = {"WEEKDAY_AM": "AM", "WEEKDAY_PM": "PM", "WEEKEND": "Cuối tuần"}
SLICE_COLOR = {"WEEKDAY_AM": "#56B4E9", "WEEKDAY_PM": "#D55E00", "WEEKEND": "#CC79A7"}

NOISE_COLOR = "#B0B0B0"
TEXT_COLOR = "#222222"
GRID_COLOR = "#DDDDDD"

# Khung nhin chung cho MOI ban do (lat/lon) — tinh tu hop cac tam cum + toa do EDA.
# Dat ra ngoai de tat ca ban do dung chung mot extent (BA 2.5).
SOURCE_NOTE = "Nguồn: Chicago Taxi Trips (wrvz-psew), 17/04–14/05/2023; master_v1"
CENTROID_CAVEAT = ("Tọa độ là centroid của census tract/community area, KHÔNG phải GPS; "
                   "không đọc là vị trí giao lộ.")

FIG_DPI = 300          # PNG cho báo cáo / slide
FIG_DPI_PREVIEW = 120  # dùng khi chạy thử


def apply_matplotlib_style() -> None:
    """Dat rcParams cho moi hinh. Goi 1 lan dau notebook/script."""
    import matplotlib as mpl

    mpl.rcParams.update({
        "figure.dpi": 100,
        "savefig.dpi": FIG_DPI,
        "savefig.bbox": "tight",
        "font.family": "DejaVu Sans",          # co dau tieng Viet day du
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelsize": 11,
        "axes.edgecolor": "#888888",
        "axes.grid": True,
        "grid.color": GRID_COLOR,
        "grid.linewidth": 0.7,
        "axes.axisbelow": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
        "legend.fontsize": 10,
        "text.color": TEXT_COLOR,
        "axes.labelcolor": TEXT_COLOR,
        "xtick.color": TEXT_COLOR,
        "ytick.color": TEXT_COLOR,
    })


def plotly_layout(title: str, subtitle: str = "") -> dict:
    """Layout Plotly thong nhat (tieu de + nguon + font)."""
    t = f"<b>{title}</b>" + (f"<br><sup>{subtitle}</sup>" if subtitle else "")
    return dict(
        title=dict(text=t, x=0.01, xanchor="left"),
        font=dict(family="DejaVu Sans, Arial, sans-serif", size=13, color=TEXT_COLOR),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend=dict(orientation="h", y=-0.18),
        margin=dict(l=60, r=30, t=90, b=90),
    )


def algo_label(name: str) -> str:
    return ALGO_LABEL.get(name, name)


def sorted_algos(names: Iterable[str]) -> list[str]:
    """Sap theo thu tu K-Means, DBSCAN, HDBSCAN (thu tu co dinh o moi hinh)."""
    s = set(names)
    return [a for a in ALGO_ORDER if a in s] + sorted(s - set(ALGO_ORDER))


def fmt_int(n: float) -> str:
    """So nguyen co dau cham ngan cach nghin kieu Viet: 60498 -> 60.498."""
    return f"{int(round(n)):,}".replace(",", ".")


def fmt_pct(x: float, digits: int = 1) -> str:
    """0.1264 -> '12,6%'."""
    return f"{x * 100:.{digits}f}%".replace(".", ",")
