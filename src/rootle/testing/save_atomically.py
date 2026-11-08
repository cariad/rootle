from os import replace
from pathlib import Path
from secrets import token_hex


def save_atomically(path: Path, body: str) -> None:
    """
    Replace a file with a new one, like an editor that saves atomically, so that its
    path names a different file.

    The new file is written beside the old one, under a short, hidden name of its own,
    like `.1f2e3d4c5b6a7980.new`, and then moved over it with
    [`os.replace`][os.replace]. The new name is created exclusively, so it never
    follows a symlink or replaces a file that's already there. When the new file can't
    be written or moved, it's removed.

    The path then names another file, with another
    [identity][rootle.types.identity.Identity], so a change is seen even when the new
    file has the same size and times as the old one. The new file has the permissions
    of any file that's created, not the old one's. To rewrite the same file instead,
    use [`edit`][rootle.testing.edit.edit].

    Args:
        path: Path to the file to replace.
        body: Text to write, as UTF-8.

    Raises:
        OSError: When the new file can't be written or moved over the old one.
        ValueError: When `path` has no name, like `/`.

    Examples:
        ```python
        def test_sees_atomic_save(tmp_path: Path) -> None:
            path = tmp_path / "file.md"
            path.write_text("Hello, world!", encoding="utf-8")
            before = identity(path)

            save_atomically(path, "Hello, world!")

            assert identity(path) != before
        ```
    """
    # A name of its own, which can't be `path` itself, even when `path` ends in `.new`,
    # and is short whatever `path` is called, so that it's never too long to create.
    new = path.with_name(f".{token_hex(8)}.new")

    # Create the file exclusively, so that it never follows a symlink or replaces a file
    # that's already there, and isn't removed when that fails.
    file = new.open("x", encoding="utf-8")

    try:
        with file:
            file.write(body)

        replace(new, path)

    except BaseException:
        new.unlink()
        raise
