from importlib import import_module
from os import PathLike
from pathlib import Path
from tomllib import loads
from typing import Any, NamedTuple

from pytest import mark, param

ROOT = Path(__file__).parent.parent
DOCS = Path("docs")


class Section(NamedTuple):
    """A module whose functions are documented, and where its documentation lives."""

    directory: str
    module: str
    navigation: str


SECTIONS = [
    Section(
        directory="functions",
        module="rootle",
        navigation="Functions",
    ),
    Section(
        directory="testing",
        module="rootle.testing",
        navigation="Testing",
    ),
]

FUNCTIONS = [
    param(section, name, id=f"{section.module}.{name}")
    for section in SECTIONS
    for name in import_module(section.module).__all__
]


def _read(path: PathLike[str] | str) -> str:
    """Read a file, given its path relative to the repository."""
    return (ROOT / path).read_text(encoding="utf-8")


@mark.parametrize(
    ("section", "name"),
    FUNCTIONS,
)
def test_navigation_lists_function(section: Section, name: str) -> None:
    """Assert that the site's navigation links to a function's page."""
    config = loads(_read("zensical.toml"))
    nav: list[dict[str, Any]] = config["project"]["nav"]

    # A missing section has no functions, so the assertion below fails and shows why.
    missing: list[dict[str, str]] = []

    functions = next(
        (entry[section.navigation] for entry in nav if section.navigation in entry),
        missing,
    )

    expect = {
        name: f"{section.directory}/{name}.md",
    }

    assert expect in functions


def test_navigation_lists_winerror() -> None:
    """Assert that the site's navigation links to the page of Windows error codes."""
    config = loads(_read("zensical.toml"))
    nav: list[dict[str, Any]] = config["project"]["nav"]

    expect = {
        "Windows errors": "winerror.md",
    }

    assert expect in nav


@mark.parametrize(
    ("section", "name"),
    FUNCTIONS,
)
def test_page_documents_function(section: Section, name: str) -> None:
    """Assert that a function has a reference page that documents it."""
    page = _read(DOCS / section.directory / f"{name}.md")
    expect = f"::: {section.module}.{name}.{name}\n"

    assert page.startswith(expect)


def test_page_documents_winerror() -> None:
    """Assert that the page of Windows error codes documents `rootle.winerror`."""
    page = _read(DOCS / "winerror.md")
    expect = "::: rootle.winerror\n"

    assert page.startswith(expect)
