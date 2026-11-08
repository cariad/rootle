from pathlib import Path
from stat import S_IMODE


def snapshot(directory: Path) -> dict[Path, tuple[bytes, int] | None]:
    """
    Snapshot everything within a directory, so that a test can assert that nothing
    changed, or that it matches what's expected: every path, and the body and
    permissions of every file.

    Symlinks to directories aren't followed into. A symlink to a file is snapshot as
    the file that it leads to.

    Args:
        directory: Path to the directory to snapshot.

    Returns:
        A dictionary of every path within `directory`, relative to it. Each file's value
        is its body and its permission bits ([`S_IMODE`][stat.S_IMODE] of its mode).
        Anything else's, like a directory's, is `None`.

    Raises:
        OSError: When anything within `directory` can't be listed or read.

    Examples:
        ```python
        def test_changes_nothing_on_failure(tmp_path: Path) -> None:
            before = snapshot(tmp_path)

            with raises(ValueError):
                build(tmp_path)

            assert snapshot(tmp_path) == before
        ```
    """
    return {
        p.relative_to(directory): (
            (p.read_bytes(), S_IMODE(p.stat().st_mode)) if p.is_file() else None
        )
        for p in directory.rglob("*")
    }
