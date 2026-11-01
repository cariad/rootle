import sys
from errno import ELOOP
from pathlib import Path

from pytest import MonkeyPatch, mark, raises, skip

from rootle import resolve, winerror
from rootle.testing import can_chmod_deny_search
from tests.marks import posix_only, windows_only


@mark.parametrize(
    (
        "path",
        "expect",
    ),
    [
        (
            "dir",
            "dir",
        ),
        (
            "dir/file.md",
            "dir/file.md",
        ),
        (
            "dir/missing/file.md",
            "dir/missing/file.md",
        ),
        (
            "dir/missing/../file.md",
            "dir/file.md",
        ),
        (
            "dir/./file.md",
            "dir/file.md",
        ),
        (
            "dir-link/file.md",
            "dir/file.md",
        ),
        (
            # `dangling` is a symlink to a missing file.
            "dangling",
            "dir/new.md",
        ),
        (
            # `file.md` is a file, not a directory, so the parts after it are kept.
            "dir/file.md/child.md",
            "dir/file.md/child.md",
        ),
        (
            "dir/file.md/child/deeper.md",
            "dir/file.md/child/deeper.md",
        ),
        (
            "file-link/child.md",
            "dir/file.md/child.md",
        ),
        (
            # `file-path-link` is a symlink to a path through a file.
            "file-path-link/x",
            "dir/file.md/child/x",
        ),
        (
            "missing/../file-path-link",
            "dir/file.md/child",
        ),
        (
            "missing/../file-path-link/x",
            "dir/file.md/child/x",
        ),
    ],
)
def test_resolve(path: str, expect: str, tmp_path: Path) -> None:
    """
    Assert that `resolve` follows every symlink along the path, whether or not the path
    exists, and keeps the parts after a file as they were given.
    """
    (tmp_path / "dir").mkdir()
    (tmp_path / "dir" / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    (tmp_path / "dir-link").symlink_to(tmp_path / "dir", target_is_directory=True)
    (tmp_path / "dangling").symlink_to(tmp_path / "dir" / "new.md")
    (tmp_path / "file-link").symlink_to(tmp_path / "dir" / "file.md")
    (tmp_path / "file-path-link").symlink_to(tmp_path / "dir" / "file.md" / "child")

    resolved = resolve(tmp_path / path)
    resolved_expect = resolve(tmp_path) / expect

    assert resolved == resolved_expect


def test_resolve_accepts_relative_strings(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Assert that `resolve` accepts strings, and resolves relative paths from the working
    directory.
    """
    monkeypatch.chdir(tmp_path)

    resolved = resolve("doc.md")
    expect = resolve(tmp_path) / "doc.md"

    assert resolved == expect


def test_resolve_keeps_directory_with_trailing_separator(tmp_path: Path) -> None:
    """Assert that `resolve` resolves a directory given with a trailing separator."""
    (tmp_path / "dir").mkdir()

    resolved = resolve(f"{tmp_path / 'dir'}/")
    expect = resolve(tmp_path) / "dir"

    assert resolved == expect


@posix_only
def test_resolve_keeps_letter_case_on_posix(tmp_path: Path) -> None:
    """
    Assert that `resolve` keeps each name in the letter case that the path gave it, on
    a case-insensitive file system like macOS's default APFS.
    """
    (tmp_path / "dir").mkdir()

    if not (tmp_path / "DIR").exists():
        skip("This file system is case-sensitive, so 'DIR' isn't 'dir'")

    resolved = resolve(tmp_path / "DIR")

    assert resolved.name == "DIR"


def test_resolve_raises_for_empty_path() -> None:
    """
    Assert that `resolve` raises `FileNotFoundError` for an empty path, which names
    nothing, rather than reading it as the working directory.
    """
    with raises(FileNotFoundError) as ex:
        resolve("")

    assert ex.value.filename == ""


@mark.parametrize(
    "suffix",
    [
        "/",
        "/.",
    ],
)
def test_resolve_raises_for_file_with_trailing_separator(
    suffix: str,
    tmp_path: Path,
) -> None:
    """
    Assert that `resolve` raises `NotADirectoryError` for a file given with a trailing
    separator or `.`, which says that it's a directory, naming the path as it was given.
    """
    (tmp_path / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    path = f"{tmp_path / 'file.md'}{suffix}"

    with raises(NotADirectoryError) as ex:
        resolve(path)

    assert ex.value.filename == path


@posix_only
def test_resolve_raises_for_symlink_loop_on_posix(tmp_path: Path) -> None:
    """
    Assert that `resolve` raises `OSError` with `ELOOP` when symlinks loop, naming the
    path as it was given rather than where it leads.
    """
    (tmp_path / "loop").symlink_to("loop")
    (tmp_path / "alias").symlink_to("loop")
    path = tmp_path / "alias" / "file.md"

    with raises(OSError) as ex:
        resolve(path)

    expect = str(path)

    assert ex.value.errno == ELOOP
    assert ex.value.filename == expect


@windows_only
def test_resolve_raises_for_symlink_loop_on_windows(tmp_path: Path) -> None:
    """
    Assert that `resolve` raises `OSError` with Windows' own error code when symlinks
    loop, naming the path as it was given rather than where it leads.
    """
    # Assure pyright that `winerror` exists.
    assert sys.platform == "win32"

    (tmp_path / "loop").symlink_to("loop")
    (tmp_path / "alias").symlink_to("loop")
    path = tmp_path / "alias" / "file.md"

    with raises(OSError) as ex:
        resolve(path)

    expect = str(path)

    assert ex.value.winerror == winerror.SYMLINK_LOOP
    assert ex.value.filename == expect


@mark.parametrize(
    "path",
    [
        "noperm/x",
        # `link` might lead anywhere, so ".." can't be resolved without reading it.
        "noperm/link/../../dir/x",
    ],
)
def test_resolve_raises_when_permission_denied(path: str, tmp_path: Path) -> None:
    """
    Assert that `resolve` raises `PermissionError` for a path through a directory that
    can't be read, naming the path as it was given, rather than guessing where a ".."
    after it leads.
    """
    if not can_chmod_deny_search(tmp_path):
        skip("chmod can't deny search permission here, like on Windows or to root")

    (tmp_path / "noperm").mkdir()
    (tmp_path / "noperm" / "link").symlink_to(tmp_path / "elsewhere" / "deep")
    (tmp_path / "noperm").chmod(0)

    try:
        with raises(PermissionError) as ex:
            resolve(tmp_path / path)

    finally:
        (tmp_path / "noperm").chmod(0o755)

    expect = str(tmp_path / path)

    assert ex.value.filename == expect


@posix_only
def test_resolve_raises_when_stepping_up_from_file_on_posix(tmp_path: Path) -> None:
    """
    Assert that `resolve` raises `NotADirectoryError` for a ".." after a file, naming
    the path as it was given, because there's nowhere for it to step up from.
    """
    (tmp_path / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    path = tmp_path / "file.md" / "child" / ".." / "other.md"

    with raises(NotADirectoryError) as ex:
        resolve(path)

    expect = str(path)

    assert ex.value.filename == expect


@mark.skipif(
    sys.platform == "win32",
    reason="Removes the working directory, which Windows won't allow",
)
def test_resolve_raises_when_working_directory_is_gone_on_posix(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Assert that `resolve` raises for a relative path when the working directory is gone,
    naming the path as it was given.
    """
    working = tmp_path / "working"
    working.mkdir()
    monkeypatch.chdir(working)
    working.rmdir()

    with raises(FileNotFoundError) as ex:
        resolve("doc.md")

    assert ex.value.filename == "doc.md"


@windows_only
def test_resolve_steps_up_from_file_on_windows(tmp_path: Path) -> None:
    """
    Assert that `resolve` steps up from a file by name on Windows, because that's how
    Windows itself resolves a ".." after a file.
    """
    (tmp_path / "file.md").write_text("Hello, world!\n", encoding="utf-8")

    resolved = resolve(tmp_path / "file.md" / "child" / ".." / "other.md")
    expect = resolve(tmp_path) / "file.md" / "other.md"

    assert resolved == expect


@windows_only
def test_resolve_uses_stored_letter_case_on_windows(tmp_path: Path) -> None:
    """
    Assert that `resolve` uses the letter case that the file system stores on Windows,
    rather than the letter case that the path gave it.
    """
    (tmp_path / "dir").mkdir()

    resolved = resolve(tmp_path / "DIR")

    assert resolved.name == "dir"
