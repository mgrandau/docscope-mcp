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
        """Analyze source code and return functions needing documentation.

        Parses code, extracts functions/methods, evaluates docstrings,
        and returns prioritized list of items needing improvement.
        Core method called by MCP server's analyze_functions tool.

        Args:
            code: Source code string to analyze.
            file_path: Optional file path for context in results.

        Returns:
            List of dicts, each containing:
            - function_name: str
            - line_number: int
            - file_path: str
            - current_docstring: str or None
            - quality_assessment: dict with quality, score, missing
            - function_info: dict with params, returns, complexity
            - priority: int (1-10)

            Empty list if all functions have excellent docs.
            [{"error": "message"}] on parse failure.

        Raises:
            ValueError: If code is empty or None.

        Example:
            >>> results = analyzer.analyze(code, 'src/module.py')
            >>> for r in results:
            ...     print(f\"{r['function_name']}: {r['priority']}\")
        """
        ...

    @abstractmethod
    def get_language(self) -> str:
        """Return the programming language this analyzer handles.

        Identifies which language this analyzer supports for routing
        in multi-language analysis pipelines. Enables MCP server to
        select appropriate analyzer based on file extension or config.

        Args:
            None - no parameters required.

        Returns:
            Language identifier string (e.g., "python", "typescript").

        Raises:
            No exceptions - always returns valid string.

        Example:
            >>> analyzer = PythonAnalyzer()
            >>> analyzer.get_language()  # 'python'
        """
        ...

    @abstractmethod
    def assess_docstring_quality(
        self, docstring: str, func_name: str, func_info: FunctionInfo
    ) -> QualityAssessment:
        """Assess documentation quality of a function's docstring.

        Evaluates docstring completeness against language-specific
        standards (Google, NumPy, etc.). Checks for required sections
        like Args, Returns, Raises, and Examples.

        Args:
            docstring: The docstring text to assess (may be empty).
            func_name: Function name for test function detection.
            func_info: Function metadata (params, returns, complexity).

        Returns:
            QualityAssessment with quality level, score, missing elements.

        Raises:
            ValueError: If func_info is invalid or incomplete.

        Example:
            >>> quality = analyzer.assess_docstring_quality(
            ...     docstring='Brief summary.',
            ...     func_name='process_data',
            ...     func_info=info
            ... )
            >>> quality.quality  # 'poor'
        """
        ...

    @abstractmethod
    def calculate_priority(
        self, func_info: FunctionInfo, quality_assessment: QualityAssessment
    ) -> int:
        """Calculate documentation improvement priority score.

        Combines function visibility, complexity, and documentation
        quality to produce priority ranking. Higher scores indicate
        more urgent need for documentation improvement. Used by MCP
        tools to order results by documentation urgency.

        Priority factors: public vs private, parameter count, return
        complexity, current quality level, missing required sections.

        Args:
            func_info: Function metadata (visibility, complexity).
            quality_assessment: Quality evaluation results.

        Returns:
            Priority score 1-10. Higher = more urgent.
            - 8-10: Critical, document immediately
            - 5-7: Important, address soon
            - 1-4: Low priority, improve if time permits

        Raises:
            KeyError: If func_info missing required fields.

        Example:
            >>> priority = analyzer.calculate_priority(info, quality)
            >>> priority  # 9 (high priority public function)
        """
        ...
