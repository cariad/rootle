from os import replace
from pathlib import Path


def save_atomically(path: Path, body: str) -> None:
    """
    Replace a file with a new one, like an editor that saves atomically, so that its
    path names a different file.

    The new file is written beside the old one, with the old one's suffix replaced by
    `.new`, like `README.new` for `README.md`, and then moved over it with
    [`os.replace`][os.replace]. Anything already at that name is replaced too.

    The path then names another file, with another
    [identity][rootle.types.identity.Identity], so a change is seen even when the new
    file has the same size and times as the old one. To rewrite the same file instead,
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
    new = path.with_suffix(".new")
    new.write_text(body, encoding="utf-8")
    replace(new, path)
