from os import listdir
from pathlib import Path
from shutil import rmtree
from stat import S_IRWXU, S_IWUSR, S_IXUSR
from tempfile import mkdtemp


def can_chmod_deny_listing(directory: Path) -> bool:
    """
    Check whether removing a directory's "read" (`r`) permission with
    [`chmod`][os.chmod] denies it to this process.

    The read permission is required by listing a directory, like with
    [`listdir`][os.listdir].

    This function only checks reading, not search (opening or [`stat`][os.stat]-ing a
    file within the directory) or writing (creating, renaming or deleting files within
    it).

    **Linux & macOS:** `False` for root, for a process that can override permissions
    (like one with Linux's `CAP_DAC_OVERRIDE` or `CAP_DAC_READ_SEARCH` capability), and
    on file systems that ignore permissions, like FAT.

    **Windows:** Always `False`, because `chmod` only sets the read-only flag.

    Args:
        directory: Path to the directory to interrogate.

    Returns:
        `True` when `chmod(0o300)` denies this process the read permission on a
        directory, otherwise `False`.

    Raises:
        OSError: When the permission probe cannot be written or deleted.

    Examples:
        ```python
        def test_raises_when_listing_denied(tmp_path: Path) -> None:
            if not can_chmod_deny_listing(tmp_path):
                skip("chmod can't deny listing here")

            ...
        ```
    """
    probe_dir = Path(mkdtemp(dir=directory))

    try:
        probe_dir.chmod(S_IWUSR | S_IXUSR)

        try:
            listdir(probe_dir)

        except PermissionError:
            return True

        finally:
            probe_dir.chmod(S_IRWXU)

        return False

    finally:
        rmtree(probe_dir)
