import functools
import re
from pathlib import Path

from robotframework_find_unused.common.normalize import normalize_variable_name

YAML_SUFFIXES = (".yaml", ".yml")
JSON_SUFFIXES = (".json",)

# Top level YAML key, e.g. `my key:` or `"my key":`
YAML_KEY_PATTERN = re.compile(r"""^(?P<key>'[^']*'|"[^"]*"|[^\s#'"-][^:]*)\s*:(\s|$)""")

# Top level JSON key, e.g. `"my key":`
JSON_KEY_PATTERN = re.compile(r"""^\s{0,4}"(?P<key>[^"]+)"\s*:""")


@functools.cache
def find_variable_line_numbers(path: Path) -> dict[str, int]:
    """
    Find the line number of every variable defined in a variable file.

    Returns a mapping of normalized variable name to 1-based line number.
    Returns an empty mapping for file types without a usable text structure,
    such as Python variable files.
    """
    suffix = path.suffix.casefold()
    if suffix in YAML_SUFFIXES:
        pattern = YAML_KEY_PATTERN
    elif suffix in JSON_SUFFIXES:
        pattern = JSON_KEY_PATTERN
    else:
        return {}

    try:
        content = path.read_text(encoding="utf8")
    except (OSError, UnicodeDecodeError):
        return {}

    line_numbers: dict[str, int] = {}
    for line_number, line in enumerate(content.splitlines(), start=1):
        match = pattern.match(line)
        if not match:
            continue

        key = match.group("key").strip().strip("'\"")
        if not key:
            continue

        normalized_key = normalize_variable_name(key)
        line_numbers.setdefault(normalized_key, line_number)

    return line_numbers
