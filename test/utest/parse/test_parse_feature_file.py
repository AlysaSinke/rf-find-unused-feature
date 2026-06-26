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
