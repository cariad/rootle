import os
import sys

from pytest import mark

IS_ROOT = sys.platform != "win32" and os.geteuid() == 0
"""Whether the tests are running as root on Linux or macOS."""


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
