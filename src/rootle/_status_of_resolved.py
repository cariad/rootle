from os import PathLike, stat, stat_result
from pathlib import Path

from rootle.exceptions import _os_error

from . import winerror


def status_of_resolved(
    resolved: Path,
    path: PathLike[str] | str,
    *,
    follow_symlinks: bool = True,
) -> stat_result | None:
    """
    Get the status of the file at `resolved`, which `path` already resolved to, or
    `None` when nothing exists there. Errors name `path` as it was given.

    Unless `follow_symlinks` is set, a symlink at `resolved` isn't followed, like when
    it appeared after `path` was resolved.
    """
    try:
        return stat(
            resolved,
            follow_symlinks=follow_symlinks,
        )

    # Windows reports a path through a file as missing, so `NotADirectoryError` is
    # raised here only on POSIX. Either way, nothing exists at the path.
    except NotADirectoryError:  # pragma: posix-only
        # `NotADirectoryError` means that one of the path's parents is a file, so
        # nothing can exist at the path.
        return None

    except FileNotFoundError as ex:
        # Windows maps more than a missing file to `ENOENT`, like a network path that
        # can't be reached, and that mustn't pass as nothing existing there.
        missing = (
            None,
            winerror.FILE_NOT_FOUND,
            winerror.PATH_NOT_FOUND,
        )

        if getattr(ex, "winerror", None) in missing:
            return None

        raise _os_error.with_path(ex, path) from ex

    except OSError as ex:
        # The path can change after it's resolved, so `stat` can still fail. `ex`
        # names the resolved path, so describe the path as it was given instead, like
        # `resolve` does.
        raise _os_error.with_path(ex, path) from ex
