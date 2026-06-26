from pathlib import Path


def filter_keyword_definition_files(file_paths: list[Path]) -> list[Path]:
    """
    Files that can contain keyword definitions discoverable by LibDoc.
    """
    return [p for p in file_paths if p.suffix.lower() in (".robot", ".resource", ".py")]


def filter_robot_like_files(file_paths: list[Path]) -> list[Path]:
    """
    Files traversable by Robot AST visitors in this project.
    """
    return [p for p in file_paths if p.suffix.lower() in (".robot", ".resource", ".feature")]