from errno import ENOTDIR
from os import PathLike, altsep, fspath, sep, strerror
from os.path import ALLOW_MISSING, realpath
from pathlib import Path

from rootle.exceptions import _os_error


def resolve(path: PathLike[str] | str) -> Path:
    """
    Resolve `path` through every symlink it contains, whether or not each part exists.

    Like `os.path.realpath`, any part that doesn't exist is kept, and a `..` after a
    directory that doesn't exist still steps up as if it does. For example,
    `missing/../doc.md` resolves to `doc.md`.

    Unlike `os.path.realpath`, this function raises an error when a part of the path
    can't be read or symlinks loop, rather than guessing where the path leads, and it
    keeps the parts of a path after a file.

    Two paths to the same file can resolve to different names — for example, through a
    hard link — so compare paths with `identity` rather than by name.

    **Linux & macOS:**

    - A `..` after a file raises an error.
    - Each name in the resolved path is kept exactly as `path` gave it, even when the
      file system stores it in a different case or Unicode form, so two spellings of
      the same file's name resolve to different names.

    **Windows:**

    - A `..` after a file steps up.
    - Each name in the resolved path is the one that the file system stores, so its case
      can differ from `path`.

    Args:
        path: Path to resolve.

    Returns:
        The absolute resolved path.

    Raises:
        OSError:
            - When a part of the path can't be read — for example, when permissions deny
              it, symlinks loop, a `..` steps up from a file on Linux or macOS, or when
              the path is relative and the working directory is gone.
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

        A path resolves to where it leads, even when it doesn't exist:

        ```python
        resolve("/docs/latest/drafts/../guide.md")
        # Path("/docs/v2/guide.md")
        ```

        A path resolves to where it leads, even when it's impossible:

        ```python
        resolve("/docs/latest/guide.md/intro.md")
        # Path("/docs/v2/guide.md/intro.md")
        ```
    """
    current = Path(path)
    tail: list[str] = []

    while True:
        try:
            canon = realpath(current, strict=ALLOW_MISSING)

        # Windows reports a path through a file as missing, which `ALLOW_MISSING`
        # allows, so `NotADirectoryError` is raised here only on POSIX.
        #
        # Only the route differs, though. Either way, the path through a file resolves
        # to the same result.
        except NotADirectoryError as ex:  # pragma: posix-only
            # An inner part of the path is a file, so we'll drop the final part, keep a
            # note of it, then try again. After some iterations, we should end up with a
            # path that ends with, rather than contains, a file — and we'll return that
            # path with all the kept names appended to it.
            #
            # A ".." can't be kept, because we can't step up from a file.
            #
            # A path with no names left, like "/", has nothing to drop.
            if current.name in ("", ".."):
                raise _os_error.with_path(ex, path) from ex

            # A symlink can't be kept as a name, because the file might be on the path
            # where it leads, so follow it by hand instead.
            #
            # Look for it in its parent's resolved path, because a `..` after a
            # directory that doesn't exist steps up in `realpath` but not in the file
            # system. If the parent leads through a file too, then nothing can be there.
            try:
                parent = realpath(current.parent, strict=ALLOW_MISSING)
                link = Path(parent, current.name)
            except NotADirectoryError:
                link = current

            if link.is_symlink():
                current = link.parent / link.readlink()
                continue

            tail.insert(0, current.name)  # Keep the name...
            current = current.parent  # ...then drop it
            continue

        except OSError as ex:
            # Something horrible has happened at the current path. Since `ex` describes
            # the current path, we'll raise our own `OSError` to describe the full path
            # as it was given to this function.
            raise _os_error.with_path(ex, path) from ex

        resolved = Path(canon).joinpath(*tail)

        # `Path` drops a trailing separator, which says that the path is a directory, so
        # check that it is one.
        is_file = resolved.exists() and not resolved.is_dir()

        if is_file and fspath(path)[-1:] in (sep, altsep):
            raise NotADirectoryError(
                ENOTDIR,
                strerror(ENOTDIR),
                fspath(path),
            )

        return resolved
