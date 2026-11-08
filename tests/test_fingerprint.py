from os import stat, utime
from pathlib import Path

from pytest import mark, skip

from rootle import fingerprint
from rootle.testing import can_chmod_deny_search
from rootle.types import Fingerprint


@mark.parametrize(
    "path",
    [
        "real/link.md",
        # A symlink to `link.md`, so two symlinks are followed to reach `file.md`.
        "real/chain.md",
        # A file within a symlink to `real`, so the symlink is partway along the path
        # rather than at its end.
        "linked/file.md",
    ],
)
def test_fingerprint_follows_symlinks(path: str, tmp_path: Path) -> None:
    """
    Assert that `fingerprint` fingerprints the file that a path leads to through every
    symlink within it, rather than a symlink, so that retargeting one is seen.
    """
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    (real_dir / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    (real_dir / "link.md").symlink_to("file.md")
    (real_dir / "chain.md").symlink_to("link.md")
    (tmp_path / "linked").symlink_to(real_dir, target_is_directory=True)

    found = fingerprint(tmp_path / path)
    expect = fingerprint(real_dir / "file.md")

    assert expect is not None
    assert found == expect


def test_fingerprint_gives_every_field_of_regular_file(tmp_path: Path) -> None:
    """
    Assert that `fingerprint` gives a regular file's identity, mode, size, and change
    and modification times, whether its path is a `Path` or a `str`.
    """
    path = tmp_path / "file.md"
    path.write_text("Hello, world!\n", encoding="utf-8")

    # Move the modification time away from the change time, so that they can't be
    # mistaken for each other.
    utime(path, ns=(0, 1_000_000_000))
    st = stat(path)
    assert st.st_ctime_ns != st.st_mtime_ns

    found_from_path = fingerprint(path)
    found_from_str = fingerprint(str(path))

    expect = Fingerprint(
        changed=st.st_ctime_ns,
        device=st.st_dev,
        inode=st.st_ino,
        mode=st.st_mode,
        modified=st.st_mtime_ns,
        size=14,
    )

    assert found_from_path == expect
    assert found_from_str == expect


@mark.parametrize(
    "path",
    [
        "directory",
        "/dev/null",
    ],
)
def test_fingerprint_gives_identity_and_mode_only_of_file_that_is_not_regular(
    path: str,
    tmp_path: Path,
) -> None:
    """
    Assert that `fingerprint` gives only the identity and mode of anything but a regular
    file, leaving its times and size `None`, because a directory's times change whenever
    any entry within it does and a device's change as it's used.
    """
    (tmp_path / "directory").mkdir()

    # An absolute path replaces `tmp_path` when they're joined.
    target = tmp_path / path

    if not target.exists():
        skip(f"This platform doesn't have {path}")

    st = stat(target)

    found = fingerprint(target)

    expect = Fingerprint(
        changed=None,
        device=st.st_dev,
        inode=st.st_ino,
        mode=st.st_mode,
        modified=None,
        size=None,
    )

    assert found == expect


def test_fingerprint_is_hashable(tmp_path: Path) -> None:
    """Assert that fingerprints can be kept in a set, one for each state of a file."""
    (tmp_path / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    (tmp_path / "link.md").symlink_to("file.md")

    found = {
        fingerprint(tmp_path / "file.md"),
        fingerprint(tmp_path / "link.md"),
    }

    expect = {
        fingerprint(tmp_path / "file.md"),
    }

    assert None not in found
    assert found == expect


@mark.parametrize(
    "path",
    [
        "missing.md",
        "missing/file.md",
        # A path that treats a regular file as a directory, which raises
        # `NotADirectoryError` rather than `FileNotFoundError`.
        "file.md/file.md",
        # A symlink to a file that doesn't exist.
        "broken.md",
        # A symlink that leads back to itself, so nothing can be found there.
        "loop.md",
        # A null character, which raises `ValueError` rather than `OSError`.
        "null\0.md",
    ],
)
def test_fingerprint_is_none_when_file_cannot_be_found(
    path: str,
    tmp_path: Path,
) -> None:
    """
    Assert that `fingerprint` gives `None`, rather than raising, for a path that leads
    to nothing that could be read, like one that's missing, a broken symlink, a loop of
    symlinks, or a path with a null character.
    """
    (tmp_path / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    (tmp_path / "broken.md").symlink_to("nowhere.md")
    (tmp_path / "loop.md").symlink_to("loop.md")

    found = fingerprint(tmp_path / path)

    assert found is None


def test_fingerprint_is_none_when_permissions_hide_file(tmp_path: Path) -> None:
    """
    Assert that `fingerprint` gives `None`, rather than raising, for a file within a
    directory that can't be searched.
    """
    if not can_chmod_deny_search(tmp_path):
        skip("chmod can't deny search permission here, like on Windows or to root")

    directory = tmp_path / "locked"
    directory.mkdir()
    (directory / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    directory.chmod(0o600)

    try:
        found = fingerprint(directory / "file.md")

    finally:
        directory.chmod(0o755)

    assert found is None
