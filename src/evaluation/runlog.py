"""Do thoi gian / RAM khi fit va ghi log moi lan chay (dung chung cho M2 va M3).

Dinh dang file theo de xuat docs/dinh-dang-du-lieu.md:
- Nhan:  outputs/labels/<run_id>.parquet   (trip_id, label, probability)
- Log:   outputs/metrics/run_log.csv       (moi lan fit them 1 dong, khong sua dong cu)

Cach dung nhanh:
    from sklearn.cluster import DBSCAN
    from src.config import load_config
    from src.evaluation.runlog import run_and_log
    cfg = load_config()
    params = {"eps": 350, "min_samples": 10}
    row = run_and_log(cfg, "dbscan", lambda X: DBSCAN(**params).fit_predict(X),
                      X, trip_ids, member="M2", time_slice="WEEKDAY_AM",
                      sample_id="sample_v1", params=params)
"""
from __future__ import annotations

import csv
import json
import os
import platform
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import psutil

from .metrics import evaluate

RUN_LOG_COLUMNS = [
    "run_id", "timestamp", "member", "algorithm", "time_slice", "sample_id",
    "n_points", "params",
    "n_clusters", "n_noise", "noise_ratio", "coverage",
    "size_min", "size_median", "size_max", "largest_share",
    "silhouette", "davies_bouldin", "calinski_harabasz",
    "n_points_metric", "silhouette_sample",
    "runtime_fit_sec", "peak_mem_mb", "mem_delta_mb",
    "machine", "lib_versions", "git_commit", "note",
]

_MB = 1024 * 1024


# ---------------------------------------------------------------- do tai nguyen

def measure(fn: Callable[[], Any], interval: float = 0.02) -> tuple[Any, float, float, float]:
    """Chay fn(), tra ve (ket qua, runtime_sec, peak_mem_mb, mem_delta_mb).

    peak_mem_mb : RSS lon nhat cua tien trinh trong luc fn() chay (MB).
    mem_delta_mb: peak - RSS truoc khi chay, tuc phan RAM fn() dung them.
    RSS duoc lay mau moi `interval` giay bang mot luong phu; fn() qua ngan
    (< interval) van co mau truoc va sau nen khong bi bo trong.
    """
    proc = psutil.Process()
    base = proc.memory_info().rss
    peak = [base]
    stop = threading.Event()

    def sampler() -> None:
        while not stop.is_set():
            try:
                rss = proc.memory_info().rss
            except psutil.Error:
                break
            if rss > peak[0]:
                peak[0] = rss
            stop.wait(interval)

    th = threading.Thread(target=sampler, daemon=True)
    th.start()
    t0 = time.perf_counter()
    try:
        result = fn()
    finally:
        runtime = time.perf_counter() - t0
        stop.set()
        th.join()
    peak[0] = max(peak[0], proc.memory_info().rss)
    return result, runtime, peak[0] / _MB, (peak[0] - base) / _MB


def system_ram_ratio() -> float:
    """Ty le RAM he thong dang dung (0-1). Dung de dung tang co mau khi vuot nguong."""
    return psutil.virtual_memory().percent / 100.0


# ---------------------------------------------------------------- thong tin moi truong

def machine_info() -> str:
    """Ten may ngan gon. Dat bien moi truong KPDL_MACHINE de tu dat ten (vd Tan-R7-7840H-16GB)."""
    if os.environ.get("KPDL_MACHINE"):
        return os.environ["KPDL_MACHINE"]
    prefix = "colab" if "google.colab" in sys.modules else platform.system().lower()
    ram_gb = round(psutil.virtual_memory().total / 1024**3)
    return f"{prefix}-{psutil.cpu_count(logical=True)}t-{ram_gb}GB"


def lib_versions() -> str:
    import sklearn
    vers = {"python": platform.python_version(), "numpy": np.__version__, "sklearn": sklearn.__version__}
    try:
        from importlib.metadata import version
        vers["hdbscan"] = version("hdbscan")
    except Exception:
        pass
    return json.dumps(vers, sort_keys=True)


def git_commit(root: str | Path | None = None) -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root,
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or None if out.returncode == 0 else None
    except Exception:
        return None


# ---------------------------------------------------------------- run_id, nhan, log

def make_run_id(algorithm: str, time_slice: str, labels_dir: str | Path | None = None,
                now: datetime | None = None) -> str:
    """<thuat_toan>_<time_slice>_<YYYYMMDD-HHMMSS>; them -2, -3... neu trung file nhan da co."""
    base = f"{algorithm}_{time_slice}_{(now or datetime.now()).strftime('%Y%m%d-%H%M%S')}"
    if labels_dir is None:
        return base
    run_id, i = base, 2
    while (Path(labels_dir) / f"{run_id}.parquet").exists():
        run_id, i = f"{base}-{i}", i + 1
    return run_id


