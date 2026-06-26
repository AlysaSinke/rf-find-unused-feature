"""
Implementation of the 'variables' command
"""

import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING

from robotframework_find_unused.commands.step.discover_files import step_discover_file_paths
from robotframework_find_unused.commands.step.variables_count_uses import step_count_variable_uses
from robotframework_find_unused.commands.step.variables_definitions import (
    step_get_variable_definitions,
)
from robotframework_find_unused.common.const import VariableData
from robotframework_find_unused.common.normalize import normalize_variable_name
from robotframework_find_unused.common.pythonpath import apply_pythonpath

if TYPE_CHECKING:
    from robotframework_find_unused.reporter.base.variable_reporter import VariableReporter

    from .options import VariableOptions


def command_variables(options: "VariableOptions", reporter: "VariableReporter") -> None:
    """
    Entry point for the CLI command 'variables'
    """
    reporter.on_command_start()

    apply_pythonpath(options.pythonpath)

    file_paths = step_discover_file_paths(options.source_path, reporter=reporter)
    if file_paths is None:
        return

    variables = step_get_variable_definitions(
        file_paths,
        Path(options.source_path),
        include_yaml_variable_files=options.yaml_variable_files == "include",
        reporter=reporter,
    )
    if len(variables) == 0:
        return

    variables = _filter_ignored_variables(variables, options.ignored_variables)
    if len(variables) == 0:
        reporter.on_command_end([])
        return

    variables = step_count_variable_uses(
        file_paths,
        variables,
        reporter=reporter,
    )

    reporter.on_command_end(variables)


def _filter_ignored_variables(
    variable_defs: dict[str, VariableData],
    ignored_globs: list[str],
) -> dict[str, VariableData]:
    if len(ignored_globs) == 0:
        return variable_defs

    normalized_patterns = [normalize_variable_name(pattern) for pattern in ignored_globs]
    filtered_variables = {}
    for var_name_normalized, var_data in variable_defs.items():
        should_ignore = any(
            fnmatch.fnmatchcase(var_name_normalized, pattern)
            for pattern in normalized_patterns
        )
        if should_ignore:
            continue

        filtered_variables[var_name_normalized] = var_data

    return filtered_variables
