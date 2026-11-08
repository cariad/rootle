from os import PathLike, scandir, stat
from pathlib import Path, PurePath

from ._identity_of_status import identity_of_status


def as_spelled(
    path: PathLike[str] | str,
    directory: PathLike[str] | str,
) -> PurePath:
    """
    Spell each name in `path`, a path relative to `directory`, the way the file system
    lists it.

    A case- or normalisation-insensitive file system can store a name in another
    spelling from the one it's given, like `templates` for `TEMPLATES` on macOS's
    default APFS. Some tools need the stored spelling, like
    [Mosey](https://cariad.github.io/mosey/starting-directories/), whose walks must
    start in a directory that's spelled exactly as it's listed.

    So each name is found in its parent's listing by
    [`identity`][rootle.identity.identity] rather than by name, starting in `directory`.
    An entry that's a symlink is never matched, because the file it leads to has the
    same identity but another name. So a name that's a symlink is spelled as a sibling
    that it leads to, and one that leads anywhere else can't be found. Pass a path
    without symlinks, like one that
    [`relative_within`][rootle.relative_within.relative_within] returns.

    A name that can't be found, like one that doesn't exist, can't be read, or is `..`,
    keeps the spelling it was given, and so does every name after it.

    **Linux & macOS:** [`relative_within`][rootle.relative_within.relative_within]
    keeps the spelling that its path gave each name, so spell its result with this
    function to get the stored spelling.

    **Windows:** [`relative_within`][rootle.relative_within.relative_within] already
    uses the stored spelling, but a path from anywhere else might not. A directory
    junction is never matched either, like a symlink.

    Args:
        path: Path to spell, relative to `directory`, with `/` or the operating
            system's own separators.
        directory: Path to the directory that `path` is relative to.

    Returns:
        The path with each name spelled the way the file system lists it, or
        `PurePath(".")` when `path` is `directory` itself.

    Examples:
        Given this directory on a file system that ignores case:

        ```text
        /site
        └── templates
            └── Posts
                └── welcome.md
        ```

        Each name is spelled the way it's listed:

        ```python
        as_spelled("TEMPLATES/posts/Welcome.md", "/site")
        # PurePath("templates/Posts/welcome.md")
        ```

        A name that can't be found keeps the spelling it was given, and so does every
        name after it:

        ```python
        as_spelled("TEMPLATES/drafts/Welcome.md", "/site")
        # PurePath("templates/drafts/Welcome.md")
        ```
    """
    given = PurePath(path).parts
    found: list[str] = []
    parent = Path(directory)

    for name in given:
        try:
            wanted = identity_of_status(stat(parent / name))

            # A file whose identity can't be read, like one that Windows can't open,
            # can't be told apart from any other such file.
            if wanted is None:
                break

            with scandir(parent) as entries:
                listed = next(
                    (
                        entry.name
                        for entry in entries
                        if not entry.is_symlink()
                        and not entry.is_junction()
                        # `entry.stat()` reads no identity on Windows, so read it from
                        # the file itself. On Linux and macOS, that costs the same.
                        and identity_of_status(stat(entry.path)) == wanted
                    ),
                    None,
                )

        except OSError, ValueError:
            # The name doesn't exist, can't be read, or holds a null character, so
            # leave it and every name after it as they were given.
            break

        if listed is None:
            break

        found.append(listed)
        parent = parent / listed

    return PurePath(
        *found,
        *given[len(found) :],
    )
