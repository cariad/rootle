from contextlib import suppress
from os import PathLike, stat, stat_result
from os.path import isabs

from ._status_of_resolved import status_of_resolved
from .ends_like_directory import ends_like_directory
from .resolve import resolve


def status(path: PathLike[str] | str) -> stat_result | None:
    """
    Get the status of the file at `path`, following every symlink it contains, like
    [`os.stat`][os.stat] does.

    Unlike `os.stat`, this function returns `None` when nothing exists at `path`, and
    raises an error only when it can't tell whether anything does.

    The path is resolved with [`resolve`][rootle.resolve.resolve] first, so a `..`
    after a directory that doesn't exist yet steps up the same way it will once the
    directory is created. For example, `missing/../doc.md` is the status of `doc.md`.

    **Linux & macOS:** A `..` after a file raises an error.

    **Windows:** A `..` after a file steps up. A network path that can't be reached
    raises an error, even though Windows reports it as missing.

    Args:
        path: Path to the file.

    Returns:
        The file's [status][os.stat_result], or `None` when nothing exists at `path`.

    Raises:
        OSError:
            - When a part of the path can't be read — for example, when permissions deny
              it, symlinks loop, a `..` steps up from a file on Linux or macOS, or when
              the path is relative and the working directory is gone. A check that can't
              be made must fail rather than pass.
            - When `path` ends with a separator or `.`, which says it's a directory, but
              leads to a file.
            - When `path` is empty, which names nothing.

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
    # A path that ends like a directory is left to `resolve`, which raises when it
    # leads to a file, because Windows' `stat` drops a trailing separator or `.`.

    # So is a relative path, because `stat` can still find `.` and `..` after the
    # working directory is gone, and that mustn't pass.
    if isabs(path) and not ends_like_directory(path):
        # A path that can be `stat`-ed already names the file that it resolves to, so
        # it needn't be resolved. An error is left to the route below to describe.
        with suppress(OSError):
            return stat(path)

    # `status_of_resolved` reads a missing file as `None`, so resolve before calling it,
    # so that a path that can't be resolved raises rather than passing as a file that
    # doesn't exist.
    return status_of_resolved(resolve(path), path)
