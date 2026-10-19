from pathlib import Path

from robotframework_find_unused.parse.parse_variable_file_lines import (
    find_variable_line_numbers,
)


def test_find_line_numbers_in_yaml_file(tmp_path: Path):
    variable_file = tmp_path / "values.yaml"
    variable_file.write_text(
        """
# comment
first value: alpha
second_value: beta
nested group:
  inner value: gamma
"third value": delta
""".lstrip(),
        encoding="utf8",
    )

    actual = find_variable_line_numbers(variable_file)

    assert actual == {
        "firstvalue": 2,
        "secondvalue": 3,
        "nestedgroup": 4,
        "thirdvalue": 6,
    }


def test_find_line_numbers_in_json_file(tmp_path: Path):
    variable_file = tmp_path / "values.json"
    variable_file.write_text(
        """
{
    "first value": "alpha",
    "second_value": ["beta"],
    "third value": {
        "inner value": "gamma"
    }
}
""".lstrip(),
        encoding="utf8",
    )

    actual = find_variable_line_numbers(variable_file)

    assert actual["firstvalue"] == 2
    assert actual["secondvalue"] == 3
    assert actual["thirdvalue"] == 4


def test_find_line_numbers_ignores_unsupported_file_type(tmp_path: Path):
    variable_file = tmp_path / "values.py"
    variable_file.write_text("FIRST_VALUE = 'alpha'\n", encoding="utf8")

    assert find_variable_line_numbers(variable_file) == {}


def test_find_line_numbers_of_missing_file(tmp_path: Path):
    assert find_variable_line_numbers(tmp_path / "missing.yaml") == {}
