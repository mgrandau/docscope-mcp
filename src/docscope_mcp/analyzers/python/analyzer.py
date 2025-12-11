"""
Python Documentation Analyzer.

AST-based analyzer for Python documentation quality.
Implements multi-criteria assessment with priority calculation.

Architecture:
    - AST parsing for function discovery
    - Quality assessment via indicator evaluation
    - Priority calculation via factor-based scoring
    - Security protections against DoS attacks
"""

import ast
import logging
import re
import signal
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

# Pre-compiled regex patterns for performance
REGEX_TEST_CAMELCASE = re.compile(r"test_[A-Z]")
REGEX_BRIEF_DESCRIPTION = re.compile(r"^\s*[A-Z][^.]*\.$")


class PythonAnalyzer:
    """Python documentation quality analyzer using AST parsing.

    Analyzes Python source code to identify functions needing documentation
    improvement. Uses multi-criteria assessment including:
    - Structural analysis (sections, format)
    - Content quality (depth, completeness)
    - Context awareness (test vs production code)
    - Terse notation support (bullet lists, technical specs)

    Attributes:
        config: Analysis configuration
        logger: Logger instance for diagnostics

    Examples:
        ```python
        analyzer = PythonAnalyzer()
        results = analyzer.analyze("def foo(): pass", "example.py")
        for result in results:
            print(f"{result['function_name']}: {result['priority']}")
        ```
    """

    def __init__(
        self,
        config: AnalysisConfig | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize Python analyzer with configuration.

        Args:
            config: Analysis configuration. Defaults to DEFAULT_CONFIG.
            logger: Logger instance. Defaults to module logger.
        """
        self.config = config or DEFAULT_CONFIG
        self.logger = logger or logging.getLogger(__name__)

    def get_language(self) -> str:
        """Return language identifier."""
        return "python"

    # ==================== PUBLIC API ====================

    def analyze(self, code: str, file_path: str = "") -> list[dict[str, Any]]:
        """Analyze Python code and return functions needing documentation.

        Args:
            code: Python source code string
            file_path: Optional file path for context

        Returns:
            Prioritized list of functions needing documentation (highest first).
            Each dict contains function_name, line_number, file_path,
            current_docstring, quality_assessment, function_info, priority.

            Returns [{"error": "message"}] on failure.
            Returns [] if all functions have excellent documentation.
        """
        # Security validation
        security_error = self._validate_code_security(code, file_path)
        if security_error:
            return security_error

        try:
            # Protected parsing
            parse_result = self._parse_with_timeout(code)
            if isinstance(parse_result, dict):
                return [parse_result]

            # Depth validation
            depth_error = self._validate_ast_depth(parse_result)
            if depth_error:
                return [depth_error]

            # Extract and analyze functions
            functions = self._extract_functions_needing_improvement(parse_result, file_path)

            # Sort by priority
            return self._sort_by_priority(functions)

        except Exception as e:
            return [{"error": f"Failed to analyze code: {e!s}"}]

    def assess_docstring_quality(
        self, docstring: str, func_name: str, func_info: FunctionInfo
    ) -> QualityAssessment:
        """Assess docstring quality using multi-dimensional standards.

        Evaluates:
        - Structural elements (brief, detailed, sections)
        - Content quality (context, implementation details)
        - Completeness (param/return coverage)
        - Test-specific indicators for test functions

        Args:
            docstring: Docstring text (may be empty)
            func_name: Function name for test detection
            func_info: Function metadata for signature validation

        Returns:
            QualityAssessment with score, quality level, and missing indicators
        """
        # Early exit for missing/minimal docstrings
        min_length = self.config.min_docstring_length
        if not docstring or len(docstring.strip()) < min_length:
            return {
                "quality": QualityLevel.POOR.value,
                "score": 0.0,
                "missing": ["docstring"],
                "needs_improvement": True,
                "indicators": {},
            }

        # Detect patterns
        is_test = self._is_test_function(func_name)
        is_terse_complete = self._detect_terse_notation(docstring)
        is_brief = self._is_brief_one_liner(docstring, is_terse_complete)

        # Calculate quality indicators
        quality_indicators = self._calculate_quality_indicators(
            docstring, func_info, is_test, is_terse_complete, is_brief
        )

        # Validate Args/Returns against signature
        quality_indicators = self._validate_signature_coverage(quality_indicators, func_info)

        # Calculate score
        indicator_values = list(quality_indicators.values())
        score = sum(cast(list[bool], indicator_values)) / len(indicator_values)

        # Identify missing elements
        missing = [key.replace("_", " ") for key, value in quality_indicators.items() if not value]

        # Determine quality level
        thresholds = self.config.quality_thresholds
        quality_str: Literal["poor", "basic", "good", "excellent"]

        if is_brief:
            quality_str = "poor"
            needs_improvement = True
            missing.insert(0, "comprehensive content (too brief)")
        elif score >= thresholds["excellent"]:
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
        """Calculate priority using factor-based scoring.

        Algorithm: Priority = Visibility + Complexity + Signature + Quality_Gap

        Factors:
        - Visibility: Public functions score higher (0-3)
        - Complexity: Higher complexity needs more docs (0-2)
        - Signature: More params/returns need documentation (0-5)
        - Quality_Gap: Lower quality = higher priority (0-3)

        Args:
            func_info: Function metadata
            quality_assessment: Quality assessment results

        Returns:
            Priority score 0-13+. Higher = more urgent.
        """
        return (
            self._calculate_visibility_score(func_info)
            + self._calculate_complexity_score(func_info)
            + self._calculate_signature_score(func_info)
            + self._calculate_quality_gap_score(quality_assessment)
        )

    # ==================== SECURITY VALIDATION ====================

    def _validate_code_security(self, code: str, file_path: str) -> list[dict[str, Any]] | None:
        """Validate code and file path for security issues."""
        # Validate code size
        if len(code) > self.config.max_code_size:
            max_kb = self.config.max_code_size // 1024
            return [{"error": f"Code too large (max {max_kb}KB)"}]

        # Validate file path
        try:
            self._validate_file_path(file_path)
        except (TypeError, ValueError) as e:
            return [{"error": str(e)}]

        return None

    def _validate_file_path(self, file_path: str) -> None:
        """Validate file_path parameter for security."""
        if not isinstance(file_path, str):
            raise TypeError(f"file_path must be string, got {type(file_path).__name__}")

        if len(file_path) > self.config.max_file_path_length:
            raise ValueError(f"file_path too long (max {self.config.max_file_path_length})")

        if chr(0) in file_path:
            raise ValueError("file_path contains null byte")

        if "../" in file_path or "..\\" in file_path:
            self.logger.warning(f"Path traversal pattern detected: {file_path[:100]}")

    def _parse_with_timeout(self, code: str) -> ast.AST | dict[str, str]:
        """Parse code with timeout protection."""

        def timeout_handler(_signum: int, _frame: Any) -> None:
            raise TimeoutError("Parse timeout")

        try:
            # Set timeout on Unix systems
            old_handler = None
            try:
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(self.config.ast_parse_timeout)
            except (AttributeError, ValueError):
                pass  # Windows or signal not available

            tree = ast.parse(code)

            # Cancel timeout
            try:
                signal.alarm(0)
                if old_handler is not None:
                    signal.signal(signal.SIGALRM, old_handler)
            except (AttributeError, ValueError):
                pass

            return tree

        except TimeoutError:
            return {"error": f"Parse timeout after {self.config.ast_parse_timeout}s"}
        except SyntaxError as e:
            return {"error": f"Syntax error: {e}"}

    def _validate_ast_depth(self, tree: ast.AST) -> dict[str, str] | None:
        """Validate AST doesn't exceed maximum depth."""
        try:
            self._check_ast_depth(tree, self.config.max_ast_depth)
            return None
        except ValueError as e:
            return {"error": str(e)}

    @staticmethod
    def _check_ast_depth(node: ast.AST, max_depth: int, current_depth: int = 0) -> None:
        """Recursively check AST depth."""
        if current_depth > max_depth:
            raise ValueError(f"AST depth {current_depth} exceeds maximum {max_depth}")
        for child in ast.iter_child_nodes(node):
            PythonAnalyzer._check_ast_depth(child, max_depth, current_depth + 1)

    # ==================== FUNCTION EXTRACTION ====================

    def _extract_functions_needing_improvement(
        self, tree: ast.AST, file_path: str
    ) -> list[dict[str, Any]]:
        """Extract functions that need documentation improvement."""
        results: list[dict[str, Any]] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                func_info = self._extract_function_info(node)
                docstring = ast.get_docstring(node) or ""

                quality = self.assess_docstring_quality(docstring, func_info["name"], func_info)

                if quality["needs_improvement"]:
                    priority = self.calculate_priority(func_info, quality)
                    results.append(
                        {
                            "function_name": func_info["name"],
                            "line_number": func_info["line"],
                            "file_path": file_path,
                            "current_docstring": docstring,
                            "quality_assessment": quality,
                            "function_info": func_info,
                            "priority": priority,
                        }
                    )

        return results

    def _extract_function_info(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionInfo:
        """Extract metadata from function AST node."""
        args: list[ArgInfo] = []
        for arg in node.args.args:
            args.append(
                {
                    "name": arg.arg,
                    "type_annotation": (ast.unparse(arg.annotation) if arg.annotation else None),
                    "default": None,
                }
            )

        # Add defaults
        num_defaults = len(node.args.defaults)
        if num_defaults > 0:
            for i, default in enumerate(node.args.defaults):
                arg_idx = len(args) - num_defaults + i
                if 0 <= arg_idx < len(args):
                    args[arg_idx]["default"] = ast.unparse(default)

        returns = ast.unparse(node.returns) if node.returns else None
        decorators = [
            ast.unparse(d)
            if isinstance(d, ast.Attribute)
            else d.id
            if isinstance(d, ast.Name)
            else str(d)
            for d in node.decorator_list
        ]

        # Calculate complexity (simple heuristic based on body size)
        complexity = self._calculate_complexity(node)

        return {
            "name": node.name,
            "line": node.lineno,
            "complexity": complexity,
            "is_private": node.name.startswith("_"),
            "is_test": self._is_test_function(node.name),
            "args": args,
            "returns": returns,
            "decorators": decorators,
            "current_docstring": ast.get_docstring(node) or "",
        }

    def _calculate_complexity(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        """Calculate cyclomatic complexity estimate."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            # Increment for branching statements
            branching_types = (
                ast.If,
                ast.While,
                ast.For,
                ast.AsyncFor,
                ast.ExceptHandler,
                ast.And,
                ast.Or,
                ast.comprehension,
            )
            if isinstance(child, branching_types):
                complexity += 1

        return complexity

    def _sort_by_priority(self, functions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Sort functions by priority (highest first)."""
        return sorted(functions, key=lambda x: x["priority"], reverse=True)

    # ==================== TEST DETECTION ====================

    def _is_test_function(self, func_name: str) -> bool:
        """Detect test functions by naming pattern.

        Identifies test functions based on:
        - Starts with "test_" prefix
        - AND has CamelCase after prefix OR multiple underscores
        """
        return func_name.startswith("test_") and (
            bool(REGEX_TEST_CAMELCASE.match(func_name)) or func_name.count("_") > 1
        )

    # ==================== TERSE NOTATION ====================

    def _detect_terse_notation(self, docstring: str) -> bool:
        """Detect terse but complete technical documentation patterns.

        Recognizes:
        - Bullet lists (≥3 items)
        - Technical notation (complexity symbols, arrows)
        - Structured sections (multiple paragraph breaks)
        """
        lines = docstring.strip().split("\n")
        thresholds = self.config.thresholds

        # Count bullet-style lines
        has_bullet_list = (
            sum(1 for line in lines if line.strip().startswith(("•", "-", "*", "1.", "2.", "3.")))
            >= thresholds.min_bullet_points
        )

        # Check for technical notation
        has_technical_specs = any(
            keyword in docstring for keyword in [":", "→", "=", "O(", "Θ(", "Ω("]
        )

        # Check for structured sections
        has_structured_sections = docstring.count("\n\n") >= thresholds.min_paragraph_breaks

        return has_bullet_list or (has_technical_specs and has_structured_sections)

    def _is_brief_one_liner(self, docstring: str, is_terse_complete: bool) -> bool:
        """Determine if docstring is insufficiently brief."""
        non_empty_count = self._count_non_empty_lines(docstring)
        thresholds = self.config.thresholds

        return (
            non_empty_count <= thresholds.max_brief_lines
            or (
                non_empty_count <= thresholds.max_brief_lines_extended
                and len(docstring) < thresholds.min_brief_chars
            )
        ) and not is_terse_complete

    def _count_non_empty_lines(self, docstring: str) -> int:
        """Count non-empty lines in docstring."""
        return len([line for line in docstring.strip().split("\n") if line.strip()])

    # ==================== QUALITY INDICATORS ====================

    def _calculate_quality_indicators(
        self,
        docstring: str,
        _func_info: FunctionInfo,
        is_test_function: bool,
        is_terse_complete: bool,
        is_brief_one_liner: bool,
    ) -> QualityIndicators:
        """Calculate quality indicators via specialized helpers."""
        lines = docstring.strip().split("\n")

        indicators: dict[str, bool] = {}
        indicators.update(
            self._check_brief_and_detailed(
                docstring, lines, is_brief_one_liner, is_terse_complete, is_test_function
            )
        )
        indicators.update(self._check_documentation_sections(docstring))

        if is_test_function:
            indicators.update(
                self._check_test_specific_indicators(
                    docstring, is_brief_one_liner, is_terse_complete
                )
            )
        else:
            indicators.update(self._check_context_and_details(docstring, is_terse_complete))

        return cast(QualityIndicators, indicators)

    def _check_brief_and_detailed(
        self,
        docstring: str,
        lines: list[str],
        is_brief_one_liner: bool,
        is_terse_complete: bool,
        is_test_function: bool,
    ) -> dict[str, bool]:
        """Calculate brief and detailed description indicators."""
        non_empty_count = self._count_non_empty_lines(docstring)
        thresholds = self.config.thresholds

        if is_test_function:
            min_lines = thresholds.min_detailed_lines_test
            min_chars = thresholds.min_detailed_chars_test
        else:
            min_lines = thresholds.min_detailed_lines_standard
            min_chars = thresholds.min_detailed_chars_standard

        return {
            "brief_description": (
                bool(REGEX_BRIEF_DESCRIPTION.search(lines[0].strip())) and not is_brief_one_liner
            ),
            "detailed_description": (
                (non_empty_count > min_lines and len(docstring) > min_chars) or is_terse_complete
            ),
        }

    def _check_documentation_sections(self, docstring: str) -> dict[str, bool]:
        """Check for standard documentation sections."""
        return {
            "args_section": "Args:" in docstring or "Parameters:" in docstring,
            "returns_section": "Returns:" in docstring or "Return:" in docstring,
            "raises_section": "Raises:" in docstring or "Raise:" in docstring,
            "example_section": "Example:" in docstring or "Examples:" in docstring,
        }

    def _check_context_and_details(
        self, docstring: str, is_terse_complete: bool
    ) -> dict[str, bool]:
        """Calculate business context and implementation detail indicators."""
        thresholds = self.config.thresholds

        return {
            "business_context": any(
                keyword in docstring.lower()
                for keyword in [
                    "business",
                    "purpose",
                    "context",
                    "responsible",
                    "protocol",
                    "interface",
                    "implements",
                    "provides",
                ]
            ),
            "implementation_details": (
                len(docstring) > thresholds.min_comprehensive_chars_standard
                or (
                    is_terse_complete
                    and len(docstring) > thresholds.min_comprehensive_chars_standard_terse
                )
            ),
        }

    def _check_test_specific_indicators(
        self,
        docstring: str,
        is_brief_one_liner: bool,
        is_terse_complete: bool,
    ) -> dict[str, bool]:
        """Calculate test function-specific indicators (AAA pattern)."""
        thresholds = self.config.thresholds

        has_arrangement = any(
            keyword in docstring
            for keyword in [
                "Arrangement",
                "Setup",
                "Given",
                "ARRANGE",
                "Arrange:",
                "Setup:",
                "Given:",
            ]
        )
        has_action = any(
            keyword in docstring
            for keyword in [
                "Action",
                "When",
                "ACT",
                "execution",
                "Act:",
                "When:",
                "Execute:",
            ]
        )
        has_assertion = any(
            keyword in docstring
            for keyword in [
                "Assertion",
                "Then",
                "ASSERT",
                "validates",
                "verifies",
                "Assert:",
                "Then:",
                "Verify:",
            ]
        )
        has_testing_principles = any(
            keyword in docstring
            for keyword in [
                "Testing Principles",
                "Principles",
                "Test:",
                "Validates:",
                "Ensures:",
            ]
        )

        return {
            "arrangement_steps": has_arrangement and not is_brief_one_liner,
            "action_description": has_action and not is_brief_one_liner,
            "assertion_strategy": has_assertion and not is_brief_one_liner,
            "testing_principles": has_testing_principles,
            "comprehensive_content": (
                len(docstring) > thresholds.min_comprehensive_chars_test
                or (
                    is_terse_complete
                    and len(docstring) > thresholds.min_comprehensive_chars_test_terse
                )
            ),
        }

    def _validate_signature_coverage(
        self,
        quality_indicators: QualityIndicators,
        func_info: FunctionInfo,
    ) -> QualityIndicators:
        """Validate Args/Returns sections against function signature."""
        # Check if function has parameters (excluding 'self')
        has_params = len([arg for arg in func_info.get("args", []) if arg["name"] != "self"]) > 0

        if has_params and not quality_indicators.get("args_section", True):
            quality_indicators["args_section"] = False

        # Check if function returns something
        has_return = func_info.get("returns") and func_info["returns"] != "None"
        if has_return and not quality_indicators.get("returns_section", True):
            quality_indicators["returns_section"] = False

        return quality_indicators

    # ==================== PRIORITY CALCULATION ====================

    def _calculate_visibility_score(self, func_info: FunctionInfo) -> int:
        """Calculate priority contribution from visibility."""
        return 0 if func_info["is_private"] else 3

    def _calculate_complexity_score(self, func_info: FunctionInfo) -> int:
        """Calculate priority contribution from complexity."""
        complexity = func_info["complexity"]
        thresholds = self.config.thresholds

        if complexity > thresholds.complexity_high:
            return 2
        elif complexity > thresholds.complexity_medium:
            return 1
        return 0

    def _calculate_signature_score(self, func_info: FunctionInfo) -> int:
        """Calculate priority contribution from signature complexity."""
        score = 0
        thresholds = self.config.thresholds

        # Parameters contribution (capped)
        param_count = len([arg for arg in func_info["args"] if arg["name"] != "self"])
        if param_count > 0:
            score += min(param_count, thresholds.max_param_priority_contribution)

        # Return value contribution
        if func_info["returns"] and func_info["returns"] != "None":
            score += 2

        return score

    def _calculate_quality_gap_score(self, quality_assessment: QualityAssessment) -> int:
        """Calculate priority contribution from documentation quality gap."""
        quality_score = quality_assessment["score"]

        if quality_score < 0.3:
            return 3
        elif quality_score < 0.6:
            return 2
        elif quality_score < 0.8:
            return 1
        return 0
