"""Safe zip extraction.

The previous implementation called `zipfile.extractall` directly, which is
vulnerable to zip-slip (member names like `../../etc/x`), symlink escapes, and
zip bombs. With open registration this is an anonymous-attacker surface, so
every member is validated before a single byte is written.
"""
import os
import shutil
import zipfile
from pathlib import Path
from typing import Tuple

ZIP_MAGIC = b"PK\x03\x04"

# Stripped after extraction; these are noise, not code.
PRUNE_DIRS = {
    "node_modules", "dist", "build", "out", ".next", ".nuxt",
    "venv", ".venv", "__pycache__", ".pytest_cache", ".git",
    ".vercel", ".netlify", "coverage", ".idea", ".vscode", ".cache",
}
PRUNE_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "composer.lock",
    "Pipfile.lock", "poetry.lock", ".DS_Store", "Thumbs.db",
}


class UnsafeArchiveError(ValueError):
    """Raised when an archive fails validation. The message is user-facing."""


def is_zip_magic(head: bytes) -> bool:
    """Check the magic bytes rather than trusting the client-supplied filename."""
    return head.startswith(ZIP_MAGIC)


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    # Unix mode lives in the top 16 bits of external_attr; 0xA000 == S_IFLNK.
    return (info.external_attr >> 16) & 0xF000 == 0xA000


def _validate_member(info: zipfile.ZipInfo, dest_root: Path, max_member_bytes: int) -> Path:
    name = info.filename

    if _is_symlink(info):
        raise UnsafeArchiveError(f"Archive contains a symlink: {name}")

    # Normalize separators; some archives use backslashes.
    normalized = name.replace("\\", "/")

    if normalized.startswith("/") or (len(normalized) > 1 and normalized[1] == ":"):
        raise UnsafeArchiveError(f"Archive contains an absolute path: {name}")

    parts = [p for p in normalized.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise UnsafeArchiveError(f"Archive contains a parent-directory reference: {name}")

    if info.file_size > max_member_bytes:
        raise UnsafeArchiveError(f"Archive member exceeds the per-file limit: {name}")

    target = (dest_root / Path(*parts)).resolve() if parts else dest_root.resolve()

    # Belt-and-braces: even after the checks above, confirm containment.
    if target != dest_root.resolve() and dest_root.resolve() not in target.parents:
        raise UnsafeArchiveError(f"Archive member escapes the destination: {name}")

    return target


def safe_extract(
    zip_path: Path,
    dest_root: Path,
    max_members: int,
    max_total_bytes: int,
    max_member_bytes: int,
) -> Tuple[int, int]:
    """Extract `zip_path` into `dest_root`, validating every member first.

    Returns (file_count, total_bytes). Raises UnsafeArchiveError on any breach.
    """
    dest_root = dest_root.resolve()
    dest_root.mkdir(parents=True, exist_ok=True)

    try:
        archive = zipfile.ZipFile(zip_path, "r")
    except zipfile.BadZipFile:
        raise UnsafeArchiveError("The uploaded file is not a valid zip archive")

    with archive:
        members = archive.infolist()

        if len(members) > max_members:
            raise UnsafeArchiveError(
                f"Archive contains {len(members)} entries, limit is {max_members}"
            )

        declared_total = sum(m.file_size for m in members)
        if declared_total > max_total_bytes:
            raise UnsafeArchiveError(
                f"Archive expands to {declared_total} bytes, limit is {max_total_bytes}"
            )

        # Validate everything up front so we never write a partial tree.
        targets = [
            (m, _validate_member(m, dest_root, max_member_bytes))
            for m in members
        ]

        file_count = 0
        written = 0
        for info, target in targets:
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)

            # Copy with a hard ceiling so a lying `file_size` header cannot
            # bomb us: decompress incrementally and stop if the real size
            # exceeds what the archive declared.
            remaining = max_member_bytes
            with archive.open(info, "r") as src, open(target, "wb") as dst:
                while True:
                    chunk = src.read(64 * 1024)
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    written += len(chunk)
                    if remaining < 0:
                        raise UnsafeArchiveError(
                            f"Archive member is larger than declared: {info.filename}"
                        )
                    if written > max_total_bytes:
                        raise UnsafeArchiveError(
                            "Archive expands beyond the total size limit"
                        )
                    dst.write(chunk)
            file_count += 1

    return file_count, written


def prune_noise(root: Path) -> None:
    """Remove dependency and build directories after a successful extraction."""
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        for d in list(dirnames):
            if d in PRUNE_DIRS:
                shutil.rmtree(os.path.join(dirpath, d), ignore_errors=True)
                dirnames.remove(d)
        for f in filenames:
            if f in PRUNE_FILES:
                try:
                    os.remove(os.path.join(dirpath, f))
                except OSError:
                    pass


def measure_tree(root: Path) -> Tuple[int, int]:
    """Return (file_count, total_bytes) for the extracted tree."""
    count = 0
    total = 0
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, f))
                count += 1
            except OSError:
                pass
    return count, total
