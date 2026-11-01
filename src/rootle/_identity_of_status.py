from os import stat_result

from .types import Identity


def identity_of_status(st: stat_result) -> Identity | None:
    """
    Get the identity in `st`, a file's status, or `None` when it has none, like when
    Windows can't open the file.
    """
    # A file's number identifies it only when it isn't zero.
    #
    # When Windows can't open a file, it reads the file's attributes from its directory
    # instead, which has no file index, and some file systems never report one. Every
    # such file would share that identity, so it mustn't pass as one.
    if st.st_ino == 0:
        return None

    return Identity(
        device=st.st_dev,
        inode=st.st_ino,
    )
