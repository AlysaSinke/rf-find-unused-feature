from pathlib import Path

from robotframework_find_unused.commands.step.file_types import (
    filter_keyword_definition_files,
    filter_robot_like_files,
)


def test_filter_keyword_definition_files():
    paths = [
        Path("suite.robot"),
        Path("keywords.resource"),
        Path("steps.feature"),
        Path("library.py"),
        Path("notes.md"),
    ]

    actual = filter_keyword_definition_files(paths)

    assert actual == [
        Path("suite.robot"),
        Path("keywords.resource"),
        Path("library.py"),
    ]


def test_filter_robot_like_files():
    paths = [
        Path("suite.robot"),
        Path("keywords.resource"),
        Path("steps.feature"),
        Path("library.py"),
        Path("notes.md"),
    ]

    actual = filter_robot_like_files(paths)

    assert actual == [
        Path("suite.robot"),
        Path("keywords.resource"),
        Path("steps.feature"),
    ]
