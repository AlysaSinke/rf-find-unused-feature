"""
Gherkin feature file visitors for counting keyword usage.
"""

from pathlib import Path

from robotframework_find_unused.common.const import GherkinFeatureData
from robotframework_find_unused.parse.parse_gherkin_file import (
    get_all_steps_from_feature,
    parse_gherkin_file,
    step_text_to_keyword_call,
)
from robotframework_find_unused.visitors.robot.keyword_visitor.keyword_definition_manager import (
    KeywordDefinitionManager,
)


def count_keyword_uses_in_feature_files(
    feature_file_paths: list[Path],
    kw_matcher: KeywordDefinitionManager,
) -> int:
    """
    Count keyword usage from Gherkin feature files.

    This processes all feature files and counts each step as a keyword call,
    using the existing KeywordDefinitionManager for matching (which handles
    BDD prefix stripping, embedded arguments, etc.).

    Returns the total number of steps processed.
    """
    total_steps = 0

    for file_path in feature_file_paths:
        feature = parse_gherkin_file(file_path)
        if feature is None:
            continue

        total_steps += _count_steps_in_feature(feature, kw_matcher)

    return total_steps


def _count_steps_in_feature(
    feature: GherkinFeatureData,
    kw_matcher: KeywordDefinitionManager,
) -> int:
    """
    Count all steps in a feature file as keyword calls.
    """
    steps = get_all_steps_from_feature(feature)

    for step in steps:
        keyword_call = step_text_to_keyword_call(step)
        # Get the keyword definition - this will increment use_count
        keyword = kw_matcher.get_keyword_definition(keyword_call)
        keyword.use_count += 1

    return len(steps)


def parse_feature_files(file_paths: list[Path]) -> list[GherkinFeatureData]:
    """
    Parse all feature files, returning successfully parsed features.
    """
    features: list[GherkinFeatureData] = []

    for file_path in file_paths:
        feature = parse_gherkin_file(file_path)
        if feature is not None:
            features.append(feature)

    return features


def filter_feature_files(file_paths: list[Path]) -> list[Path]:
    """
    Filter a list of file paths to only include .feature files.
    """
    return [p for p in file_paths if p.suffix.lower() == ".feature"]


def filter_robot_files(file_paths: list[Path]) -> list[Path]:
    """
    Filter a list of file paths to exclude .feature files.
    """
    return [p for p in file_paths if p.suffix.lower() != ".feature"]
