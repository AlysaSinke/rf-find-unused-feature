from pathlib import Path

from robotframework_find_unused.common.const import VariableData
from robotframework_find_unused.common.normalize import normalize_variable_name
from robotframework_find_unused.parse.parse_robot_file import parse_robot_file
from robotframework_find_unused.visitors.robot.variable_count import (
    RobotVisitorContextLiterals,
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
    VAR    &{dictionary} =    used_var=${USED_VAR}
""".lstrip(),
        encoding="utf8",
    )

    model = parse_robot_file(robot_file)

    variables = {
        normalize_variable_name("${USED_VAR}"): _make_variable(
            "${USED_VAR}",
        ),
    }

    visitor = RobotVisitorVariableUses(variables)
    visitor.visit(model)

    assert variables[normalize_variable_name("${USED_VAR}")].use_count == 1


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


def test_dynamic_name_template_counts_resolved_candidate(tmp_path: Path):
    robot_file = tmp_path / "dynamic_template.resource"
    robot_file.write_text(
        """
*** Keywords ***
My Keyword
    Log    ${VARIABLE_NAME_${EXTRA_VARIABLE}}
""".lstrip(),
        encoding="utf8",
    )

    model = parse_robot_file(robot_file)

    variables = {
        normalize_variable_name("${EXTRA_VARIABLE}"): _make_variable_with_value(
            "${EXTRA_VARIABLE}",
            "A",
        ),
        normalize_variable_name("${VARIABLE_NAME_A}"): _make_variable(
            "${VARIABLE_NAME_A}",
        ),
        normalize_variable_name("${VARIABLE_NAME_B}"): _make_variable(
            "${VARIABLE_NAME_B}",
        ),
    }

    visitor = RobotVisitorVariableUses(variables)
    visitor.visit(model)

    assert variables[normalize_variable_name("${EXTRA_VARIABLE}")].use_count == 1
    assert (
        variables[normalize_variable_name("${VARIABLE_NAME_A}")].use_count
        == 1
    )
    assert (
        variables[normalize_variable_name("${VARIABLE_NAME_B}")].use_count
        == 0
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


def test_dynamic_template_with_argument_selector_without_match_counts_none(
    tmp_path: Path,
):
    robot_file = tmp_path / "arg_selector.resource"
    robot_file.write_text(
        """
*** Keywords ***
My Keyword
    Should Be Equal As Strings    ${USED_VAR}    ${${variable}_EXTRA}
""".lstrip(),
        encoding="utf8",
    )

    model = parse_robot_file(robot_file)

    variables = {
        normalize_variable_name("${variable}"): _make_variable_with_value(
            "${variable}",
            "${var_extra}",
        ),
        normalize_variable_name("${A_EXTRA}"): _make_variable("${A_EXTRA}"),
        normalize_variable_name("${B_EXTRA}"): _make_variable("${BAM_EXTRA}"),
    }

    visitor = RobotVisitorVariableUses(variables)
    visitor.visit(model)

    assert variables[normalize_variable_name("${A_EXTRA}")].use_count == 0
    assert variables[normalize_variable_name("${B_EXTRA}")].use_count == 0


def test_dynamic_template_with_conflicting_selector_counts_resolved_candidate(
    tmp_path: Path,
):
    robot_file = tmp_path / "env_selector.resource"
    robot_file.write_text(
        """
*** Keywords ***
My Keyword
    I Log In With ${${ENV}_USER} Username
""".lstrip(),
        encoding="utf8",
    )

    model = parse_robot_file(robot_file)

    variables = {
        normalize_variable_name("${ENV}"): _make_variable_with_value(
            "${ENV}",
            "ENV1",
        ),
        normalize_variable_name("${ENV2_USER}"): _make_variable("${ENV2_USER}"),
        normalize_variable_name("${ENV1_USER}"): _make_variable("${ENV1_USER}"),
    }

    visitor = RobotVisitorVariableUses(variables)
    visitor.visit(model)

    assert variables[normalize_variable_name("${ENV}")].use_count == 1
    assert variables[normalize_variable_name("${ENV2_USER}")].use_count == 0
    assert variables[normalize_variable_name("${ENV1_USER}")].use_count == 1


def test_dynamic_list_template_without_selector_definition_counts_none(
    tmp_path: Path,
):
    robot_file = tmp_path / "env_selector_list.resource"
    robot_file.write_text(
        """
*** Keywords ***
My Keyword
    Variable With List    ${USED_VAR}_A    @{${USED_VAR}_SERVERS}
""".lstrip(),
        encoding="utf8",
    )

    model = parse_robot_file(robot_file)

    variables = {
        normalize_variable_name("@{VAR_A_SERVERS}"): _make_variable(
            "@{VAR_A_SERVERS}",
        ),
        normalize_variable_name("@{VAR_B_SERVERS}"): _make_variable(
            "@{VAR_B_SERVERS}",
        ),
    }

    visitor = RobotVisitorVariableUses(variables)
    visitor.visit(model)

    assert variables[normalize_variable_name("@{VAR_A_SERVERS}")].use_count == 0
    assert variables[normalize_variable_name("@{VAR_B_SERVERS}")].use_count == 0


def test_dynamic_selector_uses_feature_context_literals(tmp_path: Path):
    robot_file = tmp_path / "asset_selector.resource"
    robot_file.write_text(
        """
*** Keywords ***
Select Item Type
    Click    ${item type ${item type id}}
""".lstrip(),
        encoding="utf8",
    )

    model = parse_robot_file(robot_file)

    variables = {
        normalize_variable_name("${item type alpha}"): _make_variable(
            "${item type alpha}",
        ),
        normalize_variable_name("${item type beta group}"): _make_variable(
            "${item type beta group}",
        ),
        normalize_variable_name("${item type gamma}"): _make_variable(
            "${item type gamma}",
        ),
    }

    visitor = RobotVisitorVariableUses(variables)
    visitor.register_context_literals(["alpha", "beta group"])
    visitor.visit(model)

    assert variables[normalize_variable_name("${item type alpha}")].use_count == 1
    assert (
        variables[normalize_variable_name("${item type beta group}")].use_count
        == 1
    )
    assert variables[normalize_variable_name("${item type gamma}")].use_count == 0


def test_dynamic_selector_uses_embedded_keyword_call_literals(tmp_path: Path):
    robot_file = tmp_path / "category_selector.resource"
    robot_file.write_text(
        """
*** Keywords ***
Set Category To ${category}
    Click    ${option ${category}}

Create Example Item
    Set Category To Alpha Group
""".lstrip(),
        encoding="utf8",
    )

    model = parse_robot_file(robot_file)

    variables = {
        normalize_variable_name("${option alpha group}"): _make_variable(
            "${option alpha group}",
        ),
        normalize_variable_name("${option beta group}"): _make_variable(
            "${option beta group}",
        ),
    }

    context_collector = RobotVisitorContextLiterals()
    context_collector.visit(model)

    visitor = RobotVisitorVariableUses(variables)
    visitor.register_context_literals(context_collector.get_context_literals())
    visitor.visit(model)

    assert variables[normalize_variable_name("${option alpha group}")].use_count == 1
    assert variables[normalize_variable_name("${option beta group}")].use_count == 0


def test_dynamic_dotted_selector_counts_dictionary_root_with_prefixed_env(
    tmp_path: Path,
):
    robot_file = tmp_path / "dictionary_selector.resource"
    robot_file.write_text(
        """
*** Keywords ***
Build URI
    Log    ${${ENV}.${REGION}.${account_type}_PERSON_ID}
""".lstrip(),
        encoding="utf8",
    )

    model = parse_robot_file(robot_file)

    variables = {
        normalize_variable_name("&{ROOT}"): _make_variable("&{ROOT}"),
        normalize_variable_name("${ENV}"): _make_variable_with_value(
            "${ENV}",
            "ROOTFE",
        ),
        normalize_variable_name("${REGION}"): _make_variable_with_value(
            "${REGION}",
            "EU",
        ),
    }

    visitor = RobotVisitorVariableUses(variables)
    visitor.register_context_literals(["SELF"])
    visitor.visit(model)

    assert variables[normalize_variable_name("&{ROOT}")].use_count == 1


def test_dynamic_selector_ignores_unrelated_selector_context_literals(
    tmp_path: Path,
):
    robot_file = tmp_path / "generic_selector.resource"
    robot_file.write_text(
        """
*** Keywords ***
Pick Target Option
    Click    ${target option ${target selector id}}
""".lstrip(),
        encoding="utf8",
    )

    model = parse_robot_file(robot_file)

    variables = {
        normalize_variable_name("${target option alpha}"): _make_variable(
            "${target option alpha}",
        ),
        normalize_variable_name("${target option beta}"): _make_variable(
            "${target option beta}",
        ),
    }

    visitor = RobotVisitorVariableUses(variables)
    visitor.register_selector_context_literals(
        "different selector id",
        ["Alpha"],
    )
    visitor.visit(model)

    assert (
        variables[normalize_variable_name("${target option alpha}")].use_count
        == 0
    )
    assert variables[normalize_variable_name("${target option beta}")].use_count == 0


def test_dynamic_selector_uses_id_column_alias_context(tmp_path: Path):
    robot_file = tmp_path / "selector_id_alias.resource"
    robot_file.write_text(
        """
*** Keywords ***
Select By Identifier
    Click    ${item id ${item id}}
""".lstrip(),
        encoding="utf8",
    )

    model = parse_robot_file(robot_file)

    variables = {
        normalize_variable_name("${item id alpha-marker}"): _make_variable(
            "${item id alpha-marker}",
        ),
        normalize_variable_name("${item id beta-marker}"): _make_variable(
            "${item id beta-marker}",
        ),
    }

    visitor = RobotVisitorVariableUses(variables)
    visitor.register_selector_context_literals("id", ["alpha-marker"])
    visitor.visit(model)

    assert variables[normalize_variable_name("${item id alpha-marker}")].use_count == 1
    assert variables[normalize_variable_name("${item id beta-marker}")].use_count == 0
