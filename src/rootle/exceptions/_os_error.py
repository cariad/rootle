from errno import EINVAL
from os import PathLike, fspath


def null_character(path: PathLike[str] | str) -> OSError:
    """Make an error that says `path` holds a null character."""
    return OSError(
        # `EINVAL` rather than the `ENOENT` of an empty path, so it can't be mistaken
        # for a missing file.
        EINVAL,
        "The path holds a null character",
        fspath(path),
    )


def with_path(ex: OSError, path: PathLike[str] | str) -> OSError:
    """
    Copy `ex` so that it describes `path` as the caller gave it, rather than whichever
    part of that path, or wherever it leads, the error happened at.

    Keep Windows' own error code, because Windows maps many of them to the same `errno`.
    Other platforms ignore it.

    An error made from a message alone has no `strerror`, so keep its message.
    """
    return OSError(
        ex.errno,
        ex.strerror or str(ex),
        fspath(path),
        getattr(ex, "winerror", None),
    )
