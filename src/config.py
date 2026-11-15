"""Doc va kiem tra file cau hinh thi nghiem (config/experiment.yaml).

Cach dung trong notebook (may ca nhan hoac Colab, notebook nam trong notebooks/):

    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path.cwd().parent))   # them goc repo vao sys.path
    from src.config import load_config, resolve_path
    cfg = load_config()
    input_file = resolve_path(cfg, "model_input")
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

CONFIG_REL = Path("config") / "experiment.yaml"
_DRIVE_RE = re.compile(r"^[A-Za-z]:")


def find_repo_root(start: str | Path | None = None) -> Path:
    """Di nguoc len tu `start` (mac dinh: thu muc hien tai) toi thu muc co config/experiment.yaml."""
    here = Path(start or Path.cwd()).resolve()
    for p in (here, *here.parents):
        if (p / CONFIG_REL).is_file():
            return p
    raise FileNotFoundError(f"Khong tim thay {CONFIG_REL} tu {here} tro len.")


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Doc YAML, kiem tra hop le, va gan khoa '_root' (goc repo) de giai duong dan."""
    if path is None:
        root = find_repo_root()
        path = root / CONFIG_REL
    else:
        path = Path(path).resolve()
        root = path.parent.parent
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise ValueError(f"{path}: noi dung khong phai mot bang YAML.")
    validate_config(cfg)
    cfg["_root"] = root
    return cfg


def resolve_path(cfg: dict[str, Any], key: str) -> Path:
    """Tra ve duong dan tuyet doi cho mot khoa trong muc `paths`."""
    return Path(cfg["_root"]) / cfg["paths"][key]


def slice_hours(slice_cfg: dict[str, Any]) -> list[int]:
    """Danh sach gio (0-23) cua mot lat cat; 'all' nghia la ca ngay."""
    hours = slice_cfg["hours"]
    return list(range(24)) if hours == "all" else list(hours)


# ---------------------------------------------------------------- kiem tra

def _is_int(x: Any) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _is_num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def validate_config(cfg: dict[str, Any]) -> None:
    """Gom moi loi roi bao mot lan bang ValueError. Khong sua cau hinh."""
    err: list[str] = []

    def need(section: str) -> dict[str, Any]:
        sec = cfg.get(section)
        if not isinstance(sec, dict):
            err.append(f"thieu muc '{section}'")
            return {}
        return sec

    # project
    pr = need("project")
    if pr:
        if not _is_int(pr.get("seed")):
            err.append("project.seed phai la so nguyen")
        if not str(pr.get("crs", "")).startswith("EPSG:"):
            err.append("project.crs phai co dang 'EPSG:xxxx'")
        feats = pr.get("features")
        if not (isinstance(feats, list) and feats and all(isinstance(f, str) for f in feats)):
            err.append("project.features phai la danh sach ten cot")

    # paths: tuong doi, khong co o dia, khong di ra ngoai repo
    pa = need("paths")
    for k, v in pa.items():
        if not isinstance(v, str) or not v:
            err.append(f"paths.{k} phai la chuoi")
            continue
        if _DRIVE_RE.match(v) or v.startswith(("/", "\\")) or Path(v).is_absolute():
            err.append(f"paths.{k} = '{v}' la duong dan tuyet doi; phai la duong dan tuong doi")
        if ".." in Path(v).parts:
            err.append(f"paths.{k} = '{v}' khong duoc chua '..'")

    # time_slices: hop le va khong chong lan
    ts = need("time_slices")
    seen: dict[tuple[int, int], str] = {}
    for name, sc in ts.items():
        if not isinstance(sc, dict):
            err.append(f"time_slices.{name} phai la bang")
            continue
        wd = sc.get("weekdays")
        if not (isinstance(wd, list) and wd and all(_is_int(d) and 0 <= d <= 6 for d in wd)):
            err.append(f"time_slices.{name}.weekdays phai la danh sach so 0-6")
            continue
        hrs = sc.get("hours")
        if hrs != "all" and not (
            isinstance(hrs, list) and hrs and all(_is_int(h) and 0 <= h <= 23 for h in hrs)
        ):
            err.append(f"time_slices.{name}.hours phai la 'all' hoac danh sach so 0-23")
            continue
        for d in wd:
            for h in slice_hours(sc):
                other = seen.get((d, h))
                if other and other != name:
                    err.append(f"time_slices {other} va {name} chong lan (thu {d}, gio {h})")
                    break
                seen[(d, h)] = name

    # sampling
    sa = need("sampling")
    if sa:
        pil = sa.get("pilot_sizes")
        if not (isinstance(pil, list) and pil and all(_is_int(n) and n > 0 for n in pil)):
            err.append("sampling.pilot_sizes phai la danh sach so nguyen duong")
        elif pil != sorted(pil):
            err.append("sampling.pilot_sizes phai tang dan")
        if not (_is_int(sa.get("target_size")) and sa["target_size"] > 0):
            err.append("sampling.target_size phai la so nguyen duong")

    # evaluation
    ev = need("evaluation")
    if ev:
        if not (_is_int(ev.get("silhouette_max_sample")) and ev["silhouette_max_sample"] > 1):
            err.append("evaluation.silhouette_max_sample phai la so nguyen > 1")
        if not (_is_int(ev.get("min_clusters_for_metrics")) and ev["min_clusters_for_metrics"] >= 2):
            err.append("evaluation.min_clusters_for_metrics phai >= 2")
        r = ev.get("ram_stop_ratio")
        if not (_is_num(r) and 0 < r <= 1):
            err.append("evaluation.ram_stop_ratio phai nam trong (0, 1]")

    # kmeans
    km = need("kmeans")
    if km:
        kmin, kmax = km.get("k_min"), km.get("k_max")
        if not (_is_int(kmin) and _is_int(kmax) and 2 <= kmin <= kmax):
            err.append("kmeans: can 2 <= k_min <= k_max (so nguyen)")
        if km.get("init") not in ("k-means++", "random"):
            err.append("kmeans.init phai la 'k-means++' hoac 'random'")
        for k in ("n_init", "max_iter"):
            if not (_is_int(km.get(k)) and km[k] >= 1):
                err.append(f"kmeans.{k} phai la so nguyen >= 1")

    # dbscan
    db = need("dbscan")
    if db:
        eps = db.get("eps_m")
        if not (isinstance(eps, list) and eps and all(_is_num(e) and e > 0 for e in eps)):
            err.append("dbscan.eps_m phai la danh sach so duong (met)")
        ms = db.get("min_samples")
        if not (isinstance(ms, list) and ms and all(_is_int(m) and m >= 2 for m in ms)):
            err.append("dbscan.min_samples phai la danh sach so nguyen >= 2")
        fr = db.get("min_samples_frac")
        if fr is not None and not (isinstance(fr, list) and fr and all(_is_num(f) and 0 < f < 1 for f in fr)):
            err.append("dbscan.min_samples_frac phai la danh sach so trong (0, 1)")
        if db.get("mode", "weighted") not in ("weighted", "full"):
            err.append("dbscan.mode phai la 'weighted' hoac 'full'")
        if not isinstance(db.get("metric"), str):
            err.append("dbscan.metric phai la chuoi")
        if not _is_int(db.get("n_jobs")):
            err.append("dbscan.n_jobs phai la so nguyen")

    if err:
        raise ValueError("Cau hinh khong hop le:\n- " + "\n- ".join(err))
