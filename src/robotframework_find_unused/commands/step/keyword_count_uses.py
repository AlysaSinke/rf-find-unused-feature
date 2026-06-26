import ast
from typing import TYPE_CHECKING

from robotframework_find_unused.commands.keywords.options import KeywordOptions
from robotframework_find_unused.common.normalize import (
    normalize_keyword_name,
    normalize_library_name,
)
from robotframework_find_unused.visitors.robot import visit_robot_files
from robotframework_find_unused.visitors.robot.keyword_visitor import RobotVisitorKeywords

if TYPE_CHECKING:
    from pathlib import Path

    from robotframework_find_unused.common.const import KeywordData, LibraryData
    from robotframework_find_unused.reporter.base.partial.count_keywords import (
        PartialReporter_CountKeywords,
    )


def step_count_keyword_uses(
    file_paths: "list[Path]",
    keywords: "list[KeywordData]",
    downloaded_libraries: "list[LibraryData]",
    *,
    reporter: "PartialReporter_CountKeywords",
):
    """
    Walk through all robot files to count keyword uses and keep the user up-to-date on progress
    """
    reporter.on_count_keyword_uses_start(file_paths, keywords, downloaded_libraries)

    visitor = RobotVisitorKeywords(keywords, downloaded_libraries)
    visit_robot_files(file_paths, visitor)
    counted_keywords = list(visitor.keywords.values())

    _count_python_imported_keyword_uses(file_paths, counted_keywords)
    _count_python_internal_keyword_uses(counted_keywords)

    counted_keywords = _append_unused_keywords(counted_keywords, downloaded_libraries, reporter)

    reporter.on_count_keyword_uses_end(file_paths, keywords, downloaded_libraries, counted_keywords)
    return counted_keywords


def _count_python_internal_keyword_uses(counted_keywords: "list[KeywordData]") -> None:
    """
    Mark Python keywords as used when reached through Python call chains.

    Counts are conservative: reachable internal helpers are set to used (>=1).
    """
    keyword_lookup: dict[tuple[str, str], KeywordData] = {}
    keyword_name_candidates: dict[str, list[tuple[str, str]]] = {}
    for kw in counted_keywords:
        if kw.type != "CUSTOM_LIBRARY":
            continue

        library = normalize_library_name(kw.library)
        key = (library, kw.normalized_name)
        keyword_lookup[key] = kw
        if kw.normalized_name in keyword_name_candidates:
            keyword_name_candidates[kw.normalized_name].append(key)
        else:
            keyword_name_candidates[kw.normalized_name] = [key]

    if len(keyword_lookup) == 0:
        return

    reachable = set(
        key
        for key, kw in keyword_lookup.items()
        if kw.use_count > 0
    )
    to_visit = [*reachable]

    while len(to_visit) > 0:
        current = to_visit.pop()
        caller = keyword_lookup[current]
        call_targets = caller.python_call_targets_normalized or set()

        for callee_normalized_name in call_targets:
            callee_key = (current[0], callee_normalized_name)
            if callee_key not in keyword_lookup:
                candidates = keyword_name_candidates.get(callee_normalized_name, [])
                if len(candidates) != 1:
                    continue

                callee_key = candidates[0]

            if callee_key in reachable:
                continue

            reachable.add(callee_key)
            to_visit.append(callee_key)

    for key in reachable:
        kw = keyword_lookup[key]
        if kw.use_count == 0:
            kw.use_count = 1


def _count_python_imported_keyword_uses(
    file_paths: "list[Path]",
    counted_keywords: "list[KeywordData]",
) -> None:
    """
    Mark Python keywords as used when called through imported Python modules.

    This catches cases where a keyword function is called from another Python
    module (for example listeners), outside Robot keyword call sites.
    """
    keyword_lookup: dict[tuple[str, str], KeywordData] = {}
    keyword_name_candidates: dict[str, list[tuple[str, str]]] = {}
    for kw in counted_keywords:
        if kw.type != "CUSTOM_LIBRARY":
            continue

        key = (normalize_library_name(kw.library), kw.normalized_name)
        keyword_lookup[key] = kw
        if kw.normalized_name in keyword_name_candidates:
            keyword_name_candidates[kw.normalized_name].append(key)
        else:
            keyword_name_candidates[kw.normalized_name] = [key]

    if len(keyword_lookup) == 0:
        return

    for file_path in file_paths:
        if file_path.suffix.lower() != ".py":
            continue

        try:
            source = file_path.read_text(encoding="utf8")
        except OSError:
            continue

        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        visitor = _PythonImportedKeywordCallVisitor()
        visitor.visit(tree)

        for key in visitor.called_keywords:
            keyword = keyword_lookup.get(key)
            if keyword is None:
                continue

            if keyword.use_count == 0:
                keyword.use_count = 1

        local_reachable = set(visitor.local_called_keyword_names_normalized)
        to_visit = [*local_reachable]
        while len(to_visit) > 0:
            current = to_visit.pop()
            for callee in visitor.local_function_call_graph.get(current, set()):
                if callee in local_reachable:
                    continue

                local_reachable.add(callee)
                to_visit.append(callee)

        file_library = normalize_library_name(file_path.stem)
        for local_name in local_reachable:
            key = (file_library, local_name)
            if key not in keyword_lookup:
                candidates = keyword_name_candidates.get(local_name, [])
                if len(candidates) != 1:
                    continue
                key = candidates[0]

            keyword = keyword_lookup[key]
            if keyword.use_count == 0:
                keyword.use_count = 1


