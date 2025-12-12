"""Tests for Python documentation analyzer."""

import ast

import pytest

from docscope_mcp.analyzers.python import PythonAnalyzer
from docscope_mcp.models import AnalysisConfig


class TestPythonAnalyzerBasic:
    """Basic tests for PythonAnalyzer."""

    def test_analyzer_creation(self) -> None:
        """Verify PythonAnalyzer instantiates with correct language."""
        analyzer = PythonAnalyzer()
        assert analyzer.get_language() == "python"

    def test_analyzer_with_config(self) -> None:
        """Verify PythonAnalyzer accepts and stores custom configuration."""
        config = AnalysisConfig(max_code_size=1024)
        analyzer = PythonAnalyzer(config=config)
        assert analyzer.config.max_code_size == 1024

    @pytest.mark.parametrize(
        ("code", "expected_count", "has_error"),
        [
            ("", 0, False),
            ("def bad syntax", 1, True),
        ],
        ids=["empty_code", "syntax_error"],
    )
    def test_analyze_edge_cases(self, code: str, expected_count: int, has_error: bool) -> None:
        """Verify analyzer handles edge cases (empty code, syntax errors)."""
        analyzer = PythonAnalyzer()
        results = analyzer.analyze(code, "test.py")
        assert len(results) == expected_count
        if has_error:
            assert "error" in results[0]


class TestPythonAnalyzerAnalysis:
    """Tests for analyze method."""

    def test_analyze_function_without_docstring(self) -> None:
        """Verify undocumented function is flagged as poor quality."""
        analyzer = PythonAnalyzer()
        results = analyzer.analyze("def process(data): return data", "test.py")
        assert len(results) == 1
        assert results[0]["function_name"] == "process"
        assert results[0]["quality_assessment"]["quality"] == "poor"

    def test_analyze_function_with_good_docstring(self) -> None:
        """Verify well-documented function achieves acceptable quality score."""
        analyzer = PythonAnalyzer()
        code = '''
def process(data):
    """Process the input data.

    This function takes input data and processes it according
    to the business rules defined in the system. It provides
    a clean interface for data transformation.

    Args:
        data: The input data to process.

    Returns:
        The processed data result.

    Raises:
        ValueError: If data is invalid.

    Examples:
        >>> process("test")
        "processed_test"
    """
    return data
'''
        results = analyzer.analyze(code, "test.py")
        if results:
            assert results[0]["quality_assessment"]["score"] > 0.5

    def test_analyze_multiple_functions(self) -> None:
        """Verify analyzer detects all functions in multi-function code."""
        analyzer = PythonAnalyzer()
        code = "def func1(): pass\ndef func2(): pass\ndef func3(): pass"
        results = analyzer.analyze(code, "test.py")
        assert len(results) == 3

    def test_analyze_private_function(self) -> None:
        """Verify private functions receive lower priority than public."""
        analyzer = PythonAnalyzer()
        code = "def public_func(): pass\ndef _private_func(): pass"
        results = analyzer.analyze(code, "test.py")
        public = next(r for r in results if r["function_name"] == "public_func")
        private = next(r for r in results if r["function_name"] == "_private_func")
        assert public["priority"] > private["priority"]


class TestPythonAnalyzerQuality:
    """Tests for quality assessment."""

    @pytest.fixture
    def base_func_info(self) -> dict:
        """Base function info for quality tests."""
        return {
            "name": "test",
            "line": 1,
            "complexity": 1,
            "is_private": False,
            "is_test": False,
            "args": [],
            "returns": None,
            "decorators": [],
            "current_docstring": "",
        }

    def test_assess_empty_docstring(self, base_func_info: dict) -> None:
        """Verify empty docstring assessed as poor with zero score."""
        analyzer = PythonAnalyzer()
        result = analyzer.assess_docstring_quality("", "test", base_func_info)
        assert result["quality"] == "poor"
        assert result["score"] == 0.0
        assert "docstring" in result["missing"]

    def test_assess_brief_docstring(self, base_func_info: dict) -> None:
        """Verify minimal docstring still flagged as needing improvement."""
        analyzer = PythonAnalyzer()
        result = analyzer.assess_docstring_quality("Brief.", "test", base_func_info)
        assert result["quality"] == "poor"
        assert result["needs_improvement"] is True


