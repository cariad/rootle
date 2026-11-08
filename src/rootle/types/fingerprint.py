from typing import NamedTuple


class Fingerprint(NamedTuple):
    """
    What [`fingerprint`][rootle.fingerprint.fingerprint] saw of a file, through any
    symlinks, without reading it.

    Compare fingerprints with `==`. A file has changed when its fingerprint has. They're
    hashable too, so they can be kept in a set or used as dictionary keys.

    The file's access time is left out, because reading a file changes it. Its change
    and modification times and its size are `None` for anything but a regular file,
    because those change without its content changing: a directory's times change
    whenever any entry within it does, even one that's of no interest, and a terminal's
    change as someone types.

    **Windows:** `changed` is the file's creation time, because that's what Windows
    reports as `st_ctime_ns`, so a rewrite that puts the modification time back, at
    the same size, isn't seen.
    """

    changed: int | None
    """
    The file's status change time in nanoseconds (`st_ctime_ns`), which catches writes
    by tools that put the modification time back, like `cp -p` or `touch -r`, or `None`
    when the file isn't a regular file.
    """

    device: int
    """The device number of the file system that holds the file."""

    inode: int
    """
    The file's number within its file system. A new number, with `device`, means that
    the path names another file, like after an atomic save or a symlink retargeted.
    """

    mode: int
    """The file's type and permissions (`st_mode`)."""

    modified: int | None
    """
    The file's modification time in nanoseconds (`st_mtime_ns`), or `None` when the
    file isn't a regular file.
    """

    size: int | None
    """The file's size in bytes, or `None` when the file isn't a regular file."""
