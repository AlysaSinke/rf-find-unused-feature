import re
from collections.abc import Iterable
from typing import TYPE_CHECKING

from robot.api.parsing import (
    ModelVisitor,
    Variable,
)

from robotframework_find_unused.common.const import VariableData
from robotframework_find_unused.common.normalize import (
    normalize_keyword_name,
    normalize_variable_name,
)
from robotframework_find_unused.parse.parse_variable import get_variables_in_string
from robotframework_find_unused.resolve.resolve_variables import (
    SUPPORTED_BUILTIN_VARS,
    resolve_variable_name,
)

if TYPE_CHECKING:
    from robot.api.parsing import (
        Arguments,
        For,
        If,
        KeywordCall,
        TemplateArguments,
        Var,
        VariableSection,
        While,
    )


class RobotVisitorVariableUses(ModelVisitor):
    """
    Visit file and count variable usage.
    """

    variables: dict[str, VariableData]

    # Details: https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#special-variable-syntax
    _pattern_eval_variable = re.compile(r"\$(\w+)")
    # Details: https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#inline-python-evaluation
    _pattern_inline_eval = re.compile(r"\${{(.+?)}}")
    _pattern_feature_outline_arg = re.compile(r"<([^<>]+)>")
    _pattern_dynamic_name_template = re.compile(r"^(.*)\$\{([a-z0-9]+)\}(.*)$")
    _pattern_dynamic_name_template_raw = re.compile(
        r"^\$\{(.*)\$\{([A-Za-z0-9_]+)\}(.*)\}$",
    )

    def __init__(self, variable_defs: dict[str, VariableData]) -> None:
        self.variables = variable_defs
        super().__init__()

    def visit_VariableSection(self, node: "VariableSection"):  # noqa: N802
        """
        Look for used variables in variable definitions.
        """
        for var_node in node.body:
            if not isinstance(var_node, Variable):
                continue
            self._count_used_vars_in_args(var_node.value)

        return self.generic_visit(node)

    def visit_Arguments(self, node: "Arguments"):  # noqa: N802
        """
        Look for used variables in the default value of keyword arguments.
        """
        arguments = node.values

        for argument in arguments:
            if "=" not in argument:
                # Argument has no default. We don't care about it.
                continue

            argument_default = argument.split("=", 1)[1]
            self._count_used_vars_in_args([argument_default])

        return self.generic_visit(node)

    def visit_KeywordCall(self, node: "KeywordCall"):  # noqa: N802
        """
        Look for used variables called keyword arguments.
        """
        keyword_name_normalized = normalize_keyword_name(node.keyword)

        # Feature steps are parsed as keyword calls where placeholders are often in the keyword
        # name itself instead of argument columns.
        self._count_used_vars_in_args([node.keyword])

        if keyword_name_normalized == "evaluate":
            self._count_used_vars_in_eval(node.args[0])
        elif keyword_name_normalized in (
            "settestvariable",
            "setsuitevariable",
            "setglobalvariable",
        ):
            self._count_used_vars_in_args(node.args[1:])
        else:
            self._count_used_vars_in_args(node.args)

        return self.generic_visit(node)

    def visit_TemplateArguments(self, node: "TemplateArguments"):  # noqa: N802
        """
        Look for used variables in templated tests.
        """
        self._count_used_vars_in_args(node.args)

        return self.generic_visit(node)

    def visit_For(self, node: "For"):  # pyright: ignore[reportIncompatibleMethodOverride] # noqa: N802
        """
        Look for used variables in for loop conditions.
        """
        self._count_used_vars_in_args(node.values)

        return self.generic_visit(node)

    def visit_If(self, node: "If"):  # pyright: ignore[reportIncompatibleMethodOverride] # noqa: N802
        """
        Look for used variables in if/else/elseif statement conditions.
        """
        if node.condition:
            self._count_used_vars_in_eval(node.condition)

        return self.generic_visit(node)

    def visit_While(self, node: "While"):  # pyright: ignore[reportIncompatibleMethodOverride] # noqa: N802
        """
        Look for used variables in while loop conditions.
        """
        if node.condition:
            self._count_used_vars_in_eval(node.condition)

        return self.generic_visit(node)

    def visit_Var(self, node: "Var"):  # noqa: N802
        """
        Look for used variables in values assigned with VAR syntax.
        """
        self._count_used_vars_in_args(node.value)

        return self.generic_visit(node)

    def _count_used_vars_in_eval(self, eval_str: str) -> None:
        """
        Count used variables found in a python evaluation context
        """
        used_vars = self._get_used_vars_in_eval(eval_str)
        used_vars = self._filter_supported_vars(used_vars)
        for name in used_vars:
            self._count_variable_use(name)

    def _get_used_vars_in_eval(self, eval_str: str) -> list[str]:
        """
        Return a list of used variables in a given evaluated Python expression
        """
        eval_str = eval_str.strip()
        used_vars = self._get_used_vars_in_args([eval_str])

        match = self._pattern_eval_variable.findall(eval_str)
        for var in match:
            used_vars.append("${" + normalize_variable_name(var) + "}")

        return used_vars

    def _count_used_vars_in_args(self, args: Iterable[str]) -> None:
        """
        Count used variables found in a list of arguments
        """
        used_vars = self._get_used_vars_in_args(args)
        used_vars = self._filter_supported_vars(used_vars)
        for name in used_vars:
            self._count_variable_use(name)

    def _get_used_vars_in_args(self, args: Iterable[str]) -> list[str]:
        """
        Return a list of used variables in a given list of strings
        """
        used_vars = []
        for arg in args:
            var_match = get_variables_in_string(arg)
            used_vars += var_match

            for outline_arg in self._pattern_feature_outline_arg.findall(arg):
                outline_arg = outline_arg.strip()
                if outline_arg == "":
                    continue
                used_vars.append("${" + outline_arg + "}")

            eval_match = self._pattern_inline_eval.findall(arg)
            for inline_eval in eval_match:
                used_vars += self._get_used_vars_in_eval(inline_eval)

        return used_vars

    def _filter_supported_vars(self, variables: list[str]) -> list[str]:
        """
        Filter out unsupported variables and some Robot builtin stuff.
        """
        filtered = []
        for formatted_var in variables:
            var = normalize_variable_name(formatted_var)
            unresolved_template_var = var

            try:
                float(var)
                # Is a number, not a variable name.
                # Details: https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#number-variables
                continue
            except ValueError:
                pass

            if var in SUPPORTED_BUILTIN_VARS:
                continue

            (var, used_vars) = resolve_variable_name(var, self.variables)
            for v in used_vars:
                self._count_variable_use(v)

            dynamic_candidates = self._expand_dynamic_name_candidates(
                formatted_var,
                unresolved_template_var,
                var,
            )
            if len(dynamic_candidates) > 0:
                filtered.extend(dynamic_candidates)
                continue

            if not var.isalnum():
                # Potential extended variable syntax
                var = self._normalize_extended_variable_syntax(var)

            filtered.append(var)

        return filtered

    def _expand_dynamic_name_candidates(
        self,
        formatted_var: str,
        unresolved_template_var: str,
        resolved_var: str,
    ) -> list[str]:
        """
        Expand dynamic variable-name patterns to all matching concrete variable names.

        Example:
            unresolved_template_var="originalmifirreportfile${entity}"
            matches candidates like "originalmifirreportfilenl" and
            "originalmifirreportfilebe".
        """
        if "${" not in unresolved_template_var:
            return []

        raw_match = self._pattern_dynamic_name_template_raw.match(formatted_var)
        if not raw_match:
            return []

        (raw_prefix, _raw_template_var_name, raw_suffix) = raw_match.groups()
        has_separator_boundary = (
            raw_prefix.endswith(("_", ".", "-"))
            or raw_suffix.startswith(("_", ".", "-"))
        )
        if not has_separator_boundary:
            return []

        match = self._pattern_dynamic_name_template.match(unresolved_template_var)
        if not match:
            return []

        (prefix, template_var_name, suffix) = match.groups()
        # Guard against fully dynamic names like `${${field_name}}` which would
        # otherwise match every variable.
        if prefix == "" and suffix == "":
            return []

        # Guard against obvious non-variable selectors like `${HELLO_${1}}`
        # and `${HELLO_${True}}`.
        if template_var_name.isdigit():
            return []

        if template_var_name in SUPPORTED_BUILTIN_VARS:
            return []

        candidates = [
            var_name
            for var_name in self.variables
            if var_name.startswith(prefix) and var_name.endswith(suffix)
        ]

        if len(candidates) <= 1:
            return []

        return candidates

    def _normalize_extended_variable_syntax(self, var: str) -> str:
        if var in self.variables:
            return var

        var_name = var
        while len(var_name) > 0:
            # Remove all trailing alphanumeric
            while len(var_name) > 0 and var_name[-1].isalnum():
                var_name = var_name[0:-1]
            if len(var_name) == 0:
                break

            # Remove single trailing special char
            var_name = var_name[0:-1]
            if len(var_name) == 0:
                break

            if var_name in self.variables:
                return var_name

        # Could not find var. Don't modify.
        return var

    def _count_variable_use(self, normalized_name: str) -> None:
        """
        Count the variable.
        """
        if normalized_name not in self.variables:
            # Unknown variable definition. Ignore
            return
        self.variables[normalized_name].use_count += 1
