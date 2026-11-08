from os import utime
from pathlib import Path

_SECOND = 1_000_000_000
"""One second, in nanoseconds."""


def edit(path: Path, body: str) -> None:
    """
    Rewrite a file, like someone editing it, and set its modification time to a second
    after what it was.

    Pushing the modification time forward means that the edit is always seen, even at
    the same size, when the clock or the file system's timestamps are too coarse to tell
    two writes apart.

    The file is written in place, so it's still the same file, with the same
    [identity][rootle.types.identity.Identity]. To replace it with another file, use
    [`save_atomically`][rootle.testing.save_atomically.save_atomically].

    Args:
        path: Path to the file to rewrite.
        body: Text to write, as UTF-8.

    Raises:
        OSError: When the file can't be read, written or have its times set.

    Examples:
        ```python
        def test_sees_edit(tmp_path: Path) -> None:
            path = tmp_path / "file.md"
            path.write_text("Hello, world!", encoding="utf-8")
            before = fingerprint(path)

            edit(path, "Hello, rootle!")

            assert fingerprint(path) != before
        ```
    """
    modified = path.stat().st_mtime_ns + _SECOND
    path.write_text(body, encoding="utf-8")
    utime(path, ns=(modified, modified))
