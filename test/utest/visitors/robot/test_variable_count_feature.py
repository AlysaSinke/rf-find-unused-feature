from pathlib import Path

from robotframework_find_unused.common.const import VariableData
from robotframework_find_unused.common.normalize import normalize_variable_name
from robotframework_find_unused.parse.parse_robot_file import parse_robot_file
from robotframework_find_unused.visitors.robot.variable_count import (
    RobotVisitorVariableUses,
)


def _make_variable(name: str) -> VariableData:
    normalized_name = normalize_variable_name(name)
    return VariableData(
        name=name,
        type=None,
        normalized_name=normalized_name,
        resolved_name=name,
        use_count=0,
        defined_in_type="variables_section",
        defined_in="test.resource",
        value=[],
    )


def _make_variable_with_value(name: str, value: str) -> VariableData:
    variable = _make_variable(name)
    variable.value = [value]
    return variable


def test_feature_step_keyword_name_counts_variable_uses(tmp_path: Path):
    feature_file = tmp_path / "variables.feature"
    feature_file.write_text(
        """
Feature: Variables in steps
Scenario: Count usage
Given I use ${USED_VAR}
When I fill <outline_var>
Then I confirm
""".lstrip(),
        encoding="utf8",
    )

    model = parse_robot_file(feature_file)

    variables = {
        normalize_variable_name("${USED_VAR}"): _make_variable("${USED_VAR}"),
        normalize_variable_name("${outline_var}"): _make_variable(
            "${outline_var}",
        ),
        normalize_variable_name("${UNUSED_VAR}"): _make_variable(
            "${UNUSED_VAR}",
        ),
    }

    visitor = RobotVisitorVariableUses(variables)
    visitor.visit(model)

    assert model.source == feature_file
    assert variables[normalize_variable_name("${USED_VAR}")].use_count == 1
    assert variables[normalize_variable_name("${outline_var}")].use_count == 1
    assert variables[normalize_variable_name("${UNUSED_VAR}")].use_count == 0


def test_var_statement_value_counts_variable_use(tmp_path: Path):
    robot_file = tmp_path / "variables.resource"
    robot_file.write_text(
        """
*** Keywords ***
My Keyword
    VAR    &{payment} =    transaction_id=${INSTRUCTION_ID}
""".lstrip(),
        encoding="utf8",
    )

    model = parse_robot_file(robot_file)

    variables = {
        normalize_variable_name("${INSTRUCTION_ID}"): _make_variable(
            "${INSTRUCTION_ID}",
        ),
    }

    visitor = RobotVisitorVariableUses(variables)
    visitor.visit(model)

    assert variables[normalize_variable_name("${INSTRUCTION_ID}")].use_count == 1


def test_while_condition_counts_variable_use(tmp_path: Path):
    robot_file = tmp_path / "while_condition.resource"
    robot_file.write_text(
        """
*** Keywords ***
My Keyword
    VAR    ${counter} =    0
    WHILE    ${counter} < ${MAX_RETRIES}
        ${counter} =    Evaluate    ${counter} + 1
    END
""".lstrip(),
        encoding="utf8",
    )

    model = parse_robot_file(robot_file)

    variables = {
        normalize_variable_name("${MAX_RETRIES}"): _make_variable(
            "${MAX_RETRIES}",
        ),
    }

    visitor = RobotVisitorVariableUses(variables)
    visitor.visit(model)

    assert variables[normalize_variable_name("${MAX_RETRIES}")].use_count == 1


