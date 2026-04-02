"""
Parse Gherkin feature files to extract steps for keyword usage analysis.
"""

from pathlib import Path

from gherkin.parser import Parser
from gherkin.token_scanner import TokenScanner

from robotframework_find_unused.common.const import (
    GherkinFeatureData,
    GherkinScenarioData,
    GherkinStepData,
)


def parse_gherkin_file(file_path: Path) -> GherkinFeatureData | None:
    """
    Parse a Gherkin feature file and extract its structure.

    Returns None if the file cannot be parsed.
    """
    try:
        parser = Parser()
        with file_path.open(encoding="utf-8") as f:
            content = f.read()

        scanner = TokenScanner(content)
        gherkin_document = parser.parse(scanner)

        if gherkin_document.get("feature") is None:
            return None

        feature = gherkin_document["feature"]
        return _extract_feature_data(file_path, feature)

    except Exception:  # noqa: BLE001
        # Gherkin parsing can fail for various reasons (syntax errors, encoding, etc.)
        # We don't want to crash the whole analysis for a single bad file
        return None


def _extract_feature_data(file_path: Path, feature: dict) -> GherkinFeatureData:
    """
    Extract structured data from a parsed Gherkin feature.
    """
    background_steps: list[GherkinStepData] = []
    scenarios: list[GherkinScenarioData] = []

    for child in feature.get("children", []):
        if "background" in child:
            background = child["background"]
            background_steps = _extract_steps(background.get("steps", []))

        elif "scenario" in child:
            scenario = child["scenario"]
            scenario_data = GherkinScenarioData(
                name=scenario.get("name", ""),
                steps=_extract_steps(scenario.get("steps", [])),
                is_outline=len(scenario.get("examples", [])) > 0,
                line=scenario.get("location", {}).get("line", 0),
            )
            scenarios.append(scenario_data)

    # Extract feature-level tags
    tags = [tag.get("name", "").lstrip("@") for tag in feature.get("tags", [])]

    return GherkinFeatureData(
        file_path=file_path,
        name=feature.get("name", ""),
        background_steps=background_steps,
        scenarios=scenarios,
        tags=tags,
    )


def _extract_steps(steps: list[dict]) -> list[GherkinStepData]:
    """
    Extract step data from a list of Gherkin steps.
    """
    result: list[GherkinStepData] = []

    for step in steps:
        step_data = GherkinStepData(
            keyword=step.get("keyword", "").strip(),
            text=step.get("text", ""),
            line=step.get("location", {}).get("line", 0),
        )
        result.append(step_data)

    return result


def get_all_steps_from_feature(feature: GherkinFeatureData) -> list[GherkinStepData]:
    """
    Get all steps from a feature file (background + all scenarios).

    Background steps are included once (they run before each scenario,
    but for keyword usage counting, we count them once per feature file).
    """
    all_steps: list[GherkinStepData] = []

    # Add background steps once
    all_steps.extend(feature.background_steps)

    # Add steps from all scenarios
    for scenario in feature.scenarios:
        all_steps.extend(scenario.steps)

    return all_steps


def step_text_to_keyword_call(step: GherkinStepData) -> str:
    """
    Convert a Gherkin step to a keyword call string.

    The step keyword (Given/When/Then/And/But) is included as a prefix,
    as Robot Framework's BDD normalization will strip it when matching.

    Example:
        GherkinStepData(keyword="When", text="I click the button")
        -> "When I click the button"
    """
    # Add a space between the keyword and text since the keyword is stripped
    return f"{step.keyword} {step.text}"
