from os import stat, utime
from pathlib import Path

from rootle import identity
from rootle.testing import edit


def test_edit(tmp_path: Path) -> None:
    """
    Assert that `edit` rewrites a file in place, and sets its modification time to a
    second after what it was.
    """
    path = tmp_path / "file.md"
    path.write_text("Hello, world!\n", encoding="utf-8")
    utime(path, ns=(0, 5_000_000_000))
    before = identity(path)

    edit(path, "Hello, rootle!\n")

    body = path.read_text(encoding="utf-8")
    after = identity(path)
    modified = stat(path).st_mtime_ns

    assert body == "Hello, rootle!\n"
    assert before is not None
    assert after == before
    assert modified == 6_000_000_000