def test_dynamic_name_template_counts_all_matching_candidates(tmp_path: Path):
    robot_file = tmp_path / "dynamic_template.resource"
    robot_file.write_text(
        """
*** Keywords ***
My Keyword
    Log    ${ORIGINAL_MIFIR_REPORT_FILE_${ENTITY}}
""".lstrip(),
        encoding="utf8",
    )

    model = parse_robot_file(robot_file)

    variables = {
        normalize_variable_name("${ENTITY}"): _make_variable_with_value(
            "${ENTITY}",
            "NL",
        ),
        normalize_variable_name("${ORIGINAL_MIFIR_REPORT_FILE_NL}"): _make_variable(
            "${ORIGINAL_MIFIR_REPORT_FILE_NL}",
        ),
        normalize_variable_name("${ORIGINAL_MIFIR_REPORT_FILE_BE}"): _make_variable(
            "${ORIGINAL_MIFIR_REPORT_FILE_BE}",
        ),
    }

    visitor = RobotVisitorVariableUses(variables)
    visitor.visit(model)

    assert variables[normalize_variable_name("${ENTITY}")].use_count == 1
    assert (
        variables[normalize_variable_name("${ORIGINAL_MIFIR_REPORT_FILE_NL}")].use_count
        == 1
    )
    assert (
        variables[normalize_variable_name("${ORIGINAL_MIFIR_REPORT_FILE_BE}")].use_count
        == 1
    )


def test_fully_dynamic_name_does_not_match_all_variables(tmp_path: Path):
    robot_file = tmp_path / "fully_dynamic.resource"
    robot_file.write_text(
        """
*** Keywords ***
My Keyword
    Log    ${${field_name}}
""".lstrip(),
        encoding="utf8",
    )

    model = parse_robot_file(robot_file)

    variables = {
        normalize_variable_name("${field_name}"): _make_variable_with_value(
            "${field_name}",
            "field_a",
        ),
        normalize_variable_name("${field_a}"): _make_variable("${field_a}"),
        normalize_variable_name("${field_b}"): _make_variable("${field_b}"),
    }

    visitor = RobotVisitorVariableUses(variables)
    visitor.visit(model)

    assert variables[normalize_variable_name("${field_name}")].use_count == 1
    assert variables[normalize_variable_name("${field_a}")].use_count == 1
    assert variables[normalize_variable_name("${field_b}")].use_count == 0


def test_dynamic_template_with_argument_selector_counts_candidates(tmp_path: Path):
    robot_file = tmp_path / "arg_selector.resource"
    robot_file.write_text(
        """
*** Keywords ***
My Keyword
    Should Be Equal As Strings    ${BID_QUOTE_VALUE}    ${${instrument}_PRICE}
""".lstrip(),
        encoding="utf8",
    )

    model = parse_robot_file(robot_file)

    variables = {
        normalize_variable_name("${instrument}"): _make_variable_with_value(
            "${instrument}",
            "${outline_instrument}",
        ),
        normalize_variable_name("${BAM_PRICE}"): _make_variable("${BAM_PRICE}"),
        normalize_variable_name("${ING_PRICE}"): _make_variable("${ING_PRICE}"),
    }

    visitor = RobotVisitorVariableUses(variables)
    visitor.visit(model)

    assert variables[normalize_variable_name("${BAM_PRICE}")].use_count == 1
    assert variables[normalize_variable_name("${ING_PRICE}")].use_count == 1


def test_dynamic_template_with_conflicting_selector_still_counts_candidates(
    tmp_path: Path,
):
    robot_file = tmp_path / "env_selector.resource"
    robot_file.write_text(
        """
*** Keywords ***
My Keyword
    I Log In With Client Account With ${${ENV}_USER} Username
""".lstrip(),
        encoding="utf8",
    )

    model = parse_robot_file(robot_file)

    variables = {
        normalize_variable_name("${ENV}"): _make_variable_with_value(
            "${ENV}",
            "TESTFE",
        ),
        normalize_variable_name("${ACC_USER}"): _make_variable("${ACC_USER}"),
        normalize_variable_name("${TEST_USER}"): _make_variable("${TEST_USER}"),
    }

    visitor = RobotVisitorVariableUses(variables)
    visitor.visit(model)

    assert variables[normalize_variable_name("${ENV}")].use_count == 1
    assert variables[normalize_variable_name("${ACC_USER}")].use_count == 1
    assert variables[normalize_variable_name("${TEST_USER}")].use_count == 1
