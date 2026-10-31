"""
Windows error codes, for comparing with an `OSError`'s `winerror`.

Like Python's own `errno` module, but for the codes that only Windows reports.
"""

from typing import Final

SYMLINK_LOOP: Final = 1921
"""
A path's symlinks loop, or there are too many of them to follow.

This is Windows' `ERROR_CANT_RESOLVE_FILENAME`, and its equivalent of `errno.ELOOP`.
"""
