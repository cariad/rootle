from os import PathLike, fspath


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
