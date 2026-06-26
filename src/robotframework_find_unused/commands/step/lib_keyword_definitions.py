from typing import TYPE_CHECKING

from robotframework_find_unused.commands.step.file_types import filter_robot_like_files
from robotframework_find_unused.visitors.robot import visit_robot_files
from robotframework_find_unused.visitors.robot.library_import import RobotVisitorLibraryImports

if TYPE_CHECKING:
    from pathlib import Path

    from robotframework_find_unused.reporter.base.partial.keyword_definitions import (
        PartialReporter_DownloadedKeywordDefinitions,
    )


def step_get_downloaded_lib_keywords(
    file_paths: "list[Path]",
    *,
    reporter: "PartialReporter_DownloadedKeywordDefinitions",
    enrich_py_keywords: bool = False,
):
    """
    Gather keyword definitions from imported downloaded libraries and show progress

    Will only resolve libraries that are actually imported in an in-scope .robot or .resource file.
    """
    reporter.on_get_downloaded_keyword_definitions_start(file_paths)

    robot_file_paths = filter_robot_like_files(file_paths)

    visitor = RobotVisitorLibraryImports(reporter, enrich_py_keywords=enrich_py_keywords)
    visit_robot_files(robot_file_paths, visitor)
    downloaded_libraries = list(visitor.downloaded_libraries.values())

    reporter.on_get_downloaded_keyword_definitions_end(file_paths, downloaded_libraries)
    return downloaded_libraries