def save_labels(labels_dir: str | Path, run_id: str, trip_ids: Any, labels: Any,
                probability: Any = None) -> Path:
    labels = np.asarray(labels)
    trip_ids = np.asarray(trip_ids)
    if trip_ids.shape[0] != labels.shape[0]:
        raise ValueError(f"So trip_id ({trip_ids.shape[0]}) khac so nhan ({labels.shape[0]})")
    df = pd.DataFrame({
        "trip_id": trip_ids.astype(str),
        "label": labels.astype("int32"),
        "probability": (np.asarray(probability, dtype="float32") if probability is not None
                        else pd.array([pd.NA] * len(labels), dtype="Float32")),
    })
    path = Path(labels_dir) / f"{run_id}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return path


def _fmt(v: Any) -> Any:
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, sort_keys=True, ensure_ascii=True)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return "" if np.isnan(v) else repr(float(v))
    return v


def log_run(log_path: str | Path, row: dict[str, Any]) -> None:
    """Them 1 dong vao run_log.csv. Bao loi neu co cot la hoac header file cu khac chuan."""
    unknown = set(row) - set(RUN_LOG_COLUMNS)
    if unknown:
        raise ValueError(f"Cot khong co trong RUN_LOG_COLUMNS: {sorted(unknown)}")
    if not row.get("run_id"):
        raise ValueError("Thieu run_id")
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not log_path.exists() or log_path.stat().st_size == 0
    if not new_file:
        with open(log_path, encoding="utf-8", newline="") as f:
            header = next(csv.reader(f), [])
        if header != RUN_LOG_COLUMNS:
            raise ValueError(f"Header cua {log_path} khac RUN_LOG_COLUMNS; khong ghi de de tranh hong file")
    with open(log_path, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RUN_LOG_COLUMNS)
        if new_file:
            w.writeheader()
        w.writerow({c: _fmt(row.get(c)) for c in RUN_LOG_COLUMNS})


def read_run_log(log_path: str | Path) -> pd.DataFrame:
    return pd.read_csv(log_path, encoding="utf-8")


# ---------------------------------------------------------------- tron goi

def run_and_log(
    cfg: dict[str, Any],
    algorithm: str,
    fit_fn: Callable[[np.ndarray], Any],
    X: Any,
    trip_ids: Any,
    *,
    member: str,
    time_slice: str,
    sample_id: str,
    params: dict[str, Any],
    note: str = "",
) -> dict[str, Any]:
    """Fit + do thoi gian/RAM + tinh chi so + luu nhan + ghi log. Tra ve dong log (dict).

    fit_fn(X) tra ve labels, hoac (labels, probability) voi HDBSCAN.
    Chi phan fit_fn duoc tinh vao runtime_fit_sec / peak_mem_mb.
    """
    X = np.asarray(X, dtype=np.float64)
    if len(trip_ids) != X.shape[0]:
        raise ValueError(f"So trip_id ({len(trip_ids)}) khac so diem X ({X.shape[0]})")
    root = Path(cfg["_root"])
    labels_dir = root / cfg["paths"]["labels_dir"]
    log_path = root / cfg["paths"]["run_log"]
    ev_cfg = cfg["evaluation"]

    out, runtime, peak_mb, delta_mb = measure(lambda: fit_fn(X))
    labels, prob = (out if isinstance(out, tuple) else (out, None))
    labels = np.asarray(labels)

    res = evaluate(X, labels, silhouette_max_sample=ev_cfg["silhouette_max_sample"],
                   min_clusters=ev_cfg["min_clusters_for_metrics"], seed=cfg["project"]["seed"])
    run_id = make_run_id(algorithm, time_slice, labels_dir)
    save_labels(labels_dir, run_id, trip_ids, labels, prob)

    row = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "member": member,
        "algorithm": algorithm,
        "time_slice": time_slice,
        "sample_id": sample_id,
        "params": params,
        **res,
        "runtime_fit_sec": round(runtime, 4),
        "peak_mem_mb": round(peak_mb, 1),
        "mem_delta_mb": round(delta_mb, 1),
        "machine": machine_info(),
        "lib_versions": lib_versions(),
        "git_commit": git_commit(root),
        "note": note,
    }
    log_run(log_path, row)
    return row
