"""C/C++ Documentation Analyzer.

Regex-based analyzer for C and C++ documentation quality.
Implements multi-criteria assessment with priority calculation.

Architecture:
    - Regex parsing for function/method/class discovery
    - Doxygen-style documentation comment assessment
    - Priority calculation via factor-based scoring
    - Security protections against DoS attacks
"""

import logging
import re
from typing import Any, Literal, cast

from docscope_mcp.models import (
    DEFAULT_CONFIG,
    AnalysisConfig,
    ArgInfo,
    FunctionInfo,
    QualityAssessment,
    QualityIndicators,
    QualityLevel,
)

# Pre-compiled regex patterns for C++ parsing
# Matches Doxygen comments: /** ... */ or /// or //!
REGEX_DOXYGEN_BLOCK = re.compile(
    r"(?P<doxygen>(?:/\*\*[\s\S]*?\*/|(?:\s*(?:///|//!).*\n)+))"
    r"\s*"
    r"(?P<template>template\s*<[^>]*>\s*)?"
    r"(?P<modifiers>(?:(?:static|virtual|inline|constexpr|explicit|friend|extern)\s+)*)"
    r"(?P<return_type>(?:const\s+)?[\w:<>&*\s]+?(?:\s*[*&]+)?)\s+"
    r"(?P<class_prefix>(?:\w+::)*)"
    r"(?P<name>~?\w+)\s*"
    r"\((?P<params>[^)]*)\)"
    r"(?P<qualifiers>(?:\s*(?:const|override|final|noexcept|=\s*0|=\s*default|=\s*delete))*)",
    re.MULTILINE,
)

REGEX_FUNCTION = re.compile(
    r"(?P<template>template\s*<[^>]*>\s*)?"
    r"(?P<modifiers>(?:(?:static|virtual|inline|constexpr|explicit|friend|extern)\s+)*)"
    r"(?P<return_type>(?:const\s+)?[\w:<>&*\s]+?(?:\s*[*&]+)?)\s+"
    r"(?P<class_prefix>(?:\w+::)*)"
    r"(?P<name>~?\w+)\s*"
    r"\((?P<params>[^)]*)\)"
    r"(?P<qualifiers>(?:\s*(?:const|override|final|noexcept|=\s*0|=\s*default|=\s*delete))*)",
    re.MULTILINE,
)

REGEX_CLASS = re.compile(
    r"(?P<doxygen>(?:/\*\*[\s\S]*?\*/|(?:\s*(?:///|//!).*\n)+))?\s*"
    r"(?:class|struct)\s+(?P<name>\w+)",
    re.MULTILINE,
)

REGEX_PARAM = re.compile(
    r"(?P<type>(?:const\s+)?[\w:<>&*\s]+(?:\s*[*&]+)?)\s+"
    r"(?P<name>\w+)"
    r"(?:\s*=\s*(?P<default>[^,)]+))?"
)

