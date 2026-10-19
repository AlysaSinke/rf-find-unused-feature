from pathlib import Path
from typing import TYPE_CHECKING

import click

from robotframework_find_unused.convert.convert_path import to_relative_path

if TYPE_CHECKING:
    from robotframework_find_unused.common.const import FileUseType, KeywordData, VariableData


DONE = "[ " + click.style("DONE", fg="green") + " ]"
WARN = "[ " + click.style("WARNING", fg="yellow") + " ]"
ERROR = "[ " + click.style("ERROR", fg="red") + " ]"
NOTE = "[ " + click.style("NOTE", fg="cyan") + " ]"
INDENT = "    "


def pretty_kw_name(keyword: "KeywordData") -> str:
    """
    Format keyword name for output to the user
    """
    name = keyword.name

    if keyword.library:
        name = click.style(keyword.library + ".", fg="bright_black") + name

    if keyword.deprecated is True:
        name += " " + click.style("[DEPRECATED]", fg="red")

    return name


def pretty_file_path(path: str, file_types: "set[FileUseType]") -> str:  # noqa: PLR0911
    """
    Format file path for output to the user
    """
    if len(file_types) == 0:
        return path
    if len(file_types) > 1:
        return click.style(f"{path} [Used as: {' & '.join(file_types)}]", fg="yellow")

    file_type = next(iter(file_types))

    if file_type == "RESOURCE":
        return click.style(path, fg="bright_cyan")
    if file_type == "SUITE":
        return path
    if file_type == "SUITE_INIT":
        return path
    if file_type == "LIBRARY":
        return click.style(path, fg="bright_magenta")
    if file_type == "VARIABLE":
        return click.style(path, fg="bright_green")

    msg = f"Unexpected file type {file_type}"
    raise ValueError(msg)


def pretty_variable(var: "VariableData") -> str:
    """
    Format variable for output to the user
    """
    out = var.name

    if var.type is not None:
        out = out.removesuffix("}")
        out += click.style(": " + var.type, fg="bright_black") + "}"

    if var.name != var.resolved_name:
        out += click.style(f" -> {var.resolved_name}", fg="bright_black")

    return out


def pretty_variable_location(var: "VariableData", source_path: "Path") -> str:
    """
    Format the location a variable is defined in for output to the user
    """
    location = to_relative_path(source_path, Path(var.defined_in))

    if var.defined_at_line is not None:
        location += f":{var.defined_at_line}"

    return location
