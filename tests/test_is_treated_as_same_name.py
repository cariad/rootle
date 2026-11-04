import sys
from contextlib import suppress
from pathlib import Path
from unicodedata import normalize
from unittest.mock import patch

from pytest import mark, raises

from rootle.testing import is_treated_as_same_name
from tests.marks import windows_only


def test_is_treated_as_same_name_cleans_up(tmp_path: Path) -> None:
    """Assert that `is_treated_as_same_name` removes everything that it creates."""
    is_treated_as_same_name(
        tmp_path,
        "file.md",
        "FILE.md",
    )

    remaining = list(tmp_path.iterdir())

    assert remaining == []


def test_is_treated_as_same_name_cleans_up_when_creating_fails(tmp_path: Path) -> None:
    """
    Assert that `is_treated_as_same_name` removes the probe when it isn't permitted to
    create the file within it, like under a umask that leaves out the owner's write
    permission.
    """
    with (
        patch.object(Path, "touch", side_effect=PermissionError),
        raises(PermissionError),
    ):
        is_treated_as_same_name(
            tmp_path,
            "file.md",
            "FILE.md",
        )

    remaining = list(tmp_path.iterdir())

    assert remaining == []


def test_is_treated_as_same_name_cleans_up_when_umask_denies_reading(
    tmp_path: Path,
) -> None:
    """
    Assert that `is_treated_as_same_name` removes the probe when the umask left the
    owner's read permission out of it, which listing it would need.
    """
    probe_dir = tmp_path / "probe"
    probe_dir.mkdir()
    probe_dir.chmod(0o300)  # Like mkdtemp under a umask of 0o400

    try:
        with patch(
            "rootle.testing.is_treated_as_same_name.mkdtemp",
            return_value=str(probe_dir),
        ):
            is_treated_as_same_name(
                tmp_path,
                "file.md",
                "FILE.md",
            )

    finally:
        # Let pytest clean up a probe that was left behind, which it can't list.
        with suppress(FileNotFoundError):
            probe_dir.chmod(0o700)

    remaining = list(tmp_path.iterdir())

    assert remaining == []


def test_is_treated_as_same_name_is_false_for_another_file(tmp_path: Path) -> None:
    """
    Assert that `is_treated_as_same_name` is `False` when `alt_name` leads somewhere
    that exists but isn't the probe's file, like `NUL` on Windows.
    """
    with patch.object(Path, "samefile", return_value=False):
        same = is_treated_as_same_name(
            tmp_path,
            "file.md",
            "file.md",
        )

    assert same is False


@mark.parametrize(
    "alt_name",
    [
        "NUL",  # The null device
        ". ",  # The probe's directory, once Windows drops the trailing space
    ],
)
@windows_only
def test_is_treated_as_same_name_is_false_for_another_file_on_windows(
    alt_name: str,
    tmp_path: Path,
) -> None:
    """
    Assert that `is_treated_as_same_name` is `False` on Windows for a name that leads
    somewhere other than the probe's file, and that it still leads somewhere, without
    which this test would prove nothing.
    """
    leads_somewhere = (tmp_path / alt_name).exists()

    same = is_treated_as_same_name(
        tmp_path,
        "file.md",
        alt_name,
    )

    assert leads_somewhere is True
    assert same is False


def test_is_treated_as_same_name_is_false_for_different_name(tmp_path: Path) -> None:
    """Assert that `is_treated_as_same_name` is `False` for a different name."""
    same = is_treated_as_same_name(
        tmp_path,
        "file.md",
        "other.md",
    )

    assert same is False


@windows_only
def test_is_treated_as_same_name_is_false_for_different_normalisation_on_windows(
    tmp_path: Path,
) -> None:
    """
    Assert that `is_treated_as_same_name` is `False` for a different Unicode
    normalisation on Windows, which compares names without normalising them.
    """
    name = normalize("NFC", "café.md")
    alt_name = normalize(
        "NFD",
        "café.md",
    )

    same = is_treated_as_same_name(tmp_path, name, alt_name)

    assert same is False


@mark.parametrize(
    (
        "name",
        "alt_name",
    ),
    [
        (
            "file.md",
            "FILE.md",
        ),
        (
            normalize("NFC", "café.md"),
            normalize("NFD", "café.md"),
        ),
    ],
)
@mark.skipif(
    sys.platform != "linux",
    reason="Expects Linux's usual file systems, which compare names byte for byte",
)
def test_is_treated_as_same_name_is_false_for_different_spelling_on_linux(
    name: str,
    alt_name: str,
    tmp_path: Path,
) -> None:
    """
    Assert that `is_treated_as_same_name` is `False` for a different case or Unicode
    normalisation on Linux, whose usual file systems compare names byte for byte.
    """
    same = is_treated_as_same_name(
        tmp_path,
        name,
        alt_name,
    )

    assert same is False


@windows_only
def test_is_treated_as_same_name_is_true_for_different_case_on_windows(
    tmp_path: Path,
) -> None:
    """
    Assert that `is_treated_as_same_name` is `True` for a different case on Windows,
    whose file systems are case-insensitive.
    """
    same = is_treated_as_same_name(
        tmp_path,
        "file.md",
        "FILE.md",
    )

    assert same is True


@mark.parametrize(
    (
        "name",
        "alt_name",
    ),
    [
        (
            "file.md",
            "FILE.md",
        ),
        (
            normalize("NFC", "café.md"),
            normalize("NFD", "café.md"),
        ),
    ],
)
@mark.skipif(
    sys.platform != "darwin",
    reason="Expects macOS's default APFS, which is case- and normalisation-insensitive",
)
def test_is_treated_as_same_name_is_true_for_different_spelling_on_macos(
    name: str,
    alt_name: str,
    tmp_path: Path,
) -> None:
    """
    Assert that `is_treated_as_same_name` is `True` for a different case or Unicode
    normalisation on macOS's default APFS.
    """
    same = is_treated_as_same_name(
        tmp_path,
        name,
        alt_name,
    )

    assert same is True


def test_is_treated_as_same_name_is_true_for_same_spelling(tmp_path: Path) -> None:
    """Assert that `is_treated_as_same_name` is `True` for the same spelling."""
    same = is_treated_as_same_name(
        tmp_path,
        "file.md",
        "file.md",
    )

    assert same is True


@mark.parametrize(
    (
        "name",
        "alt_name",
    ),
    [
        (
            "",
            "file.md",
        ),
        (
            "file.md",
            ".",
        ),
        (
            "..",
            "file.md",
        ),
        (
            "dir/file.md",
            "dir/FILE.md",
        ),
        (
            "file.md",
            "../FILE.md",
        ),
        (
            "/file.md",
            "/FILE.md",
        ),
    ],
)
def test_is_treated_as_same_name_raises_unless_given_single_names(
    name: str,
    alt_name: str,
    tmp_path: Path,
) -> None:
    """
    Assert that `is_treated_as_same_name` raises `ValueError` when `name` or `alt_name`
    isn't a single name, which could lead out of the probe's directory.
    """
    with raises(ValueError):
        is_treated_as_same_name(
            tmp_path,
            name,
            alt_name,
        )


def test_is_treated_as_same_name_raises_when_directory_does_not_exist(
    tmp_path: Path,
) -> None:
    """
    Assert that `is_treated_as_same_name` raises `FileNotFoundError` when the directory
    to probe doesn't exist.
    """
    missing = tmp_path / "missing"

    with raises(FileNotFoundError):
        is_treated_as_same_name(
            missing,
            "file.md",
            "FILE.md",
        )
