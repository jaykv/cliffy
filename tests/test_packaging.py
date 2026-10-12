"""What the installed package has to carry besides its modules."""

from importlib import metadata
from importlib.resources import files


def test_package_is_marked_as_typed():
    # without py.typed a type checker ignores the annotations of an installed cliffy (PEP 561)
    assert files("cliffy").joinpath("py.typed").is_file()
    assert "Typing :: Typed" in (metadata.metadata("cliffy").get_all("Classifier") or [])


def test_llms_txt_is_bundled():
    # printed by `cli ai llms-txt`; scripts/docs.py generates it and `make docs-check` fails when it is stale
    text = files("cliffy").joinpath("llms.txt").read_text(encoding="utf-8")
    assert text.startswith("# cliffy\n")
