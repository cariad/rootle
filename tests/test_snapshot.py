from pathlib import Path
from stat import S_IMODE

from pytest import raises, skip

from rootle.testing import can_chmod_deny_listing, snapshot


def test_snapshot(tmp_path: Path) -> None:
    """
    Assert that `snapshot` gives every path within a directory, relative to it, with
    the body and permissions of every file, following a symlink to a file but not one
    to a directory, and giving a broken symlink no body.
    """
    (tmp_path / "sub").mkdir()

    # Bytes rather than text, which Windows would write with `\r\n`.
    (tmp_path / "sub" / "file.md").write_bytes(b"Hello, world!\n")

    (tmp_path / "link.md").symlink_to(Path("sub", "file.md"))
    (tmp_path / "linked").symlink_to("sub", target_is_directory=True)
    (tmp_path / "dangling.md").symlink_to("missing.md")
    mode = S_IMODE((tmp_path / "sub" / "file.md").stat().st_mode)

    found = snapshot(tmp_path)

    expect = {
        Path("dangling.md"): None,
        Path("link.md"): (b"Hello, world!\n", mode),
        Path("linked"): None,
        Path("sub"): None,
        Path("sub", "file.md"): (b"Hello, world!\n", mode),
    }

    assert found == expect


def test_snapshot_of_empty_directory(tmp_path: Path) -> None:
    """Assert that `snapshot` of an empty directory is empty."""
    found = snapshot(tmp_path)

    assert found == {}


def test_snapshot_raises_when_directory_is_missing(tmp_path: Path) -> None:
    """
    Assert that `snapshot` raises `FileNotFoundError` for a directory that doesn't
    exist, rather than saying that it's empty.
    """
    with raises(FileNotFoundError):
        snapshot(tmp_path / "missing")


def test_snapshot_raises_when_listing_is_denied(tmp_path: Path) -> None:
    """
    Assert that `snapshot` raises `PermissionError` for a directory within it that
    can't be listed, rather than leaving out what's within it.
    """
    if not can_chmod_deny_listing(tmp_path):
        skip("chmod can't deny listing here, like on Windows or to root")

    (tmp_path / "locked").mkdir()
    (tmp_path / "locked" / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    (tmp_path / "locked").chmod(0o300)

    try:
        with raises(PermissionError):
            snapshot(tmp_path)

    finally:
        (tmp_path / "locked").chmod(0o755)


def test_snapshot_sees_change_of_mode(tmp_path: Path) -> None:
    """Assert that `snapshot` sees a change to a file's permissions."""
    path = tmp_path / "file.md"
    path.write_text("Hello, world!\n", encoding="utf-8")
    path.chmod(0o644)
    before = snapshot(tmp_path)

    path.chmod(0o444)

    after = snapshot(tmp_path)

    assert after != before
