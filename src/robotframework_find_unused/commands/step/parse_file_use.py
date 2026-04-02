from pathlib import Path

import click

from robotframework_find_unused.common.const import (
    DONE_MARKER,
    INDENT,
    VERBOSE_NO,
    VERBOSE_SINGLE,
    FileUseData,
    FileUsedByData,
)
from robotframework_find_unused.common.normalize import normalize_file_path
from robotframework_find_unused.visitors.gherkin import filter_feature_files, filter_robot_files
from robotframework_find_unused.visitors.robot import visit_robot_files
from robotframework_find_unused.visitors.robot.file_import import RobotVisitorFileImports


def cli_step_parse_file_use(file_paths: list[Path], source_path: Path, *, verbose: int):
    """
    Parse files and keep the user up-to-date on progress
    """
    click.echo("Parsing file imports...")

    files = _count_file_uses(file_paths, source_path)

    _log_file_stats(files, verbose)
    return files


def _count_file_uses(file_paths: list[Path], source_path: Path) -> list[FileUseData]:
    """
    Walk through all robot and feature files to keep track of imports.
    """
    # Separate robot files from feature files
    robot_files = filter_robot_files(file_paths)
    feature_files = filter_feature_files(file_paths)

    # Process robot files with the visitor
    visitor = RobotVisitorFileImports(source_path, set(file_paths))
    visit_robot_files(
        robot_files,
        visitor,
        parse_sections=("settings", "keywords", "test cases", "tasks"),
    )
    files = visitor.files

    # Register feature files as FEATURE type
    _register_feature_files(feature_files, files, visitor.init_files, source_path)

    # Add undiscovered files from input file paths
    for path in file_paths:
        path_normalized = normalize_file_path(path)
        if path_normalized in files:
            continue

        files[path_normalized] = FileUseData(
            id=path_normalized,
            path_absolute=path,
            type=set(),
            used_by=[],
        )

    return list(files.values())


def _register_feature_files(
    feature_files: list[Path],
    files: dict[str, FileUseData],
    init_files: dict[Path, FileUseData],
    root_directory: Path,
) -> None:
    """
    Register feature files and their relationship to suite __init__ files.

    Feature files are test suites that inherit resources from __init__.robot
    files in their directory hierarchy, just like .robot test suites.
    """
    root_dir_parts_len = len(root_directory.resolve().parts)

    for feature_path in feature_files:
        feature_path_resolved = feature_path.resolve()
        path_normalized = normalize_file_path(feature_path_resolved)

        if path_normalized in files:
            # Already registered (unlikely for feature files)
            continue

        # Create FileUseData for the feature file
        feature_file = FileUseData(
            id=path_normalized,
            path_absolute=feature_path_resolved,
            type={"FEATURE"},
            used_by=[],
        )
        files[path_normalized] = feature_file

        # Register usage of suite __init__ files in parent directories
        path = feature_path_resolved
        while len(path.parts) > root_dir_parts_len:
            path = path.parent
            init_file = init_files.get(path, None)

            if init_file:
                init_file.used_by.append(
                    FileUsedByData(
                        file=feature_file,
                        as_alias=None,
                        normalized_as_alias=None,
                        args=(),
                    ),
                )


def _log_file_stats(files: list[FileUseData], verbose: int) -> None:
    """
    Output details on parsed files to the user
    """
    click.echo(f"{DONE_MARKER} Parsed {len(files)} files")

    if verbose == VERBOSE_NO:
        return

    file_types: dict[str, list[str]] = {}
    for file in files:
        file_type = "UNKNOWN" if len(file.type) == 0 else next(iter(file.type))

        if file_type not in file_types:
            file_types[file_type] = []
        file_types[file_type].append(file.id)

    for file_type, file_paths in sorted(file_types.items(), key=lambda x: len(x[1]), reverse=True):
        click.echo(f"{INDENT}{len(file_paths)} files of type {file_type}")

        if verbose == VERBOSE_SINGLE:
            continue

        sorted_file_paths = sorted(file_paths, key=lambda f: f)
        for path in sorted_file_paths:
            click.echo(f"{INDENT}{INDENT}{click.style(path, fg='bright_black')}")
