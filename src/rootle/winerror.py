"""
Windows error codes, for comparing with an `OSError`'s `winerror`.

Like Python's own `errno` module, but for the codes that only Windows reports.
"""

from typing import Final

FILE_NOT_FOUND: Final = 2
"""
A file doesn't exist.

This is Windows' `ERROR_FILE_NOT_FOUND`, one of several codes that it maps to
`errno.ENOENT`.
"""

PATH_NOT_FOUND: Final = 3
"""
A directory on a path doesn't exist.

This is Windows' `ERROR_PATH_NOT_FOUND`, one of several codes that it maps to
`errno.ENOENT`.
"""

SYMLINK_LOOP: Final = 1921
"""
A path's symlinks loop, or there are too many of them to follow.

This is Windows' `ERROR_CANT_RESOLVE_FILENAME`, and its equivalent of `errno.ELOOP`.
"""
