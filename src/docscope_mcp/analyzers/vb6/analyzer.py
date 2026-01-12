"""
Visual Basic 6 Documentation Analyzer.

Regex-based analyzer for VB6 documentation quality.
Implements multi-criteria assessment with priority calculation.

Architecture:
    - Regex parsing for Sub/Function/Property discovery
    - Traditional comment block assessment (no XML)
    - Priority calculation via factor-based scoring
    - Security protections against DoS attacks

VB6 Specifics:
    - Comments use single quote (') only
    - No XML documentation support
    - Modifiers: Public, Private, Static, Friend
    - No generics, nullable types, or async
"""

import logging
import re
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

# Pre-compiled regex patterns for VB6 parsing
# Captures comment block immediately before Sub/Function
REGEX_COMMENT_BLOCK = re.compile(
    r"(?P<comments>(?:^\s*'.*\n)+)"  # One or more comment lines
    r"\s*"
    r"(?P<modifiers>(?:Public|Private|Friend|Static)\s+)*"
    r"(?:Sub|Function|Property\s+(?:Get|Let|Set))\s+"
    r"(?P<name>\w+)",
    re.MULTILINE,
)

REGEX_FUNCTION = re.compile(
    r"(?P<modifiers>(?:Public|Private|Friend|Static)\s+)*"
    r"(?P<type>Sub|Function|Property\s+(?:Get|Let|Set))\s+"
    r"(?P<name>\w+)\s*"
    r"\((?P<params>[^)]*)\)"
    r"(?:\s+As\s+(?P<return_type>\w+))?",
    re.MULTILINE,
)

REGEX_PARAM = re.compile(
    r"(?:ByVal|ByRef|Optional|ParamArray)?\s*"
    r"(?P<name>\w+)"
    r"(?:\s+As\s+(?P<type>\w+))?"
    r"(?:\s*=\s*(?P<default>[^,)]+))?",
    re.IGNORECASE,
)

# Quality patterns for VB6 comments
REGEX_PURPOSE_KEYWORDS = re.compile(
    r"purpose|description|summary|overview|this (?:sub|function|procedure)",
    re.IGNORECASE,
)
REGEX_PARAM_DOC = re.compile(r"param(?:eter)?s?[:\s]|arguments?[:\s]", re.IGNORECASE)
REGEX_RETURN_DOC = re.compile(r"returns?[:\s]|result[:\s]", re.IGNORECASE)
REGEX_AUTHOR_DOC = re.compile(r"author[:\s]|written by|created by", re.IGNORECASE)
REGEX_DATE_DOC = re.compile(r"date[:\s]|created[:\s]|modified[:\s]", re.IGNORECASE)
REGEX_EXAMPLE_DOC = re.compile(r"example[:\s]|usage[:\s]|sample[:\s]", re.IGNORECASE)
# Raises/error documentation patterns
REGEX_RAISES_KEYWORDS = re.compile(
    r"raises?[:\s]|errors?[:\s]|exceptions?[:\s]|throws?[:\s]|"
    r"error handling|prerequisites|preconditions|bounds|overflow|underflow",
    re.IGNORECASE,
)
# Business context documentation patterns
REGEX_BUSINESS_CONTEXT = re.compile(
    r"business[:\s]?context|role[:\s]|impact[:\s]|purpose[:\s]|why[:\s]|"
    r"when to use|accuracy|workflow|integration|depends on|affects?",
    re.IGNORECASE,
)