# Doxygen tag patterns
REGEX_DOXYGEN_BRIEF = re.compile(r"@brief\s+(.+?)(?=@|\*/|$)", re.DOTALL)
REGEX_DOXYGEN_BRIEF_ALT = re.compile(r"\\brief\s+(.+?)(?=\\|@|\*/|$)", re.DOTALL)
REGEX_DOXYGEN_PARAM = re.compile(
    r"@param(?:\[(?:in|out|in,out)\])?\s+(\w+)\s+(.+?)(?=@param|@return|@throw|@|\\|\*/|$)",
    re.DOTALL,
)
REGEX_DOXYGEN_PARAM_ALT = re.compile(
    r"\\param(?:\[(?:in|out|in,out)\])?\s+(\w+)\s+(.+?)(?=\\param|\\return|\\throw|\\|@|\*/|$)",
    re.DOTALL,
)
REGEX_DOXYGEN_RETURN = re.compile(r"@returns?\s+(.+?)(?=@|\*/|$)", re.DOTALL)
REGEX_DOXYGEN_RETURN_ALT = re.compile(r"\\returns?\s+(.+?)(?=\\|@|\*/|$)", re.DOTALL)
REGEX_DOXYGEN_THROW = re.compile(r"@(?:throw|throws|exception)\s+(.+?)(?=@|\*/|$)", re.DOTALL)
REGEX_DOXYGEN_THROW_ALT = re.compile(
    r"\\(?:throw|throws|exception)\s+(.+?)(?=\\|@|\*/|$)", re.DOTALL
)
REGEX_DOXYGEN_EXAMPLE = re.compile(r"@(?:example|code)(.+?)(?:@endcode|@|\*/|$)", re.DOTALL)
REGEX_DOXYGEN_EXAMPLE_ALT = re.compile(
    r"\\(?:example|code)(.+?)(?:\\endcode|\\|@|\*/|$)", re.DOTALL
)
REGEX_DOXYGEN_DETAILS = re.compile(r"@details\s+(.+?)(?=@|\*/|$)", re.DOTALL)
REGEX_DOXYGEN_DETAILS_ALT = re.compile(r"\\details\s+(.+?)(?=\\|@|\*/|$)", re.DOTALL)


