from errno import ENOTDIR
from os import PathLike, fspath, strerror


def not_a_directory(path: PathLike[str] | str) -> NotADirectoryError:
    """Make the error that says `path`, as the caller gave it, isn't a directory."""
    return NotADirectoryError(
        ENOTDIR,
        strerror(ENOTDIR),
        fspath(path),
    )
