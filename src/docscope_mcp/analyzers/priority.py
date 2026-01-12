"""
Priority calculation mixin for documentation analyzers.

Provides shared priority scoring logic used across all language analyzers.
Extracted to eliminate code duplication and ensure consistent behavior.
"""

from typing import Any

from docscope_mcp.models import AnalysisConfig, FunctionInfo, QualityAssessment


class PriorityCalculationMixin:
    """Mixin providing priority calculation methods for analyzers.

    Implements the priority algorithm for ranking functions by documentation
    urgency. All language-specific analyzers should inherit from this mixin
    to share consistent priority scoring logic.

    Algorithm: Priority = Visibility + Complexity + Signature + Quality_Gap

    Factors:
    - Visibility: Public functions score higher (0-3)
    - Complexity: Higher complexity needs more docs (0-2)
    - Signature: More params/returns need documentation (0-5)
    - Quality_Gap: Lower quality = higher priority (0-3)

    Requirements:
        Subclasses must have a `config: AnalysisConfig` attribute.

    Example:
        >>> class MyAnalyzer(PriorityCalculationMixin):
        ...     def __init__(self):
        ...         self.config = AnalysisConfig()
        ...
        ...     def calculate_priority(self, func_info, quality):
        ...         return (
        ...             self._calculate_visibility_score(func_info)
        ...             + self._calculate_complexity_score(func_info)
        ...             + self._calculate_signature_score(func_info)
        ...             + self._calculate_quality_gap_score(quality)
        ...         )
    """

    config: AnalysisConfig  # Required attribute from analyzer

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
            >>> mixin._calculate_visibility_score({'is_private': False, ...})
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
            0-2 based on complexity thresholds from config.

        Raises:
            KeyError: If func_info missing 'complexity' key.

        Example:
            >>> mixin._calculate_complexity_score({'complexity': 15, ...})
            2
        """
        complexity = func_info["complexity"]
        thresholds = self.config.thresholds

        if complexity > thresholds.complexity_high:
            return 2
        elif complexity > thresholds.complexity_medium:
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
            >>> func_info = {'args': [{'name': 'x'}], 'returns': 'int', ...}
            >>> mixin._calculate_signature_score(func_info)
            3
        """
        score = 0
        thresholds = self.config.thresholds

        param_count = len(func_info["args"])
        if param_count > 0:
            score += min(param_count, thresholds.max_param_priority_contribution)
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
            >>> mixin._calculate_quality_gap_score({'score': 0.2, ...})
            3
        """
        quality_score = quality_assessment["score"]
        thresholds = self.config.thresholds

        if quality_score < thresholds.quality_gap_poor:
            return 3
        elif quality_score < thresholds.quality_gap_basic:
            return 2
        elif quality_score < thresholds.quality_gap_good:
            return 1
        return 0

    def _sort_by_priority(self, functions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Sort function results by priority descending.

        Orders analysis results so highest priority (most urgent)
        functions appear first. Provides actionable ordering for
        MCP tool output.

        Args:
            functions: List of function analysis dicts.

        Returns:
            Same list sorted by priority (highest first).

        Raises:
            KeyError: If function dict missing 'priority' key.

        Example:
            >>> sorted_funcs = mixin._sort_by_priority(results)
            >>> sorted_funcs[0]['priority'] >= sorted_funcs[-1]['priority']
            True
        """
        return sorted(functions, key=lambda x: x["priority"], reverse=True)
