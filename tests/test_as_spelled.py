from os import stat_result
from pathlib import Path, PurePath, PurePosixPath
from unicodedata import normalize
from unittest.mock import patch

from pytest import MonkeyPatch, mark, skip

from rootle import as_spelled, relative_within
from rootle.testing import can_chmod_deny_listing, is_treated_as_same_name


@mark.parametrize(
    (
        "path",
        "expect",
    ),
    [
        (
            "",
            ".",
        ),
        (
            ".",
            ".",
        ),
        (
            "sub",
            "sub",
        ),
        (
            "sub/file.md",
            "sub/file.md",
        ),
        (
            # A trailing separator says nothing about the name.
            "sub/",
            "sub",
        ),
    ],
)
def test_as_spelled(path: str, expect: str, tmp_path: Path) -> None:
    """
    Assert that `as_spelled` keeps names that are already spelled the way they're
    listed, and gives `.` for the directory itself.
    """
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "file.md").write_text("Hello, world!\n", encoding="utf-8")

    found = as_spelled(path, tmp_path)
    expected = PurePath(expect)

    assert found == expected


def test_as_spelled_accepts_relative_strings_and_paths(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Assert that `as_spelled` accepts a `PurePath` and a directory relative to the
    working directory.
    """
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path.parent)

    found = as_spelled(PurePosixPath("sub/file.md"), tmp_path.name)
    expect = PurePath("sub/file.md")

    assert found == expect


@mark.parametrize(
    (
        "name",
        "spelling",
    ),
    [
        (
            "sub",
            "SUB",
        ),
        (
            normalize("NFC", "café"),
            normalize("NFD", "café"),
        ),
    ],
)
def test_as_spelled_by_different_spelling(
    name: str,
    spelling: str,
    tmp_path: Path,
) -> None:
    """
    Assert that `as_spelled` spells each name the way the file system lists it, on a
    file system that treats another spelling as the same name, like macOS's default
    APFS.
    """
    if not is_treated_as_same_name(
        tmp_path,
        name,
        spelling,
    ):
        skip(f"This file system doesn't treat {spelling!a} as {name!a}")

    (tmp_path / name / name).mkdir(parents=True)
    (tmp_path / name / name / "file.md").write_text("Hello, world!\n", encoding="utf-8")

    found = as_spelled(f"{spelling}/{spelling}/file.md", tmp_path)
    expect = PurePath(name, name, "file.md")

    assert found == expect


def test_as_spelled_does_not_match_name_that_starts_the_same(tmp_path: Path) -> None:
    """
    Assert that `as_spelled` matches only the directory that's named, and not another
    whose name starts with the same letters.
    """
    if not is_treated_as_same_name(tmp_path, "sub", "SUB"):
        skip("This file system doesn't treat 'SUB' as 'sub'")

    (tmp_path / "subway").mkdir()
    (tmp_path / "sub").mkdir()

    found = as_spelled("SUB", tmp_path)
    expect = PurePath("sub")

    assert found == expect


@mark.parametrize(
    (
        "path",
        "expect",
    ),
    [
        (
            "missing",
            "missing",
        ),
        (
            "missing/FILE.md",
            "missing/FILE.md",
        ),
        (
            # `..` is never listed.
            "..",
            "..",
        ),
        (
            # `file.md` is a file, not a directory, so nothing can be within it.
            "file.md/FILE.md",
            "file.md/FILE.md",
        ),
        (
            # `dangling` is a symlink to a missing file.
            "dangling/FILE.md",
            "dangling/FILE.md",
        ),
        (
            # `loop` is a symlink to itself.
            "loop/FILE.md",
            "loop/FILE.md",
        ),
        (
            "na\0me/FILE.md",
            "na\0me/FILE.md",
        ),
    ],
)
def test_as_spelled_keeps_names_that_cannot_be_found(
    path: str,
    expect: str,
    tmp_path: Path,
) -> None:
    """
    Assert that `as_spelled` keeps the spelling of a name that can't be found, and of
    every name after it, rather than raising.
    """
    (tmp_path / "file.md").write_text("Hello, world!\n", encoding="utf-8")
    (tmp_path / "dangling").symlink_to("missing", target_is_directory=True)
    (tmp_path / "loop").symlink_to("loop", target_is_directory=True)

    found = as_spelled(path, tmp_path)
    expected = PurePath(expect)

    assert found == expected


def test_as_spelled_keeps_names_when_directory_is_missing(tmp_path: Path) -> None:
    """Assert that `as_spelled` keeps every name when the directory doesn't exist."""
    found = as_spelled("SUB/FILE.md", tmp_path / "missing")
    expect = PurePath("SUB/FILE.md")

    assert found == expect


def test_as_spelled_keeps_names_when_identity_is_unreadable(tmp_path: Path) -> None:
    """
    Assert that `as_spelled` keeps every name when the identity of the file it names
    can't be read, like when Windows can't open it, rather than matching it to another
    file whose identity can't be read either.
    """
    (tmp_path / "sub").mkdir()
    unreadable = stat_result((0o040755, 0, 0, 1, 0, 0, 64, 0, 0, 0))

    with patch("rootle.as_spelled.stat", return_value=unreadable):
        found = as_spelled("SUB", tmp_path)

    expect = PurePath("SUB")

    assert found == expect


def test_as_spelled_keeps_names_when_listing_is_denied(tmp_path: Path) -> None:
    """
    Assert that `as_spelled` keeps every name within a directory that can't be listed,
    rather than raising.
    """
    if not can_chmod_deny_listing(tmp_path):
        skip("chmod can't deny listing here, like on Windows or to root")

    if not is_treated_as_same_name(tmp_path, "file.md", "FILE.md"):
        skip("This file system doesn't treat 'FILE.md' as 'file.md'")

    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "file.md").write_text("Hello, world!\n", encoding="utf-8")

    # Search, but not read, so `sub/FILE.md` can be found but `sub` can't be listed.
    (tmp_path / "sub").chmod(0o300)

    try:
        found = as_spelled("sub/FILE.md", tmp_path)

    finally:
        (tmp_path / "sub").chmod(0o755)

    expect = PurePath("sub/FILE.md")

    assert found == expect


