import re
from dataclasses import dataclass, field
from pathlib import Path

_PATTERN_OUTLINE_PLACEHOLDER = re.compile(r"<([^<>]+)>")

# Lines that end the steps of the previous scenario. Limitation: No localisation.
_BLOCK_STARTERS = (
    "feature:",
    "background:",
    "rule:",
    "scenario:",
    "scenario outline:",
    "scenario template:",
    "example:",
)


@dataclass
class _ScenarioBlock:
    """Steps of a single gherkin block together with the rows of its examples tables."""

    steps: list[str] = field(default_factory=list)
    example_rows: list[dict[str, str]] = field(default_factory=list)


def parse_feature_file(file_path: Path) -> str:
    """
    Convert a .feature file into Robot-compatible content.

    Output keeps one synthetic test case section with step lines only. This lets existing Robot
    visitors process keyword calls from .feature files without introducing parser dependencies.

    Steps of a scenario outline are also emitted once per examples row, with the `<placeholder>`
    values filled in. Without that, keywords and variables that are only used through an examples
    table would look unused.
    """
    with file_path.open(encoding="utf8") as f:
        raw_lines = f.readlines()

    step_lines: list[str] = []
    for block in _split_into_blocks(raw_lines):
        for step in block.steps:
            step_lines.extend(_expand_step(step, block.example_rows))

    if len(step_lines) == 0:
        return "*** Test Cases ***\nPlaceholder\n"

    content_lines: list[str] = ["*** Test Cases ***", "Feature", *step_lines]
    return "\n".join(content_lines) + "\n"


def _split_into_blocks(raw_lines: list[str]) -> list[_ScenarioBlock]:
    """Group step lines per gherkin block and collect the examples rows of that block."""
    parser = _FeatureParser()
    for raw_line in raw_lines:
        parser.feed(raw_line.strip())
    return parser.finish()


class _FeatureParser:
    """Line based gherkin reader that only keeps steps and examples rows."""

    def __init__(self) -> None:
        self._blocks: list[_ScenarioBlock] = []
        self._current = _ScenarioBlock()
        self._examples_header: list[str] | None = None
        self._in_examples = False

    def feed(self, line: str) -> None:
        if line == "" or line.startswith(("#", "@")):
            return

        lower = line.casefold()

        if lower.startswith("examples:"):
            self._in_examples = True
            self._examples_header = None
        elif line.startswith("|"):
            self._feed_table_row(line)
        elif lower.startswith(_BLOCK_STARTERS):
            self._start_block()
        else:
            self._feed_step(line)

    def finish(self) -> list[_ScenarioBlock]:
        if len(self._current.steps) > 0:
            self._blocks.append(self._current)
        return self._blocks

    def _feed_table_row(self, line: str) -> None:
        if not self._in_examples:
            # Not an examples table, so there is nothing to expand with.
            return

        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if self._examples_header is None:
            self._examples_header = cells
        elif len(cells) == len(self._examples_header):
            self._current.example_rows.append(
                dict(zip(self._examples_header, cells, strict=True)),
            )

    def _start_block(self) -> None:
        if len(self._current.steps) > 0:
            self._blocks.append(self._current)
        self._current = _ScenarioBlock()
        self._examples_header = None
        self._in_examples = False

    def _feed_step(self, line: str) -> None:
        self._in_examples = False
        step = _to_robot_step_line(line)
        if step is not None:
            self._current.steps.append(step)


def _expand_step(step: str, example_rows: list[dict[str, str]]) -> list[str]:
    """Return the step itself plus one variant per examples row that fills its placeholders."""
    placeholders = set(_PATTERN_OUTLINE_PLACEHOLDER.findall(step))
    if len(placeholders) == 0 or len(example_rows) == 0:
        return [step]

    lines = [step]
    for row in example_rows:
        if not any(placeholder in row for placeholder in placeholders):
            continue

        expanded = step
        for name, value in row.items():
            expanded = expanded.replace(f"<{name}>", value)

        if expanded != step and expanded not in lines:
            lines.append(expanded)

    return lines


def _to_robot_step_line(line: str) -> str | None:
    lower = line.casefold()

    if lower.startswith(("given ", "when ", "then ", "and ", "but ")):
        return "    " + line

    if lower.startswith("*"):
        stripped = line[1:].lstrip()
        if stripped == "":
            return None
        return "    " + stripped

    return None
