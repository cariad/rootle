from os import stat, utime
from pathlib import Path

from pytest import raises

from rootle import identity
from rootle.testing import rewrite_and_keep_times
from tests.marks import posix_only, windows_only


@posix_only
def test_rewrite_and_keep_times_on_posix(tmp_path: Path) -> None:
    """
    Assert that `rewrite_and_keep_times` rewrites a file in place, puts its access and
    modification times back, and leaves only its change time moved on.
    """
    path = tmp_path / "file.md"
    path.write_text("Hello, world!\n", encoding="utf-8")
    utime(path, ns=(1_000_000_000, 2_000_000_000))
    before = stat(path)
    before_identity = identity(path)

    rewrite_and_keep_times(path, "Hello, rootle!\n")

    # Reading the body moves the access time on, so look at the times first.
    after = stat(path)
    after_identity = identity(path)
    body = path.read_text(encoding="utf-8")

    assert body == "Hello, rootle!\n"
    assert before_identity is not None
    assert after_identity == before_identity
    assert after.st_atime_ns == before.st_atime_ns
    assert after.st_mtime_ns == before.st_mtime_ns
    assert after.st_ctime_ns != before.st_ctime_ns


@windows_only
def test_rewrite_and_keep_times_raises_on_windows(tmp_path: Path) -> None:
    """
    Assert that `rewrite_and_keep_times` raises `NotImplementedError` on Windows, which
    reports a file's creation time as its change time, rather than writing forever,
    and leaves the file as it was.
    """
    path = tmp_path / "file.md"
    path.write_text("Hello, world!\n", encoding="utf-8")

    with raises(NotImplementedError):
        rewrite_and_keep_times(path, "Hello, rootle!\n")

    body = path.read_text(encoding="utf-8")

    assert body == "Hello, world!\n"
