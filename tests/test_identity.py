import sys
from errno import EACCES, ELOOP
from os import link, stat, stat_result
from pathlib import Path
from unicodedata import normalize
from unittest.mock import patch

from pytest import MonkeyPatch, mark, raises, skip

from rootle import identity, winerror
from rootle.testing import can_chmod_deny_search
from rootle.types import Identity
from tests.marks import posix_only, windows_only


@mark.parametrize(
    (
        "path",
        "expect_same",
    ),
    [
        (
            "file.md",
            True,
        ),
        (
            "link.md",
            True,
        ),
        (
            "hard.md",
            True,
        ),
        (
            "missing/../file.md",
            True,
        ),
        (
            "other.md",
            False,
        ),
    ],
)
def test_identity(path: str, expect_same: bool, tmp_path: Path) -> None:
    """
    Assert that `identity` is the same for every name of a file, and different for
    different files.
    """
    (tmp_path / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    (tmp_path / "other.md").write_text("Hello, world!\n", encoding="utf-8")
    (tmp_path / "link.md").symlink_to("file.md")
    link(tmp_path / "file.md", tmp_path / "hard.md")

    found = identity(tmp_path / path)
    expect = identity(tmp_path / "file.md")
    same = found == expect

    assert found is not None
    assert expect is not None
    assert same is expect_same


def test_identity_accepts_relative_strings(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Assert that `identity` accepts strings, and finds relative paths from the working
    directory.
    """
    (tmp_path / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    found = identity("file.md")
    expect = identity(tmp_path / "file.md")

    assert found is not None
    assert found == expect


@mark.parametrize(
    (
        "name",
        "spelling",
    ),
    [
        (
            "file.md",
            "FILE.md",
        ),
        (
            normalize("NFC", "café.md"),
            normalize("NFD", "café.md"),
        ),
    ],
)
def test_identity_by_different_spelling(
    name: str,
    spelling: str,
    tmp_path: Path,
) -> None:
    """
    Assert that `identity` is the same for a different spelling of a file's name, on a
    file system that treats it as the same name, like macOS's default APFS.
    """
    (tmp_path / name).write_text("Hello, world!\n", encoding="utf-8")

    if not (tmp_path / spelling).exists():
        skip(f"This file system doesn't treat {spelling!r} as {name!r}")

    found = identity(tmp_path / spelling)
    expect = identity(tmp_path / name)

    assert found is not None
    assert found == expect


def test_identity_is_device_and_inode(tmp_path: Path) -> None:
    """Assert that `identity` is made of the file's device and inode numbers."""
    (tmp_path / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    st = stat(tmp_path / "file.md")

    found = identity(tmp_path / "file.md")
    expect = Identity(device=st.st_dev, inode=st.st_ino)

    assert found == expect


def test_identity_is_hashable(tmp_path: Path) -> None:
    """Assert that identities can be kept in a set, one for each file."""
    (tmp_path / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    link(tmp_path / "file.md", tmp_path / "hard.md")

    found = {
        identity(tmp_path / "file.md"),
        identity(tmp_path / "hard.md"),
    }

    expect = {
        identity(tmp_path / "file.md"),
    }

    assert None not in found
    assert found == expect


@mark.parametrize(
    "path",
    [
        "missing.md",
        "missing/child.md",
        # `dangling` is a symlink to a missing file.
        "dangling.md",
        # `file.md` is a file, not a directory, so nothing can be within it.
        "file.md/child.md",
    ],
)
def test_identity_is_none_when_nothing_exists(path: str, tmp_path: Path) -> None:
    """Assert that `identity` is `None` when nothing exists at the path."""
    (tmp_path / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    (tmp_path / "dangling.md").symlink_to("missing.md")

    found = identity(tmp_path / path)

    assert found is None


@mark.parametrize(
    "path",
    [
        "dir",
        "dir/",
        "dir-link",
        "dir-link/",
    ],
)
def test_identity_of_directory(path: str, tmp_path: Path) -> None:
    """
    Assert that `identity` identifies a directory, given with or without a trailing
    separator.
    """
    (tmp_path / "dir").mkdir()
    (tmp_path / "dir-link").symlink_to("dir", target_is_directory=True)

    found = identity(f"{tmp_path}/{path}")
    expect = identity(tmp_path / "dir")

    assert found is not None
    assert found == expect


def test_identity_raises_for_file_with_trailing_separator(tmp_path: Path) -> None:
    """
    Assert that `identity` raises `NotADirectoryError` for a file given with a trailing
    separator, which says that it's a directory, naming the path as it was given.
    """
    (tmp_path / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    path = f"{tmp_path / 'file.md'}/"

    with raises(NotADirectoryError) as ex:
        identity(path)

    assert ex.value.filename == path


@posix_only
def test_identity_raises_for_symlink_loop_on_posix(tmp_path: Path) -> None:
    """
    Assert that `identity` raises `OSError` with `ELOOP` when symlinks loop, naming the
    path as it was given rather than where it leads.
    """
    (tmp_path / "loop").symlink_to("loop")
    (tmp_path / "alias").symlink_to("loop")
    path = tmp_path / "alias"

    with raises(OSError) as ex:
        identity(path)

    expect = str(path)

    assert ex.value.errno == ELOOP
    assert ex.value.filename == expect


@windows_only
def test_identity_raises_for_symlink_loop_on_windows(tmp_path: Path) -> None:
    """
    Assert that `identity` raises `OSError` with Windows' own error code when symlinks
    loop, naming the path as it was given rather than where it leads.
    """
    # Assure pyright that `winerror` exists.
    assert sys.platform == "win32"

    (tmp_path / "loop").symlink_to("loop")
    (tmp_path / "alias").symlink_to("loop")
    path = tmp_path / "alias"

    with raises(OSError) as ex:
        identity(path)

    expect = str(path)

    assert ex.value.winerror == winerror.SYMLINK_LOOP
    assert ex.value.filename == expect


@mark.parametrize(
    "device",
    [
        0,  # Like when Windows can't open the file
        64,  # Like a file system that never reports file numbers
    ],
)
def test_identity_raises_when_identity_is_unreadable(
    device: int,
    tmp_path: Path,
) -> None:
    """
    Assert that `identity` raises `PermissionError` when the file's number reads as
    zero, like when Windows can't open the file, whatever its device, rather than
    passing it as an identity that every such file shares. Names the path as it was
    given.
    """
    (tmp_path / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    (tmp_path / "link.md").symlink_to("file.md")
    path = tmp_path / "link.md"
    unreadable = stat_result((0o100644, 0, device, 1, 0, 0, 14, 0, 0, 0))

    with (
        patch("rootle.status.stat", return_value=unreadable),
        raises(PermissionError) as ex,
    ):
        identity(path)

    expect = str(path)

    assert ex.value.errno == EACCES
    assert ex.value.filename == expect


def test_identity_raises_when_permission_denied(tmp_path: Path) -> None:
    """
    Assert that `identity` raises `PermissionError` for a file within a directory that
    can't be read, naming the path as it was given, rather than saying that nothing
    exists there.
    """
    if not can_chmod_deny_search(tmp_path):
        skip("chmod can't deny search permission here, like on Windows or to root")

    (tmp_path / "noperm").mkdir()
    (tmp_path / "noperm" / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    (tmp_path / "noperm").chmod(0)
    path = tmp_path / "noperm" / "file.md"

    try:
        with raises(PermissionError) as ex:
            identity(path)

    finally:
        (tmp_path / "noperm").chmod(0o755)

    expect = str(path)

    assert ex.value.filename == expect


@posix_only
def test_identity_raises_when_stepping_up_from_file_on_posix(tmp_path: Path) -> None:
    """
    Assert that `identity` raises `NotADirectoryError` for a ".." after a file, naming
    the path as it was given, because there's nowhere for it to step up from.
    """
    (tmp_path / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    path = tmp_path / "file.md" / ".." / "file.md"

    with raises(NotADirectoryError) as ex:
        identity(path)

    expect = str(path)

    assert ex.value.filename == expect


@mark.skipif(
    sys.platform == "win32",
    reason="Removes the working directory, which Windows won't allow",
)
@mark.parametrize(
    "path",
    [
        ".",
        "..",
        "doc.md",
    ],
)
def test_identity_raises_when_working_directory_is_gone_on_posix(
    monkeypatch: MonkeyPatch,
    path: str,
    tmp_path: Path,
) -> None:
    """
    Assert that `identity` raises for a relative path when the working directory is
    gone, rather than saying that nothing exists there. A safety check that can't be
    made must fail rather than pass.
    """
    working = tmp_path / "working"
    working.mkdir()
    monkeypatch.chdir(working)
    working.rmdir()

    with raises(FileNotFoundError) as ex:
        identity(path)

    assert ex.value.filename == path


@windows_only
def test_identity_steps_up_from_file_on_windows(tmp_path: Path) -> None:
    """
    Assert that `identity` steps up from a file by name on Windows, because that's how
    Windows itself resolves a ".." after a file.
    """
    (tmp_path / "file.md").write_text("Hello, world!\n", encoding="utf-8")

    found = identity(tmp_path / "file.md" / ".." / "file.md")
    expect = identity(tmp_path / "file.md")

    assert found is not None
    assert found == expect
