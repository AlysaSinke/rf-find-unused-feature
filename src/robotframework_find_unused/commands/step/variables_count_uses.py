from pathlib import Path

from robotframework_find_unused.commands.step.file_types import filter_robot_like_files
from robotframework_find_unused.common.const import VariableData
from robotframework_find_unused.parse.parse_feature_table import get_feature_table_cells
from robotframework_find_unused.reporter.base.variable_reporter import VariableReporter
from robotframework_find_unused.visitors.robot import visit_robot_files
from robotframework_find_unused.visitors.robot.variable_count import (
    RobotVisitorContextLiterals,
    RobotVisitorVariableUses,
)


def step_count_variable_uses(
    file_paths: list[Path],
    variable_defs: dict[str, VariableData],
    *,
    reporter: VariableReporter,
):
    """
    Walk through all robot files to count keyword uses and show progress
    """
    reporter.on_count_variable_uses_start(file_paths, variable_defs)

    robot_like_file_paths = filter_robot_like_files(file_paths)
    feature_table_cells = _get_feature_table_cells(robot_like_file_paths)
    context_literals = _get_dynamic_context_literals(robot_like_file_paths)

    visitor = RobotVisitorVariableUses(variable_defs)
    visitor.register_context_literals(feature_table_cells)
    visitor.register_context_literals(context_literals)
    visit_robot_files(robot_like_file_paths, visitor)
    _count_feature_table_variable_uses(feature_table_cells, visitor)

    variables = list(visitor.variables.values())

    reporter.on_count_variable_uses_end(file_paths, variable_defs, variables)
    return variables


def _count_feature_table_variable_uses(
    table_cells: list[str],
    visitor: RobotVisitorVariableUses,
) -> None:
    if len(table_cells) == 0:
        return

    visitor.count_used_vars_in_strings(table_cells)


def _get_feature_table_cells(file_paths: list[Path]) -> list[str]:
    feature_files = [p for p in file_paths if p.suffix.lower() == ".feature"]
    table_cells: list[str] = []
    for feature_file in feature_files:
        table_cells.extend(get_feature_table_cells(feature_file))

    return table_cells


def _get_dynamic_context_literals(file_paths: list[Path]) -> list[str]:
    collector = RobotVisitorContextLiterals()
    visit_robot_files(file_paths, collector)
    return collector.get_context_literals()
