import ast

from robot.libdocpkg.model import KeywordDoc

from robotframework_find_unused.common.impossible_state_error import ImpossibleStateError
from robotframework_find_unused.common.normalize import normalize_keyword_name


class EnrichedKeywordDoc:
    """Wrap Libdocs KeywordDoc to add more data."""

    returns: bool | None = None
    is_local_definition: bool
    python_call_targets_normalized: set[str]

    def __init__(self, doc: KeywordDoc) -> None:
        self.doc = doc
        self.is_local_definition = False
        self.python_call_targets_normalized = set()


class PythonKeywordVisitor(ast.NodeVisitor):
    """Visit single Python file AST to find data in functions"""

    def __init__(self, keywords: list[KeywordDoc]) -> None:
        self.keywords: list[EnrichedKeywordDoc] = []
        for keyword in keywords:
            self.keywords.append(EnrichedKeywordDoc(keyword))

        self.keyword_names_normalized = {
            normalize_keyword_name(keyword.doc.name) for keyword in self.keywords
        }

    def visit_FunctionDef(self, node: ast.FunctionDef):  # noqa: N802
        """Visit function definition"""
        self._register_function_data(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):  # noqa: N802
        """Visit async function definition"""
        self._register_function_data(node)

    def _register_function_data(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        matching_keywords = [kw for kw in self.keywords if kw.doc.lineno == node.lineno]
        if not matching_keywords:
            # Function is not a keyword
            return

        if len(matching_keywords) > 1:
            msg = "Found multiple Python keyword definitions on the same line"
            raise ImpossibleStateError(msg)

        matching_keyword = matching_keywords[0]
        matching_keyword.is_local_definition = True

        return_visitor = PythonKeywordReturnVisitor()
        return_visitor.visit(node)
        matching_keyword.returns = return_visitor.has_return_node

        call_visitor = PythonKeywordCallVisitor()
        call_visitor.visit(node)
        matching_keyword.python_call_targets_normalized = {
            name
            for name in call_visitor.called_keyword_names_normalized
            if name in self.keyword_names_normalized
        }


class PythonKeywordReturnVisitor(ast.NodeVisitor):
    """Only visit return statements of Python AST."""

    def __init__(self) -> None:
        self.has_return_node: bool = False

    def visit_Return(self, node: ast.Return):  # noqa: N802
        """Visit function return"""
        if self.has_return_node is True:
            return
        self.has_return_node = node.value is not None


class PythonKeywordCallVisitor(ast.NodeVisitor):
    """Visit call nodes in Python AST."""

    def __init__(self) -> None:
        self.called_keyword_names_normalized: set[str] = set()

    def visit_Call(self, node: ast.Call):  # noqa: N802
        """Visit function call."""
        callee_name = _get_callee_function_name(node)
        if callee_name:
            normalized_name = normalize_keyword_name(callee_name.replace("_", " "))
            self.called_keyword_names_normalized.add(normalized_name)

        self.generic_visit(node)


def _get_callee_function_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id

    if isinstance(node.func, ast.Attribute):
        if isinstance(node.func.value, ast.Name) and node.func.value.id in {
            "self",
            "cls",
        }:
            return node.func.attr

    return None
