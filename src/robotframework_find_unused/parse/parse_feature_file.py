from pathlib import Path


def parse_feature_file(file_path: Path) -> str:
    """
    Convert a .feature file into Robot-compatible content.

    Output keeps one synthetic test case section with step lines only. This lets existing Robot
    visitors process keyword calls from .feature files without introducing parser dependencies.
    """
    with file_path.open(encoding="utf8") as f:
        raw_lines = f.readlines()

    step_lines = [_to_robot_step_line(line) for line in raw_lines]
    step_lines = [line for line in step_lines if line is not None]

    if len(step_lines) == 0:
        return "*** Test Cases ***\nPlaceholder\n"

    content_lines: list[str] = ["*** Test Cases ***", "Feature", *step_lines]
    return "\n".join(content_lines) + "\n"


def _to_robot_step_line(raw_line: str) -> str | None:
    line = raw_line.strip()
    if line == "":
        return None

    if line.startswith("#"):
        return None

    if line.startswith("@"):
        return None

    if line.startswith("|"):
        # Ignore examples/data table rows.
        return None

    # Ignore common gherkin headers and free-text description lines.
    lower = line.casefold()
    if lower.startswith("feature:"):
        return None
    if lower.startswith("background:"):
        return None
    if lower.startswith("scenario:"):
        return None
    if lower.startswith("scenario outline:"):
        return None
    if lower.startswith("examples:"):
        return None
    if lower.startswith("rule:"):
        return None

    if lower.startswith(("given ", "when ", "then ", "and ", "but ")):
        return "    " + line

    if lower.startswith("*"):
        stripped = line[1:].lstrip()
        if stripped == "":
            return None
        return "    " + stripped

    return None