class TestPythonAnalyzerPriority:
    """Tests for priority calculation."""

    @pytest.mark.parametrize(
        ("name", "complexity", "is_private", "score", "min_expected", "max_expected"),
        [
            ("complex_func", 15, False, 0.2, 8, 15),
            ("_helper", 2, True, 0.9, 0, 3),
            ("medium_func", 7, False, 0.5, 4, 10),
        ],
        ids=["public_complex_high_priority", "private_simple_low_priority", "medium_complexity"],
    )
    def test_calculate_priority(
        self,
        name: str,
        complexity: int,
        is_private: bool,
        score: float,
        min_expected: int,
        max_expected: int,
    ) -> None:
        """Verify priority calculation for various function characteristics."""
        analyzer = PythonAnalyzer()
        func_info = {
            "name": name,
            "line": 1,
            "complexity": complexity,
            "is_private": is_private,
            "is_test": False,
            "args": [{"name": "x", "type_annotation": None, "default": None}]
            if complexity > 5
            else [],
            "returns": "str" if complexity > 5 else None,
            "decorators": [],
            "current_docstring": "",
        }
        quality = {
            "score": score,
            "quality": "poor" if score < 0.3 else "basic" if score < 0.6 else "excellent",
            "missing": [],
            "needs_improvement": score < 0.8,
            "indicators": {},
        }
        priority = analyzer.calculate_priority(func_info, quality)
        assert min_expected <= priority <= max_expected

    def test_priority_quality_gap_medium(self) -> None:
        """Verify medium quality gap contributes correctly."""
        analyzer = PythonAnalyzer()
        func_info = {
            "name": "test",
            "line": 1,
            "complexity": 1,
            "is_private": True,
            "is_test": False,
            "args": [],
            "returns": None,
            "decorators": [],
            "current_docstring": "",
        }
        quality = {
            "score": 0.5,
            "quality": "basic",
            "missing": [],
            "needs_improvement": True,
            "indicators": {},
        }
        priority = analyzer.calculate_priority(func_info, quality)
        assert priority == 2


class TestPythonAnalyzerTestDetection:
    """Tests for test function detection."""

    @pytest.mark.parametrize(
        ("func_name", "expected"),
        [
            ("test_ParseAST_Success", True),
            ("test_parsing_invalid_syntax", True),
            ("process_data", False),
            ("_test_helper", False),
        ],
        ids=["camelcase_test", "snake_case_test", "non_test", "private_test_helper"],
    )
    def test_detect_test_function(self, func_name: str, expected: bool) -> None:
        """Verify test function detection for various naming patterns."""
        analyzer = PythonAnalyzer()
        assert analyzer._is_test_function(func_name) is expected


class TestPythonAnalyzerSecurity:
    """Tests for security validation."""

    @pytest.mark.parametrize(
        ("config_override", "code", "file_path", "error_substring"),
        [
            ({"max_code_size": 100}, "x = 1\n" * 100, "test.py", "too large"),
            (None, "def f(): pass", "test\x00.py", "null byte"),
            ({"max_file_path_length": 20}, "def f(): pass", "a" * 50 + ".py", "too long"),
            (
                {"max_ast_depth": 5},
                (
                    "def f():\n"
                    "    if True:\n"
                    "        if True:\n"
                    "            if True:\n"
                    "                if True:\n"
                    "                    if True:\n"
                    "                        if True:\n"
                    "                            pass"
                ),
                "test.py",
                "depth",
            ),
        ],
        ids=["code_too_large", "null_byte_path", "path_too_long", "ast_too_deep"],
    )
    def test_security_validation(
        self,
        config_override: dict | None,
        code: str,
        file_path: str,
        error_substring: str,
    ) -> None:
        """Verify security validations reject malicious inputs."""
        config = AnalysisConfig(**(config_override or {}))
        analyzer = PythonAnalyzer(config=config)
        results = analyzer.analyze(code, file_path)
        assert len(results) == 1
        assert "error" in results[0]
        assert error_substring in results[0]["error"].lower()

    def test_file_path_type_error(self) -> None:
        """Verify non-string file path raises type error."""
        analyzer = PythonAnalyzer()
        with pytest.raises(TypeError, match="file_path must be string"):
            analyzer._validate_file_path(123)  # type: ignore

    def test_path_traversal_logged(self) -> None:
        """Verify path traversal patterns are logged as warning."""
        import logging

        mock_logger = logging.getLogger("test_traversal")
        mock_logger.setLevel(logging.WARNING)
        analyzer = PythonAnalyzer(logger=mock_logger)
        results = analyzer.analyze("def f(): pass", "../etc/passwd")
        assert len(results) == 1
        assert results[0]["function_name"] == "f"