class _PythonImportedKeywordCallVisitor(ast.NodeVisitor):
    """Collect calls to imported functions and modules."""

    def __init__(self) -> None:
        self.imported_names_to_library: dict[str, str] = {}
        self.imported_modules_to_library: dict[str, str] = {}
        self.called_keywords: set[tuple[str, str]] = set()
        self.local_called_keyword_names_normalized: set[str] = set()
        self.local_function_call_graph: dict[str, set[str]] = {}
        self._scope_depth = 0
        self._class_depth = 0
        self._current_local_function_stack: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):  # noqa: N802
        self._scope_depth += 1

        if self._class_depth == 0:
            function_name = normalize_keyword_name(node.name.replace("_", " "))
            self.local_function_call_graph.setdefault(function_name, set())
            self._current_local_function_stack.append(function_name)

        self.generic_visit(node)

        if self._class_depth == 0:
            self._current_local_function_stack.pop()

        self._scope_depth -= 1

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):  # noqa: N802
        self._scope_depth += 1

        if self._class_depth == 0:
            function_name = normalize_keyword_name(node.name.replace("_", " "))
            self.local_function_call_graph.setdefault(function_name, set())
            self._current_local_function_stack.append(function_name)

        self.generic_visit(node)

        if self._class_depth == 0:
            self._current_local_function_stack.pop()

        self._scope_depth -= 1

    def visit_ClassDef(self, node: ast.ClassDef):  # noqa: N802
        self._class_depth += 1
        self._scope_depth += 1
        self.generic_visit(node)
        self._scope_depth -= 1
        self._class_depth -= 1

    def visit_Import(self, node: ast.Import):  # noqa: N802
        for alias in node.names:
            alias_name = alias.asname or alias.name.split(".")[-1]
            library = _import_module_to_library(alias.name)
            self.imported_modules_to_library[alias_name] = library

    def visit_ImportFrom(self, node: ast.ImportFrom):  # noqa: N802
        if node.module is None:
            return

        library = _import_module_to_library(node.module)
        for alias in node.names:
            if alias.name == "*":
                continue

            alias_name = alias.asname or alias.name
            self.imported_names_to_library[alias_name] = library

    def visit_Call(self, node: ast.Call):  # noqa: N802
        if self._scope_depth == 0 and isinstance(node.func, ast.Name):
            normalized_name = normalize_keyword_name(
                node.func.id.replace("_", " "),
            )
            self.local_called_keyword_names_normalized.add(normalized_name)

        if self._current_local_function_stack and isinstance(node.func, ast.Name):
            function_name = node.func.id
            if function_name not in self.imported_names_to_library:
                caller = self._current_local_function_stack[-1]
                normalized_name = normalize_keyword_name(
                    function_name.replace("_", " "),
                )
                self.local_function_call_graph.setdefault(caller, set()).add(
                    normalized_name,
                )

        if isinstance(node.func, ast.Name):
            function_name = node.func.id
            library = self.imported_names_to_library.get(function_name)
            if library is not None:
                normalized_name = normalize_keyword_name(
                    function_name.replace("_", " "),
                )
                self.called_keywords.add((library, normalized_name))

        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            module_alias = node.func.value.id
            library = self.imported_modules_to_library.get(module_alias)
            if library is not None:
                normalized_name = normalize_keyword_name(
                    node.func.attr.replace("_", " "),
                )
                self.called_keywords.add((library, normalized_name))

        self.generic_visit(node)


def _import_module_to_library(module: str) -> str:
    return normalize_library_name(module.split(".")[-1])


def _append_unused_keywords(
    counted_keywords: "list[KeywordData]",
    downloaded_libraries: "list[LibraryData]",
    reporter: "PartialReporter_CountKeywords",
) -> "list[KeywordData]":
    if reporter.options.library_keywords == "exclude":
        return counted_keywords

    if (
        isinstance(reporter.options, KeywordOptions)
        and reporter.options.unused_library_keywords == "exclude"
    ):
        return counted_keywords

    for lib in downloaded_libraries:
        for kw in lib.keywords:
            if kw in counted_keywords:
                continue
            counted_keywords.append(kw)

    return counted_keywords
