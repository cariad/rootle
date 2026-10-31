import os
import sys
from pathlib import Path
from unittest.mock import patch

from pytest import mark

from rootle.testing import can_chmod_deny_search
from tests.marks import windows_only

IS_ROOT = sys.platform != "win32" and os.geteuid() == 0


def test_can_chmod_deny_search_cleans_up(tmp_path: Path) -> None:
    """Assert that `can_chmod_deny_search` removes everything that it creates."""
    can_chmod_deny_search(tmp_path)

    remaining = list(tmp_path.iterdir())

    assert remaining == []


@mark.skipif(
    not IS_ROOT,
    reason="Expects to run as root on POSIX, which ignores search permission",
)
def test_can_chmod_deny_search_is_false_for_root_on_posix(tmp_path: Path) -> None:
    """Assert that `can_chmod_deny_search` is `False` for root on Linux and macOS."""
    denied = can_chmod_deny_search(tmp_path)

    assert denied is False


@windows_only
def test_can_chmod_deny_search_is_false_on_windows(tmp_path: Path) -> None:
    """
    Assert that `can_chmod_deny_search` is `False` on Windows, where `chmod` only sets
    the read-only flag.
    """
    denied = can_chmod_deny_search(tmp_path)

    assert denied is False


def test_can_chmod_deny_search_is_false_when_chmod_is_ignored(tmp_path: Path) -> None:
    """
    Assert that `can_chmod_deny_search` is `False` when `chmod` doesn't take effect,
    like on a file system that ignores permissions.
    """
    with patch.object(Path, "chmod"):
        denied = can_chmod_deny_search(tmp_path)

    assert denied is False


def test_can_chmod_deny_search_is_true_when_chmod_denies_search(
    tmp_path: Path,
) -> None:
    """
    Assert that `can_chmod_deny_search` is `True` when `chmod` denies the search
    permission.
    """
    with patch.object(Path, "stat", side_effect=PermissionError):
        denied = can_chmod_deny_search(tmp_path)

    assert denied is True


@mark.skipif(
    sys.platform == "win32" or IS_ROOT,
    reason="chmod can't deny search permission on Windows, or to root",
)
def test_can_chmod_deny_search_on_posix(tmp_path: Path) -> None:
    """
    Assert that `can_chmod_deny_search` is `True` on Linux and macOS for a process other
    than root.
    """
    denied = can_chmod_deny_search(tmp_path)

    assert denied is True
