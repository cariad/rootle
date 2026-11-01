from os import PathLike, altsep, fspath, sep
from os.path import splitdrive


def ends_like_directory(path: PathLike[str] | str) -> bool:
    r"""
    Check whether `path` ends like a directory, with a separator or a `.` or `..` name,
    which only a directory can have, whether or not one exists there.

    [`Path`][pathlib.Path] drops a trailing separator and `.`, so `Path("docs/")` and
    `Path("docs/.")` can't say this, but the path as it was given still can. Only the
    spelling is checked, never the file system.

    **Linux & macOS:** The separator is `/`.

    **Windows:** The separator is `\` or `/`, and a drive or share comes off first, so
    `C:.` and `C:..` end like a directory but `C:` alone doesn't.

    Args:
        path: Path to check.

    Returns:
        `True` when `path` ends with a separator or a `.` or `..` name, otherwise
        `False`.

    Examples:
        ```python
        ends_like_directory("docs/")
        # True

        ends_like_directory("docs/.")
        # True

        ends_like_directory("docs/..")
        # True

        ends_like_directory("docs")
        # False
        ```
    """
    name = fspath(path)

    # Only Windows has drives, and a drive on its own names no path component.
    name = splitdrive(name)[1]

    # An empty path names nothing, so it doesn't end like anything.
    if not name:
        return False

    # Only Windows has an alternative separator.
    for separator in (s for s in (sep, altsep) if s):
        name = name.rpartition(separator)[2]

    # A path that ends with a separator has an empty last name.
    return name in ("", ".", "..")
