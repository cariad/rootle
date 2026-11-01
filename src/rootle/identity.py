from os import PathLike

from rootle.exceptions import _permission_error

from ._identity_of_status import identity_of_status
from .status import status
from .types import Identity


def identity(path: PathLike[str] | str) -> Identity | None:
    """
    Identify the file at `path`, following every symlink it contains.

    Two paths have the same identity when they name the same file. That's true of a
    symlink or a hard link to the file, and of a spelling that a case- or
    normalisation-insensitive file system treats as the same name, like `README.md` and
    `readme.md` on macOS's default APFS.

    Comparing paths as strings can't see any of those, so compare identities instead.
    Nothing exists at a missing path, so it has no identity, `None`, and two missing
    paths compare as equal. Check for `None` before comparing.

    The path is resolved with [`resolve`][rootle.resolve.resolve] before it's
    identified, so a `..` after a directory that doesn't exist yet steps up the same
    way it will once the directory is created. For example, `missing/../doc.md` is
    identified as `doc.md`.

    **Linux & macOS:** A `..` after a file raises an error.

    **Windows:** A `..` after a file steps up. Windows can't read the identity of a
    file that it can't open, like one that's locked or whose permissions deny it, so
    that raises an error. So does a network path that can't be reached, which Windows
    reports as missing.

    Args:
        path: Path to the file to identify.

    Returns:
        The file's [identity][rootle.types.identity.Identity], or `None` when nothing
        exists at `path`.

    Raises:
        OSError:
            - When a part of the path can't be read — for example, when permissions deny
              it, symlinks loop, a `..` steps up from a file on Linux or macOS, or when
              the path is relative and the working directory is gone. A safety check
              that can't be made must fail rather than pass.
            - When `path` ends with a separator or `.`, which says it's a directory, but
              leads to a file.
            - When `path` is empty, which names nothing.
            - When the file exists but its identity can't be read, like when Windows
              can't open it.

            The error names `path` as it was given.

    Examples:
        Given this directory, where `latest` is a symlink to `v2`:

        ```text
        /docs
        ├── latest -> v2
        └── v2
            └── guide.md
        ```

        Every name for a file has the same identity:

        ```python
        identity("/docs/latest/guide.md") == identity("/docs/v2/guide.md")
        # True
        ```

        Nothing exists at a missing path, so it has no identity:

        ```python
        identity("/docs/v2/missing.md")
        # None
        ```
    """
    st = status(path)

    if st is None:
        return None

    found = identity_of_status(st)

    if found is None:
        raise _permission_error.unreadable_identity_error(path)

    return found
