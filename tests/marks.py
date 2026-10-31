import sys

from pytest import mark

posix_only = mark.skipif(
    sys.platform == "win32",
    reason="POSIX-only behaviour",
)
"""Decorator for tests that must run on POSIX only."""


windows_only = mark.skipif(
    sys.platform != "win32",
    reason="Windows-only behaviour",
)
"""Decorator for tests that must run on Windows only."""
