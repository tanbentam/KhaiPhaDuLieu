"""Kiem tra repo sach truoc khi release: python scripts/check_repo.py (exit 1 neu co loi)."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".git", "__pycache__", ".ipynb_checkpoints", ".pytest_cache"}
MAX_MB = 8
ABS = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:(?:\\{2,4}|\\(?![ntrbf]))[A-Za-z0-9_]|/Users/[A-Za-z]|/home/[a-z]+/")
SECRET = re.compile(r"(api[_-]?key|secret|password|token)\s*[=:]\s*['\"][^'\"]{8,}", re.I)
ALLOW_ABS = {"src/colab.py", "scripts/check_repo.py"}   # /content/drive la duong dan Colab co chu dich

problems, notes = [], []
for p in ROOT.rglob("*"):
    if any(s in p.parts for s in SKIP) or not p.is_file():
        continue
    rel = p.relative_to(ROOT).as_posix()
    if p.stat().st_size > MAX_MB * 1024 * 1024:
        problems.append(f"file > {MAX_MB} MB: {rel}")
    if rel.startswith(("data/", "outputs/labels/")):
        problems.append(f"du lieu/nhan khong duoc dong goi: {rel}")
    if p.suffix in {".py", ".ipynb", ".md", ".yaml", ".yml", ".txt"} and rel not in ALLOW_ABS:
        t = p.read_text(encoding="utf-8", errors="ignore")
        if p.suffix in {".py", ".ipynb"} and ABS.search(t):
            problems.append(f"duong dan tuyet doi ca nhan: {rel} -> {ABS.search(t).group(0)!r}")
        if SECRET.search(t):
            problems.append(f"nghi chua secret: {rel}")
for must in ["README.md", "requirements.txt", ".gitignore", "config/experiment.yaml",
             "notebooks/07_visualization_reporting.ipynb", "outputs/metrics/metrics_comparison.csv"]:
    if not (ROOT / must).exists():
        problems.append(f"thieu: {must}")
print("\n".join(problems) or "Repo sach: khong co van de.")
sys.exit(1 if problems else 0)