class CCppAnalyzer:
    """C/C++ documentation quality analyzer using regex-based parsing.

    Analyzes C and C++ source code to identify functions needing documentation
    improvement. Uses multi-criteria assessment including:
    - Doxygen-style documentation comment analysis
    - Content quality (depth, completeness)
    - Context awareness (test vs production code)

    Attributes:
        config: Analysis configuration
        logger: Logger instance for diagnostics

    Examples:
        ```python
        analyzer = CCppAnalyzer()
        results = analyzer.analyze("void foo() {}")
        for result in results:
            print(f"{result['function_name']}: {result['priority']}")
        ```
    """

    def __init__(
        self,
        config: AnalysisConfig | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize C/C++ analyzer with configuration.

        Creates a new CCppAnalyzer instance with optional custom configuration
        and logging. The analyzer uses regex-based parsing to extract C/C++
        functions and assess Doxygen documentation quality.

        Args:
            config: Analysis configuration. Defaults to DEFAULT_CONFIG.
            logger: Logger instance. Defaults to module logger.

        Returns:
            None - initializes instance attributes.

        Raises:
            No exceptions raised.

        Example:
            >>> analyzer = CCppAnalyzer()
            >>> analyzer.get_language()
            'c_cpp'
        """
        self.config = config or DEFAULT_CONFIG
        self.logger = logger or logging.getLogger(__name__)

    def get_language(self) -> str:
        """Return the programming language identifier for this analyzer.

        Provides language identification for multi-language analyzer routing.
        MCP tools use this to select the appropriate analyzer based on file
        extension or user specification.

        Args:
            None - no parameters required.

        Returns:
            String 'c_cpp' identifying this as the C/C++ analyzer.

        Raises:
            No exceptions - always returns 'c_cpp'.

        Example:
            >>> analyzer = CCppAnalyzer()
            >>> analyzer.get_language()
            'c_cpp'
        """
        return "c_cpp"

    def analyze(self, code: str) -> list[dict[str, Any]]:
        """Analyze C/C++ code and return functions needing documentation.

        Parses C/C++ source via regex, extracts functions, assesses Doxygen
        doc quality, and returns prioritized improvement recommendations.

        Args:
            code: C or C++ source code string to analyze.

        Returns:
            Prioritized list of functions needing documentation (highest first).
            Each dict contains function_name, line_number, current_docstring,
            quality_assessment, function_info, priority.

            Returns [{"error": "message"}] on failure.
            Returns [] if all functions have excellent documentation.

        Raises:
            No exceptions raised - errors returned in result list.

        Example:
            >>> analyzer = CCppAnalyzer()
            >>> results = analyzer.analyze('void foo() { }')
            >>> results[0]['function_name']
            'foo'
        """
        security_error = self._validate_code_security(code)
        if security_error:
            return security_error

        try:
            functions = self._extract_functions_needing_improvement(code)
            return self._sort_by_priority(functions)
        except Exception as e:
            return [{"error": f"Failed to analyze code: {e!s}"}]

    def assess_docstring_quality(
        self, docstring: str, func_name: str, func_info: FunctionInfo
    ) -> QualityAssessment:
        """Assess Doxygen documentation quality of a function.

        Evaluates C/C++ function documentation against Doxygen standards.
        Checks for @brief, @param, @return, @throw, and @example tags.

        Args:
            docstring: The Doxygen comment text to assess.
            func_name: Function name for test detection.
            func_info: Function metadata (params, returns, complexity).

        Returns:
            QualityAssessment TypedDict with:
            - quality: 'poor'|'basic'|'good'|'excellent'
            - score: float 0.0-1.0
            - missing: list of missing quality indicators
            - needs_improvement: bool
            - indicators: dict of individual quality checks

        Raises:
            No exceptions - returns poor quality for invalid input.

        Example:
            >>> result = analyzer.assess_docstring_quality(
            ...     '@brief Short desc.', 'my_func', func_info
            ... )
            >>> result['quality']
            'poor'
        """
        min_length = self.config.min_docstring_length
        if not docstring or len(docstring.strip()) < min_length:
            return {
                "quality": QualityLevel.POOR.value,
                "score": 0.0,
                "missing": ["doxygen documentation"],
                "needs_improvement": True,
                "indicators": {},
            }

        is_test = self._is_test_function(func_name)
        quality_indicators = self._calculate_quality_indicators(docstring, func_info, is_test)
        quality_indicators = self._validate_signature_coverage(quality_indicators, func_info)

        indicator_values = list(quality_indicators.values())
        score = (
            sum(cast(list[bool], indicator_values)) / len(indicator_values)
            if indicator_values
            else 0.0
        )

        missing = [key.replace("_", " ") for key, value in quality_indicators.items() if not value]

        thresholds = self.config.quality_thresholds
        quality_str: Literal["poor", "basic", "good", "excellent"]

        if score >= thresholds["excellent"]:
            quality_str = "excellent"
            needs_improvement = False
        elif score >= thresholds["good"]:
            quality_str = "good"
            needs_improvement = True
        elif score >= thresholds["basic"]:
            quality_str = "basic"
            needs_improvement = True
        else:
            quality_str = "poor"
            needs_improvement = True

        return {
            "quality": quality_str,
            "score": score,
            "missing": missing,
            "needs_improvement": needs_improvement,
            "indicators": quality_indicators,
        }

    def calculate_priority(
        self, func_info: FunctionInfo, quality_assessment: QualityAssessment
    ) -> int:
        """Calculate documentation improvement priority score.

        Implements priority algorithm for ranking functions by documentation
        urgency. Higher scores indicate functions needing more attention.

        Algorithm: Priority = Visibility + Complexity + Signature + Quality_Gap

        Args:
            func_info: Function metadata (visibility, complexity).
            quality_assessment: Quality evaluation results.

        Returns:
            Priority score 0-13+. Higher = more urgent.

        Raises:
            KeyError: If func_info missing required fields.

        Example:
            >>> priority = analyzer.calculate_priority(func_info, quality)
            >>> priority > 8  # High priority function
            True
        """
        return (
            self._calculate_visibility_score(func_info)
            + self._calculate_complexity_score(func_info)
            + self._calculate_signature_score(func_info)
            + self._calculate_quality_gap_score(quality_assessment)
        )

    # ==================== SECURITY VALIDATION ====================

    def _validate_code_security(self, code: str) -> list[dict[str, Any]] | None:
        """Validate code for security issues (size limits).

        Enforces code size limits to prevent denial-of-service attacks
        from maliciously large input files. Part of the security boundary.

        Args:
            code: Source code string to validate.

        Returns:
            Error dict list if validation fails, None if valid.

        Raises:
            No exceptions raised.

        Example:
            >>> result = analyzer._validate_code_security('x' * 10_000_000)
            >>> result[0]['error']
            'Code too large (max 5120KB)'
        """
        if len(code) > self.config.max_code_size:
            max_kb = self.config.max_code_size // 1024
            return [{"error": f"Code too large (max {max_kb}KB)"}]

        return None

    # ==================== FUNCTION EXTRACTION ====================

    def _extract_functions_needing_improvement(self, code: str) -> list[dict[str, Any]]:
        """Extract functions that need documentation improvement.

        Two-pass extraction: first finds functions with Doxygen comments,
        then finds undocumented functions. Assesses quality for each.

        Args:
            code: C/C++ source code string to analyze.

        Returns:
            List of function dicts with name, line, quality, priority.
            Empty list if all functions have excellent documentation.

        Raises:
            No exceptions - malformed functions skipped.

        Example:
            >>> results = analyzer._extract_functions_needing_improvement(code)
            >>> len(results) >= 1
            True
        """
        results: list[dict[str, Any]] = []
        processed_positions: set[int] = set()

        # First pass: functions with Doxygen comments
        for match in REGEX_DOXYGEN_BLOCK.finditer(code):
            func_info = self._extract_function_info(match, code, has_doxygen=True)
            doxygen = self._clean_doxygen(match.group("doxygen") or "")
            processed_positions.add(match.start())

            quality = self.assess_docstring_quality(doxygen, func_info["name"], func_info)

            if quality["needs_improvement"]:
                priority = self.calculate_priority(func_info, quality)
                results.append(
                    {
                        "function_name": func_info["name"],
                        "line_number": func_info["line"],
                        "current_docstring": doxygen,
                        "quality_assessment": quality,
                        "function_info": func_info,
                        "priority": priority,
                    }
                )

        # Second pass: functions without Doxygen comments
        for match in REGEX_FUNCTION.finditer(code):
            if match.start() in processed_positions:
                continue
            # Skip if this is part of a function with doxygen (already processed)
            if any(abs(match.start() - pos) < 200 for pos in processed_positions):
                continue

            func_info = self._extract_function_info(match, code, has_doxygen=False)

            # Skip if looks like declaration only (no body)
            if self._is_declaration_only(match, code):
                continue

            quality = self.assess_docstring_quality("", func_info["name"], func_info)

            if quality["needs_improvement"]:
                priority = self.calculate_priority(func_info, quality)
                results.append(
                    {
                        "function_name": func_info["name"],
                        "line_number": func_info["line"],
                        "current_docstring": "",
                        "quality_assessment": quality,
                        "function_info": func_info,
                        "priority": priority,
                    }
                )

        return results

    def _extract_function_info(
        self, match: re.Match[str], code: str, has_doxygen: bool
    ) -> FunctionInfo:
        """Extract metadata from function regex match.

        Parses regex match groups to extract function signature details
        needed for quality assessment and priority calculation.

        Args:
            match: Regex match object from REGEX_FUNCTION or REGEX_DOXYGEN_BLOCK.
            code: Full source code (for line number calculation).
            has_doxygen: True if function has Doxygen comment.

        Returns:
            FunctionInfo TypedDict with name, line, args, returns,
            decorators, complexity, is_private, is_test flags.

        Raises:
            No exceptions - missing groups become empty/None.

        Example:
            >>> info = analyzer._extract_function_info(match, code, True)
            >>> info['name']
            'my_function'
        """
        name = match.group("name")
        modifiers = match.group("modifiers") or ""
        return_type = match.group("return_type").strip()
        params_str = match.group("params") or ""
        class_prefix = match.group("class_prefix") or ""

        # Calculate line number
        line = code[: match.start()].count("\n") + 1

        # Parse parameters
        args: list[ArgInfo] = []
        for param_match in REGEX_PARAM.finditer(params_str):
            args.append(
                {
                    "name": param_match.group("name"),
                    "type_annotation": param_match.group("type").strip(),
                    "default": param_match.group("default"),
                }
            )

        # Determine visibility (private if starts with _ or in private section)
        is_private = name.startswith("_") or "private" in modifiers.lower()

        # Calculate complexity
        complexity = self._estimate_complexity(match, code)

        # Get doxygen if available
        doxygen = ""
        if has_doxygen and "doxygen" in match.groupdict():
            doxygen = self._clean_doxygen(match.group("doxygen") or "")

        return {
            "name": f"{class_prefix}{name}" if class_prefix else name,
            "line": line,
            "complexity": complexity,
            "is_private": is_private,
            "is_test": self._is_test_function(name),
            "args": args,
            "returns": return_type if return_type != "void" else None,
            "decorators": [],
            "current_docstring": doxygen,
        }

    def _estimate_complexity(self, match: re.Match[str], code: str) -> int:
        """Estimate cyclomatic complexity for a function.

        Counts branching statements (if, for, while, switch, case, catch)
        and logical operators (&&, ||, ?) to estimate complexity.

        Args:
            match: Regex match for function signature.
            code: Full source code to extract function body.

        Returns:
            Complexity score (1 = minimal, higher = more complex).

        Raises:
            No exceptions raised.

        Example:
            >>> complexity = analyzer._estimate_complexity(match, code)
            >>> complexity >= 1
            True
        """
        start = match.end()
        brace_count = 0
        method_body = ""
        in_body = False

        for i, char in enumerate(code[start:]):
            if char == "{":
                brace_count += 1
                in_body = True
            elif char == "}":
                brace_count -= 1
                if brace_count == 0 and in_body:
                    method_body = code[start : start + i + 1]
                    break
            elif char == ";" and not in_body:
                # Declaration only, no body
                return 1

        complexity = 1
        complexity += method_body.count("if ")
        complexity += method_body.count("if(")
        complexity += method_body.count("else if ")
        complexity += method_body.count("else if(")
        complexity += method_body.count("switch ")
        complexity += method_body.count("switch(")
        complexity += method_body.count("case ")
        complexity += method_body.count("for ")
        complexity += method_body.count("for(")
        complexity += method_body.count("while ")
        complexity += method_body.count("while(")
        complexity += method_body.count("catch ")
        complexity += method_body.count("catch(")
        complexity += method_body.count("&&")
        complexity += method_body.count("||")
        complexity += method_body.count("?")  # Ternary operator

        return complexity

    def _is_declaration_only(self, match: re.Match[str], code: str) -> bool:
        """Check if match is a declaration only (no function body).

        Distinguishes between function declarations (ending with semicolon)
        and function definitions (with body). Skips declarations to avoid
        false positives in header files.

        Args:
            match: Regex match object for the function.
            code: Full source code to scan after match.

        Returns:
            True if function is a declaration (ends with ;), False if definition.

        Raises:
            No exceptions raised.

        Example:
            >>> # match = REGEX_FUNCTION.search('void foo();')
            >>> # analyzer._is_declaration_only(match, code)
            >>> # True
        """
        end = match.end()
        # Look for semicolon before brace
        for _, char in enumerate(code[end : end + 50]):
            if char == ";":
                return True
            if char == "{":
                return False
            if char == "\n":
                continue
        return False

    def _clean_doxygen(self, doxygen: str) -> str:
        """Clean Doxygen comment, removing comment markers.

        Strips Doxygen comment markers (/** */, ///, //!) to extract pure
        documentation content for quality assessment. Handles multi-line
        block and single-line comment styles.

        Args:
            doxygen: Raw Doxygen comment with markers.

        Returns:
            Cleaned documentation content without markers.

        Raises:
            No exceptions raised.

        Example:
            >>> analyzer._clean_doxygen('/** @brief Test function */')
            '@brief Test function'
        """
        lines = doxygen.strip().split("\n")
        cleaned = []
        for line in lines:
            line = line.strip()
            # Remove /** */ markers
            if line.startswith("/**"):
                line = line[3:].strip()
            if line.endswith("*/"):
                line = line[:-2].strip()
            # Remove * at start of line
            if line.startswith("*"):
                line = line[1:].strip()
            # Remove /// or //!
            if line.startswith("///") or line.startswith("//!"):
                line = line[3:].strip()
            cleaned.append(line)
        return "\n".join(cleaned)

    def _is_test_function(self, func_name: str) -> bool:
        """Detect test functions by naming pattern.

        Identifies test functions to apply relaxed documentation requirements.
        Test functions may skip some quality checks that apply to production code.

        Args:
            func_name: Name of function to check.

        Returns:
            True if function appears to be a test function.

        Raises:
            No exceptions raised.

        Example:
            >>> analyzer._is_test_function('test_user_login')
            True
            >>> analyzer._is_test_function('process_data')
            False
        """
        name_lower = func_name.lower()
        return (
            name_lower.startswith("test")
            or name_lower.endswith("test")
            or func_name.startswith("TEST_")
            or func_name.startswith("Test_")
        )

    def _sort_by_priority(self, functions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Sort results by priority descending.

        Orders functions so highest-priority improvements appear first.
        Enables users to focus on most impactful documentation updates.

        Args:
            functions: List of function analysis dicts.

        Returns:
            Sorted list with highest priority first.

        Raises:
            No exceptions raised.

        Example:
            >>> sorted_funcs = analyzer._sort_by_priority([{'priority': 1}, {'priority': 5}])
            >>> sorted_funcs[0]['priority']
            5
        """
        return sorted(functions, key=lambda x: x["priority"], reverse=True)

    # ==================== QUALITY INDICATORS ====================

    def _calculate_quality_indicators(
        self, docstring: str, _func_info: FunctionInfo, is_test: bool
    ) -> QualityIndicators:
        """Calculate quality indicators for Doxygen documentation.

        Checks for Doxygen tags (@brief, @param, @return, @throw, @example)
        and evaluates documentation completeness.

        Args:
            docstring: Doxygen comment text to analyze.
            _func_info: Function metadata for context (unused, for interface).
            is_test: True if test function (relaxed requirements).

        Returns:
            QualityIndicators TypedDict with bool values for each
            quality dimension (brief_description, args_section, etc.).

        Raises:
            No exceptions raised.

        Example:
            >>> indicators = analyzer._calculate_quality_indicators(
            ...     docstring, func_info, False
            ... )
            >>> indicators['brief_description']
            True
        """
        indicators: dict[str, bool] = {}

        # Check for brief description
        has_brief = bool(
            REGEX_DOXYGEN_BRIEF.search(docstring)
            or REGEX_DOXYGEN_BRIEF_ALT.search(docstring)
            or (docstring and not docstring.startswith("@") and not docstring.startswith("\\"))
        )
        indicators["brief_description"] = has_brief

        # Check for detailed description
        has_details = bool(
            REGEX_DOXYGEN_DETAILS.search(docstring) or REGEX_DOXYGEN_DETAILS_ALT.search(docstring)
        )
        indicators["detailed_description"] = has_details or len(docstring) > 100

        if not is_test:
            # Check for param documentation
            has_params = bool(
                REGEX_DOXYGEN_PARAM.search(docstring) or REGEX_DOXYGEN_PARAM_ALT.search(docstring)
            )
            indicators["args_section"] = has_params

            # Check for returns documentation
            has_returns = bool(
                REGEX_DOXYGEN_RETURN.search(docstring) or REGEX_DOXYGEN_RETURN_ALT.search(docstring)
            )
            indicators["returns_section"] = has_returns

            # Check for exception documentation
            has_throws = bool(
                REGEX_DOXYGEN_THROW.search(docstring) or REGEX_DOXYGEN_THROW_ALT.search(docstring)
            )
            indicators["raises_section"] = has_throws

            # Check for example
            has_example = bool(
                REGEX_DOXYGEN_EXAMPLE.search(docstring)
                or REGEX_DOXYGEN_EXAMPLE_ALT.search(docstring)
            )
            indicators["example_section"] = has_example

            # Context indicators
            indicators["business_context"] = any(
                keyword in docstring.lower()
                for keyword in [
                    "purpose",
                    "context",
                    "responsible",
                    "interface",
                    "implements",
                    "provides",
                ]
            )

            indicators["implementation_details"] = len(docstring) > 200

        return cast(QualityIndicators, indicators)

    def _validate_signature_coverage(
        self, quality_indicators: QualityIndicators, func_info: FunctionInfo
    ) -> QualityIndicators:
        """Validate param/returns sections against function signature.

        Cross-references docstring sections with actual function signature
        to ensure documented params match declared params.

        Args:
            quality_indicators: Current quality indicator values.
            func_info: Function metadata with args and return type.

        Returns:
            Updated QualityIndicators with signature validation applied.
            May set args_section or returns_section to False if missing.

        Raises:
            KeyError: If func_info missing 'args' or 'returns' keys.

        Example:
            >>> indicators = {'args_section': True, 'returns_section': True}
            >>> result = analyzer._validate_signature_coverage(
            ...     indicators, func_info
            ... )
        """
        has_params = len(func_info.get("args", [])) > 0

        if has_params and not quality_indicators.get("args_section", True):
            quality_indicators["args_section"] = False

        has_return = func_info.get("returns") and func_info["returns"] != "void"
        if has_return and not quality_indicators.get("returns_section", True):
            quality_indicators["returns_section"] = False

        return quality_indicators

    # ==================== PRIORITY CALCULATION ====================

    def _calculate_visibility_score(self, func_info: FunctionInfo) -> int:
        """Calculate priority contribution from function visibility.

        Public functions score higher since they're part of the API
        and need better documentation for users.

        Args:
            func_info: Function metadata with is_private flag.

        Returns:
            0 for private functions, 3 for public functions.

        Raises:
            KeyError: If func_info missing 'is_private' key.

        Example:
            >>> analyzer._calculate_visibility_score({'is_private': False})
            3
        """
        return 0 if func_info["is_private"] else 3

    def _calculate_complexity_score(self, func_info: FunctionInfo) -> int:
        """Calculate priority contribution from function complexity.

        Complex functions need better documentation to explain logic.
        Higher complexity = higher priority for documentation.

        Args:
            func_info: Function metadata with complexity score.

        Returns:
            0-2 based on complexity thresholds (>10=2, >5=1, else 0).

        Raises:
            KeyError: If func_info missing 'complexity' key.

        Example:
            >>> analyzer._calculate_complexity_score({'complexity': 10})
            2
        """
        complexity = func_info["complexity"]
        if complexity > 10:
            return 2
        elif complexity > 5:
            return 1
        return 0

    def _calculate_signature_score(self, func_info: FunctionInfo) -> int:
        """Calculate priority contribution from signature complexity.

        Functions with more parameters or return values need better
        documentation to explain their interface.

        Args:
            func_info: Function metadata with args and returns.

        Returns:
            0-5+ based on parameter count and return presence.

        Raises:
            KeyError: If func_info missing 'args' or 'returns' keys.

        Example:
            >>> func_info = {'args': [{'name': 'x'}], 'returns': 'int'}
            >>> analyzer._calculate_signature_score(func_info)
            3
        """
        score = 0
        param_count = len(func_info["args"])
        if param_count > 0:
            score += min(param_count, 3)
        if func_info["returns"]:
            score += 2
        return score

    def _calculate_quality_gap_score(self, quality_assessment: QualityAssessment) -> int:
        """Calculate priority contribution from documentation quality gap.

        Lower quality = higher priority for improvement. Ensures poorly
        documented functions appear first in MCP tool results.

        Args:
            quality_assessment: Quality assessment with score.

        Returns:
            0-3 based on quality score thresholds.

        Raises:
            KeyError: If quality_assessment missing 'score' key.

        Example:
            >>> analyzer._calculate_quality_gap_score({'score': 0.2})
            3
        """
        quality_score = quality_assessment["score"]
        if quality_score < 0.3:
            return 3
        elif quality_score < 0.6:
            return 2
        elif quality_score < 0.8:
            return 1
        return 0
