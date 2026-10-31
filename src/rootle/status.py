from contextlib import suppress
from os import PathLike, altsep, fspath, sep, stat, stat_result

from rootle.exceptions import _os_error

from . import winerror
from .resolve import resolve


def status(path: PathLike[str] | str) -> stat_result | None:
    """
    Get the status of the file at `path`, following every symlink it contains, like
    `os.stat` does.

    Unlike `os.stat`, this function returns `None` when nothing exists at `path`, and
    raises an error only when it can't tell whether anything does.

    The path is resolved with `resolve` first, so a `..` after a directory that doesn't
    exist yet steps up the same way it will once the directory is created. For example,
    `missing/../doc.md` is the status of `doc.md`.

    **Linux & macOS:** A `..` after a file raises an error.

    **Windows:** A `..` after a file steps up. A network path that can't be reached
    raises an error, even though Windows reports it as missing.

    Args:
        path: Path to the file.

    Returns:
        The file's status, or `None` when nothing exists at `path`.

    Raises:
        OSError:
            - When a part of the path can't be read — for example, when permissions deny
              it, symlinks loop, a `..` steps up from a file on Linux or macOS, or when
              the path is relative and the working directory is gone. A check that can't
              be made must fail rather than pass.
            - When `path` ends with a separator, which says it's a directory, but leads
              to a file.

            The error names `path` as it was given.

    Examples:
        Given this directory, where `latest` is a symlink to `v2`:

        ```text
        /docs
        ├── latest -> v2
        └── v2
            └── guide.md
        ```

        The status of a file is found through every symlink:

        ```python
        status("/docs/latest/guide.md").st_size
        # 1024
        ```

        Nothing exists at a missing path, so it has no status:

        ```python
        status("/docs/v2/missing.md")
        # None
        ```
    """
    # A path that ends with a separator is left to `resolve`, which raises when it leads
    # to a file.
    if fspath(path)[-1:] not in (sep, altsep):
        # A path that can be `stat`-ed already names the file that it resolves to, so
        # it needn't be resolved. An error is left to the route below to describe.
        with suppress(OSError):
            return stat(path)

    # Resolve outside of the `try`, so that a path that can't be resolved raises rather
    # than passing as a file that doesn't exist.
    resolved = resolve(path)

    try:
        return stat(resolved)

    # Windows reports a path through a file as missing, so `NotADirectoryError` is
    # raised here only on POSIX. Either way, nothing exists at the path.
    except NotADirectoryError:  # pragma: posix-only
        # `NotADirectoryError` means that one of the path's parents is a file, so
        # nothing can exist at the path.
        return None

    except FileNotFoundError as ex:
        # Windows maps more than a missing file to `ENOENT`, like a network path that
        # can't be reached, and that mustn't pass as nothing existing there.
        missing = (None, winerror.FILE_NOT_FOUND, winerror.PATH_NOT_FOUND)

        if getattr(ex, "winerror", None) in missing:
            return None

        raise _os_error.with_path(ex, path) from ex

    except OSError as ex:
        # The path can change after it's resolved, so `stat` can still fail. `ex`
        # names the resolved path, so describe the path as it was given instead, like
        # `resolve` does.
        raise _os_error.with_path(ex, path) from ex
