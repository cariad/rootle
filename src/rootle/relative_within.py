from os import PathLike, stat_result
from os.path import ALLOW_MISSING, realpath
from pathlib import Path, PurePath
from stat import S_ISDIR

from rootle.exceptions import _not_a_directory_error, _os_error, _permission_error

from ._identity_of_status import identity_of_status
from ._status_of_resolved import status_of_resolved
from .resolve import resolve
from .status import status


def _resolves_to_itself(part: Path, path: PathLike[str] | str) -> bool:
    """
    Check whether `part`, a part of the path that `path` resolved to, still resolves to
    itself, so that a path through it isn't redirected somewhere else, like by a symlink
    or a Windows directory junction that's appeared since. Errors name `path` as it was
    given.
    """
    try:
        canon = realpath(
            part,
            strict=ALLOW_MISSING,
        )

    except OSError as ex:
        raise _os_error.with_path(ex, path) from ex

    return Path(canon) == part


def relative_within(
    path: PathLike[str] | str,
    directory: PathLike[str] | str,
) -> PurePath | None:
    """
    Get the path of `path` relative to `directory`, or `None` when `path` isn't
    `directory` or within it.

    The path is resolved with [`resolve`][rootle.resolve.resolve] first, so every
    symlink it contains is followed, even a dangling one at its end, and a `..` after a
    directory that doesn't exist yet steps up the same way it will once the directory
    is created. A path that leads out of `directory` through a symlink isn't within it,
    even when it's named within it.

    Then the resolved path and each of its parents are compared with `directory` by
    [`identity`][rootle.identity.identity], so a spelling that a case- or
    normalisation-insensitive file system treats as the same name, like
    `TEMPLATES/build` for `templates/build` on macOS's default APFS, is still within
    `templates`. A path that doesn't exist yet is judged by its nearest parents that
    do.

    Each part of the resolved path is checked again as it's compared, so a symlink that
    appears in the path after it's resolved isn't followed into `directory`. The answer
    is only true at the moment it's made, though. A path that changes while it's
    checked, or afterwards, can lead somewhere else by the time it's used.

    Nothing can be within a directory that doesn't exist, so a missing `directory`
    returns `None`. Nothing can be within a file either, so a `directory` that's a file
    raises an error.

    The relative path is a [`PurePath`][pathlib.PurePath], which can't touch the file
    system, because it's relative to `directory` rather than to the working directory.
    Join it to `directory` to make a [`Path`][pathlib.Path], or call
    [`as_posix()`][pathlib.PurePath.as_posix] to spell it with forward slashes on every
    operating system.

    **Linux & macOS:** The relative path keeps the spelling that `path` gave each name,
    or that a symlink gave the names it leads to, so `docs/GUIDE.md` is `GUIDE.md`
    within `docs`, even when the file system stores `guide.md`. A `..` after a file
    raises an error.

    **Windows:** The relative path uses the spelling that the file system stores for
    each name that exists, so `docs/GUIDE.md` is `guide.md` within `docs` when the file
    system stores `guide.md`. A name that doesn't exist keeps the spelling that `path`
    gave it. A `..` after a file steps up. Windows can't read the identity of a file
    that it can't open, like one that's locked or whose permissions deny it. When
    that's `directory`, it raises an error, but when it's a part of `path`, it can't be
    `directory`, so `path` is judged by its parents.

    A network path that can't be reached raises an error when `directory` exists, even
    though Windows reports it as missing.

    Args:
        path: Path to find within `directory`.
        directory: Path to the directory.

    Returns:
        The path of `path` relative to `directory`, `PurePath(".")` when `path` is
        `directory` itself, or `None` when `path` is neither `directory` nor within it,
        or when `directory` doesn't exist.

    Raises:
        OSError:
            - When a part of `path` or `directory` can't be read — for example, when
              permissions deny it, symlinks loop, a `..` steps up from a file on Linux
              or macOS, or when the path is relative and the working directory is gone.
              A safety check that can't be made must fail rather than pass.
            - When `path` or `directory` ends with a separator or `.`, which says it's
              a directory, but leads to a file.
            - When `path` or `directory` is empty, which names nothing.
            - When `directory` is a file.
            - When `directory` exists but its identity can't be read, like when Windows
              can't open it.

            Errors in resolving `path` are raised even when `directory` doesn't exist.
            The error names `path` or `directory` as it was given.

    Examples:
        Given this directory, where `latest` is a symlink to `v2` and `shared` is a
        symlink to `/assets`:

        ```text
        /docs
        ├── latest -> v2
        ├── shared -> /assets
        └── v2
            └── guide.md
        ```

        A path within the directory, whether or not it exists, is relative to it:

        ```python
        relative_within(
            "/docs/latest/guide.md",
            "/docs/v2",
        )
        # PurePath("guide.md")

        relative_within(
            "/docs/v2/drafts/intro.md",
            "/docs/v2",
        )
        # PurePath("drafts/intro.md")
        ```

        A path that leads out of the directory isn't within it:

        ```python
        relative_within(
            "/docs/shared/logo.svg",
            "/docs",
        )
        # None
        ```
    """
    # Resolve before looking for the directory, so that a path that can't be resolved
    # raises even when the directory doesn't exist.
    #
    # `resolve` can keep the caller's spelling, which a case- or normalisation-
    # insensitive file system can store differently, so find the directory by identity
    # rather than by name.
    resolved = resolve(path)

    directory_status = status(directory)

    if directory_status is None:
        # The paths that don't exist have no identity either, so they mustn't be
        # compared with it.
        return None

    if not S_ISDIR(directory_status.st_mode):
        raise _not_a_directory_error.not_a_directory(directory)

    directory_identity = identity_of_status(directory_status)

    if directory_identity is None:
        raise _permission_error.unreadable_identity_error(directory)

    # The resolved path had no symlinks, so one that's appeared since mustn't be
    # followed out of the path that was checked.
    #
    # Reading a part's status follows any symlink in the parts before it, so walk down
    # from the root, and stop at the first part that doesn't resolve to itself any more.
    # The parts after it, if any, aren't on the path that was checked.
    #
    # A part that resolved to itself, like a folder that Windows mounts a volume in,
    # still does, so it doesn't stop the walk.
    parts: list[tuple[Path, stat_result]] = []

    for part in reversed((resolved, *resolved.parents)):
        part_status = status_of_resolved(
            part,
            path,
            follow_symlinks=False,
        )

        if part_status is None:
            break

        parts.append((part, part_status))

        if not _resolves_to_itself(part, path):
            break

    # Compare from the end, so the nearest part that's the directory wins.
    for part, part_status in reversed(parts):
        # The directory's identity could be read, so a part whose identity can't be
        # read, `None`, isn't the directory, and never compares as equal to it.
        part_identity = identity_of_status(part_status)

        if part_identity == directory_identity:
            return PurePath(resolved.relative_to(part))

    return None
