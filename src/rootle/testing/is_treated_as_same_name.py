from pathlib import Path, PurePath
from tempfile import mkdtemp


def is_treated_as_same_name(directory: Path, name: str, alt_name: str) -> bool:
    """
    Check whether the file system treats two spellings as the same name.

    For example:

    - `README.md` and `readme.md`
    - the NFC and NFD forms of `café.md`.

    The probe is made in a new directory within `directory`. Some file systems decide
    this for each directory, like ext4 with case folding and NTFS with case sensitivity
    turned on, but a new directory takes its parent's setting, so the answer holds for
    `directory` and the directories made within it.

    **Linux:** Usually `False` for a different case or Unicode normalisation, because
    most file systems compare names byte for byte. Some don't, like FAT, which is
    case-insensitive.

    **macOS:** `True` for a different Unicode normalisation on APFS, HFS+, FAT and
    exFAT, and for a different case unless APFS or HFS+ was formatted as
    case-sensitive.

    **Windows:** `True` for a different case unless the directory is case-sensitive,
    but `False` for a different Unicode normalisation, because Windows compares names
    without normalising them.

    Args:
        directory: Path to the directory to interrogate.
        name: Name of the file to create.
        alt_name: Another spelling of `name` to look for.

    Returns:
        `True` when `alt_name` names the file created as `name`, otherwise `False`.

    Raises:
        OSError: When the probe cannot be written or deleted.
        ValueError: When `name` or `alt_name` is or contains a directory.

    Examples:
        ```python
        def test_identity_by_different_case(tmp_path: Path) -> None:
            if not is_treated_as_same_name(tmp_path, "readme.md", "README.md"):
                skip("This file system doesn't treat 'README.md' as 'readme.md'")

            ...
        ```
    """
    for given in (name, alt_name):
        if given in ("", ".", "..") or PurePath(given).name != given:
            raise ValueError(f"{given!r} is or contains a directory")

    probe_dir = Path(mkdtemp(dir=directory))
    probe_file = probe_dir / name

    try:
        probe_file.touch()

        try:
            return (probe_dir / alt_name).exists()

        finally:
            probe_file.unlink()

    finally:
        # Removing the file and then the directory, rather than the whole tree, doesn't
        # need the permission to list the directory, which the umask can leave out.
        probe_dir.rmdir()
