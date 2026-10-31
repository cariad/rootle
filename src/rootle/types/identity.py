from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class Identity:
    """
    The identity of a file, which is the same for every path that names it.

    Compare identities with `==`. They're hashable too, so they can be kept in a set or
    used as dictionary keys.

    **Linux & macOS:** The identity is made of the file system's device number and the
    file's inode number.

    **Windows:** The identity is made of the volume's serial number and the file's
    index.
    """

    device: int
    """The device number of the file system that holds the file."""

    inode: int
    """The file's number within its file system."""
