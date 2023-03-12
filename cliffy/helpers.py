from typing import Optional


def wrap_as_comment(text: str, split_on: Optional[str] = None) -> str:
    if split_on:
        joiner = "\n# "
        return "# " + joiner.join(text.split(split_on))

    return f"# {text}"