class VB6Analyzer(QualityAssessmentMixin, PriorityCalculationMixin):
    """VB6 documentation quality analyzer using regex-based parsing.

    Analyzes Visual Basic 6 source code to identify procedures needing
    documentation improvement. Uses multi-criteria assessment including:
    - Traditional comment block analysis
    - Content quality (presence of key information)
    - Context awareness (test vs production code)

    VB6 uses simple ' comments rather than XML documentation.
    Quality is assessed based on:
    - Presence of purpose/description
    - Parameter documentation
    - Return value documentation
    - Author/date metadata

    Attributes:
        config: Analysis configuration
        logger: Logger instance for diagnostics

    Examples:
        ```python
        analyzer = VB6Analyzer()
        results = analyzer.analyze("Public Sub Foo()\nEnd Sub", "example.bas")
        for result in results:
            print(f"{result['function_name']}: {result['priority']}")
        ```
    """

    def __init__(
        self,
        config: AnalysisConfig | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize VB6 analyzer with configuration.

        Creates a new VB6Analyzer instance with optional custom configuration
        and logging. The analyzer uses regex-based parsing to extract VB6
        procedures and assess comment block quality.

        Args:
            config: Analysis configuration. Defaults to DEFAULT_CONFIG.
            logger: Logger instance. Defaults to module logger.

        Returns:
            None - initializes instance attributes.

        Raises:
            No exceptions raised.

        Example:
            >>> analyzer = VB6Analyzer()
            >>> analyzer.get_language()
            'vb6'
        """
        self.config = config or DEFAULT_CONFIG
        self.logger = logger or logging.getLogger(__name__)

    def get_language(self) -> str:
        """Return the programming language identifier for this analyzer.

        Provides language identification for multi-language analyzer routing.
        MCP tools use this to select the appropriate analyzer based on file
        extension or user specification.

        Returns:
            String 'vb6' identifying this as the VB6 analyzer.

        Raises:
            No exceptions raised.

        Example:
            >>> analyzer = VB6Analyzer()
            >>> analyzer.get_language()
            'vb6'
        """
        return "vb6"

    def analyze(self, code: str) -> list[dict[str, Any]]:
        """Analyze VB6 code and return procedures needing documentation.

        Parses VB6 source via regex, extracts Subs/Functions, assesses
        comment quality, and returns prioritized improvement recommendations.

        Args:
            code: VB6 source code string to analyze.

        Returns:
            Prioritized list of procedures needing documentation (highest first).
            Returns [{"error": "message"}] on failure.
            Returns [] if all procedures have excellent documentation.

        Raises:
            No exceptions raised - errors returned in result list.

        Example:
            >>> analyzer = VB6Analyzer()
            >>> results = analyzer.analyze('Public Sub Foo()\nEnd Sub')
            >>> results[0]['function_name']
            'Foo'
        """
        security_error = self._validate_code_security(code)
        if security_error:
            return security_error

        try:
            functions = self._extract_procedures_needing_improvement(code)
            return self._sort_by_priority(functions)
        except Exception as e:
            return [{"error": f"Failed to analyze code: {e!s}"}]

    def assess_docstring_quality(
        self, docstring: str, func_name: str, func_info: FunctionInfo
    ) -> QualityAssessment:
        """Assess comment block quality of a Sub/Function.

        VB6 doesn't have structured documentation, so we assess:
        - Presence of any comments
        - Purpose/description keywords
        - Parameter documentation
        - Return value documentation
        - Metadata (author, date)

        Args:
            docstring: The comment block text to assess.
            func_name: Procedure name for context.
            func_info: Procedure metadata (params, returns, complexity).

        Returns:
            QualityAssessment with quality level, score, missing elements.

        Raises:
            No exceptions - returns poor quality for invalid input.

        Example:
            >>> result = analyzer.assess_docstring_quality(
            ...     "' Purpose: Do something", 'MySub', func_info
            ... )
            >>> result['quality']
            'poor'
        """
        # No comments at all
        min_length = self.config.min_docstring_length
        if not docstring or len(docstring.strip()) < min_length:
            return cast(QualityAssessment, self._build_empty_quality_assessment("comments"))

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

        Implements priority algorithm for ranking procedures by documentation
        urgency. Higher scores indicate procedures needing more attention.

        Args:
            func_info: Procedure metadata (visibility, complexity).
            quality_assessment: Quality evaluation results.

        Returns:
            Priority score 0-13+. Higher = more urgent.

        Raises:
            KeyError: If func_info missing required fields.

        Example:
            >>> priority = analyzer.calculate_priority(func_info, quality)
            >>> priority > 8  # High priority procedure
            True
        """
        return (
            self._calculate_visibility_score(func_info)
            + self._calculate_complexity_score(func_info)
            + self._calculate_signature_score(func_info)
            + self._calculate_quality_gap_score(quality_assessment)
        )

    # ==================== PROCEDURE EXTRACTION ====================

    def _extract_procedures_needing_improvement(self, code: str) -> list[dict[str, Any]]:
        """Extract Subs/Functions that need documentation improvement.

        Scans VB6 code in two passes: first for procedures with comment
        blocks, then for undocumented procedures. Filters for improvable ones.

        Args:
            code: VB6 source code to analyze.

        Returns:
            List of procedure dicts with quality assessments and priorities.

        Raises:
            No exceptions raised.

        Example:
            >>> procs = analyzer._extract_procedures_needing_improvement(
            ...     'Public Sub Foo()\nEnd Sub'
            ... )
            >>> len(procs) >= 0
            True
        """
        results: list[dict[str, Any]] = []
        documented_procs: set[str] = set()

        # First pass: procedures with comment blocks
        for match in REGEX_COMMENT_BLOCK.finditer(code):
            name = match.group("name")
            documented_procs.add(name.lower())

            func_info = self._extract_procedure_info_from_comment_match(match, code)
            comments = self._clean_comments(match.group("comments") or "")

            quality = self.assess_docstring_quality(comments, func_info["name"], func_info)

            priority = self.calculate_priority(func_info, quality)
            results.append(
                {
                    "function_name": func_info["name"],
                    "line_number": func_info["line"],
                    "current_docstring": comments,
                    "quality_assessment": quality,
                    "function_info": func_info,
                    "priority": priority,
                }
            )

        # Second pass: procedures without comment blocks
        for match in REGEX_FUNCTION.finditer(code):
            name = match.group("name")
            if name.lower() in documented_procs:
                continue

            func_info = self._extract_procedure_info(match, code)
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

    def _extract_procedure_info_from_comment_match(
        self, match: re.Match[str], code: str
    ) -> FunctionInfo:
        """Extract metadata from a comment block match.

        Parses regex match groups to build FunctionInfo dict. Locates the
        associated function definition to extract parameters and return type.

        Args:
            match: Regex match from REGEX_COMMENT_BLOCK.
            code: Full source code for line number calculation.

        Returns:
            FunctionInfo with name, line, args, returns, complexity.

        Raises:
            No exceptions raised.

        Example:
            >>> code = "' Purpose: Test\nPublic Sub MyProc()\nEnd Sub"
            >>> match = REGEX_COMMENT_BLOCK.search(code)
            >>> info = analyzer._extract_procedure_info_from_comment_match(match, code)
            >>> info['name']
            'MyProc'
        """
        name = match.group("name")
        modifiers = match.group("modifiers") or ""

        # Calculate line number
        line = code[: match.start()].count("\n") + 1

        # Find the full function definition to get params
        func_match = REGEX_FUNCTION.search(code, match.start())
        args: list[ArgInfo] = []
        return_type = None

        if func_match and func_match.group("name") == name:
            params_str = func_match.group("params") or ""
            for param_match in REGEX_PARAM.finditer(params_str):
                if param_match.group("name"):
                    args.append(
                        {
                            "name": param_match.group("name"),
                            "type_annotation": param_match.group("type"),
                            "default": param_match.group("default"),
                        }
                    )
            return_type = func_match.group("return_type")

        is_private = "private" in modifiers.lower()
        complexity = self._estimate_complexity_by_name(name, code)

        return {
            "name": name,
            "line": line,
            "complexity": complexity,
            "is_private": is_private,
            "is_test": self._is_test_function_common(name),
            "args": args,
            "returns": return_type,
            "decorators": [],
            "current_docstring": self._clean_comments(match.group("comments") or ""),
        }

    def _extract_procedure_info(self, match: re.Match[str], code: str) -> FunctionInfo:
        """Extract metadata from Sub/Function regex match.

        Parses regex match groups for undocumented procedures. Extracts
        signature details including modifiers, parameters, and return type.

        Args:
            match: Regex match from REGEX_FUNCTION.
            code: Full source code for line number calculation.

        Returns:
            FunctionInfo with name, line, args, returns, complexity.

        Raises:
            No exceptions raised.

        Example:
            >>> code = 'Public Sub Test()\nEnd Sub'
            >>> match = REGEX_FUNCTION.search(code)
            >>> info = analyzer._extract_procedure_info(match, code)
            >>> info['name']
            'Test'
        """
        name = match.group("name")
        modifiers = match.group("modifiers") or ""
        proc_type = match.group("type")
        return_type = match.group("return_type")
        params_str = match.group("params") or ""

        # Calculate line number
        line = code[: match.start()].count("\n") + 1

        # Parse parameters
        args: list[ArgInfo] = []
        for param_match in REGEX_PARAM.finditer(params_str):
            if param_match.group("name"):
                args.append(
                    {
                        "name": param_match.group("name"),
                        "type_annotation": param_match.group("type"),
                        "default": param_match.group("default"),
                    }
                )

        is_private = "private" in modifiers.lower()

        # Functions return values, Subs don't
        if "sub" in proc_type.lower():
            return_type = None

        complexity = self._estimate_complexity_by_name(name, code)

        return {
            "name": name,
            "line": line,
            "complexity": complexity,
            "is_private": is_private,
            "is_test": self._is_test_function_common(name),
            "args": args,
            "returns": return_type,
            "decorators": [],
            "current_docstring": "",
        }

    def _estimate_complexity_by_name(self, proc_name: str, code: str) -> int:
        """Estimate cyclomatic complexity for a procedure by finding its body.

        Searches code for the procedure definition and counts control flow
        statements. Higher complexity indicates more documentation need.

        Args:
            proc_name: Name of procedure to analyze.
            code: Full source code to search for procedure body.

        Returns:
            Complexity score (1 = minimal, higher = more complex).

        Raises:
            No exceptions raised.

        Example:
            >>> complexity = analyzer._estimate_complexity_by_name('MyProc', code)
            >>> complexity >= 1
            True
        """
        # Find the procedure
        pattern = re.compile(
            rf"\b(?:Sub|Function|Property\s+(?:Get|Let|Set))\s+{re.escape(proc_name)}\b.*?"
            rf"End\s+(?:Sub|Function|Property)",
            re.IGNORECASE | re.DOTALL,
        )
        match = pattern.search(code)
        if not match:
            return 1

        body = match.group(0).lower()
        complexity = 1
        complexity += body.count("if ")
        complexity += body.count("elseif ")
        complexity += body.count("select case")
        complexity += body.count("case ")
        complexity += body.count("for ")
        complexity += body.count("for each ")
        complexity += body.count("do ")
        complexity += body.count("while ")
        complexity += body.count(" and ")
        complexity += body.count(" or ")

        return complexity

    def _clean_comments(self, comments: str) -> str:
        """Clean comment block, removing ' prefixes.

        Strips VB6 comment markers to extract pure text content
        for quality assessment. Handles multi-line comment blocks.

        Args:
            comments: Raw comment block with ' prefixes.

        Returns:
            Cleaned comment content without markers.

        Raises:
            No exceptions raised.

        Example:
            >>> analyzer._clean_comments("' Purpose: Test procedure")
            'Purpose: Test procedure'
        """
        lines = comments.strip().split("\n")
        cleaned = []
        for line in lines:
            line = line.strip()
            if line.startswith("'"):
                line = line[1:].strip()
            cleaned.append(line)
        return "\n".join(cleaned)

    # ==================== QUALITY INDICATORS ====================

    def _calculate_quality_indicators(
        self, docstring: str, _func_info: FunctionInfo, is_test: bool
    ) -> QualityIndicators:
        """Calculate quality indicators for VB6 comment blocks.

        VB6 doesn't have structured docs, so we look for:
        - Any descriptive content (brief_description)
        - Detailed explanation (detailed_description)
        - Parameter mentions (args_section)
        - Return value mentions (returns_section)
        - Metadata like author/date

        Args:
            docstring: Comment block text to analyze.
            _func_info: Function metadata for context (unused, for interface).
            is_test: True if test procedure (relaxed requirements).

        Returns:
            QualityIndicators dict with bool values for each dimension.

        Raises:
            No exceptions raised.
        """
        indicators: dict[str, bool] = {}

        # Has any meaningful description
        has_description = bool(REGEX_PURPOSE_KEYWORDS.search(docstring) or len(docstring) > 20)
        indicators["brief_description"] = has_description

        # Has detailed content
        line_count = len([line for line in docstring.split("\n") if line.strip()])
        indicators["detailed_description"] = (
            line_count >= 3 or len(docstring) > self.config.thresholds.min_detailed_chars_brief
        )

        if not is_test:
            # Check for parameter documentation
            indicators["args_section"] = bool(REGEX_PARAM_DOC.search(docstring))

            # Check for return value documentation
            indicators["returns_section"] = bool(REGEX_RETURN_DOC.search(docstring))

            # Check for raises/error documentation
            indicators["raises_section"] = bool(REGEX_RAISES_KEYWORDS.search(docstring))

            # Check for business context documentation
            indicators["business_context"] = bool(REGEX_BUSINESS_CONTEXT.search(docstring))

            # Check for examples
            indicators["example_section"] = bool(REGEX_EXAMPLE_DOC.search(docstring))

            # Implementation details
            indicators["implementation_details"] = len(docstring) > 150

        return cast(QualityIndicators, indicators)
