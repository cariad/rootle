import sys
from pathlib import Path
from unittest.mock import patch

from pytest import mark, raises

from rootle.testing import can_chmod_deny_writing
from tests.marks import IS_ROOT, windows_only


def test_can_chmod_deny_writing_cleans_up(tmp_path: Path) -> None:
    """Assert that `can_chmod_deny_writing` removes everything that it creates."""
    can_chmod_deny_writing(tmp_path)

    remaining = list(tmp_path.iterdir())

    assert remaining == []


def test_can_chmod_deny_writing_cleans_up_when_chmod_fails(tmp_path: Path) -> None:
    """
    Assert that `can_chmod_deny_writing` removes the probe when it isn't permitted to
    change the probe's permissions, like on a file system owned by another user.
    """
    with (
        patch.object(Path, "chmod", side_effect=PermissionError),
        raises(PermissionError),
    ):
        can_chmod_deny_writing(tmp_path)

    remaining = list(tmp_path.iterdir())

    assert remaining == []


def test_can_chmod_deny_writing_cleans_up_when_chmod_is_ignored(
    tmp_path: Path,
) -> None:
    """
    Assert that `can_chmod_deny_writing` removes the file that it was able to create
    when `chmod` doesn't take effect, like on a file system that ignores permissions.
    """
    with patch.object(Path, "chmod"):
        can_chmod_deny_writing(tmp_path)

    remaining = list(tmp_path.iterdir())

    assert remaining == []


@mark.skipif(
    not IS_ROOT,
    reason="Expects to run as root on POSIX, which ignores write permission",
)
def test_can_chmod_deny_writing_is_false_for_root_on_posix(tmp_path: Path) -> None:
    """Assert that `can_chmod_deny_writing` is `False` for root on Linux and macOS."""
    denied = can_chmod_deny_writing(tmp_path)

    assert denied is False


@windows_only
def test_can_chmod_deny_writing_is_false_on_windows(tmp_path: Path) -> None:
    """
    Assert that `can_chmod_deny_writing` is `False` on Windows, where `chmod` only sets
    the read-only flag, which isn't honoured on directories.
    """
    denied = can_chmod_deny_writing(tmp_path)

    assert denied is False


def test_can_chmod_deny_writing_is_false_when_chmod_is_ignored(tmp_path: Path) -> None:
    """
    Assert that `can_chmod_deny_writing` is `False` when `chmod` doesn't take effect,
    like on a file system that ignores permissions.
    """
    with patch.object(Path, "chmod"):
        denied = can_chmod_deny_writing(tmp_path)

    assert denied is False


def test_can_chmod_deny_writing_is_true_when_chmod_denies_writing(
    tmp_path: Path,
) -> None:
    """
    Assert that `can_chmod_deny_writing` is `True` when `chmod` denies the write
    permission.
    """
    with (
        patch.object(Path, "chmod"),
        patch.object(Path, "touch", side_effect=PermissionError),
    ):
        denied = can_chmod_deny_writing(tmp_path)

    assert denied is True


@mark.skipif(
    sys.platform == "win32" or IS_ROOT,
    reason="chmod can't deny write permission on Windows, or to root",
)
def test_can_chmod_deny_writing_on_posix(tmp_path: Path) -> None:
    """
    Assert that `can_chmod_deny_writing` is `True` on Linux and macOS for a process
    other than root.
    """
    denied = can_chmod_deny_writing(tmp_path)

    assert denied is True


def test_can_chmod_deny_writing_raises_when_directory_does_not_exist(
    tmp_path: Path,
) -> None:
    """
    Assert that `can_chmod_deny_writing` raises `FileNotFoundError` when the directory
    to probe doesn't exist.
    """
    missing = tmp_path / "missing"

    with raises(FileNotFoundError):
        can_chmod_deny_writing(missing)


def test_can_chmod_deny_writing_restores_permissions(tmp_path: Path) -> None:
    """
    Assert that `can_chmod_deny_writing` restores the probe's original permissions,
    because a file system like FAT can silently ignore a `chmod` to any others.
    """
    probe_dir = tmp_path / "probe"
    probe_dir.mkdir()
    probe_dir.chmod(0o755)  # Like a directory on FAT with the usual dmask, 022
    expect = probe_dir.stat().st_mode

    with (
        patch(
            "rootle.testing.can_chmod_deny_writing.mkdtemp",
            return_value=str(probe_dir),
        ),
        patch("rootle.testing.can_chmod_deny_writing.rmtree"),
    ):
        can_chmod_deny_writing(tmp_path)

    restored = probe_dir.stat().st_mode

    assert restored == expect
