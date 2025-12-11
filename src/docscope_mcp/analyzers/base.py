"""
Base analyzer protocol for documentation analysis.

Defines the interface that all language-specific analyzers must implement.
Uses Protocol for structural typing (duck typing with type safety).
"""

from abc import abstractmethod
from typing import Any, Protocol

from docscope_mcp.models import FunctionInfo, QualityAssessment


class BaseAnalyzer(Protocol):
    """Protocol defining documentation analyzer interface.

    All language-specific analyzers must implement this interface.
    Enables multi-language support while maintaining consistent API.

    The analyzer is responsible for:
    1. Parsing source code into function metadata
    2. Assessing documentation quality
    3. Calculating improvement priority
    4. Returning prioritized analysis results

    Examples:
        ```python
        class PythonAnalyzer:
            def analyze(self, code: str, file_path: str = "") -> list[dict[str, Any]]:
                # Parse Python code, assess docs, return results
                ...

            def get_language(self) -> str:
                return "python"

        # Use with any analyzer implementing the protocol
        def process(analyzer: BaseAnalyzer, code: str) -> list[dict[str, Any]]:
            return analyzer.analyze(code)
        ```
    """

    @abstractmethod
    def analyze(self, code: str, file_path: str = "") -> list[dict[str, Any]]:
        """Analyze source code and return functions needing documentation improvement.

        Args:
            code: Source code string to analyze
            file_path: Optional file path for context (used in results)

        Returns:
            List of analysis results, each containing:
                - function_name: Name of the function
                - line_number: Line where function is defined
                - file_path: Path to the file
                - current_docstring: Existing documentation
                - quality_assessment: Quality evaluation results
                - function_info: Function metadata
                - priority: Improvement priority score

            Returns error dict in list on failure:
                [{"error": "Error message"}]

            Returns empty list if all functions have excellent documentation.
        """
        ...

    @abstractmethod
    def get_language(self) -> str:
        """Return the programming language this analyzer handles.

        Returns:
            Language identifier string (e.g., "python", "typescript", "rust")
        """
        ...

    @abstractmethod
    def assess_docstring_quality(
        self, docstring: str, func_name: str, func_info: FunctionInfo
    ) -> QualityAssessment:
        """Assess the quality of a docstring.

        Args:
            docstring: The docstring text to assess
            func_name: Name of the function (for test detection)
            func_info: Function metadata for context

        Returns:
            QualityAssessment with score, quality level, and missing indicators
        """
        ...

    @abstractmethod
    def calculate_priority(
        self, func_info: FunctionInfo, quality_assessment: QualityAssessment
    ) -> int:
        """Calculate documentation improvement priority.

        Higher priority indicates more urgent need for documentation.

        Args:
            func_info: Function metadata
            quality_assessment: Quality assessment results

        Returns:
            Priority score (typically 0-15+, higher = more urgent)
        """
        ...
