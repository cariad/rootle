from pathlib import Path
from stat import S_IMODE
from typing import NoReturn


def _raise(error: OSError) -> NoReturn:
    """Raise `error`, so that a directory that can't be listed isn't skipped."""
    raise error


def snapshot(directory: Path) -> dict[Path, tuple[bytes, int] | None]:
    """
    Snapshot everything within a directory, so that a test can assert that nothing
    changed, or that it matches what's expected: every path, and the body and
    permissions of every file.

    Symlinks to directories aren't followed into. A symlink to a file is snapshot as
    the file that it leads to, and one that's broken or loops is snapshot like a
    directory, because it has no body.

    Every directory must be listed, so one that can't be raises an error rather than
    being left out, which would hide any change within it.

    Args:
        directory: Path to the directory to snapshot.

    Returns:
        A dictionary of every path within `directory`, relative to it. Each file's value
        is its body and its permission bits ([`S_IMODE`][stat.S_IMODE] of its mode).
        Anything else's, like a directory's, is `None`.

    Raises:
        OSError: When `directory` doesn't exist or isn't a directory, or when anything
            within it can't be listed or read.

    Examples:
        ```python
        def test_changes_nothing_on_failure(tmp_path: Path) -> None:
            before = snapshot(tmp_path)

            with raises(ValueError):
                build(tmp_path)

            assert snapshot(tmp_path) == before
        ```
    """
    found: dict[Path, tuple[bytes, int] | None] = {}

    # `rglob` skips a directory that can't be listed, so walk instead, raising.
    for parent, directories, files in directory.walk(on_error=_raise):
        for name in (*directories, *files):
            path = parent / name

            found[path.relative_to(directory)] = (
                (path.read_bytes(), S_IMODE(path.stat().st_mode))
                if path.is_file()
                else None
            )

    return found
