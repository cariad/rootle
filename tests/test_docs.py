from importlib import import_module
from os import PathLike
from pathlib import Path
from tomllib import loads
from typing import Any, NamedTuple

from pytest import mark, param

ROOT = Path(__file__).parent.parent
DOCS = Path("docs")


class Section(NamedTuple):
    """A module whose exports are documented, and where its documentation lives."""

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
    Section(
        directory="types",
        module="rootle.types",
        navigation="Types",
    ),
]

EXPORTS = [
    param(section, name, id=f"{section.module}.{name}")
    for section in SECTIONS
    for name in import_module(section.module).__all__
]


def _module(section: Section, name: str) -> str:
    """
    The module that an export must be defined in, which is named after it in lowercase,
    like `rootle.types.identity` for `rootle.types.Identity`.
    """
    return f"{section.module}.{name.lower()}"


def _page(section: Section, name: str) -> str:
    """The path to an export's page, relative to the documentation's directory."""
    return f"{section.directory}/{name.lower()}.md"


def _read(path: PathLike[str] | str) -> str:
    """Read a file, given its path relative to the repository."""
    return (ROOT / path).read_text(encoding="utf-8")


@mark.parametrize(
    ("section", "name"),
    EXPORTS,
)
def test_export_is_defined_in_its_own_module(section: Section, name: str) -> None:
    """Assert that an export is defined in a module named after it, in lowercase."""
    export = getattr(import_module(section.module), name)
    defined_in: str | None = getattr(export, "__module__", None)
    expect = _module(section, name)

    assert defined_in == expect


@mark.parametrize(
    ("section", "name"),
    EXPORTS,
)
def test_navigation_lists_export(section: Section, name: str) -> None:
    """Assert that the site's navigation links to an export's page."""
    config = loads(_read("zensical.toml"))
    nav: list[dict[str, Any]] = config["project"]["nav"]

    # A missing section has no entries, so the assertion below fails and shows why.
    missing: list[dict[str, str]] = []

    entries = next(
        (entry[section.navigation] for entry in nav if section.navigation in entry),
        missing,
    )

    expect = {
        name: _page(section, name),
    }

    assert expect in entries


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
    EXPORTS,
)
def test_page_documents_export(section: Section, name: str) -> None:
    """Assert that an export has a reference page that documents it."""
    page = _read(DOCS / _page(section, name))
    expect = f"::: {_module(section, name)}.{name}\n"

    assert page.startswith(expect)


def test_page_documents_winerror() -> None:
    """Assert that the page of Windows error codes documents `rootle.winerror`."""
    page = _read(DOCS / "winerror.md")
    expect = "::: rootle.winerror\n"

    assert page.startswith(expect)
