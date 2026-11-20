"""Dung lai artifact truc quan M4: python scripts/build_m4.py [--fast]"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.visualization.build_m4 import build_all  # noqa: E402

if __name__ == "__main__":
    dpi = 100 if "--fast" in sys.argv else 300
    man = build_all(ROOT, dpi=dpi)
    print(man[["artifact", "size_kb"]].to_string(index=False))
    print(f"\nDa tao {len(man)} artifact (dpi={dpi}). Manifest: outputs/m4_artifact_manifest.csv")
