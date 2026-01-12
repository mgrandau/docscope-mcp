"""
Quality assessment mixin for documentation analyzers.

Provides shared quality scoring logic used across all language analyzers.
Extracted to eliminate code duplication and ensure consistent behavior.
"""

from typing import Any, Literal

from docscope_mcp.models import AnalysisConfig, FunctionInfo, QualityIndicators, QualityLevel


class QualityAssessmentMixin:
    """Mixin providing quality assessment methods for analyzers.

    Implements shared quality scoring logic for determining documentation
    quality levels from indicator scores. All language-specific analyzers
    should inherit from this mixin to share consistent quality assessment.

    The mixin provides:
    - Score calculation from quality indicators
    - Quality level determination from score thresholds
    - Missing element identification from indicators

    Requirements:
        Subclasses must have a `config: AnalysisConfig` attribute.

    Example:
        >>> class MyAnalyzer(QualityAssessmentMixin, PriorityCalculationMixin):
        ...     def __init__(self):
        ...         self.config = AnalysisConfig()
        ...
        ...     def assess_docstring_quality(self, docstring, func_name, func_info):
        ...         indicators = self._calculate_quality_indicators(docstring)
        ...         return self._build_quality_assessment(indicators)
    """

    config: AnalysisConfig  # Required attribute from analyzer

    def _calculate_indicator_score(self, quality_indicators: QualityIndicators) -> float:
        """Calculate quality score from indicator boolean values.

        Computes average of True values across all quality indicators.
        Score represents the proportion of quality dimensions satisfied.

        Args:
            quality_indicators: Dict of indicator name to boolean value.

        Returns:
            Score from 0.0 (no indicators True) to 1.0 (all True).

        Raises:
            ZeroDivisionError: If indicators dict is empty (shouldn't happen).

        Example:
            >>> indicators = {'brief': True, 'detailed': False}
            >>> mixin._calculate_indicator_score(indicators)
            0.5
        """
        indicator_values = list(quality_indicators.values())
        if not indicator_values:
            return 0.0
        return sum(1 for v in indicator_values if v) / len(indicator_values)

    def _determine_quality_level(
        self, score: float
    ) -> tuple[Literal["poor", "basic", "good", "excellent"], bool]:
        """Determine quality level and improvement need from score.

        Maps numeric score to categorical quality level using configured
        thresholds. Also determines whether documentation needs improvement
        (only 'excellent' does not need improvement).

        Args:
            score: Quality score from 0.0 to 1.0.

        Returns:
            Tuple of (quality_level, needs_improvement).
            quality_level: One of 'poor', 'basic', 'good', 'excellent'.
            needs_improvement: True unless quality is 'excellent'.

        Raises:
            KeyError: If config missing required threshold keys.

        Example:
            >>> level, needs_work = mixin._determine_quality_level(0.85)
            >>> level
            'good'
            >>> needs_work
            True
        """
        thresholds = self.config.quality_thresholds

        if score >= thresholds["excellent"]:
            return "excellent", False
        elif score >= thresholds["good"]:
            return "good", True
        elif score >= thresholds["basic"]:
            return "basic", True
        else:
            return "poor", True

    def _identify_missing_elements(self, quality_indicators: QualityIndicators) -> list[str]:
        """Identify missing quality elements from indicator values.

        Extracts names of indicators that are False, converting underscores
        to spaces for human-readable output. Used in quality assessment
        results to guide documentation improvements.

        Args:
            quality_indicators: Dict of indicator name to boolean value.

        Returns:
            List of missing element names with underscores replaced by spaces.

        Raises:
            No exceptions raised.

        Example:
            >>> indicators = {'brief_description': True, 'args_section': False}
            >>> mixin._identify_missing_elements(indicators)
            ['args section']
        """
        return [key.replace("_", " ") for key, value in quality_indicators.items() if not value]

    def _build_empty_quality_assessment(
        self, missing_label: str = "docstring"
    ) -> dict[str, object]:
        """Build quality assessment for missing/empty documentation.

        Creates a standardized 'poor' quality assessment for functions
        with no documentation or documentation below minimum length.

        Args:
            missing_label: Description of what's missing (e.g., 'docstring',
                          'xml documentation', 'comments').

        Returns:
            QualityAssessment dict with quality='poor', score=0.0.

        Raises:
            No exceptions raised.

        Example:
            >>> result = mixin._build_empty_quality_assessment('xml documentation')
            >>> result['missing']
            ['xml documentation']
        """
        return {
            "quality": QualityLevel.POOR.value,
            "score": 0.0,
            "missing": [missing_label],
            "needs_improvement": True,
            "indicators": {},
        }

    def _is_test_function_common(self, func_name: str) -> bool:
        """Detect test functions using unified naming patterns.

        Identifies test functions across all supported languages using
        consistent patterns. Test functions receive relaxed documentation
        requirements focused on AAA pattern rather than Args/Returns.

        Recognized patterns (case-insensitive):
        - Starts with 'test' (covers 'test_', 'Test', 'TEST_' conventions)
        - Ends with 'Test' (xUnit convention)

        Args:
            func_name: Function/method name to check.

        Returns:
            True if function appears to be a test function.

        Raises:
            No exceptions raised.

        Example:
            >>> mixin._is_test_function_common('test_user_login')
            True
            >>> mixin._is_test_function_common('TestUserLogin')
            True
            >>> mixin._is_test_function_common('process_data')
            False
        """
        name_lower = func_name.lower()
        return name_lower.startswith("test") or name_lower.endswith("test")

    def _validate_signature_coverage(
        self, quality_indicators: QualityIndicators, func_info: FunctionInfo
    ) -> QualityIndicators:
        """Validate param/returns sections against function signature.

        Cross-references docstring sections with actual function signature
        to ensure documented params match declared params. Methods with
        parameters need param docs; methods with returns need returns docs.

        This shared implementation works across all languages since the
        validation logic is language-agnostic (checks presence of args
        and non-void returns).

        Args:
            quality_indicators: Current quality indicator values.
            func_info: Function metadata with args and return type.

        Returns:
            Updated QualityIndicators with signature validation applied.
            May set args_section or returns_section to False if missing.

        Raises:
            No exceptions raised.

        Example:
            >>> indicators = {'args_section': True, 'returns_section': True}
            >>> result = mixin._validate_signature_coverage(indicators, func_info)
            >>> # indicators updated based on signature requirements
        """
        has_params = len(func_info.get("args", [])) > 0

        if has_params and not quality_indicators.get("args_section", True):
            quality_indicators["args_section"] = False

        # Check for non-void/non-None return
        returns = func_info.get("returns")
        has_return = returns is not None and returns not in ("void", "None")
        if has_return and not quality_indicators.get("returns_section", True):
            quality_indicators["returns_section"] = False

        return quality_indicators

    def _validate_code_security(self, code: str) -> list[dict[str, Any]] | None:
        """Validate code for security issues (size limits).

        Enforces code size limits to prevent denial-of-service attacks
        from maliciously large input files. Part of the defense-in-depth
        security model for MCP tool inputs.

        Args:
            code: Source code string to validate.

        Returns:
            None if validation passes.
            List with error dict if validation fails.

        Raises:
            No exceptions raised.

        Example:
            >>> error = analyzer._validate_code_security('x = 1')
            >>> error is None
            True
            >>> error = analyzer._validate_code_security('x' * 10_000_000)
            >>> error[0]['error']
            'Code too large (max 5120KB)'
        """
        if len(code) > self.config.max_code_size:
            max_kb = self.config.max_code_size // 1024
            return [{"error": f"Code too large (max {max_kb}KB)"}]

        return None
