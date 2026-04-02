import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

import click
from robot.libdocpkg.model import ArgumentSpec

DONE_MARKER = "[ " + click.style("DONE", fg="green") + " ]"
WARN_MARKER = "[ " + click.style("WARNING", fg="yellow") + " ]"
ERROR_MARKER = "[ " + click.style("ERROR", fg="red") + " ]"
NOTE_MARKER = "[ " + click.style("NOTE", fg="cyan") + " ]"
INDENT = "    "
VERBOSE_NO = 0
VERBOSE_SINGLE = 1
VERBOSE_DOUBLE = 2

FilterOption: TypeAlias = Literal["include", "exclude", "only"]


@dataclass
class KeywordData:
    """Data structure for Keywords"""

    name: str
    normalized_name: str
    name_parts: list[str]
    name_match_pattern: re.Pattern | None
    type: Literal[
        "CUSTOM_SUITE",
        "CUSTOM_LIBRARY",
        "CUSTOM_RESOURCE",
        "LIBRARY",
        "UNKNOWN",
    ]
    argument_use_count: None | dict[str, int]
    deprecated: None | bool
    private: bool
    use_count: int
    returns: None | bool
    """If True: Returns something. If False: Does not return anything. If None: Unknown"""

    return_use_count: int
    """If the keyword returns, how often is the return used during keyword call?"""

    arguments: ArgumentSpec | None
    library: str


VariableDefinedInType: TypeAlias = Literal["variables_section", "variable_file", "runtime"]


@dataclass
class VariableValue:
    """Data structure for Variable resolution"""

    normalized_name: str
    value: Iterable[str]


@dataclass
class VariableData(VariableValue):
    """Data structure for Variables"""

    name: str
    type: str | None
    resolved_name: str
    use_count: int
    defined_in_type: VariableDefinedInType
    defined_in: str


@dataclass
class LibraryData:
    """Data structure for Library keywords"""

    name: str
    name_normalized: str
    keywords: list[KeywordData]
    keyword_names_normalized: set[str]


@dataclass
class FileUseData:
    """Data structure for file imports"""

    id: str
    path_absolute: Path
    type: set["FileUseType"]
    used_by: list["FileUsedByData"]

    def __hash__(self) -> int:
        """Hash by id"""
        return hash(self.id)


FileUseType: TypeAlias = Literal[
    "SUITE",
    "SUITE_INIT",
    "RESOURCE",
    "LIBRARY",
    "VARIABLE",
    "FEATURE",
]


@dataclass
class FileUsedByData:
    """Data structure for which file is using a file."""

    file: FileUseData
    as_alias: str | None
    normalized_as_alias: str | None
    args: tuple[str, ...]


# Gherkin/Feature file data structures


@dataclass
class GherkinStepData:
    """Data structure for a Gherkin step (Given/When/Then/And/But)"""

    keyword: str
    """The Gherkin keyword (Given, When, Then, And, But, *)"""

    text: str
    """The step text after the keyword"""

    line: int
    """Line number in the feature file"""


@dataclass
class GherkinScenarioData:
    """Data structure for a Gherkin Scenario or Scenario Outline"""

    name: str
    """Scenario name"""

    steps: list[GherkinStepData]
    """Steps in this scenario"""

    is_outline: bool
    """True if this is a Scenario Outline with Examples"""

    line: int
    """Line number where scenario starts"""


@dataclass
class GherkinFeatureData:
    """Data structure for a parsed Gherkin feature file"""

    file_path: Path
    """Path to the feature file"""

    name: str
    """Feature name"""

    background_steps: list[GherkinStepData]
    """Background steps that apply to all scenarios"""

    scenarios: list[GherkinScenarioData]
    """All scenarios in the feature"""

    tags: list[str]
    """Feature-level tags"""
