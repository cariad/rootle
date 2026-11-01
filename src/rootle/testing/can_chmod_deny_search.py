from pathlib import Path
from shutil import rmtree
from stat import S_IRWXU
from tempfile import mkdtemp


def can_chmod_deny_search(directory: Path) -> bool:
    """
    Check whether removing a directory's permissions with [`chmod`][os.chmod] denies
    this process the "search" (`x`) permission.

    The search permission is required by opening or [`stat`][os.stat]-ing a file.

    This function only checks search, not reading (listing the directory) or writing
    (creating, renaming or deleting files within it).

    **Linux & macOS:** `False` for root, for a process that can override permissions
    (like one with Linux's `CAP_DAC_OVERRIDE` capability), and on file systems that
    ignore permissions, like FAT.

    **Windows:** Always `False`, because `chmod` only sets the read-only flag.

    Args:
        directory: Path to the directory to interrogate.

    Returns:
        `True` when `chmod(0)` denies this process the search permission on a directory,
        otherwise `False`.

    Raises:
        OSError: When the permission probe cannot be written or deleted.

    Examples:
        ```python
        def test_raises_when_permission_denied(tmp_path: Path) -> None:
            if not can_chmod_deny_search(tmp_path):
                skip("chmod can't deny search permission here")

            ...
        ```
    """
    probe_dir = Path(mkdtemp(dir=directory))
    probe_file = probe_dir / "file"

    try:
        probe_file.touch()
        probe_dir.chmod(0)

        try:
            probe_file.stat()

        except PermissionError:
            return True

        return False

    finally:
        probe_dir.chmod(S_IRWXU)
        rmtree(probe_dir)
