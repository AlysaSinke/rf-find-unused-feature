from pathlib import Path

from robotframework_find_unused.parse.parse_feature_file import (
    parse_feature_file,
)


def test_parse_feature_file_keeps_only_steps(tmp_path: Path):
    feature_file = tmp_path / "suite.feature"
    feature_file.write_text(
        """
Feature: Demo feature

@api @smoke
Scenario Outline: Login
Given I open login page
When I type <username> into username
And I type ${PASSWORD} into password
* I click submit
Then I should see home page
| username |
| alice    |
Background details for humans only
# comment
""".lstrip(),
        encoding="utf8",
    )

    actual = parse_feature_file(feature_file)

    assert actual == (
        "*** Test Cases ***\n"
        "Feature\n"
        "    Given I open login page\n"
        "    When I type <username> into username\n"
        "    And I type ${PASSWORD} into password\n"
        "    I click submit\n"
        "    Then I should see home page\n"
    )


def test_parse_feature_file_expands_examples_placeholders(tmp_path: Path):
    feature_file = tmp_path / "outline.feature"
    feature_file.write_text(
        """
Feature: Shapes

Background:
Given I open the shape page

Scenario: Draw <shape> shape
When I draw <shape> shape
Then The <shape> shape should exist

Examples:
| shape  |
| circle |
| square |
""".lstrip(),
        encoding="utf8",
    )

    actual = parse_feature_file(feature_file)

    assert actual == (
        "*** Test Cases ***\n"
        "Feature\n"
        "    Given I open the shape page\n"
        "    When I draw <shape> shape\n"
        "    When I draw circle shape\n"
        "    When I draw square shape\n"
        "    Then The <shape> shape should exist\n"
        "    Then The circle shape should exist\n"
        "    Then The square shape should exist\n"
    )


def test_parse_feature_file_does_not_leak_examples_between_scenarios(tmp_path: Path):
    feature_file = tmp_path / "outline.feature"
    feature_file.write_text(
        """
Feature: Shapes

Scenario: First
When I draw <shape> shape

Examples:
| shape  |
| circle |

Scenario: Second
When I erase <shape> shape
""".lstrip(),
        encoding="utf8",
    )

    actual = parse_feature_file(feature_file)

    assert actual == (
        "*** Test Cases ***\n"
        "Feature\n"
        "    When I draw <shape> shape\n"
        "    When I draw circle shape\n"
        "    When I erase <shape> shape\n"
    )


def test_parse_feature_file_returns_placeholder_when_no_steps(tmp_path: Path):
    feature_file = tmp_path / "empty.feature"
    feature_file.write_text(
        """
Feature: Empty
Rule: Also empty
Scenario: No steps
# comment
@tag
""".lstrip(),
        encoding="utf8",
    )

    expected = "*** Test Cases ***\nPlaceholder\n"
    assert parse_feature_file(feature_file) == expected
