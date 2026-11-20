"""Benchmark HDBSCAN pilot sizes and record the exact runtime environment."""
from __future__ import annotations

import hashlib
import json
import pathlib
import platform
import sys

import numpy as np
import pandas as pd
from importlib.metadata import version

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_config, resolve_path
from src.evaluation.runlog import git_commit, machine_info, measure
from src.models.hdbscan import fit_hdbscan, get_cluster_persistence_table


def validate_hdbscan_api() -> None:
    """Exercise fit_predict and the fitted outputs required by M3."""
    import hdbscan

    X = np.array([
        [0.0, 0.0], [0.1, 0.0], [0.0, 0.1],
        [10.0, 10.0], [10.1, 10.0], [10.0, 10.1],
    ])
    model = hdbscan.HDBSCAN(min_cluster_size=2, min_samples=1)
    labels = model.fit_predict(X)
    missing = [
        name for name in ("probabilities_", "cluster_persistence_", "condensed_tree_")
        if not hasattr(model, name)
    ]
    if missing:
        raise RuntimeError("HDBSCAN API check failed; missing: " + ", ".join(missing))
    if labels.shape != (len(X),) or not np.array_equal(labels, model.labels_):
        raise RuntimeError("HDBSCAN fit_predict returned unexpected labels.")
    if model.probabilities_.shape != (len(X),) or not np.isfinite(model.probabilities_).all():
        raise RuntimeError("HDBSCAN probabilities_ has an invalid shape or value.")
    if not callable(getattr(model.condensed_tree_, "to_pandas", None)):
        raise RuntimeError("HDBSCAN condensed_tree_ does not expose to_pandas().")
    get_cluster_persistence_table(model)


def main() -> None:
    cfg = load_config()
    data_path = resolve_path(cfg, "master")
    manifest_path = resolve_path(cfg, "master_manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(data_path.read_bytes()).hexdigest()
    if digest != manifest["sha256"]:
        raise ValueError(f"SHA256 mismatch for {data_path.name}: {digest}")

    validate_hdbscan_api()
    df = pd.read_parquet(data_path)
    am = df.loc[df["time_slice"] == "WEEKDAY_AM", ["x_m", "y_m"]].to_numpy(dtype=np.float64)
    sample_sizes = [5_000, 10_000, 30_000]
    if len(am) < max(sample_sizes):
        raise ValueError(
            f"WEEKDAY_AM has {len(am):,} rows; pilot requires {max(sample_sizes):,}."
        )

    hdb_cfg = cfg["hdbscan"]
    final_cfg = hdb_cfg["final"]
    indices = np.random.default_rng(cfg["project"]["seed"]).permutation(len(am))
    rows = []
    for sample_size in sample_sizes:
        X = am[indices[:sample_size]]
        (labels, _, clusterer), runtime, peak_mb, delta_mb = measure(
            lambda: fit_hdbscan(
                X,
                min_cluster_size=int(final_cfg["min_cluster_size"]),
                min_samples=int(final_cfg["min_samples"]),
                metric=hdb_cfg["metric"],
                cluster_selection_method=final_cfg["cluster_selection_method"],
                cluster_selection_epsilon=float(hdb_cfg["cluster_selection_epsilon"]),
            )
        )
        persistence = get_cluster_persistence_table(clusterer)
        rows.append({
            "sample_size": sample_size,
            "n_unique_coords": int(np.unique(X, axis=0).shape[0]),
            "n_clusters": int(np.unique(labels[labels != -1]).size),
            "n_noise": int((labels == -1).sum()),
            "noise_ratio": float((labels == -1).mean()),
            "mean_persistence": (
                float(persistence["persistence"].mean()) if not persistence.empty else None
            ),
            "runtime_sec": round(runtime, 4),
            "peak_mem_mb": round(peak_mb, 1),
            "mem_delta_mb": round(delta_mb, 1),
            "backend": f"{type(clusterer).__module__}.{type(clusterer).__name__}",
            "python": platform.python_version(),
            "hdbscan": version("hdbscan"),
            "machine": machine_info(),
            "git_commit": git_commit(ROOT),
        })

    metrics_dir = resolve_path(cfg, "run_log").parent
    benchmark_path = metrics_dir / "hdbscan_benchmark.csv"
    pd.DataFrame(rows).to_csv(benchmark_path, index=False)

    environment_path = metrics_dir / "environment_hdbscan.txt"
    environment_path.write_text(
        "\n".join([
            f"python={platform.python_version()}",
            f"hdbscan={version('hdbscan')}",
            f"numpy={np.__version__}",
            f"pandas={pd.__version__}",
            f"scipy={version('scipy')}",
            f"scikit-learn={version('scikit-learn')}",
            f"pyarrow={version('pyarrow')}",
            f"machine={machine_info()}",
            f"backend={rows[-1]['backend']}",
            f"git_commit={git_commit(ROOT)}",
        ]) + "\n",
        encoding="utf-8",
    )
    print(f"Saved pilot benchmark: {benchmark_path.relative_to(ROOT)}")
    print(f"Saved environment record: {environment_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
