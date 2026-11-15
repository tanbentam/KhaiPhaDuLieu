"""Hinh minh hoa nguyen ly K-Means va DBSCAN cho slide (du lieu do choi 2D, khong phai du lieu that).

Dung:
    from src.visualization.illustrations import kmeans_steps_figure, dbscan_points_figure
    kmeans_steps_figure("outputs/figures/slide_kmeans_nguyen_ly.png")
    dbscan_points_figure("outputs/figures/slide_dbscan_nguyen_ly.png")
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c"]


def _toy_blobs(seed: int = 3) -> np.ndarray:
    rng = np.random.default_rng(seed)
    centers = np.array([[2.0, 2.0], [7.0, 2.5], [4.5, 7.0]])
    return np.vstack([c + rng.normal(0, 0.9, (25, 2)) for c in centers])


def kmeans_steps_figure(out_png: str | Path, seed: int = 3) -> Path:
    """3 o: (1) khoi tao tam, (2) gan diem vao tam gan nhat, (3) cap nhat tam = trung binh, lap lai."""
    import matplotlib.pyplot as plt

    X = _toy_blobs(seed)
    mu0 = np.array([[1.0, 6.5], [3.5, 1.0], [5.0, 4.0]])            # tam khoi tao (co y dat lech)
    lab = np.argmin(((X[:, None, :] - mu0[None]) ** 2).sum(-1), axis=1)
    mu1 = np.array([X[lab == k].mean(0) for k in range(3)])

    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2))
    titles = ["1. Khởi tạo K = 3 tâm", "2. Gán: mỗi điểm về tâm gần nhất", "3. Cập nhật: tâm = trung bình cụm"]
    for ax, t in zip(axes, titles):
        ax.set_title(t, fontsize=12); ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect("equal")
        ax.set_xlim(-1, 10); ax.set_ylim(-1, 10)
    axes[0].scatter(X[:, 0], X[:, 1], c="#999999", s=22)
    for ax in axes[1:]:
        ax.scatter(X[:, 0], X[:, 1], c=[COLORS[k] for k in lab], s=22)
    for k in range(3):
        for ax in axes[:2]:
            ax.scatter(*mu0[k], marker="X", s=260, c=COLORS[k], edgecolors="k", linewidths=1.2, zorder=3)
        axes[2].scatter(*mu0[k], marker="X", s=180, c="white", edgecolors=COLORS[k], linewidths=1.5, zorder=3)
        axes[2].scatter(*mu1[k], marker="X", s=260, c=COLORS[k], edgecolors="k", linewidths=1.2, zorder=4)
        axes[2].annotate("", xy=mu1[k], xytext=mu0[k], arrowprops=dict(arrowstyle="->", color="k", lw=1.3))
    fig.text(0.5, 0.02, "Lặp bước 2-3 tới khi tâm không đổi. Mục tiêu: nhỏ nhất tổng bình phương khoảng cách tới tâm (SSE). "
             "Mọi điểm đều phải thuộc một cụm.", ha="center", fontsize=10)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.88, bottom=0.1, wspace=0.08)
    out_png = Path(out_png); out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200); plt.close(fig)
    return out_png


def dbscan_points_figure(out_png: str | Path, eps: float = 1.0, min_samples: int = 4, seed: int = 7) -> Path:
    """Diem core / border / noise cua DBSCAN that (sklearn) tren du lieu do choi, ve vong eps minh hoa."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    from sklearn.cluster import DBSCAN

    rng = np.random.default_rng(seed)
    dense = np.vstack([[2.5, 3.0] + rng.normal(0, 0.45, (14, 2)), [6.5, 5.5] + rng.normal(0, 0.5, (12, 2))])
    edge = np.array([[3.6, 3.9], [7.6, 6.4]])                        # diem bien du kien
    sparse = np.array([[0.6, 7.6], [8.8, 1.2], [5.0, 1.0], [4.6, 8.4]])  # diem le
    X = np.vstack([dense, edge, sparse])
    db = DBSCAN(eps=eps, min_samples=min_samples).fit(X)
    core = np.zeros(len(X), bool); core[db.core_sample_indices_] = True
    lab = db.labels_
    border = (lab != -1) & ~core
    noise = lab == -1

    fig, ax = plt.subplots(figsize=(9.2, 6))
    for k in sorted(set(lab) - {-1}):
        m = (lab == k) & core
        ax.scatter(X[m, 0], X[m, 1], s=70, c=COLORS[k % 3], edgecolors="k", linewidths=.6, zorder=3,
                   label=f"core - cụm {k}")
        m = (lab == k) & border
        if m.any():                                    # chi them chu giai khi cum co diem border
            ax.scatter(X[m, 0], X[m, 1], s=70, facecolors="white", edgecolors=COLORS[k % 3], linewidths=2, zorder=3,
                       label=f"border - cụm {k}")
    ax.scatter(X[noise, 0], X[noise, 1], s=80, marker="x", c="#555555", linewidths=2, zorder=3, label="noise (nhãn -1)")
    # vong eps quanh 1 diem core va 1 diem border
    ci = np.where(core)[0][0]
    ax.add_patch(Circle(X[ci], eps, fill=False, ls="--", lw=1.4, color="k"))
    ax.annotate(f"core: ≥ {min_samples} điểm trong eps", X[ci] + [0, -eps - .35], ha="center", fontsize=9)
    if border.any():
        bi = np.where(border)[0][0]
        ax.add_patch(Circle(X[bi], eps, fill=False, ls=":", lw=1.4, color=COLORS[lab[bi] % 3]))
        ax.annotate("border: < min_samples,\nnhưng nằm trong eps của 1 core", X[bi] + [-1.2, eps + .25],
                    ha="center", fontsize=9)
    ni = np.where(noise)[0][0]
    ax.annotate("noise: không thuộc cụm nào", X[ni] + [0.2, -0.5], fontsize=9)
    ax.set_title(f"DBSCAN: eps = {eps}, min_samples = {min_samples}", fontsize=12)
    ax.set_xlim(-0.5, 10); ax.set_ylim(-0.3, 9.5); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=9, frameon=False)   # dat ngoai khung, khong de len diem
    fig.text(0.5, 0.01, "Cụm = các điểm core nối liền nhau trong bán kính eps, cộng các điểm border. Không cần chọn trước số cụm.",
             ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    out_png = Path(out_png); out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200); plt.close(fig)
    return out_png
