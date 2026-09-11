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
        Keyword,
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
        r"^[\$@&%]\{(.*)\$\{([^{}]+)\}(.*)\}$",
    )

    def __init__(self, variable_defs: dict[str, VariableData]) -> None:
        self.variables = variable_defs
        self.context_literals_normalized: set[str] = set()
        self.selector_context_literals_normalized: dict[str, set[str]] = {}
        super().__init__()

    def register_context_literals(self, values: Iterable[str]) -> None:
        """
        Register plain-text values that can help resolve dynamic variable names.
        """
        for value in values:
            value = value.strip()
            if value == "":
                continue

            self.context_literals_normalized.add(
                normalize_variable_name(value, strip_decoration=False),
            )

    def register_selector_context_literals(
        self,
        selector_name: str,
        values: Iterable[str],
    ) -> None:
        """
        Register selector-scoped literals (for example from feature table columns).
        """
        selector_name_normalized = normalize_variable_name(
            selector_name,
            strip_decoration=False,
        )
        if selector_name_normalized == "":
            return

        selector_values = self.selector_context_literals_normalized.setdefault(
            selector_name_normalized,
            set(),
        )
        for value in values:
            value = value.strip()
            if value == "":
                continue
            selector_values.add(
                normalize_variable_name(value, strip_decoration=False),
            )

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

    def count_used_vars_in_strings(self, values: Iterable[str]) -> None:
        """
        Count variable use for free-form strings outside Robot AST nodes.
        """
        self._count_used_vars_in_args(values)

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
            or raw_prefix.endswith(" ")
            or raw_suffix.startswith(("_", ".", "-"))
            or raw_suffix.startswith(" ")
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

        context_filtered_candidates = self._filter_candidates_with_context_literals(
            candidates,
            prefix,
            suffix,
            template_var_name,
        )
        if len(context_filtered_candidates) > 0:
            return context_filtered_candidates

        if resolved_var != unresolved_template_var and resolved_var in self.variables:
            return [resolved_var]

        if len(candidates) == 1:
            return candidates

        if len(candidates) == 0:
            return []

        # Ambiguous dynamic template with multiple possible matches and no
        # reliable selector context; avoid marking all candidates as used.
        return []

    def _filter_candidates_with_context_literals(
        self,
        candidates: list[str],
        prefix: str,
        suffix: str,
        template_var_name: str,
    ) -> list[str]:
        """
        Keep dynamic-name candidates whose variable-specific segment appears in context literals.

        Context literals are loaded from feature table values and help map selectors such as
        `${asset class ${asset class id}}` to concrete variables like
        `${asset class business values}`.
        """
        template_var_name_normalized = normalize_variable_name(
            template_var_name,
            strip_decoration=False,
        )

        selector_scoped_literals = self.selector_context_literals_normalized.get(
            template_var_name_normalized,
            set(),
        )

        # Selector-scoped literals are strongest signal (same semantic column).
        selector_filtered = self._filter_candidates_against_literals(
            candidates,
            prefix,
            suffix,
            selector_scoped_literals,
        )
        if len(selector_filtered) > 0:
            return selector_filtered

        # Generic literals (embedded keyword call captures) are fallback.
        return self._filter_candidates_against_literals(
            candidates,
            prefix,
            suffix,
            self.context_literals_normalized,
        )

    def _filter_candidates_against_literals(
        self,
        candidates: list[str],
        prefix: str,
        suffix: str,
        literals: set[str],
    ) -> list[str]:
        if len(literals) == 0:
            return []

        filtered = []
        prefix_len = len(prefix)
        suffix_len = len(suffix)

        for candidate in candidates:
            if suffix_len > 0:
                middle = candidate[prefix_len:-suffix_len]
            else:
                middle = candidate[prefix_len:]

            if middle in literals:
                filtered.append(candidate)

        return filtered

    def _normalize_extended_variable_syntax(self, var: str) -> str:
        if var in self.variables:
            return var

        dict_root_match = self._match_dictionary_root_for_extended_var(var)
        if dict_root_match is not None:
            return dict_root_match

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

    def _match_dictionary_root_for_extended_var(self, var: str) -> str | None:
        """
        Fallback for dynamic dotted syntax where selectors resolve to prefixed roots.

        Example: `${${ENV}.${ENTITY}.${account_type}_ACCOUNT_PERSON_ID}` may become
        `accbe.nl.self...` while the imported dictionary variable is `&{ACC}`.
        In that case, map root `accbe` back to known dict root `acc`.
        """
        if "." not in var:
            return None

        root = var.split(".", maxsplit=1)[0]
        root_normalized = normalize_variable_name(root)
        if root_normalized == "":
            return None

        dict_candidates = [
            normalized_name
            for normalized_name, data in self.variables.items()
            if data.name.startswith("&{")
        ]
        if len(dict_candidates) == 0:
            return None

        matching = [
            candidate
            for candidate in dict_candidates
            if root_normalized.startswith(candidate)
        ]
        if len(matching) == 0:
            return None

        # Prefer the most specific root if multiple prefixes match.
        matching = sorted(matching, key=len, reverse=True)
        return matching[0]

    def _count_variable_use(self, normalized_name: str) -> None:
        """
        Count the variable.
        """
        if normalized_name not in self.variables:
            # Unknown variable definition. Ignore
            return
        self.variables[normalized_name].use_count += 1


class RobotVisitorContextLiterals(ModelVisitor):
    """
    Collect plain-text context literals from embedded-argument keyword calls.
    """

    _embedded_patterns: list[re.Pattern]
    _normalized_calls: list[str]

    def __init__(self) -> None:
        self._embedded_patterns = []
        self._normalized_calls = []
        super().__init__()

    def visit_Keyword(self, node: "Keyword"):  # noqa: N802
        pattern = self._build_embedded_capture_pattern(node.name)
        if pattern is not None:
            self._embedded_patterns.append(pattern)

        return self.generic_visit(node)

    def visit_KeywordCall(self, node: "KeywordCall"):  # noqa: N802
        self._normalized_calls.append(normalize_keyword_name(node.keyword))

        return self.generic_visit(node)

    def get_context_literals(self) -> list[str]:
        if len(self._embedded_patterns) == 0 or len(self._normalized_calls) == 0:
            return []

        values: set[str] = set()
        for call in self._normalized_calls:
            for pattern in self._embedded_patterns:
                match = pattern.fullmatch(call)
                if not match:
                    continue

                for value in match.groups():
                    if value == "":
                        continue
                    values.add(value)

        return list(values)

    def _build_embedded_capture_pattern(self, keyword_name: str) -> re.Pattern | None:
        normalized = normalize_keyword_name(keyword_name)
        embedded_vars = get_variables_in_string(normalized)
        if len(embedded_vars) == 0:
            return None

        pattern = "^"
        remaining = normalized
        for embedded_var in embedded_vars:
            (prefix, remaining) = remaining.split(embedded_var, maxsplit=1)
            pattern += re.escape(prefix)
            pattern += "(.+?)"
        pattern += re.escape(remaining)
        pattern += "$"
        return re.compile(pattern)

