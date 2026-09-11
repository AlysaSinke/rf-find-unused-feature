from dataclasses import dataclass
from typing import Literal


@dataclass
class VariableOptions:
    """
    Command line options for the 'variables' command
    """

    show_all_count: bool
    filter_glob: str | None
    ignored_variables: list[str]
    verbose: int
    pythonpath: list[str]
    yaml_variable_files: Literal["include", "exclude"]
    source_path: str
