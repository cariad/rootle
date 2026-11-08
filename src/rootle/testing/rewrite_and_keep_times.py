import sys
from os import utime
from pathlib import Path


def rewrite_and_keep_times(path: Path, body: str) -> None:
    """
    Rewrite a file and put its access and modification times back, like `cp -p` or
    `touch -r` does, so that only its change time (`st_ctime_ns`) tells.

    Write a `body` of the same size as the file's, and nothing but the change time can
    tell that the file was rewritten. The file is written until its change time has
    moved on, in case the clock is too coarse to tell this write from the last.

    The file is written in place, so it's still the same file, with the same
    [identity][rootle.types.identity.Identity].

    **Linux & macOS:** Setting the times back changes the change time, which can't be
    set, so the rewrite is always seen there.

    **Windows:** Raises `NotImplementedError`, because Windows reports a file's
    creation time as its change time, which a rewrite never moves on.

    Args:
        path: Path to the file to rewrite.
        body: Text to write, as UTF-8.

    Raises:
        NotImplementedError: On Windows.
        OSError: When the file can't be read, written or have its times set.

    Examples:
        ```python
        def test_sees_rewrite_and_keep_times(tmp_path: Path) -> None:
            path = tmp_path / "file.md"
            path.write_text("Hello, world!", encoding="utf-8")
            before = fingerprint(path)

            rewrite_and_keep_times(path, "Hello, rootle!")

            assert fingerprint(path) != before
        ```
    """
    if sys.platform == "win32":  # pragma: windows-only
        raise NotImplementedError(
            "Windows reports a file's creation time as its change time, which a "
            "rewrite never moves on"
        )

    else:  # pragma: posix-only
        before = path.stat()

        while path.stat().st_ctime_ns == before.st_ctime_ns:
            path.write_text(body, encoding="utf-8")
            utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
