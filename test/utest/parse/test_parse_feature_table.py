from pathlib import Path

from robotframework_find_unused.parse.parse_feature_table import (
    get_feature_table_cells,
    get_feature_table_selector_value_map,
)


def test_get_feature_table_cells_from_examples_and_step_data_table(tmp_path: Path):
    feature_file = tmp_path / "suite.feature"
    feature_file.write_text(
        """
Feature: Demo

  Scenario Outline: Validate value
    Given I submit data
      | name  | amount      |
      | alice | ${YAML_VAR} |

    Examples:
      | account |
      | literal |
""".lstrip(),
        encoding="utf8",
    )

    assert get_feature_table_cells(feature_file) == [
        "name",
        "amount",
        "alice",
        "${YAML_VAR}",
        "account",
        "literal",
    ]


def test_get_feature_table_cells_ignores_non_table_lines(tmp_path: Path):
    feature_file = tmp_path / "suite.feature"
    feature_file.write_text(
        """
Feature: Demo

  Scenario: No table
    Given I do a thing

|
""".lstrip(),
        encoding="utf8",
    )

    assert get_feature_table_cells(feature_file) == []


def test_get_feature_table_selector_value_map_uses_header_to_group_values(
    tmp_path: Path,
):
    feature_file = tmp_path / "selectors.feature"
    feature_file.write_text(
        """
Feature: Demo

  Scenario Outline: Select item
    Given I choose <primary selector id>
      | primary selector id | secondary selector id |
      | Alpha Value         | Group One             |
      | Beta Value          | Group Two             |
""".lstrip(),
        encoding="utf8",
    )

    selector_values = get_feature_table_selector_value_map(feature_file)

    assert selector_values["primaryselectorid"] == ["Alpha Value", "Beta Value"]
    assert selector_values["secondaryselectorid"] == ["Group One", "Group Two"]
