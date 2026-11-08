from pathlib import Path
from stat import S_IMODE

from rootle.testing import snapshot


def test_snapshot(tmp_path: Path) -> None:
    """
    Assert that `snapshot` gives every path within a directory, relative to it, with
    the body and permissions of every file, following a symlink to a file but not one
    to a directory.
    """
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    (tmp_path / "link.md").symlink_to(Path("sub", "file.md"))
    (tmp_path / "linked").symlink_to("sub", target_is_directory=True)
    mode = S_IMODE((tmp_path / "sub" / "file.md").stat().st_mode)

    found = snapshot(tmp_path)

    expect = {
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


def test_snapshot_sees_change_of_mode(tmp_path: Path) -> None:
    """Assert that `snapshot` sees a change to a file's permissions."""
    path = tmp_path / "file.md"
    path.write_text("Hello, world!\n", encoding="utf-8")
    path.chmod(0o644)
    before = snapshot(tmp_path)

    path.chmod(0o444)

    after = snapshot(tmp_path)

    assert after != before
