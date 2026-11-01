from errno import EACCES
from os import PathLike, fspath


def unreadable_identity_error(path: PathLike[str] | str) -> PermissionError:
    """Make the error that says the identity of the file at `path` can't be read."""
    return PermissionError(
        EACCES,
        "The file's identity can't be read",
        fspath(path),
    )
