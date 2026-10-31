import sys
from errno import EACCES, ELOOP, ENOENT
from os import link, stat
from pathlib import Path
from unittest.mock import patch

from pytest import MonkeyPatch, mark, raises, skip

from rootle import status, winerror
from rootle.testing import can_chmod_deny_search
from tests.marks import posix_only, windows_only


class _UnreachableNetworkPathError(FileNotFoundError):
    """The error that Windows raises for a network path that it can't reach."""

    winerror = 53  # ERROR_BAD_NETPATH, which Windows maps to `ENOENT`

    def __init__(self) -> None:
        """Make the error, with the `errno` that Windows maps it to."""
        super().__init__(ENOENT, "The network path was not found")


@mark.parametrize(
    (
        "path",
        "target",
    ),
    [
        (
            "file.md",
            "file.md",
        ),
        (
            "link.md",
            "file.md",
        ),
        (
            "hard.md",
            "file.md",
        ),
        (
            "missing/../file.md",
            "file.md",
        ),
        (
            "dir",
            "dir",
        ),
        (
            "dir/",
            "dir",
        ),
        (
            "dir-link/",
            "dir",
        ),
    ],
)
def test_status(path: str, target: str, tmp_path: Path) -> None:
    """
    Assert that `status` is the status of the file that a path leads to, through every
    symlink it contains.
    """
    (tmp_path / "dir").mkdir()
    (tmp_path / "dir-link").symlink_to("dir", target_is_directory=True)
    (tmp_path / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    (tmp_path / "link.md").symlink_to("file.md")
    link(tmp_path / "file.md", tmp_path / "hard.md")

    found = status(f"{tmp_path}/{path}")
    expect = stat(tmp_path / target)

    assert found is not None
    assert found == expect


def test_status_accepts_relative_strings(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Assert that `status` accepts strings, and finds relative paths from the working
    directory.
    """
    (tmp_path / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    found = status("file.md")
    expect = stat(tmp_path / "file.md")

    assert found is not None
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
def test_status_is_none_when_nothing_exists(path: str, tmp_path: Path) -> None:
    """Assert that `status` is `None` when nothing exists at the path."""
    (tmp_path / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    (tmp_path / "dangling.md").symlink_to("missing.md")

    found = status(tmp_path / path)

    assert found is None


def test_status_raises_for_file_with_trailing_separator(tmp_path: Path) -> None:
    """
    Assert that `status` raises `NotADirectoryError` for a file given with a trailing
    separator, which says that it's a directory, naming the path as it was given.
    """
    (tmp_path / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    path = f"{tmp_path / 'file.md'}/"

    with raises(NotADirectoryError) as ex:
        status(path)

    assert ex.value.filename == path


@posix_only
def test_status_raises_for_symlink_loop_on_posix(tmp_path: Path) -> None:
    """
    Assert that `status` raises `OSError` with `ELOOP` when symlinks loop, naming the
    path as it was given rather than where it leads.
    """
    (tmp_path / "loop").symlink_to("loop")
    (tmp_path / "alias").symlink_to("loop")
    path = tmp_path / "alias"

    with raises(OSError) as ex:
        status(path)

    expect = str(path)

    assert ex.value.errno == ELOOP
    assert ex.value.filename == expect


@windows_only
def test_status_raises_for_symlink_loop_on_windows(tmp_path: Path) -> None:
    """
    Assert that `status` raises `OSError` with Windows' own error code when symlinks
    loop, naming the path as it was given rather than where it leads.
    """
    # Assure pyright that `winerror` exists.
    assert sys.platform == "win32"

    (tmp_path / "loop").symlink_to("loop")
    (tmp_path / "alias").symlink_to("loop")
    path = tmp_path / "alias"

    with raises(OSError) as ex:
        status(path)

    expect = str(path)

    assert ex.value.winerror == winerror.SYMLINK_LOOP
    assert ex.value.filename == expect


def test_status_raises_when_network_path_is_unreachable(tmp_path: Path) -> None:
    """
    Assert that `status` raises `FileNotFoundError` when Windows can't reach a network
    path, which it reports as missing, rather than saying that nothing exists there.
    Names the path as it was given.
    """
    path = tmp_path / "file.md"

    with (
        patch("rootle.status.stat", side_effect=_UnreachableNetworkPathError()),
        raises(FileNotFoundError) as ex,
    ):
        status(path)

    expect = str(path)

    assert ex.value.errno == ENOENT
    assert ex.value.filename == expect


def test_status_raises_when_permission_denied(tmp_path: Path) -> None:
    """
    Assert that `status` raises `PermissionError` for a file within a directory that
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
            status(path)

    finally:
        (tmp_path / "noperm").chmod(0o755)

    expect = str(path)

    assert ex.value.filename == expect


def test_status_raises_when_stat_fails(tmp_path: Path) -> None:
    """
    Assert that `status` raises when the path resolves but can't be `stat`-ed, like when
    it changes in between, naming the path as it was given rather than where it leads.
    """
    (tmp_path / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    (tmp_path / "link.md").symlink_to("file.md")
    path = tmp_path / "link.md"

    with (
        patch("rootle.status.stat", side_effect=PermissionError(EACCES, "Denied")),
        raises(PermissionError) as ex,
    ):
        status(path)

    expect = str(path)

    assert ex.value.errno == EACCES
    assert ex.value.filename == expect


@posix_only
def test_status_raises_when_stepping_up_from_file_on_posix(tmp_path: Path) -> None:
    """
    Assert that `status` raises `NotADirectoryError` for a ".." after a file, naming the
    path as it was given, because there's nowhere for it to step up from.
    """
    (tmp_path / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    path = tmp_path / "file.md" / ".." / "file.md"

    with raises(NotADirectoryError) as ex:
        status(path)

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
def test_status_raises_when_working_directory_is_gone_on_posix(
    monkeypatch: MonkeyPatch,
    path: str,
    tmp_path: Path,
) -> None:
    """
    Assert that `status` raises for a relative path when the working directory is gone,
    rather than saying that nothing exists there. A check that can't be made must fail
    rather than pass.
    """
    working = tmp_path / "working"
    working.mkdir()
    monkeypatch.chdir(working)
    working.rmdir()

    with raises(FileNotFoundError) as ex:
        status(path)

    assert ex.value.filename == path


@windows_only
def test_status_steps_up_from_file_on_windows(tmp_path: Path) -> None:
    """
    Assert that `status` steps up from a file by name on Windows, because that's how
    Windows itself resolves a ".." after a file.
    """
    (tmp_path / "file.md").write_text("Hello, world!\n", encoding="utf-8")

    found = status(tmp_path / "file.md" / ".." / "file.md")
    expect = stat(tmp_path / "file.md")

    assert found is not None
    assert found == expect
