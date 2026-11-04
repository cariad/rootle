from pathlib import Path
from shutil import rmtree
from stat import S_IMODE, S_IRGRP, S_IROTH, S_IRUSR, S_IRWXU, S_IXGRP, S_IXOTH, S_IXUSR
from tempfile import mkdtemp


def can_chmod_deny_writing(directory: Path) -> bool:
    """
    Check whether removing a directory's "write" (`w`) permission with
    [`chmod`][os.chmod] denies it to this process.

    The write permission is required by creating, renaming or deleting a file within a
    directory.

    This function only checks writing, not reading (listing the directory) or search
    (opening or [`stat`][os.stat]-ing a file within it).

    **Linux & macOS:** `False` for root, for a process that can override permissions
    (like one with Linux's `CAP_DAC_OVERRIDE` capability), and on file systems that
    ignore permissions, like FAT.

    **Windows:** Always `False`, because `chmod` only sets the read-only flag, which
    Windows doesn't honour on directories.

    Args:
        directory: Path to the directory to interrogate.

    Returns:
        `True` when `chmod(0o555)` denies this process the write permission on a
        directory, otherwise `False`.

    Raises:
        OSError: When the permission probe cannot be written or deleted.

    Examples:
        ```python
        def test_raises_when_writing_denied(tmp_path: Path) -> None:
            if not can_chmod_deny_writing(tmp_path):
                skip("chmod can't deny writing here")

            ...
        ```
    """
    probe_dir = Path(mkdtemp(dir=directory))

    try:
        original_mode = S_IMODE(probe_dir.stat().st_mode)

        # chmod(0o555), which keeps every read and search bit rather than only the
        # owner's.
        #
        # Linux's FAT driver silently ignores a chmod that removes a read or search bit
        # that its mount options allow, but with the `rodir` option it honours one that
        # removes every write bit and nothing else.
        probe_dir.chmod(S_IRUSR | S_IXUSR | S_IRGRP | S_IXGRP | S_IROTH | S_IXOTH)

        try:
            (probe_dir / "file").touch()

        except PermissionError:
            return True

        finally:
            # The original mode plus every owner permission, which rmtree needs even if
            # the umask left some out.
            probe_dir.chmod(original_mode | S_IRWXU)

        return False

    finally:
        rmtree(probe_dir)
