"""Tien ich khi chay tren Google Colab.

Du lieu lon khong nam tren Git. Tren Colab, dat thu muc `data/` cua do an trong
Google Drive roi noi (symlink) vao repo da clone:

    from src.colab import in_colab, link_drive_data
    if in_colab():
        link_drive_data("KhaiPhaDuLieu")   # = /content/drive/MyDrive/KhaiPhaDuLieu/data

Sau do doc file nhu tren may ca nhan: data/processed/model_input.parquet.
Thu muc tren Drive nhom chua chot (diem 4 trong docs/dinh-dang-du-lieu.md).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

DRIVE_MOUNT = Path("/content/drive")


def in_colab() -> bool:
    return "google.colab" in sys.modules


def link_drive_data(drive_subdir: str, repo_root: str | Path | None = None,
                    mount: Path = DRIVE_MOUNT) -> Path:
    """Mount Google Drive va tao symlink <repo>/data -> MyDrive/<drive_subdir>/data.

    Tra ve duong dan thu muc data tren Drive. Chi dung tren Colab.
    Neu <repo>/data da ton tai va khong phai symlink thi bao loi, khong xoa.
    """
    if not in_colab():
        raise RuntimeError("link_drive_data chi dung tren Colab; tren may ca nhan dat du lieu vao data/")
    from google.colab import drive  # type: ignore[import-not-found]

    drive.mount(str(mount))
    src = mount / "MyDrive" / drive_subdir / "data"
    if not src.is_dir():
        raise FileNotFoundError(f"Khong thay {src}. Tao thu muc nay tren Drive va dat du lieu vao.")
    root = Path(repo_root) if repo_root else Path.cwd()
    dst = root / "data"
    if dst.is_symlink():
        dst.unlink()
    elif dst.exists():
        raise FileExistsError(f"{dst} da ton tai (khong phai symlink); xu ly tay truoc khi noi Drive")
    os.symlink(src, dst, target_is_directory=True)
    return src
