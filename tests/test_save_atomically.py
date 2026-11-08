from pathlib import Path
from unittest.mock import patch

from pytest import mark, raises, skip

from rootle import identity
from rootle.testing import save_atomically


@mark.parametrize(
    "name",
    [
        "file.md",
        "file",
        # A name that the new file's could have been, if it were only given `.new`.
        "file.new",
        ".hidden",
    ],
)
def test_save_atomically(name: str, tmp_path: Path) -> None:
    """
    Assert that `save_atomically` replaces a file with another one with the new body,
    and leaves nothing else behind.
    """
    path = tmp_path / name
    path.write_text("Hello, world!\n", encoding="utf-8")
    before = identity(path)

    # Keep the old file, so that its number can't be given to the new one.
    kept = tmp_path / "kept.md"
    kept.hardlink_to(path)

    save_atomically(path, "Hello, world!\n")

    body = path.read_text(encoding="utf-8")
    after = identity(path)
    names = sorted(p.name for p in tmp_path.iterdir())
    expect_names = sorted([name, "kept.md"])

    assert body == "Hello, world!\n"
    assert before is not None
    assert after is not None
    assert after != before
    assert names == expect_names


def test_save_atomically_never_follows_symlink(tmp_path: Path) -> None:
    """
    Assert that `save_atomically` raises `FileExistsError`, rather than following a
    symlink at the new file's name, and leaves every file as it was.
    """
    path = tmp_path / "file.md"
    path.write_text("Hello, world!\n", encoding="utf-8")
    target = tmp_path / "target.md"
    target.write_text("Target\n", encoding="utf-8")
    (tmp_path / ".0123.new").symlink_to("target.md")

    with (
        patch("rootle.testing.save_atomically.token_hex", return_value="0123"),
        raises(FileExistsError),
    ):
        save_atomically(path, "Hello, rootle!\n")

    body = path.read_text(encoding="utf-8")
    target_body = target.read_text(encoding="utf-8")
    names = sorted(p.name for p in tmp_path.iterdir())

    expect_names = [
        ".0123.new",
        "file.md",
        "target.md",
    ]

    assert body == "Hello, world!\n"
    assert target_body == "Target\n"
    assert names == expect_names


def test_save_atomically_of_longest_name(tmp_path: Path) -> None:
    """
    Assert that `save_atomically` replaces a file whose name is as long as most file
    systems allow, because the new file's name doesn't grow with it.
    """
    path = tmp_path / ("a" * 255)

    try:
        path.write_text("Hello, world!\n", encoding="utf-8")

    except OSError:
        skip("This file system can't name a file with 255 characters here")

    before = identity(path)

    save_atomically(path, "Hello, rootle!\n")

    body = path.read_text(encoding="utf-8")
    after = identity(path)

    assert body == "Hello, rootle!\n"
    assert before is not None
    assert after is not None
    assert after != before


def test_save_atomically_removes_new_file_when_replacing_fails(tmp_path: Path) -> None:
    """
    Assert that `save_atomically` raises when the new file can't be moved over the old
    one, like when the old one is a directory, and removes the new file.
    """
    path = tmp_path / "dir.md"
    path.mkdir()
    (path / "child.md").write_text("Hello, world!\n", encoding="utf-8")

    with raises(OSError):
        save_atomically(path, "Hello, rootle!\n")

    names = sorted(p.name for p in tmp_path.iterdir())

    expect_names = [
        "dir.md",
    ]

    assert names == expect_names
