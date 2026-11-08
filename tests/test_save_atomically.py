from pathlib import Path

from rootle import identity
from rootle.testing import save_atomically


def test_save_atomically(tmp_path: Path) -> None:
    """
    Assert that `save_atomically` replaces a file with another one with the new body,
    and leaves nothing else behind.
    """
    path = tmp_path / "file.md"
    path.write_text("Hello, world!\n", encoding="utf-8")
    before = identity(path)

    # Keep the old file, so that its number can't be given to the new one.
    kept = tmp_path / "kept.md"
    kept.hardlink_to(path)

    save_atomically(path, "Hello, world!\n")

    body = path.read_text(encoding="utf-8")
    after = identity(path)
    names = sorted(p.name for p in tmp_path.iterdir())

    expect_names = [
        "file.md",
        "kept.md",
    ]

    assert body == "Hello, world!\n"
    assert before is not None
    assert after is not None
    assert after != before
    assert names == expect_names
