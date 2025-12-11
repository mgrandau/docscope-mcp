"""Tests for Python documentation analyzer."""

from docscope_mcp.analyzers.python import PythonAnalyzer
from docscope_mcp.models import AnalysisConfig


class TestPythonAnalyzerBasic:
    """Basic tests for PythonAnalyzer."""

    def test_analyzer_creation(self) -> None:
        """Test analyzer can be created."""
        analyzer = PythonAnalyzer()
        assert analyzer.get_language() == "python"

    def test_analyzer_with_config(self) -> None:
        """Test analyzer accepts custom config."""
        config = AnalysisConfig(max_code_size=1024)
        analyzer = PythonAnalyzer(config=config)
        assert analyzer.config.max_code_size == 1024

    def test_analyze_empty_code(self) -> None:
        """Test analyzing empty code."""
        analyzer = PythonAnalyzer()
        results = analyzer.analyze("", "test.py")
        assert results == []

    def test_analyze_syntax_error(self) -> None:
        """Test handling syntax errors."""
        analyzer = PythonAnalyzer()
        results = analyzer.analyze("def bad syntax", "test.py")
        assert len(results) == 1
        assert "error" in results[0]


class TestPythonAnalyzerAnalysis:
    """Tests for analyze method."""

    def test_analyze_function_without_docstring(self) -> None:
        """Test function without docstring is flagged."""
        analyzer = PythonAnalyzer()
        code = "def process(data): return data"
        results = analyzer.analyze(code, "test.py")
        assert len(results) == 1
        assert results[0]["function_name"] == "process"
        assert results[0]["quality_assessment"]["quality"] == "poor"

    def test_analyze_function_with_good_docstring(self) -> None:
        """Test function with good docstring passes or has lower priority."""
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
        # Should either pass or have lower priority
        if results:
            assert results[0]["quality_assessment"]["score"] > 0.5

    def test_analyze_multiple_functions(self) -> None:
        """Test analyzing multiple functions."""
        analyzer = PythonAnalyzer()
        code = """
def func1(): pass
def func2(): pass
def func3(): pass
"""
        results = analyzer.analyze(code, "test.py")
        assert len(results) == 3

    def test_analyze_private_function(self) -> None:
        """Test private functions have lower priority."""
        analyzer = PythonAnalyzer()
        code = """
def public_func(): pass
def _private_func(): pass
"""
        results = analyzer.analyze(code, "test.py")
        public = next(r for r in results if r["function_name"] == "public_func")
        private = next(r for r in results if r["function_name"] == "_private_func")
        assert public["priority"] > private["priority"]


class TestPythonAnalyzerQuality:
    """Tests for quality assessment."""

    def test_assess_empty_docstring(self) -> None:
        """Test assessment of empty docstring."""
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
        result = analyzer.assess_docstring_quality("", "test", func_info)
        assert result["quality"] == "poor"
        assert result["score"] == 0.0
        assert "docstring" in result["missing"]

    def test_assess_brief_docstring(self) -> None:
        """Test assessment of brief docstring."""
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
        result = analyzer.assess_docstring_quality("Brief.", "test", func_info)
        assert result["quality"] == "poor"
        assert result["needs_improvement"] is True


class TestPythonAnalyzerPriority:
    """Tests for priority calculation."""

    def test_calculate_priority_public_complex(self) -> None:
        """Test priority for public complex function."""
        analyzer = PythonAnalyzer()
        func_info = {
            "name": "complex_func",
            "line": 1,
            "complexity": 15,
            "is_private": False,
            "is_test": False,
            "args": [{"name": "x", "type_annotation": None, "default": None}],
            "returns": "str",
            "decorators": [],
            "current_docstring": "",
        }
        quality = {
            "score": 0.2,
            "quality": "poor",
            "missing": [],
            "needs_improvement": True,
            "indicators": {},
        }
        priority = analyzer.calculate_priority(func_info, quality)
        # Should be high: visibility(3) + complexity(2) + signature(3) + quality_gap(3) = 11
        assert priority >= 8

    def test_calculate_priority_private_simple(self) -> None:
        """Test priority for private simple function."""
        analyzer = PythonAnalyzer()
        func_info = {
            "name": "_helper",
            "line": 1,
            "complexity": 2,
            "is_private": True,
            "is_test": False,
            "args": [],
            "returns": None,
            "decorators": [],
            "current_docstring": "",
        }
        quality = {
            "score": 0.9,
            "quality": "excellent",
            "missing": [],
            "needs_improvement": False,
            "indicators": {},
        }
        priority = analyzer.calculate_priority(func_info, quality)
        # Should be low: visibility(0) + complexity(0) + signature(0) + quality_gap(0) = 0
        assert priority <= 3


class TestPythonAnalyzerTestDetection:
    """Tests for test function detection."""

    def test_detect_test_function_camelcase(self) -> None:
        """Test detection of CamelCase test function."""
        analyzer = PythonAnalyzer()
        assert analyzer._is_test_function("test_ParseAST_Success") is True

    def test_detect_test_function_underscores(self) -> None:
        """Test detection of underscore test function."""
        analyzer = PythonAnalyzer()
        assert analyzer._is_test_function("test_parsing_invalid_syntax") is True

    def test_detect_non_test_function(self) -> None:
        """Test non-test function detection."""
        analyzer = PythonAnalyzer()
        assert analyzer._is_test_function("process_data") is False
        assert analyzer._is_test_function("test_func") is False  # Too simple


class TestPythonAnalyzerSecurity:
    """Tests for security validation."""

    def test_validate_code_size(self) -> None:
        """Test code size validation."""
        config = AnalysisConfig(max_code_size=100)
        analyzer = PythonAnalyzer(config=config)
        large_code = "x = 1\n" * 100
        results = analyzer.analyze(large_code, "test.py")
        assert len(results) == 1
        assert "error" in results[0]
        assert "too large" in results[0]["error"].lower()

    def test_validate_file_path_null_byte(self) -> None:
        """Test file path null byte validation."""
        analyzer = PythonAnalyzer()
        results = analyzer.analyze("def f(): pass", "test\x00.py")
        assert len(results) == 1
        assert "error" in results[0]
        assert "null byte" in results[0]["error"].lower()
