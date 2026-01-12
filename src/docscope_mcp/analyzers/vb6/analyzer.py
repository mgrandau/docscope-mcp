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


class VB6Analyzer:
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
        if not docstring or len(docstring.strip()) < 5:
            return {
                "quality": QualityLevel.POOR.value,
                "score": 0.0,
                "missing": ["comments"],
                "needs_improvement": True,
                "indicators": {},
            }

        is_test = self._is_test_procedure(func_name)
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

            if quality["needs_improvement"]:
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
            >>> # match = REGEX_COMMENT_BLOCK.search(code)
            >>> # info = analyzer._extract_procedure_info_from_comment_match(match, code)
            >>> # info['name'] == 'MyProcedure'
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
            "is_test": self._is_test_procedure(name),
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
            >>> # match = REGEX_FUNCTION.search('Public Sub Test()\nEnd Sub')
            >>> # info = analyzer._extract_procedure_info(match, code)
            >>> # info['name'] == 'Test'
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
            "is_test": self._is_test_procedure(name),
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

    def _is_test_procedure(self, proc_name: str) -> bool:
        """Detect test procedures by naming pattern.

        Identifies test procedures to apply relaxed documentation requirements.
        Test procedures may skip some quality checks that apply to production code.

        Args:
            proc_name: Name of procedure to check.

        Returns:
            True if procedure appears to be a test.

        Raises:
            No exceptions raised.

        Example:
            >>> analyzer._is_test_procedure('TestUserLogin')
            True
        """
        name_lower = proc_name.lower()
        return (
            name_lower.startswith("test")
            or name_lower.endswith("test")
            or name_lower.startswith("test_")
        )

    def _sort_by_priority(self, functions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Sort results by priority descending.

        Orders procedures so highest-priority improvements appear first.
        Enables users to focus on most impactful documentation updates.

        Args:
            functions: List of function analysis dicts.

        Returns:
            Sorted list with highest priority first.

        Raises:
            No exceptions raised.

        Example:
            >>> sorted_procs = analyzer._sort_by_priority([{'priority': 1}, {'priority': 5}])
            >>> sorted_procs[0]['priority']
            5
        """
        return sorted(functions, key=lambda x: x["priority"], reverse=True)

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
        indicators["detailed_description"] = line_count >= 3 or len(docstring) > 100

        if not is_test:
            # Check for parameter documentation
            indicators["args_section"] = bool(REGEX_PARAM_DOC.search(docstring))

            # Check for return value documentation
            indicators["returns_section"] = bool(REGEX_RETURN_DOC.search(docstring))

            # Check for metadata (author, date) - common in VB6 codebases
            has_metadata = bool(
                REGEX_AUTHOR_DOC.search(docstring) or REGEX_DATE_DOC.search(docstring)
            )
            indicators["business_context"] = has_metadata

            # Check for examples
            indicators["example_section"] = bool(REGEX_EXAMPLE_DOC.search(docstring))

            # Implementation details
            indicators["implementation_details"] = len(docstring) > 150

        return cast(QualityIndicators, indicators)

    def _validate_signature_coverage(
        self, quality_indicators: QualityIndicators, func_info: FunctionInfo
    ) -> QualityIndicators:
        """Validate param/returns sections against procedure signature.

        Ensures documentation matches actual procedure signature. Procedures
        with parameters need param docs; functions need returns docs.

        Args:
            quality_indicators: Current quality indicator values.
            func_info: Function metadata with args and return type.

        Returns:
            Updated QualityIndicators with signature validation applied.

        Raises:
            No exceptions raised.

        Example:
            >>> # indicators = analyzer._validate_signature_coverage(indicators, func_info)
            >>> # indicators['args_section'] == True/False based on signature
        """
        has_params = len(func_info.get("args", [])) > 0

        if has_params and not quality_indicators.get("args_section", True):
            quality_indicators["args_section"] = False

        has_return = func_info.get("returns") is not None
        if has_return and not quality_indicators.get("returns_section", True):
            quality_indicators["returns_section"] = False

        return quality_indicators

    # ==================== PRIORITY CALCULATION ====================

    def _calculate_visibility_score(self, func_info: FunctionInfo) -> int:
        """Calculate priority contribution from visibility.

        Public procedures get higher priority since they define the API surface.
        Private procedures are implementation details with lower priority.

        Args:
            func_info: Function metadata with is_private flag.

        Returns:
            0 for private, 3 for public procedures.

        Raises:
            No exceptions raised.

        Example:
            >>> func = {'is_private': False, 'name': 'Foo', 'line': 1,
            ...         'complexity': 1, 'is_test': False, 'args': [],
            ...         'returns': None, 'decorators': [], 'current_docstring': ''}
            >>> analyzer._calculate_visibility_score(func)
            3
        """
        return 0 if func_info["is_private"] else 3

    def _calculate_complexity_score(self, func_info: FunctionInfo) -> int:
        """Calculate priority contribution from complexity.

        More complex procedures need better documentation to aid understanding.
        Uses cyclomatic complexity thresholds to assign priority.

        Args:
            func_info: Function metadata with complexity score.

        Returns:
            0-2 based on complexity thresholds.

        Raises:
            No exceptions raised.

        Example:
            >>> func = {'complexity': 15, 'name': 'Foo', 'line': 1,
            ...         'is_private': False, 'is_test': False, 'args': [],
            ...         'returns': None, 'decorators': [], 'current_docstring': ''}
            >>> analyzer._calculate_complexity_score(func)
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

        Procedures with more parameters and return values need documentation
        to explain their interface. Each parameter adds to priority.

        Args:
            func_info: Function metadata with args and returns.

        Returns:
            0-5+ based on parameter count and return presence.

        Raises:
            No exceptions raised.

        Example:
            >>> func = {'args': [{'name': 'a', 'type_annotation': None,
            ...                   'default': None}], 'returns': 'Integer',
            ...         'name': 'Foo', 'line': 1, 'complexity': 1,
            ...         'is_private': False, 'is_test': False, 'decorators': [],
            ...         'current_docstring': ''}
            >>> analyzer._calculate_signature_score(func)
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

        Procedures with poor documentation get higher priority to maximize
        improvement impact. Uses quality score thresholds.

        Args:
            quality_assessment: Quality assessment with score.

        Returns:
            0-3 based on quality score thresholds.

        Raises:
            No exceptions raised.

        Example:
            >>> qa = {'score': 0.2, 'quality': 'poor', 'missing': [],
            ...       'needs_improvement': True, 'indicators': {}}
            >>> analyzer._calculate_quality_gap_score(qa)
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
