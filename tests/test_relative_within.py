import sys
from errno import EACCES, ELOOP, ENOENT
from os import PathLike, link, stat, stat_result
from pathlib import Path, PurePath
from subprocess import DEVNULL, run
from unicodedata import normalize
from unittest.mock import patch

from pytest import MonkeyPatch, mark, raises, skip

from rootle import relative_within, resolve, winerror
from rootle.testing import can_chmod_deny_search
from tests.marks import posix_only, windows_only


class _UnreachableNetworkPathError(FileNotFoundError):
    """The error that Windows raises for a network path that it can't reach."""

    winerror = 53  # ERROR_BAD_NETPATH, which Windows maps to `ENOENT`

    def __init__(self) -> None:
        """Make the error, with the `errno` that Windows maps it to."""
        super().__init__(
            ENOENT,
            "The network path was not found",
        )


@mark.parametrize(
    (
        "path",
        "expect",
    ),
    [
        (
            "dir",
            PurePath("."),
        ),
        (
            "dir/",
            PurePath("."),
        ),
        (
            "dir/sub",
            PurePath("sub"),
        ),
        (
            "dir/sub/deep",
            PurePath("sub/deep"),
        ),
        (
            "dir/file.md",
            PurePath("file.md"),
        ),
        (
            "dir/missing/file.md",
            PurePath("missing/file.md"),
        ),
        (
            "dir/missing/../sub",
            PurePath("sub"),
        ),
        (
            # `file.md` is a file, not a directory, so the parts after it are kept.
            "dir/file.md/child.md",
            PurePath("file.md/child.md"),
        ),
        (
            # `hard-in.md` is a hard link within `dir` to a file outside of it.
            "dir/hard-in.md",
            PurePath("hard-in.md"),
        ),
        (
            "link/file.md",
            PurePath("sub/file.md"),
        ),
        (
            # `dangling` is a symlink to a missing file within `dir`.
            "dangling",
            PurePath("new.md"),
        ),
        (
            # `hard-out.md` is a hard link outside of `dir` to a file within it.
            "hard-out.md",
            None,
        ),
        (
            # `out` is a symlink within `dir` to `sibling`, which is outside of it.
            "dir/out/file.md",
            None,
        ),
        (
            # `escape` is a dangling symlink within `dir` to a missing file outside of
            # it.
            "dir/escape",
            None,
        ),
        (
            # `escape-dir` is a dangling symlink within `dir` to a missing directory
            # outside of it.
            "dir/escape-dir/file.md",
            None,
        ),
        (
            "dir/missing/../../sibling",
            None,
        ),
        (
            "sibling",
            None,
        ),
        (
            "missing/file.md",
            None,
        ),
        (
            ".",
            None,
        ),
    ],
)
def test_relative_within(
    path: str,
    expect: PurePath | None,
    tmp_path: Path,
) -> None:
    """
    Assert that `relative_within` is the path relative to the directory when the path is
    the directory or within it, wherever symlinks lead and whether or not the path
    exists, and `None` otherwise.
    """
    (tmp_path / "dir" / "sub" / "deep").mkdir(parents=True)
    (tmp_path / "dir" / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    (tmp_path / "outside.md").write_text("Hello, world!\n", encoding="utf-8")
    (tmp_path / "sibling").mkdir()
    (tmp_path / "link").symlink_to(tmp_path / "dir" / "sub", target_is_directory=True)
    (tmp_path / "dangling").symlink_to(tmp_path / "dir" / "new.md")

    (tmp_path / "dir" / "out").symlink_to(
        tmp_path / "sibling",
        target_is_directory=True,
    )

    (tmp_path / "dir" / "escape").symlink_to(tmp_path / "sibling" / "missing.md")

    (tmp_path / "dir" / "escape-dir").symlink_to(
        tmp_path / "sibling" / "missing",
        target_is_directory=True,
    )

    link(tmp_path / "dir" / "file.md", tmp_path / "hard-out.md")
    link(tmp_path / "outside.md", tmp_path / "dir" / "hard-in.md")

    found = relative_within(f"{tmp_path}/{path}", tmp_path / "dir")

    assert found == expect


def test_relative_within_accepts_relative_strings(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Assert that `relative_within` accepts strings, and finds relative paths from the
    working directory.
    """
    (tmp_path / "dir" / "sub").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    found = relative_within("dir/sub", "dir")
    expect = PurePath("sub")

    assert found == expect


@mark.parametrize(
    (
        "name",
        "spelling",
    ),
    [
        (
            "dir",
            "DIR",
        ),
        (
            normalize("NFC", "café"),
            normalize("NFD", "café"),
        ),
    ],
)
def test_relative_within_by_different_spelling(
    name: str,
    spelling: str,
    tmp_path: Path,
) -> None:
    """
    Assert that `relative_within` finds the directory when the path names it in a
    different spelling, on a file system that treats it as the same name, like macOS's
    default APFS.
    """
    (tmp_path / name).mkdir()

    if not (tmp_path / spelling).exists():
        skip(f"This file system doesn't treat {spelling!r} as {name!r}")

    found = relative_within(tmp_path / spelling / "file.md", tmp_path / name)
    expect = PurePath("file.md")

    assert found == expect


def test_relative_within_directory_through_symlink(tmp_path: Path) -> None:
    """
    Assert that `relative_within` finds the directory when it's given through a symlink
    to it.
    """
    (tmp_path / "dir" / "sub").mkdir(parents=True)
    (tmp_path / "link").symlink_to(tmp_path / "dir", target_is_directory=True)

    found = relative_within(tmp_path / "dir" / "sub", tmp_path / "link")
    expect = PurePath("sub")

    assert found == expect


def test_relative_within_is_none_when_directory_is_missing(tmp_path: Path) -> None:
    """
    Assert that `relative_within` is `None` when the directory doesn't exist, even for a
    path within it that doesn't exist either.
    """
    missing = tmp_path / "missing"

    found = relative_within(missing / "file.md", missing)

    assert found is None


@mark.parametrize(
    (
        "path",
        "target",
    ),
    [
        # The symlink appears at the end of the path, and leads to the directory.
        (
            "upload/x",
            "dir",
        ),
        # The symlink appears within the path, and leads to the directory's parent, so
        # the rest of the path names the directory.
        (
            "upload/x/dir/file.md",
            ".",
        ),
    ],
)
def test_relative_within_is_none_when_symlink_appears_after_resolving(
    path: str,
    target: str,
    tmp_path: Path,
) -> None:
    """
    Assert that `relative_within` doesn't follow a symlink that appears in the path
    after it's resolved, so a path that resolved outside of the directory can't be
    swapped into it.
    """
    (tmp_path / "dir").mkdir()
    (tmp_path / "upload").mkdir()

    (tmp_path / "dir" / "file.md").write_text(
        "Hello, world!\n",
        encoding="utf-8",
    )

    # Resolve the path before the symlink appears, as if it appeared in between.
    resolved = resolve(tmp_path / path)

    (tmp_path / "upload" / "x").symlink_to(
        tmp_path / target,
        target_is_directory=True,
    )

    with patch("rootle.relative_within.resolve", return_value=resolved):
        found = relative_within(
            tmp_path / path,
            tmp_path / "dir",
        )

    assert found is None


@windows_only
def test_relative_within_is_none_when_junction_appears_after_resolving_on_windows(
    tmp_path: Path,
) -> None:
    """
    Assert that `relative_within` doesn't follow a directory junction that appears in
    the path after it's resolved, so a path that resolved outside of the directory
    can't be swapped into it.
    """
    (tmp_path / "dir").mkdir()
    (tmp_path / "upload").mkdir()

    (tmp_path / "dir" / "file.md").write_text(
        "Hello, world!\n",
        encoding="utf-8",
    )

    path = tmp_path / "upload" / "x" / "dir" / "file.md"

    # Resolve the path before the junction appears, as if it appeared in between.
    resolved = resolve(path)

    run(
        [
            "cmd",
            "/c",
            "mklink",
            "/J",
            str(tmp_path / "upload" / "x"),
            str(tmp_path),
        ],
        check=True,
        stdout=DEVNULL,
    )

    with patch("rootle.relative_within.resolve", return_value=resolved):
        found = relative_within(
            path,
            tmp_path / "dir",
        )

    assert found is None


@mark.parametrize(
    (
        "path",
        "unreadable",
        "expect",
    ),
    [
        (
            "dir/sub/file.md",
            "dir/sub/file.md",
            PurePath("sub/file.md"),
        ),
        (
            "dir/sub/file.md",
            "dir/sub",
            PurePath("sub/file.md"),
        ),
        (
            # A part outside of the directory doesn't make the path within it.
            "other/file.md",
            "other",
            None,
        ),
    ],
)
def test_relative_within_judges_unreadable_part_by_parents(
    expect: PurePath | None,
    path: str,
    tmp_path: Path,
    unreadable: str,
) -> None:
    """
    Assert that `relative_within` judges the path by its parents when the identity of a
    part of it reads as zero, like when Windows can't open it, because the directory's
    identity could be read, so that part can't be the directory.
    """
    (tmp_path / "dir" / "sub").mkdir(parents=True)

    (tmp_path / "dir" / "sub" / "file.md").write_text(
        "Hello, world!\n",
        encoding="utf-8",
    )

    (tmp_path / "other").mkdir()

    (tmp_path / "other" / "file.md").write_text(
        "Hello, world!\n",
        encoding="utf-8",
    )

    zero = stat_result((0o040755, 0, 0, 1, 0, 0, 64, 0, 0, 0))

    def fake_stat(
        p: PathLike[str] | str,
        *,
        follow_symlinks: bool = True,
    ) -> stat_result:
        if Path(p) == tmp_path / unreadable:
            return zero

        return stat(
            p,
            follow_symlinks=follow_symlinks,
        )

    with (
        patch("rootle.status.stat", side_effect=fake_stat),
        patch("rootle._status_of_resolved.stat", side_effect=fake_stat),
    ):
        found = relative_within(tmp_path / path, tmp_path / "dir")

    assert found == expect


@posix_only
def test_relative_within_keeps_letter_case_on_posix(tmp_path: Path) -> None:
    """
    Assert that `relative_within` keeps the letter case that the path gave it, on a
    case-insensitive file system like macOS's default APFS.
    """
    (tmp_path / "dir" / "sub").mkdir(parents=True)

    if not (tmp_path / "dir" / "SUB").exists():
        skip("This file system is case-sensitive, so 'SUB' isn't 'sub'")

    found = relative_within(tmp_path / "dir" / "SUB", tmp_path / "dir")
    expect = PurePath("SUB")

    assert found == expect


def test_relative_within_raises_for_directory_file(tmp_path: Path) -> None:
    """
    Assert that `relative_within` raises `NotADirectoryError` when the directory is a
    file, because nothing can be within a file, naming the directory as it was given.
    """
    (tmp_path / "file.md").write_text(
        "Hello, world!\n",
        encoding="utf-8",
    )

    directory = tmp_path / "file.md"

    with raises(NotADirectoryError) as ex:
        relative_within(directory / "child.md", directory)

    expect = str(directory)

    assert ex.value.filename == expect


def test_relative_within_raises_for_directory_file_with_trailing_separator(
    tmp_path: Path,
) -> None:
    """
    Assert that `relative_within` raises `NotADirectoryError` when the directory is a
    file given with a trailing separator, which says that it's a directory, naming the
    directory as it was given.
    """
    (tmp_path / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    directory = f"{tmp_path / 'file.md'}/"

    with raises(NotADirectoryError) as ex:
        relative_within(tmp_path / "file.md", directory)

    assert ex.value.filename == directory


@mark.parametrize(
    (
        "path",
        "directory",
    ),
    [
        (
            "",
            ".",
        ),
        (
            ".",
            "",
        ),
    ],
)
def test_relative_within_raises_for_empty_path(
    directory: str,
    monkeypatch: MonkeyPatch,
    path: str,
    tmp_path: Path,
) -> None:
    """
    Assert that `relative_within` raises `FileNotFoundError` when the path or the
    directory is empty, which names nothing, rather than reading it as the working
    directory.
    """
    monkeypatch.chdir(tmp_path)

    with raises(FileNotFoundError) as ex:
        relative_within(
            path,
            directory,
        )

    assert ex.value.filename == ""


@mark.parametrize(
    "suffix",
    [
        "/",
        "/.",
    ],
)
@mark.parametrize(
    "directory",
    [
        ".",
        "missing",
    ],
)
def test_relative_within_raises_for_file_with_trailing_separator(
    directory: str,
    suffix: str,
    tmp_path: Path,
) -> None:
    """
    Assert that `relative_within` raises `NotADirectoryError` when the path is a file
    given with a trailing separator or `.`, which says that it's a directory, naming the
    path as it was given, even when the directory doesn't exist.
    """
    (tmp_path / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    path = f"{tmp_path / 'file.md'}{suffix}"

    with raises(NotADirectoryError) as ex:
        relative_within(
            path,
            tmp_path / directory,
        )

    assert ex.value.filename == path


@posix_only
@mark.parametrize(
    (
        "path",
        "directory",
        "named",
    ),
    [
        (
            "alias/file.md",
            ".",
            "alias/file.md",
        ),
        (
            "file.md",
            "alias",
            "alias",
        ),
    ],
)
def test_relative_within_raises_for_symlink_loop_on_posix(
    directory: str,
    named: str,
    path: str,
    tmp_path: Path,
) -> None:
    """
    Assert that `relative_within` raises `OSError` with `ELOOP` when the symlinks of
    the path or the directory loop, naming it as it was given rather than where it
    leads.
    """
    (tmp_path / "loop").symlink_to("loop")
    (tmp_path / "alias").symlink_to("loop")

    with raises(OSError) as ex:
        relative_within(tmp_path / path, tmp_path / directory)

    expect = str(tmp_path / named)

    assert ex.value.errno == ELOOP
    assert ex.value.filename == expect


@windows_only
@mark.parametrize(
    (
        "path",
        "directory",
        "named",
    ),
    [
        (
            "alias/file.md",
            ".",
            "alias/file.md",
        ),
        (
            "file.md",
            "alias",
            "alias",
        ),
    ],
)
def test_relative_within_raises_for_symlink_loop_on_windows(
    directory: str,
    named: str,
    path: str,
    tmp_path: Path,
) -> None:
    """
    Assert that `relative_within` raises `OSError` with Windows' own error code when
    the symlinks of the path or the directory loop, naming it as it was given rather
    than where it leads.
    """
    # Assure pyright that `winerror` exists.
    assert sys.platform == "win32"

    (tmp_path / "loop").symlink_to("loop")
    (tmp_path / "alias").symlink_to("loop")

    with raises(OSError) as ex:
        relative_within(tmp_path / path, tmp_path / directory)

    expect = str(tmp_path / named)

    assert ex.value.winerror == winerror.SYMLINK_LOOP
    assert ex.value.filename == expect


@mark.parametrize(
    "device",
    [
        0,  # Like when Windows can't open the file
        64,  # Like a file system that never reports file numbers
    ],
)
def test_relative_within_raises_when_directory_identity_is_unreadable(
    device: int,
    tmp_path: Path,
) -> None:
    """
    Assert that `relative_within` raises `PermissionError` when the directory's number
    reads as zero, like when Windows can't open it, whatever its device, rather than
    passing it as an identity that every such file shares. Names the directory as it
    was given.
    """
    (tmp_path / "dir").mkdir()

    (tmp_path / "link").symlink_to(
        tmp_path / "dir",
        target_is_directory=True,
    )

    directory = tmp_path / "link"
    zero = stat_result((0o040755, 0, device, 1, 0, 0, 64, 0, 0, 0))

    with (
        patch("rootle.status.stat", return_value=zero),
        raises(PermissionError) as ex,
    ):
        relative_within(
            tmp_path / "dir" / "file.md",
            directory,
        )

    expect = str(directory)

    assert ex.value.errno == EACCES
    assert ex.value.filename == expect


@mark.parametrize(
    (
        "path",
        "directory",
        "named",
    ),
    [
        (
            "noperm/x",
            "dir",
            "noperm/x",
        ),
        (
            # `link` might lead anywhere, so ".." can't be resolved without reading it.
            "noperm/link/../../dir/x",
            "dir",
            "noperm/link/../../dir/x",
        ),
        (
            "dir/x",
            "noperm/sub",
            "noperm/sub",
        ),
    ],
)
def test_relative_within_raises_when_permission_denied(
    directory: str,
    named: str,
    path: str,
    tmp_path: Path,
) -> None:
    """
    Assert that `relative_within` raises `PermissionError` when the path or the
    directory is through a directory that can't be read, naming it as it was given,
    rather than guessing where it leads.
    """
    if not can_chmod_deny_search(tmp_path):
        skip("chmod can't deny search permission here, like on Windows or to root")

    (tmp_path / "dir").mkdir()
    (tmp_path / "noperm" / "sub").mkdir(parents=True)
    (tmp_path / "noperm" / "link").symlink_to(tmp_path / "elsewhere" / "deep")
    (tmp_path / "noperm").chmod(0)

    try:
        with raises(PermissionError) as ex:
            relative_within(f"{tmp_path}/{path}", f"{tmp_path}/{directory}")

    finally:
        (tmp_path / "noperm").chmod(0o755)

    expect = f"{tmp_path}/{named}"

    assert ex.value.filename == expect


def test_relative_within_raises_when_rechecking_part_fails(tmp_path: Path) -> None:
    """
    Assert that `relative_within` raises when a part of the path resolves, but can't be
    resolved again when it's checked, like when it changes in between, naming the path
    as it was given rather than the part. A safety check that can't be made must fail
    rather than pass.
    """
    (tmp_path / "dir").mkdir()
    path = tmp_path / "dir" / "file.md"
    error = PermissionError(EACCES, "Permission denied")

    with (
        patch("rootle.relative_within.realpath", side_effect=error),
        raises(OSError) as ex,
    ):
        relative_within(
            path,
            tmp_path / "dir",
        )

    expect = str(path)

    assert ex.value.errno == EACCES
    assert ex.value.filename == expect


@mark.parametrize(
    "error",
    [
        PermissionError(EACCES, "Denied"),
        _UnreachableNetworkPathError(),
    ],
)
def test_relative_within_raises_when_stat_fails(
    error: OSError,
    tmp_path: Path,
) -> None:
    """
    Assert that `relative_within` raises when a part of the path resolves but can't be
    `stat`-ed, like when it changes in between or when Windows can't reach a network
    path, which it reports as missing, naming the path as it was given rather than the
    part. A safety check that can't be made must fail rather than pass.
    """
    (tmp_path / "dir").mkdir()
    (tmp_path / "dir" / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    path = tmp_path / "dir" / "file.md"

    def fake_stat(
        p: PathLike[str] | str,
        *,
        follow_symlinks: bool = True,
    ) -> stat_result:
        if Path(p) == path:
            raise error

        return stat(
            p,
            follow_symlinks=follow_symlinks,
        )

    with (
        patch("rootle._status_of_resolved.stat", side_effect=fake_stat),
        raises(OSError) as ex,
    ):
        relative_within(
            path,
            tmp_path / "dir",
        )

    expect = str(path)

    assert ex.value.errno == error.errno
    assert ex.value.filename == expect


@posix_only
def test_relative_within_raises_when_stepping_up_from_file_on_posix(
    tmp_path: Path,
) -> None:
    """
    Assert that `relative_within` raises `NotADirectoryError` for a ".." after a file,
    naming the path as it was given, because there's nowhere for it to step up from.
    """
    (tmp_path / "dir").mkdir()
    (tmp_path / "dir" / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    path = tmp_path / "dir" / "file.md" / "child" / ".." / "other.md"

    with raises(NotADirectoryError) as ex:
        relative_within(path, tmp_path / "dir")

    expect = str(path)

    assert ex.value.filename == expect


@mark.skipif(
    sys.platform == "win32",
    reason="Removes the working directory, which Windows won't allow",
)
def test_relative_within_raises_when_working_directory_is_gone_for_directory_on_posix(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Assert that `relative_within` raises for a relative directory when the working
    directory is gone, rather than saying that the directory doesn't exist, naming the
    directory as it was given.
    """
    working = tmp_path / "working"
    working.mkdir()
    monkeypatch.chdir(working)
    working.rmdir()

    with raises(FileNotFoundError) as ex:
        relative_within(tmp_path, ".")

    assert ex.value.filename == "."


@mark.skipif(
    sys.platform == "win32",
    reason="Removes the working directory, which Windows won't allow",
)
def test_relative_within_raises_when_working_directory_is_gone_on_posix(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Assert that `relative_within` raises for a relative path when the working directory
    is gone, rather than saying that it isn't within the directory, naming the path as
    it was given. A safety check that can't be made must fail rather than pass.
    """
    working = tmp_path / "working"
    working.mkdir()
    monkeypatch.chdir(working)
    working.rmdir()

    with raises(FileNotFoundError) as ex:
        relative_within("doc.md", tmp_path)

    assert ex.value.filename == "doc.md"


@windows_only
def test_relative_within_steps_up_from_file_on_windows(tmp_path: Path) -> None:
    """
    Assert that `relative_within` steps up from a file by name on Windows, because
    that's how Windows itself resolves a ".." after a file.
    """
    (tmp_path / "dir").mkdir()
    (tmp_path / "dir" / "file.md").write_text("Hello, world!\n", encoding="utf-8")

    found = relative_within(
        tmp_path / "dir" / "file.md" / "child" / ".." / "other.md",
        tmp_path / "dir",
    )
    expect = PurePath("file.md", "other.md")

    assert found == expect


@windows_only
def test_relative_within_uses_stored_letter_case_on_windows(tmp_path: Path) -> None:
    """
    Assert that `relative_within` uses the letter case that the file system stores on
    Windows, rather than the letter case that the path gave it.
    """
    (tmp_path / "dir" / "sub").mkdir(parents=True)

    found = relative_within(tmp_path / "dir" / "SUB", tmp_path / "dir")
    expect = PurePath("sub")

    assert found == expect
