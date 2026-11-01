from pathlib import Path

from pytest import mark

from rootle import ends_like_directory
from tests.marks import posix_only, windows_only


@mark.parametrize(
    (
        "path",
        "expect",
    ),
    [
        (
            "docs/",
            True,
        ),
        (
            "docs/.",
            True,
        ),
        (
            "docs/./",
            True,
        ),
        (
            "docs/..",
            True,
        ),
        (
            "/",
            True,
        ),
        (
            ".",
            True,
        ),
        (
            "..",
            True,
        ),
        (
            "docs",
            False,
        ),
        (
            "docs.",
            False,
        ),
        (
            "docs/.hidden",
            False,
        ),
        (
            "docs/..md",
            False,
        ),
        (
            "docs/...",
            False,
        ),
        (
            "",
            False,
        ),
    ],
)
def test_ends_like_directory(path: str, expect: bool) -> None:
    """
    Assert that `ends_like_directory` is `True` only when the path ends with a separator
    or a `.` or `..` name.
    """
    found = ends_like_directory(path)

    assert found is expect


def test_ends_like_directory_accepts_path_like() -> None:
    """
    Assert that `ends_like_directory` accepts a path-like object, which can't keep a
    directory's ending.
    """
    found = ends_like_directory(Path("docs/"))

    assert found is False


@mark.parametrize(
    "path",
    [
        "docs\\",
        "docs\\.",
        "docs\\..",
    ],
)
@posix_only
def test_ends_like_directory_ignores_backslash_on_posix(path: str) -> None:
    """
    Assert that `ends_like_directory` doesn't read a backslash as a separator on POSIX,
    where it's an ordinary character in a name.
    """
    found = ends_like_directory(path)

    assert found is False


@mark.parametrize(
    "path",
    [
        "C:.",
        "C:..",
    ],
)
@posix_only
def test_ends_like_directory_ignores_drive_on_posix(path: str) -> None:
    """
    Assert that `ends_like_directory` doesn't read a drive on POSIX, where `C:` is an
    ordinary start to a name.
    """
    found = ends_like_directory(path)

    assert found is False


@mark.parametrize(
    "path",
    [
        "docs\\",
        "docs\\.",
        "docs\\..",
    ],
)
@windows_only
def test_ends_like_directory_reads_backslash_as_separator_on_windows(
    path: str,
) -> None:
    """Assert that `ends_like_directory` reads a backslash as a separator on Windows."""
    found = ends_like_directory(path)

    assert found is True


@mark.parametrize(
    (
        "path",
        "expect",
    ),
    [
        (
            "C:.",
            True,
        ),
        (
            "C:..",
            True,
        ),
        (
            "C:",
            False,
        ),
        (
            "C:docs",
            False,
        ),
        (
            "\\\\server\\share",
            False,
        ),
        (
            "\\\\server\\share\\",
            True,
        ),
    ],
)
@windows_only
def test_ends_like_directory_strips_drive_on_windows(path: str, expect: bool) -> None:
    """
    Assert that `ends_like_directory` takes the drive or share off a path on Windows
    before reading its last name.
    """
    found = ends_like_directory(path)

    assert found is expect
