"""Zip handling. These run without a database or a server."""
import zipfile

import pytest

from app.utils.archive import UnsafeArchiveError, is_zip_magic, safe_extract

LIMITS = dict(max_members=100, max_total_bytes=1_000_000, max_member_bytes=100_000)


def _zip(members, path):
    with zipfile.ZipFile(path, "w") as z:
        for name, content in members:
            z.writestr(name, content)
    return path


def test_extracts_a_normal_archive(tmp_path):
    src = _zip([("a.py", "print(1)"), ("pkg/b.py", "x=2")], tmp_path / "ok.zip")
    count, written = safe_extract(src, tmp_path / "out", **LIMITS)
    assert count == 2
    assert written > 0
    assert (tmp_path / "out" / "a.py").read_text() == "print(1)"
    assert (tmp_path / "out" / "pkg" / "b.py").read_text() == "x=2"


@pytest.mark.parametrize(
    "name", ["../escape.py", "../../etc/passwd", "a/../../escape.py", "a/../../../x"]
)
def test_zip_slip_is_rejected(tmp_path, name):
    src = _zip([(name, "pwned")], tmp_path / "evil.zip")
    with pytest.raises(UnsafeArchiveError, match="parent-directory"):
        safe_extract(src, tmp_path / "out", **LIMITS)
    assert not (tmp_path / "escape.py").exists()


def test_absolute_path_is_rejected(tmp_path):
    src = _zip([("/tmp/abs.py", "pwned")], tmp_path / "abs.zip")
    with pytest.raises(UnsafeArchiveError):
        safe_extract(src, tmp_path / "out", **LIMITS)


def test_symlink_member_is_rejected(tmp_path):
    path = tmp_path / "link.zip"
    with zipfile.ZipFile(path, "w") as z:
        info = zipfile.ZipInfo("link")
        info.external_attr = (0xA1FF) << 16  # S_IFLNK | 0777
        z.writestr(info, "/etc/passwd")
    with pytest.raises(UnsafeArchiveError, match="symlink"):
        safe_extract(path, tmp_path / "out", **LIMITS)


def test_too_many_members_is_rejected(tmp_path):
    src = _zip([(f"f{i}.py", "x") for i in range(20)], tmp_path / "many.zip")
    with pytest.raises(UnsafeArchiveError, match="entries"):
        safe_extract(src, tmp_path / "out", max_members=5,
                     max_total_bytes=1_000_000, max_member_bytes=100_000)


def test_zip_bomb_total_size_is_rejected(tmp_path):
    src = _zip([("big.txt", "A" * 50_000)], tmp_path / "bomb.zip")
    with pytest.raises(UnsafeArchiveError, match="expands"):
        safe_extract(src, tmp_path / "out", max_members=100,
                     max_total_bytes=1000, max_member_bytes=100_000)


def test_oversized_member_is_rejected(tmp_path):
    src = _zip([("big.txt", "A" * 50_000)], tmp_path / "big.zip")
    with pytest.raises(UnsafeArchiveError, match="per-file"):
        safe_extract(src, tmp_path / "out", max_members=100,
                     max_total_bytes=1_000_000, max_member_bytes=1000)


def test_not_a_zip_is_rejected(tmp_path):
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"this is not a zip")
    with pytest.raises(UnsafeArchiveError, match="not a valid zip"):
        safe_extract(bad, tmp_path / "out", **LIMITS)


def test_magic_byte_check():
    assert is_zip_magic(b"PK\x03\x04rest")
    assert not is_zip_magic(b"%PDF-1.4")
    assert not is_zip_magic(b"")


def test_nothing_is_written_when_a_later_member_is_unsafe(tmp_path):
    """Validation happens up front, so a partial tree is never left behind."""
    src = _zip([("good.py", "ok"), ("../bad.py", "no")], tmp_path / "mixed.zip")
    out = tmp_path / "out"
    with pytest.raises(UnsafeArchiveError):
        safe_extract(src, out, **LIMITS)
    assert not (out / "good.py").exists()
