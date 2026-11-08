from os import PathLike, stat
from stat import S_ISREG

from .types import Fingerprint


def fingerprint(path: PathLike[str] | str) -> Fingerprint | None:
    """
    Fingerprint the file at `path` without reading it, so that a change to it can be
    seen by comparing fingerprints.

    It's a single [`os.stat`][os.stat], so it's cheap enough to call on many paths
    over and over: for example, to watch them for changes.

    **Linux & macOS:** A `..` after a file returns `None`.

    **Windows:** A `..` after a file steps up. Windows can't read the number of a file
    that it can't open, like one that's locked or whose permissions deny it, so its
    `inode` is `0`. See [`Fingerprint`][rootle.types.fingerprint.Fingerprint] for why
    a rewrite that puts the modification time back isn't seen.

    Args:
        path: Path to the file.

    Returns:
        The file's [fingerprint][rootle.types.fingerprint.Fingerprint], or `None` when
        it can't be found or read.

    Examples:
        ```python
        before = fingerprint("/docs/guide.md")

        # ...time passes...

        if fingerprint("/docs/guide.md") != before:
            print("guide.md changed")
        ```
    """
    try:
        found = stat(path)

    except OSError, ValueError:
        return None

    if not S_ISREG(found.st_mode):
        return Fingerprint(
            changed=None,
            device=found.st_dev,
            inode=found.st_ino,
            mode=found.st_mode,
            modified=None,
            size=None,
        )

    return Fingerprint(
        changed=found.st_ctime_ns,
        device=found.st_dev,
        inode=found.st_ino,
        mode=found.st_mode,
        modified=found.st_mtime_ns,
        size=found.st_size,
    )
