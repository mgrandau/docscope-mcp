"""
Visual Basic .NET Documentation Analyzer.

Regex-based analyzer for VB.NET documentation quality.
Implements multi-criteria assessment with priority calculation.

Architecture:
    - Regex parsing for Sub/Function/Property discovery
    - XML documentation comment assessment
    - Priority calculation via factor-based scoring
    - Security protections against DoS attacks
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

# Pre-compiled regex patterns for VB.NET parsing
REGEX_FUNCTION = re.compile(
    r"(?P<xml_doc>(?:\s*'''.*\n)*)"  # XML doc comments (''' in VB)
    r"\s*(?P<attributes>(?:<.*?>\s*)*)"  # Attributes
    r"\s*(?P<modifiers>(?:Public|Private|Protected|Friend|Shared|Overridable|Overrides|MustOverride|Async|Partial)\s+)*"
    r"(?:Function|Sub)\s+"
    r"(?P<name>\w+)\s*"
    r"\((?P<params>[^)]*)\)"
    r"(?:\s+As\s+(?P<return_type>[\w\(\)\s,\.]+))?",
    re.MULTILINE | re.IGNORECASE,
)

REGEX_PROPERTY = re.compile(
    r"(?P<xml_doc>(?:\s*'''.*\n)*)"
    r"\s*(?P<modifiers>(?:Public|Private|Protected|Friend|Shared|Overridable|Overrides|ReadOnly|WriteOnly)\s+)*"
    r"Property\s+"
    r"(?P<name>\w+)"
    r"(?:\s*\((?P<params>[^)]*)\))?"
    r"(?:\s+As\s+(?P<type>[\w\(\)\s,\.]+))?",
    re.MULTILINE | re.IGNORECASE,
)

REGEX_CLASS = re.compile(
    r"(?P<xml_doc>(?:\s*'''.*\n)*)"
    r"\s*(?P<modifiers>(?:Public|Private|Protected|Friend|MustInherit|NotInheritable|Partial)\s+)*"
    r"Class\s+(?P<name>\w+)",
    re.MULTILINE | re.IGNORECASE,
)

REGEX_PARAM = re.compile(
    r"(?:ByVal|ByRef|Optional|ParamArray)?\s*"
    r"(?P<name>\w+)\s+"
    r"As\s+(?P<type>[\w\(\)\s,\.]+)"
    r"(?:\s*=\s*(?P<default>[^,)]+))?",
    re.IGNORECASE,
)

REGEX_XML_SUMMARY = re.compile(r"<summary>(.*?)</summary>", re.DOTALL | re.IGNORECASE)
REGEX_XML_PARAM = re.compile(
    r'<param\s+name=["\'](\w+)["\']>(.*?)</param>', re.DOTALL | re.IGNORECASE
)
REGEX_XML_RETURNS = re.compile(r"<returns>(.*?)</returns>", re.DOTALL | re.IGNORECASE)
REGEX_XML_EXCEPTION = re.compile(
    r'<exception\s+cref=["\']([^"\']+)["\']>(.*?)</exception>', re.DOTALL | re.IGNORECASE
)
REGEX_XML_EXAMPLE = re.compile(r"<example>(.*?)</example>", re.DOTALL | re.IGNORECASE)
REGEX_XML_REMARKS = re.compile(r"<remarks>(.*?)</remarks>", re.DOTALL | re.IGNORECASE)


class VBAnalyzer(QualityAssessmentMixin, PriorityCalculationMixin):
    """VB.NET documentation quality analyzer using regex-based parsing.

    Analyzes Visual Basic .NET source code to identify methods needing
    documentation improvement. Uses multi-criteria assessment including:
    - XML documentation comment analysis
    - Content quality (depth, completeness)
    - Context awareness (test vs production code)

    Attributes:
        config: Analysis configuration
        logger: Logger instance for diagnostics

    Examples:
        ```python
        analyzer = VBAnalyzer()
        results = analyzer.analyze("Public Sub Foo()\nEnd Sub", "example.vb")
        for result in results:
            print(f"{result['function_name']}: {result['priority']}")
        ```
    """

    def __init__(
        self,
        config: AnalysisConfig | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Create VB.NET documentation analyzer with optional configuration.

        Initializes a new VBAnalyzer instance for analyzing VB.NET source code
        documentation quality. The analyzer uses regex-based parsing to extract
        VB.NET methods and assess XML documentation against quality standards.

        Purpose: Provides the analyzer component for VB.NET language support in
        the multi-language documentation analysis system.

        Args:
            config: Analysis configuration. Defaults to DEFAULT_CONFIG.
            logger: Logger instance. Defaults to module logger.

        Returns:
            None - initializes instance attributes.

        Raises:
            No exceptions raised.

        Example:
            >>> analyzer = VBAnalyzer()
            >>> analyzer.get_language()
            'vb'
        """
        self.config = config or DEFAULT_CONFIG
        self.logger = logger or logging.getLogger(__name__)

    def get_language(self) -> str:
        """Return the programming language identifier for this analyzer.

        Provides language identification for multi-language analyzer routing.
        MCP tools use this to select the appropriate analyzer based on file
        extension or user specification.

        Returns:
            String 'vb' identifying this as the VB.NET analyzer.

        Raises:
            No exceptions raised.

        Example:
            >>> analyzer = VBAnalyzer()
            >>> analyzer.get_language()
            'vb'
        """
        return "vb"

    def analyze(self, code: str) -> list[dict[str, Any]]:
        """Find VB.NET methods with inadequate documentation.

        Parses VB.NET source via regex, extracts Subs/Functions, assesses
        XML doc quality, and returns prioritized improvement recommendations.
        This is the primary entry point for VB.NET documentation analysis.

        Purpose: Enables AI assistants to identify which methods need
        documentation improvements in VB.NET codebases.

        Args:
            code: VB.NET source code string to analyze.

        Returns:
            Prioritized list of methods needing documentation (highest first).
            Returns [{"error": "message"}] on failure.
            Returns [] if all methods have excellent documentation.

        Raises:
            No exceptions raised - errors returned in result list.

        Example:
            >>> analyzer = VBAnalyzer()
            >>> results = analyzer.analyze('Public Sub Foo()\nEnd Sub')
            >>> results[0]['function_name']
            'Foo'
        """
        security_error = self._validate_code_security(code)
        if security_error:
            return security_error

        try:
            functions = self._extract_methods_needing_improvement(code)
            return self._sort_by_priority(functions)
        except Exception as e:
            return [{"error": f"Failed to analyze code: {e!s}"}]

    def assess_docstring_quality(
        self, docstring: str, func_name: str, func_info: FunctionInfo
    ) -> QualityAssessment:
        """Assess XML documentation quality of a Sub/Function.

        Evaluates VB.NET method documentation against XML doc standards.
        Checks for summary, param, returns, exception, and example tags.

        Args:
            docstring: The XML doc comment text to assess.
            func_name: Method name for test detection.
            func_info: Method metadata (params, returns, complexity).

        Returns:
            QualityAssessment with quality level, score, missing elements.

        Raises:
            No exceptions - returns poor quality for invalid input.

        Example:
            >>> result = analyzer.assess_docstring_quality(
            ...     '<summary>Brief desc.</summary>', 'MySub', func_info
            ... )
            >>> result['quality']
            'poor'
        """
        min_length = self.config.min_docstring_length
        if not docstring or len(docstring.strip()) < min_length:
            return cast(
                QualityAssessment, self._build_empty_quality_assessment("xml documentation")
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

        Implements priority algorithm for ranking methods by documentation
        urgency. Higher scores indicate methods needing more attention.

        Args:
            func_info: Method metadata (visibility, complexity).
            quality_assessment: Quality evaluation results.

        Returns:
            Priority score 0-13+. Higher = more urgent.

        Raises:
            KeyError: If func_info missing required fields.

        Example:
            >>> priority = analyzer.calculate_priority(func_info, quality)
            >>> priority > 8  # High priority method
            True
        """
        return (
            self._calculate_visibility_score(func_info)
            + self._calculate_complexity_score(func_info)
            + self._calculate_signature_score(func_info)
            + self._calculate_quality_gap_score(quality_assessment)
        )

    # ==================== METHOD EXTRACTION ====================

    def _extract_methods_needing_improvement(self, code: str) -> list[dict[str, Any]]:
        """Extract Subs/Functions that need documentation improvement.

        Scans VB.NET code for method definitions, extracts metadata,
        assesses documentation quality, and filters for improvable methods.

        Args:
            code: VB.NET source code to analyze.

        Returns:
            List of method dicts with quality assessments and priorities.

        Raises:
            No exceptions raised.

        Example:
            >>> methods = analyzer._extract_methods_needing_improvement(
            ...     'Public Sub Foo()\nEnd Sub'
            ... )
            >>> len(methods) >= 0
            True
        """
        results: list[dict[str, Any]] = []

        for match in REGEX_FUNCTION.finditer(code):
            func_info = self._extract_method_info(match, code)
            xml_doc = self._clean_xml_doc(match.group("xml_doc") or "")

            quality = self.assess_docstring_quality(xml_doc, func_info["name"], func_info)

            priority = self.calculate_priority(func_info, quality)
            results.append(
                {
                    "function_name": func_info["name"],
                    "line_number": func_info["line"],
                    "current_docstring": xml_doc,
                    "quality_assessment": quality,
                    "function_info": func_info,
                    "priority": priority,
                }
            )

        return results

    def _extract_method_info(self, match: re.Match[str], code: str) -> FunctionInfo:
        """Extract metadata from Sub/Function regex match.

        Parses regex match groups to build FunctionInfo dict with name,
        line number, parameters, return type, and complexity estimate.

        Args:
            match: Regex match object from REGEX_FUNCTION.
            code: Full source code for line number calculation.

        Returns:
            FunctionInfo with name, line, args, returns, complexity.

        Raises:
            No exceptions raised.

        Example:
            >>> code = 'Public Sub Test()\nEnd Sub'
            >>> match = REGEX_FUNCTION.search(code)
            >>> info = analyzer._extract_method_info(match, code)
            >>> info['name']
            'Test'
        """
        name = match.group("name")
        modifiers = match.group("modifiers") or ""
        return_type = match.group("return_type")
        params_str = match.group("params") or ""

        # Calculate line number
        line = code[: match.start()].count("\n") + 1

        # Parse parameters
        args: list[ArgInfo] = []
        for param_match in REGEX_PARAM.finditer(params_str):
            args.append(
                {
                    "name": param_match.group("name"),
                    "type_annotation": param_match.group("type").strip()
                    if param_match.group("type")
                    else None,
                    "default": param_match.group("default"),
                }
            )

        # Determine visibility
        modifiers_lower = modifiers.lower()
        is_private = "private" in modifiers_lower or name.startswith("_")

        # Calculate complexity
        complexity = self._estimate_complexity(match, code)

        return {
            "name": name,
            "line": line,
            "complexity": complexity,
            "is_private": is_private,
            "is_test": self._is_test_function_common(name),
            "args": args,
            "returns": return_type.strip() if return_type else None,
            "decorators": [],
            "current_docstring": self._clean_xml_doc(match.group("xml_doc") or ""),
        }

    def _estimate_complexity(self, match: re.Match[str], code: str) -> int:
        """Estimate cyclomatic complexity for a Sub/Function.

        Counts control flow statements (If, For, While, etc.) to estimate
        code complexity. Higher complexity methods need better documentation.

        Args:
            match: Regex match for method signature.
            code: Full source code to extract method body.

        Returns:
            Complexity score (1 = minimal, higher = more complex).

        Raises:
            No exceptions raised.

        Example:
            >>> code = 'Public Sub Test()\nIf x Then\nEnd If\nEnd Sub'
            >>> match = REGEX_FUNCTION.search(code)
            >>> complexity = analyzer._estimate_complexity(match, code)
            >>> complexity >= 1
            True
        """
        start = match.end()
        method_body = ""

        # Find End Sub or End Function
        end_pattern = re.compile(r"\bEnd\s+(Sub|Function)\b", re.IGNORECASE)
        end_match = end_pattern.search(code, start)
        if end_match:
            method_body = code[start : end_match.start()]

        body_lower = method_body.lower()
        complexity = 1
        complexity += body_lower.count("if ")
        complexity += body_lower.count("elseif ")
        complexity += body_lower.count("select case")
        complexity += body_lower.count("case ")
        complexity += body_lower.count("for ")
        complexity += body_lower.count("for each ")
        complexity += body_lower.count("while ")
        complexity += body_lower.count("do ")
        complexity += body_lower.count("catch ")
        complexity += body_lower.count(" andalso ")
        complexity += body_lower.count(" orelse ")

        return complexity

    def _clean_xml_doc(self, xml_doc: str) -> str:
        """Clean XML documentation comment, removing ''' prefixes.

        Strips VB.NET XML doc comment markers to extract pure XML content
        for quality assessment. Handles multi-line comments.

        Args:
            xml_doc: Raw XML doc comment with ''' prefixes.

        Returns:
            Cleaned XML content without comment markers.

        Raises:
            No exceptions raised.

        Example:
            >>> analyzer._clean_xml_doc("''' <summary>Test</summary>")
            '<summary>Test</summary>'
        """
        lines = xml_doc.strip().split("\n")
        cleaned = []
        for line in lines:
            line = line.strip()
            if line.startswith("'''"):
                line = line[3:].strip()
            cleaned.append(line)
        return "\n".join(cleaned)

    # ==================== QUALITY INDICATORS ====================

    def _calculate_quality_indicators(
        self, docstring: str, _func_info: FunctionInfo, is_test: bool
    ) -> QualityIndicators:
        """Calculate quality indicators for XML documentation.

        Args:
            docstring: XML doc comment text to analyze.
            _func_info: Function metadata for context (unused, for interface).
            is_test: True if test method (relaxed requirements).

        Returns:
            QualityIndicators dict with bool values for each dimension.

        Raises:
            No exceptions raised.
        """
        indicators: dict[str, bool] = {}

        summary_match = REGEX_XML_SUMMARY.search(docstring)
        has_summary = bool(summary_match and summary_match.group(1).strip())
        indicators["brief_description"] = has_summary

        remarks_match = REGEX_XML_REMARKS.search(docstring)
        indicators["detailed_description"] = bool(remarks_match and remarks_match.group(1).strip())

        if not is_test:
            indicators["args_section"] = bool(REGEX_XML_PARAM.search(docstring))
            indicators["returns_section"] = bool(REGEX_XML_RETURNS.search(docstring))
            indicators["raises_section"] = bool(REGEX_XML_EXCEPTION.search(docstring))
            indicators["example_section"] = bool(REGEX_XML_EXAMPLE.search(docstring))

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