def test_as_spelled_spells_symlink_as_sibling_it_leads_to(tmp_path: Path) -> None:
    """
    Assert that `as_spelled` never matches a symlink, so a name that's a symlink to a
    sibling is spelled as the sibling.
    """
    (tmp_path / "real").mkdir()
    (tmp_path / "alias").symlink_to("real", target_is_directory=True)

    found = as_spelled("alias", tmp_path)
    expect = PurePath("real")

    assert found == expect


def test_as_spelled_spells_symlink_target(tmp_path: Path) -> None:
    """
    Assert that the path that `relative_within` gives for a directory named through a
    symlink, spelled with the symlink's target, is spelled the way the file system lists
    the directory, on a file system that ignores case, like macOS's default APFS.
    """
    if not is_treated_as_same_name(tmp_path, "posts", "Posts"):
        skip("This file system doesn't treat 'Posts' as 'posts'")

    (tmp_path / "posts").mkdir()
    (tmp_path / "latest").symlink_to("Posts", target_is_directory=True)
    relative = relative_within(tmp_path / "latest", tmp_path)
    assert relative is not None

    found = as_spelled(relative, tmp_path)
    expect = PurePath("posts")

    assert found == expect


def test_as_spelled_stops_at_symlink_that_leads_elsewhere(tmp_path: Path) -> None:
    """
    Assert that `as_spelled` never matches a symlink, so a name that's a symlink that
    leads out of its directory can't be found, and keeps its spelling and every name
    after it.
    """
    if not is_treated_as_same_name(tmp_path, "sub", "SUB"):
        skip("This file system doesn't treat 'SUB' as 'sub'")

    (tmp_path / "outside" / "sub").mkdir(parents=True)
    (tmp_path / "inside").mkdir()
    (tmp_path / "inside" / "linked").symlink_to(
        tmp_path / "outside",
        target_is_directory=True,
    )

    found = as_spelled("INSIDE/linked/SUB", tmp_path)
    expect = PurePath("inside/linked/SUB")

    assert found == expect