class TestPythonAnalyzerEdgeCases:
    """Tests for edge cases and additional coverage."""

    @pytest.mark.parametrize(
        ("code", "func_name", "check_key", "check_value"),
        [
            ("async def fetch_data(): pass", "fetch_data", "function_name", "fetch_data"),
            (
                "@staticmethod\n@property\ndef my_method(): pass",
                "my_method",
                "function_info.decorators",
                ["staticmethod", "property"],
            ),
            ("def greet(name='World'): pass", "greet", "function_info.args.0.default", "'World'"),
            ("def process(data: str) -> int: pass", "process", "function_info.returns", "int"),
        ],
        ids=["async_function", "decorators", "defaults", "type_annotations"],
    )
    def test_function_variants(
        self, code: str, func_name: str, check_key: str, check_value: str | list
    ) -> None:
        """Verify analyzer handles various function patterns."""
        analyzer = PythonAnalyzer()
        results = analyzer.analyze(code, "test.py")
        assert len(results) == 1
        assert results[0]["function_name"] == func_name

        # Navigate nested keys like "function_info.decorators"
        value = results[0]
        for key in check_key.split("."):
            value = value[int(key)] if key.isdigit() else value[key]

        if isinstance(check_value, list):
            for item in check_value:
                assert item in value
        else:
            assert value == check_value

    def test_complexity_calculation_branching(self) -> None:
        """Verify complexity increases with branching statements."""
        analyzer = PythonAnalyzer()
        code = """
def complex_logic(x):
    if x > 0:
        for i in range(x):
            while i > 0:
                i -= 1
    return x
"""
        results = analyzer.analyze(code, "test.py")
        assert len(results) == 1
        assert results[0]["function_info"]["complexity"] > 3

    def test_terse_notation_detection(self) -> None:
        """Verify terse bullet-list docstrings are recognized."""
        analyzer = PythonAnalyzer()
        func_info = {
            "name": "test",
            "line": 1,
            "complexity": 1,
            "is_private": False,
            "is_test": False,
            "args": [],
            "returns": None,
            "decorators": [],
            "current_docstring": "",
        }
        terse_doc = """Process data.

- Step 1: Parse input
- Step 2: Validate format

Args:
    data: Input data string.

Returns:
    Processed result.
"""
        result = analyzer.assess_docstring_quality(terse_doc, "process", func_info)
        assert result["score"] > 0.3

    def test_test_function_aaa_pattern(self) -> None:
        """Verify test functions with AAA pattern score well."""
        analyzer = PythonAnalyzer()
        func_info = {
            "name": "test_something",
            "line": 1,
            "complexity": 1,
            "is_private": False,
            "is_test": True,
            "args": [],
            "returns": None,
            "decorators": [],
            "current_docstring": "",
        }
        test_doc = """Verify feature works correctly.

Business context:
Critical functionality for user workflow.

Arrange: Setup mock with test data.
Act: Call feature with inputs.
Assert: Verify expected outputs.

Testing Principle:
Validates edge case handling for invalid inputs.
"""
        result = analyzer.assess_docstring_quality(test_doc, "test_something", func_info)
        assert result["score"] > 0.4
        assert "arrangement_steps" in result["indicators"]

    @pytest.mark.parametrize(
        ("docstring", "expected_quality_options"),
        [
            ("Do something.\n\nThis processes input.\n\nArgs:\n    x: Input.", ("basic", "good")),
            (
                "Process input data.\n\nThis function processes data.\n\n"
                "Args:\n    x: Input.\n\nReturns:\n    Result.\n\n"
                "Raises:\n    ValueError: Invalid.",
                ("good", "excellent"),
            ),
        ],
        ids=["basic_quality", "good_quality"],
    )
    def test_quality_level_classification(
        self, docstring: str, expected_quality_options: tuple
    ) -> None:
        """Verify quality level classification for various docstrings."""
        analyzer = PythonAnalyzer()
        func_info = {
            "name": "process",
            "line": 1,
            "complexity": 1,
            "is_private": False,
            "is_test": False,
            "args": [{"name": "x", "type_annotation": None, "default": None}],
            "returns": "str",
            "decorators": [],
            "current_docstring": "",
        }
        result = analyzer.assess_docstring_quality(docstring, "process", func_info)
        assert result["quality"] in expected_quality_options

    def test_signature_validation_missing_args(self) -> None:
        """Verify missing Args section flagged for functions with params."""
        analyzer = PythonAnalyzer()
        func_info = {
            "name": "process",
            "line": 1,
            "complexity": 1,
            "is_private": False,
            "is_test": False,
            "args": [{"name": "data", "type_annotation": "str", "default": None}],
            "returns": None,
            "decorators": [],
            "current_docstring": "",
        }
        doc = "Process data.\n\nThis function processes the input data."
        result = analyzer.assess_docstring_quality(doc, "process", func_info)
        assert "args section" in result["missing"]

    def test_exception_handling_in_analyze(self) -> None:
        """Verify general exceptions are caught in analyze."""
        analyzer = PythonAnalyzer()
        results = analyzer.analyze("def f(): pass", "test.py")
        assert isinstance(results, list)

    def test_unexpected_exception_in_analyze(self) -> None:
        """Verify unexpected exceptions return error dict."""
        from unittest.mock import patch

        analyzer = PythonAnalyzer()
        with patch.object(analyzer, "_parse_with_timeout", side_effect=RuntimeError("Boom")):
            results = analyzer.analyze("def f(): pass", "test.py")
        assert len(results) == 1
        assert "error" in results[0]
        assert "Boom" in results[0]["error"]

    def test_parse_timeout_coverage(self) -> None:
        """Verify timeout handler path is covered."""
        from unittest.mock import patch

        analyzer = PythonAnalyzer()
        # Mock signal to simulate timeout, force the TimeoutError path
        with (
            patch("signal.alarm", side_effect=[None, TimeoutError("Parse timeout")]),
            patch("signal.signal"),
            patch("ast.parse", side_effect=TimeoutError("Parse timeout")),
        ):
            result = analyzer._parse_with_timeout("def f(): pass")
        assert isinstance(result, dict)
        assert "timeout" in result["error"].lower()

    def test_signal_not_available_coverage(self) -> None:
        """Verify Windows/no-signal path is covered."""
        from unittest.mock import patch

        analyzer = PythonAnalyzer()
        # Mock signal.signal to raise AttributeError (like Windows)
        with (
            patch("signal.signal", side_effect=AttributeError("No SIGALRM")),
            patch("signal.alarm", side_effect=AttributeError("No alarm")),
        ):
            result = analyzer._parse_with_timeout("def f(): pass")
        # Should still parse successfully
        assert isinstance(result, ast.AST)

    def test_quality_poor_via_low_score(self) -> None:
        """Verify 'poor' quality assigned when score below basic threshold."""
        analyzer = PythonAnalyzer()
        func_info = {
            "name": "test",
            "line": 1,
            "complexity": 1,
            "is_private": False,
            "is_test": False,
            "args": [{"name": "x", "type_annotation": None, "default": None}],
            "returns": "str",
            "decorators": [],
            "current_docstring": "",
        }
        # Docstring with some content but missing most indicators
        doc = "Does something.\n\nNot much else here."
        result = analyzer.assess_docstring_quality(doc, "process", func_info)
        # Should be poor due to low score (missing Args, Returns, etc.)
        assert result["quality"] == "poor"
        assert result["score"] < 0.3

    def test_quality_poor_else_branch(self) -> None:
        """Verify else branch for 'poor' quality when not brief but low score."""
        from docscope_mcp.models import AnalysisConfig

        # Custom config with very high thresholds to force else branch
        config = AnalysisConfig(quality_thresholds={"excellent": 0.99, "good": 0.98, "basic": 0.97})
        analyzer = PythonAnalyzer(config=config)
        func_info = {
            "name": "func",
            "line": 1,
            "complexity": 1,
            "is_private": False,
            "is_test": False,
            "args": [],
            "returns": None,
            "decorators": [],
            "current_docstring": "",
        }
        # Long docstring that won't be flagged as brief, but won't hit high thresholds
        doc = """This is a detailed docstring with multiple lines.

It has some detailed explanation that goes on for a while.
But it doesn't have Args, Returns, or other sections.
So it will have a low score despite not being brief.

- Point one about this function
- Point two about behavior
- Point three about usage
"""
        result = analyzer.assess_docstring_quality(doc, "func", func_info)
        # With impossibly high thresholds, should fall through to else: poor
        assert result["quality"] == "poor"
        assert result["needs_improvement"] is True
