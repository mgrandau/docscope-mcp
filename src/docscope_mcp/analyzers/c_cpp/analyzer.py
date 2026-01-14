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
from dataclasses import dataclass, field
from typing import Any, cast

from docscope_mcp.analyzers.priority import PriorityCalculationMixin
from docscope_mcp.analyzers.quality import QualityAssessmentMixin
from docscope_mcp.models import (
    DEFAULT_CONFIG,
    AnalysisConfig,
    ArgInfo,
    FunctionInfo,
    QualityAssessment,
    QualityIndicators,
)


@dataclass(frozen=True)
class CppParsingPatterns:
    """Pre-compiled regex patterns for C/C++ function parsing.

    Groups patterns for function/method discovery in C/C++ source code.
    All patterns are pre-compiled at module load for performance.

    Attributes:
        doxygen_block: Matches function with preceding Doxygen comment.
        function: Matches function signature without documentation.
        class_decl: Matches class/struct declarations.
        param: Matches function parameter declarations.
    """

    doxygen_block: re.Pattern[str] = field(
        default_factory=lambda: re.compile(
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
    )
    function: re.Pattern[str] = field(
        default_factory=lambda: re.compile(
            r"(?P<template>template\s*<[^>]*>\s*)?"
            r"(?P<modifiers>(?:(?:static|virtual|inline|constexpr|explicit|friend|extern)\s+)*)"
            r"(?P<return_type>(?:const\s+)?[\w:<>&*]+(?:\s*[*&]+)?)\s+"
            r"(?P<class_prefix>(?:\w+::)*)"
            r"(?P<name>~?\w+)\s*"
            r"\((?P<params>[^)]*)\)"
            r"(?P<qualifiers>(?:\s*(?:const|override|final|noexcept|=\s*0|=\s*default|=\s*delete))*)",
            re.MULTILINE,
        )
    )
    class_decl: re.Pattern[str] = field(
        default_factory=lambda: re.compile(
            r"(?P<doxygen>(?:/\*\*[\s\S]*?\*/|(?:\s*(?:///|//!).*\n)+))?\s*"
            r"(?:class|struct)\s+(?P<name>\w+)",
            re.MULTILINE,
        )
    )
    param: re.Pattern[str] = field(
        default_factory=lambda: re.compile(
            r"(?P<type>(?:const\s+)?[\w:<>&*\s]+(?:\s*[*&]+)?)\s+"
            r"(?P<name>\w+)"
            r"(?:\s*=\s*(?P<default>[^,)]+))?"
        )
    )


@dataclass(frozen=True)
class DoxygenTagPatterns:
    """Pre-compiled regex patterns for Doxygen tag parsing.

    Groups patterns for extracting documentation from Doxygen comments.
    Supports both @ and \\ command prefixes per Doxygen spec.

    Attributes:
        brief: @brief tag pattern.
        brief_alt: \\brief tag pattern.
        param: @param tag pattern with optional [in/out] direction.
        param_alt: \\param tag pattern.
        returns: @return/@returns tag pattern.
        returns_alt: \\return/\\returns tag pattern.
        throws: @throw/@throws/@exception tag pattern.
        throws_alt: \\throw/\\throws/\\exception tag pattern.
        example: @example/@code tag pattern.
        example_alt: \\example/\\code tag pattern.
        details: @details tag pattern.
        details_alt: \\details tag pattern.
    """

    brief: re.Pattern[str] = field(
        default_factory=lambda: re.compile(r"@brief\s+(.+?)(?=@|\*/|$)", re.DOTALL)
    )
    brief_alt: re.Pattern[str] = field(
        default_factory=lambda: re.compile(r"\\brief\s+(.+?)(?=\\|@|\*/|$)", re.DOTALL)
    )
    param: re.Pattern[str] = field(
        default_factory=lambda: re.compile(
            r"@param(?:\[(?:in|out|in,out)\])?\s+(\w+)\s+(.+?)(?=@param|@return|@throw|@|\\|\*/|$)",
            re.DOTALL,
        )
    )
    param_alt: re.Pattern[str] = field(
        default_factory=lambda: re.compile(
            r"\\param(?:\[(?:in|out|in,out)\])?\s+(\w+)\s+(.+?)(?=\\param|\\return|\\throw|\\|@|\*/|$)",
            re.DOTALL,
        )
    )
    returns: re.Pattern[str] = field(
        default_factory=lambda: re.compile(r"@returns?\s+(.+?)(?=@|\*/|$)", re.DOTALL)
    )
    returns_alt: re.Pattern[str] = field(
        default_factory=lambda: re.compile(r"\\returns?\s+(.+?)(?=\\|@|\*/|$)", re.DOTALL)
    )
    throws: re.Pattern[str] = field(
        default_factory=lambda: re.compile(
            r"@(?:throw|throws|exception)\s+(.+?)(?=@|\*/|$)", re.DOTALL
        )
    )
    throws_alt: re.Pattern[str] = field(
        default_factory=lambda: re.compile(
            r"\\(?:throw|throws|exception)\s+(.+?)(?=\\|@|\*/|$)", re.DOTALL
        )
    )
    example: re.Pattern[str] = field(
        default_factory=lambda: re.compile(r"@(?:example|code)(.+?)(?:@endcode|@|\*/|$)", re.DOTALL)
    )
    example_alt: re.Pattern[str] = field(
        default_factory=lambda: re.compile(
            r"\\(?:example|code)(.+?)(?:\\endcode|\\|@|\*/|$)", re.DOTALL
        )
    )
    details: re.Pattern[str] = field(
        default_factory=lambda: re.compile(r"@details\s+(.+?)(?=@|\*/|$)", re.DOTALL)
    )
    details_alt: re.Pattern[str] = field(
        default_factory=lambda: re.compile(r"\\details\s+(.+?)(?=\\|@|\*/|$)", re.DOTALL)
    )


# Module-level pattern instances (compiled once at import)
CPP_PATTERNS = CppParsingPatterns()
DOXYGEN_PATTERNS = DoxygenTagPatterns()


class CCppAnalyzer(QualityAssessmentMixin, PriorityCalculationMixin):
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
            return cast(
                QualityAssessment, self._build_empty_quality_assessment("doxygen documentation")
            )

        is_test = self._is_test_function_common(func_name)
        quality_indicators = self._calculate_quality_indicators(docstring, func_info, is_test)
        quality_indicators = self._validate_signature_coverage(quality_indicators, func_info)

        score = self._calculate_indicator_score(quality_indicators)
        missing = self._identify_missing_elements(quality_indicators)
        quality_str, needs_improvement = self._determine_quality_level(score)

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
        for match in CPP_PATTERNS.doxygen_block.finditer(code):
            func_info = self._extract_function_info(match, code, has_doxygen=True)
            doxygen = self._clean_doxygen(match.group("doxygen") or "")
            processed_positions.add(match.start())

            quality = self.assess_docstring_quality(doxygen, func_info["name"], func_info)

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
        for match in CPP_PATTERNS.function.finditer(code):
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
        for param_match in CPP_PATTERNS.param.finditer(params_str):
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
            "is_test": self._is_test_function_common(name),
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
            >>> code = 'void foo();'
            >>> match = REGEX_FUNCTION.search(code)
            >>> analyzer._is_declaration_only(match, code)
            True
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
        dp = DOXYGEN_PATTERNS  # Local alias for readability

        # Check for brief description
        has_brief = bool(
            dp.brief.search(docstring)
            or dp.brief_alt.search(docstring)
            or (docstring and not docstring.startswith("@") and not docstring.startswith("\\"))
        )
        indicators["brief_description"] = has_brief

        # Check for detailed description
        has_details = bool(dp.details.search(docstring) or dp.details_alt.search(docstring))
        indicators["detailed_description"] = (
            has_details or len(docstring) > self.config.thresholds.min_detailed_chars_brief
        )

        if not is_test:
            # Check for param documentation
            has_params = bool(dp.param.search(docstring) or dp.param_alt.search(docstring))
            indicators["args_section"] = has_params

            # Check for returns documentation
            has_returns = bool(dp.returns.search(docstring) or dp.returns_alt.search(docstring))
            indicators["returns_section"] = has_returns

            # Check for exception documentation
            has_throws = bool(dp.throws.search(docstring) or dp.throws_alt.search(docstring))
            indicators["raises_section"] = has_throws

            # Check for example
            has_example = bool(dp.example.search(docstring) or dp.example_alt.search(docstring))
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
                    "role",
                    "impact",
                    "business",
                    "workflow",
                    "accuracy",
                    "why",
                    "when to use",
                    "depends on",
                    "affects",
                ]
            )

            indicators["implementation_details"] = (
                len(docstring) > self.config.thresholds.min_detailed_chars_standard
            )

        return cast(QualityIndicators, indicators)
