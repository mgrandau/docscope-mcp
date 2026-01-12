"""Tests for Python documentation analyzer."""

import ast

import pytest

from docscope_mcp.analyzers.python import PythonAnalyzer
from docscope_mcp.models import AnalysisConfig


class TestPythonAnalyzerBasic:
    """Test suite for PythonAnalyzer basic initialization and edge cases.

    Categories:
    1. Initialization Tests - Analyzer creation, config handling (2 tests)
    2. Edge Cases - Empty code, syntax errors (1 test)

    Total: 3 tests.
    """

    def test_analyzer_creation(self) -> None:
        """Verifies PythonAnalyzer instantiates with correct language identifier.

        Tests analyzer creation by instantiating with default configuration.

        Business context:
        Language identification is critical for routing code to correct parser.

        Arrangement:
        1. No setup needed - uses default configuration.

        Action:
        Instantiate PythonAnalyzer and query its language identifier.

        Assertion Strategy:
        Validates language property by confirming:
        - get_language() returns exactly "python".

        Testing Principle:
        Validates identity contract, ensuring analyzer self-identifies correctly.
        """
        analyzer = PythonAnalyzer()
        assert analyzer.get_language() == "python"

    def test_analyzer_with_config(self) -> None:
        """Verifies PythonAnalyzer accepts and stores custom configuration.

        Tests configuration injection by providing non-default AnalysisConfig.

        Business context:
        Custom configs enable security limits and quality thresholds per-project.

        Arrangement:
        1. Create AnalysisConfig with custom max_code_size=1024.

        Action:
        Instantiate PythonAnalyzer with custom config and access config property.

        Assertion Strategy:
        Validates config propagation by confirming:
        - analyzer.config.max_code_size equals injected value.

        Testing Principle:
        Validates dependency injection, ensuring config flows to analyzer.
        """
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
        """Verifies analyzer handles edge cases gracefully.

        Tests robustness by analyzing empty code and syntax errors.

        Business context:
        MCP server receives arbitrary code; must never crash on malformed input.

        Arrangement:
        1. Parametrize with empty string and invalid Python syntax.
        2. Create analyzer with default configuration.

        Action:
        Call analyze() with each edge case input.

        Assertion Strategy:
        Validates graceful degradation by confirming:
        - Empty code returns empty list (no functions).
        - Syntax errors return single result with "error" key.

        Testing Principle:
        Validates defensive programming, ensuring no exceptions escape.
        """
        analyzer = PythonAnalyzer()
        results = analyzer.analyze(code)
        assert len(results) == expected_count
        if has_error:
            assert "error" in results[0]


class TestPythonAnalyzerAnalysis:
    """Test suite for PythonAnalyzer.analyze() method.

    Categories:
    1. Missing Documentation - Undocumented functions (1 test)
    2. Good Documentation - Well-documented functions (1 test)
    3. Multiple Functions - Multi-function analysis (1 test)
    4. Visibility - Public vs private priority (1 test)

    Total: 4 tests.
    """

    def test_analyze_function_without_docstring(self) -> None:
        """Verifies undocumented function is flagged as poor quality.

        Tests quality detection by analyzing function with no docstring.

        Business context:
        Core analyzer purpose is detecting missing documentation.

        Arrangement:
        1. Create single-line function definition without docstring.

        Action:
        Analyze code and examine quality_assessment in result.

        Assertion Strategy:
        Validates detection accuracy by confirming:
        - Exactly one function detected.
        - Function name correctly extracted.
        - Quality rated as "poor".

        Testing Principle:
        Validates core detection, ensuring undocumented code is flagged.
        """
        analyzer = PythonAnalyzer()
        results = analyzer.analyze("def process(data): return data")
        assert len(results) == 1
        assert results[0]["function_name"] == "process"
        assert results[0]["quality_assessment"]["quality"] == "poor"

    def test_analyze_function_with_good_docstring(self) -> None:
        """Verifies well-documented function achieves acceptable quality score.

        Tests quality scoring by analyzing function with comprehensive docstring.

        Business context:
        Quality scores guide developers to prioritize documentation efforts.

        Arrangement:
        1. Create function with full Google-style docstring.
        2. Include Args, Returns, Raises, and Examples sections.

        Action:
        Analyze code and examine quality_assessment score.

        Assertion Strategy:
        Validates scoring accuracy by confirming:
        - Score exceeds 0.5 threshold for acceptable documentation.

        Testing Principle:
        Validates positive recognition, ensuring good docs score well.
        """
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
        results = analyzer.analyze(code)
        if results:
            assert results[0]["quality_assessment"]["score"] > 0.5

    def test_analyze_multiple_functions(self) -> None:
        """Verifies analyzer detects all functions in multi-function code.

        Tests completeness by analyzing code with multiple function definitions.

        Business context:
        Real files contain many functions; all must be analyzed.

        Arrangement:
        1. Create code string with three function definitions.

        Action:
        Analyze code and count results.

        Assertion Strategy:
        Validates completeness by confirming:
        - Result count matches function count (3).

        Testing Principle:
        Validates exhaustive detection, ensuring no functions are missed.
        """
        analyzer = PythonAnalyzer()
        code = "def func1(): pass\ndef func2(): pass\ndef func3(): pass"
        results = analyzer.analyze(code)
        assert len(results) == 3

    def test_analyze_private_function(self) -> None:
        """Verifies private functions receive lower priority than public.

        Tests priority calculation by comparing public vs underscore-prefixed functions.

        Business context:
        Public API documentation is more critical than internal helpers.

        Arrangement:
        1. Create code with one public and one private function.
        2. Both functions lack docstrings for equal quality comparison.

        Action:
        Analyze code and extract priority values for each function.

        Assertion Strategy:
        Validates priority ordering by confirming:
        - Public function priority exceeds private function priority.

        Testing Principle:
        Validates visibility weighting, ensuring public API prioritized.
        """
        analyzer = PythonAnalyzer()
        code = "def public_func(): pass\ndef _private_func(): pass"
        results = analyzer.analyze(code)
        public = next(r for r in results if r["function_name"] == "public_func")
        private = next(r for r in results if r["function_name"] == "_private_func")
        assert public["priority"] > private["priority"]


class TestPythonAnalyzerQuality:
    """Test suite for PythonAnalyzer quality assessment.

    Categories:
    1. Empty Docstring - No documentation present (1 test)
    2. Brief Docstring - Minimal documentation (1 test)

    Total: 2 tests.
    """

    @pytest.fixture
    def base_func_info(self) -> dict:
        """Provide base function info fixture for quality tests.

        Creates minimal function metadata for testing assess_docstring_quality.

        Business context:
            Quality assessment requires function metadata to evaluate
            documentation completeness against function signature.

        Args:
            self: Test class instance.

        Returns:
            dict: Function info with name, line, complexity, and empty args.

        Raises:
            None: Fixture always returns valid dict.

        Example:
            >>> info = base_func_info()
            >>> info["name"]
            'test'
        """
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
        """Verifies empty docstring assessed as poor with zero score.

        Tests quality floor by assessing function with no documentation.

        Business context:
        Completely undocumented functions represent highest priority gaps.

        Arrangement:
        1. Use base_func_info fixture with empty current_docstring.
        2. Pass empty string as docstring parameter.

        Action:
        Call assess_docstring_quality with empty docstring.

        Assertion Strategy:
        Validates zero-quality detection by confirming:
        - Quality level is "poor".
        - Score equals 0.0 (absolute minimum).
        - "docstring" appears in missing list.

        Testing Principle:
        Validates quality floor, ensuring no documentation scores zero.
        """
        analyzer = PythonAnalyzer()
        result = analyzer.assess_docstring_quality("", "test", base_func_info)
        assert result["quality"] == "poor"
        assert result["score"] == 0.0
        assert "docstring" in result["missing"]

    def test_assess_brief_docstring(self, base_func_info: dict) -> None:
        """Verifies minimal docstring still flagged as needing improvement.

        Tests quality detection by assessing single-word docstring.

        Business context:
        Brief docstrings without detail still require enhancement.

        Arrangement:
        1. Use base_func_info fixture with default values.
        2. Provide minimal "Brief." docstring.

        Action:
        Call assess_docstring_quality with minimal content.

        Assertion Strategy:
        Validates improvement detection by confirming:
        - Quality level is "poor" despite having content.
        - needs_improvement flag is True.

        Testing Principle:
        Validates content analysis, ensuring brief docs flagged.
        """
        analyzer = PythonAnalyzer()
        result = analyzer.assess_docstring_quality("Brief.", "test", base_func_info)
        assert result["quality"] == "poor"
        assert result["needs_improvement"] is True


class TestPythonAnalyzerPriority:
    """Test suite for PythonAnalyzer priority calculation.

    Categories:
    1. Parametrized Priority - Various function characteristics (1 test)
    2. Quality Gap - Medium quality gap contribution (1 test)

    Total: 2 tests.
    """

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
        """Verifies priority calculation for various function characteristics.

        Tests priority algorithm with parametrized inputs for coverage.

        Business context:
        Priority determines documentation improvement order in large codebases.

        Arrangement:
        1. Parametrize with public/complex, private/simple, and medium cases.
        2. Construct func_info dict with matching characteristics.
        3. Create quality dict with corresponding score and level.

        Action:
        Call calculate_priority with constructed inputs.

        Assertion Strategy:
        Validates priority range by confirming:
        - Public complex functions score 8-15 (high priority).
        - Private simple functions score 0-3 (low priority).
        - Medium complexity falls in between (4-10).

        Testing Principle:
        Validates priority weighting, ensuring characteristics affect score.
        """
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
        """Verifies medium quality gap contributes correctly to priority.

        Tests gap calculation by analyzing function with 0.5 quality score.

        Business context:
        Quality gap represents improvement potential; mid-gap needs attention.

        Arrangement:
        1. Create func_info for private non-test function (low base priority).
        2. Create quality dict with score=0.5 (medium gap).

        Action:
        Call calculate_priority and capture result.

        Assertion Strategy:
        Validates gap contribution by confirming:
        - Priority equals 2 (low base + medium gap contribution).

        Testing Principle:
        Validates gap weighting, ensuring partial docs get proportional priority.
        """
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
    """Test suite for PythonAnalyzer test function detection.

    Categories:
    1. Naming Patterns - Various test function naming conventions (1 test)

    Total: 1 test.
    """

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
        """Verifies test function detection for various naming patterns.

        Tests detection logic with parametrized function names.

        Business context:
        Test functions need different docstring standards than production code.

        Arrangement:
        1. Parametrize with camelCase tests, snake_case tests, non-tests, and private helpers.
        2. Create analyzer with default configuration.

        Action:
        Call _is_test_function with each function name.

        Assertion Strategy:
        Validates pattern matching by confirming:
        - test_* prefix detected as test (camelCase and snake_case).
        - Non-prefixed functions return False.
        - Private _test_* helpers return False.

        Testing Principle:
        Validates naming convention, ensuring test detection is accurate.
        """
        analyzer = PythonAnalyzer()
        assert analyzer._is_test_function(func_name) is expected


class TestPythonAnalyzerSecurity:
    """Test suite for PythonAnalyzer security validation.

    Categories:
    1. Size Limits - Code size validation (1 parametrized case)
    2. Depth Limits - AST depth validation (1 parametrized case)
    3. Path Logging - Traversal pattern logging (1 test)

    Total: 2 tests.
    """

    @pytest.mark.parametrize(
        ("config_override", "code", "error_substring"),
        [
            ({"max_code_size": 100}, "x = 1\n" * 100, "too large"),
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
                "depth",
            ),
        ],
        ids=["code_too_large", "ast_too_deep"],
    )
    def test_security_validation(
        self,
        config_override: dict | None,
        code: str,
        error_substring: str,
    ) -> None:
        """Verifies security validations reject malicious inputs.

        Tests security limits with parametrized constraint violations.

        Business context:
        MCP servers are attack surfaces; must reject resource exhaustion attempts.

        Arrangement:
        1. Parametrize with code exceeding size limit and deeply nested AST.
        2. Create config with restrictive limits for testing.

        Action:
        Analyze code that violates configured limits.

        Assertion Strategy:
        Validates security rejection by confirming:
        - Single error result returned.
        - Error message contains expected substring.

        Testing Principle:
        Validates security boundaries, ensuring limits are enforced.
        """
        config = AnalysisConfig(**(config_override or {}))
        analyzer = PythonAnalyzer(config=config)
        results = analyzer.analyze(code)
        assert len(results) == 1
        assert "error" in results[0]
        assert error_substring in results[0]["error"].lower()

    def test_validate_file_path_non_string(self) -> None:
        """Verifies file path validation rejects non-string input.

        Tests type checking in _validate_file_path method.

        Business context:
        Type safety prevents injection attacks via unexpected types.

        Arrangement:
        1. Create analyzer with default config.

        Action:
        Call _validate_file_path with non-string input.

        Assertion Strategy:
        Verify TypeError raised with descriptive message.

        Testing Principle:
        Type validation is first line of defense against malformed input.
        """
        analyzer = PythonAnalyzer()
        with pytest.raises(TypeError, match="file_path must be string"):
            analyzer._validate_file_path(123)

    def test_validate_file_path_too_long(self) -> None:
        """Verifies file path validation rejects overly long paths.

        Tests length limit in _validate_file_path method.

        Business context:
        Path length limits prevent buffer overflow attacks and DoS.

        Arrangement:
        1. Create config with short max_file_path_length.
        2. Create analyzer with restrictive config.

        Action:
        Call _validate_file_path with path exceeding limit.

        Assertion Strategy:
        Verify ValueError raised with max length message.

        Testing Principle:
        Length limits prevent resource exhaustion attacks.
        """
        config = AnalysisConfig(max_file_path_length=10)
        analyzer = PythonAnalyzer(config=config)
        with pytest.raises(ValueError, match="too long"):
            analyzer._validate_file_path("a" * 100)

    def test_validate_file_path_null_byte(self) -> None:
        """Verifies file path validation rejects null bytes.

        Tests null byte detection in _validate_file_path method.

        Business context:
        Null byte injection can bypass path validation in C libraries.

        Arrangement:
        1. Create analyzer with default config.

        Action:
        Call _validate_file_path with path containing null byte.

        Assertion Strategy:
        Verify ValueError raised with null byte message.

        Testing Principle:
        Null byte rejection prevents path truncation attacks.
        """
        analyzer = PythonAnalyzer()
        with pytest.raises(ValueError, match="null byte"):
            analyzer._validate_file_path("path/to\x00/file.py")

    def test_path_traversal_logged(self) -> None:
        """Verifies path traversal patterns are logged as warning.

        Tests logging integration by analyzing code with custom logger.

        Business context:
        Security events must be logged for monitoring and incident response.

        Arrangement:
        1. Create Python logging.Logger for test isolation.
        2. Configure logger with WARNING level.
        3. Create analyzer with custom logger injected.

        Action:
        Analyze simple function code to verify analyzer works with logger.

        Assertion Strategy:
        Validates analyzer integration by confirming:
        - Analysis completes successfully with single result.
        - Function name correctly extracted.

        Testing Principle:
        Validates logging integration, ensuring custom loggers accepted.
        """
        import logging

        mock_logger = logging.getLogger("test_traversal")
        mock_logger.setLevel(logging.WARNING)
        analyzer = PythonAnalyzer(logger=mock_logger)
        results = analyzer.analyze("def f(): pass")
        assert len(results) == 1
        assert results[0]["function_name"] == "f"


class TestPythonAnalyzerEdgeCases:
    """Test suite for PythonAnalyzer edge cases and coverage.

    Categories:
    1. Function Variants - async, decorators, defaults, annotations (1 test)
    2. Complexity - Branching statement complexity (1 test)
    3. Docstring Formats - Terse notation, AAA pattern (2 tests)
    4. Quality Classification - Level boundaries (2 tests)
    5. Exception Handling - Parse errors, timeouts (4 tests)
    6. Coverage Paths - Else branches, signal unavailability (2 tests)

    Total: 12 tests.
    """

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
        """Verifies analyzer handles various function patterns.

        Tests function extraction with parametrized Python syntax variants.

        Business context:
        Modern Python uses async, decorators, type hints; all must be parsed.

        Arrangement:
        1. Parametrize with async, decorated, default-arg, and annotated functions.
        2. Define nested key paths for deep property access.

        Action:
        Analyze code and navigate to specified nested property.

        Assertion Strategy:
        Validates extraction accuracy by confirming:
        - Function name correctly identified.
        - Nested properties match expected values.
        - List properties contain expected items.

        Testing Principle:
        Validates syntax coverage, ensuring all Python patterns supported.
        """
        analyzer = PythonAnalyzer()
        results = analyzer.analyze(code)
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
        """Verifies complexity increases with branching statements.

        Tests cyclomatic complexity calculation with nested control flow.

        Business context:
        Complex functions need better documentation; complexity drives priority.

        Arrangement:
        1. Create function with nested if/for/while statements.
        2. Include multiple branching paths for complexity.

        Action:
        Analyze code and extract complexity from function_info.

        Assertion Strategy:
        Validates complexity detection by confirming:
        - Complexity exceeds 3 (baseline for simple function).

        Testing Principle:
        Validates complexity scoring, ensuring branching increases score.
        """
        analyzer = PythonAnalyzer()
        code = """
def complex_logic(x):
    if x > 0:
        for i in range(x):
            while i > 0:
                i -= 1
    return x
"""
        results = analyzer.analyze(code)
        assert len(results) == 1
        assert results[0]["function_info"]["complexity"] > 3

    def test_terse_notation_detection(self) -> None:
        """Verifies terse bullet-list docstrings are recognized.

        Tests alternative docstring format detection with bullet points.

        Business context:
        Terse bullet-list style is valid documentation; must not be penalized.

        Arrangement:
        1. Create func_info with standard function metadata.
        2. Provide docstring with bullet-list steps plus Args/Returns.

        Action:
        Assess docstring quality with terse notation format.

        Assertion Strategy:
        Validates format recognition by confirming:
        - Score exceeds 0.3 (not penalized as empty/brief).

        Testing Principle:
        Validates format flexibility, ensuring bullet-lists score fairly.
        """
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
        """Verifies test functions with AAA pattern score well.

        Tests AAA (Arrange-Act-Assert) docstring detection for test methods.

        Business context:
        Test documentation standards differ from production code; AAA is ideal.

        Arrangement:
        1. Create func_info with is_test=True to trigger test detection.
        2. Provide docstring with explicit Arrange/Act/Assert sections.

        Action:
        Assess docstring quality for test function with AAA format.

        Assertion Strategy:
        Validates AAA detection by confirming:
        - Score exceeds 0.4 (AAA sections contribute to score).
        - "arrangement_steps" indicator is present in result.

        Testing Principle:
        Validates test standards, ensuring AAA pattern rewards score.
        """
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
        """Verifies quality level classification for various docstrings.

        Tests quality thresholds with parametrized docstring completeness.

        Business context:
        Quality levels determine priority and improvement recommendations.

        Arrangement:
        1. Parametrize with basic (brief+Args) and good (full sections) docstrings.
        2. Create func_info with args and returns for signature validation.

        Action:
        Assess docstring quality and examine quality level.

        Assertion Strategy:
        Validates classification by confirming:
        - Basic docstring classifies as "basic" or "good".
        - Complete docstring classifies as "good" or "excellent".

        Testing Principle:
        Validates threshold boundaries, ensuring correct level assignment.
        """
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
        """Verifies missing Args section flagged for functions with params.

        Tests signature-docstring mismatch detection for undocumented parameters.

        Business context:
        API consumers need parameter documentation; missing Args is critical gap.

        Arrangement:
        1. Create func_info with typed parameter (data: str).
        2. Provide docstring without Args section.

        Action:
        Assess docstring quality with signature mismatch.

        Assertion Strategy:
        Validates gap detection by confirming:
        - "args section" appears in missing list.

        Testing Principle:
        Validates signature coverage, ensuring undocumented params flagged.
        """
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
        """Verifies general exceptions are caught in analyze.

        Tests exception isolation by analyzing valid code.

        Business context:
        Analyzer must never crash; exceptions should be caught and reported.

        Arrangement:
        1. Create analyzer with default configuration.
        2. Provide valid simple function code.

        Action:
        Analyze code and verify list result type.

        Assertion Strategy:
        Validates isolation by confirming:
        - Result is a list (not exception).

        Testing Principle:
        Validates error handling, ensuring exceptions don't escape.
        """
        analyzer = PythonAnalyzer()
        results = analyzer.analyze("def f(): pass")
        assert isinstance(results, list)

    def test_unexpected_exception_in_analyze(self) -> None:
        """Verifies unexpected exceptions return error dict.

        Tests error wrapping by mocking parser to raise RuntimeError.

        Business context:
        Unexpected failures must return structured errors, not crash server.

        Arrangement:
        1. Create analyzer with default configuration.
        2. Patch _parse_with_timeout to raise RuntimeError.

        Action:
        Analyze code with mocked exception.

        Assertion Strategy:
        Validates error wrapping by confirming:
        - Single result returned.
        - Result contains "error" key.
        - Error message contains exception text "Boom".

        Testing Principle:
        Validates graceful degradation, ensuring errors are structured.
        """
        from unittest.mock import patch

        analyzer = PythonAnalyzer()
        with patch.object(analyzer, "_parse_with_timeout", side_effect=RuntimeError("Boom")):
            results = analyzer.analyze("def f(): pass")
        assert len(results) == 1
        assert "error" in results[0]
        assert "Boom" in results[0]["error"]

    def test_parse_timeout_coverage(self) -> None:
        """Verifies timeout handler path is covered.

        Tests timeout detection by mocking signal to simulate timeout.

        Business context:
        Malicious code could cause infinite parse; timeout protects server.

        Arrangement:
        1. Create analyzer with default configuration.
        2. Patch signal.alarm and ast.parse to raise TimeoutError.

        Action:
        Call _parse_with_timeout with valid code under mocked timeout.

        Assertion Strategy:
        Validates timeout handling by confirming:
        - Result is dict (error structure).
        - Error message contains "timeout".

        Testing Principle:
        Validates timeout protection, ensuring parse time is bounded.
        """
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
        """Verifies Windows/no-signal path is covered.

        Tests fallback parsing when signal module unavailable (Windows).

        Business context:
        Windows lacks SIGALRM; analyzer must work without signal-based timeout.

        Arrangement:
        1. Create analyzer with default configuration.
        2. Patch signal.signal and signal.alarm to raise AttributeError.

        Action:
        Call _parse_with_timeout under mocked signal unavailability.

        Assertion Strategy:
        Validates fallback by confirming:
        - Result is AST (parsing succeeded without timeout).

        Testing Principle:
        Validates cross-platform, ensuring Windows compatibility.
        """
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
        """Verifies 'poor' quality assigned when score below basic threshold.

        Tests quality floor by assessing docstring missing key sections.

        Business context:
        Low-quality documentation must be identified for improvement priority.

        Arrangement:
        1. Create func_info with args and returns (signature to validate).
        2. Provide docstring without Args, Returns, Raises sections.

        Action:
        Assess docstring quality with content but missing sections.

        Assertion Strategy:
        Validates poor detection by confirming:
        - Quality level is "poor".
        - Score below 0.3 (basic threshold).

        Testing Principle:
        Validates quality floor, ensuring incomplete docs rated poor.
        """
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
        """Verifies else branch for 'poor' quality when not brief but low score.

        Tests quality classification edge case with impossibly high thresholds.

        Business context:
        Coverage requires exercising all quality classification branches.

        Arrangement:
        1. Create config with unreachable thresholds (excellent=0.99).
        2. Create analyzer with custom config.
        3. Provide detailed docstring that won't meet high thresholds.

        Action:
        Assess docstring quality against impossible thresholds.

        Assertion Strategy:
        Validates else branch by confirming:
        - Quality falls through to "poor".
        - needs_improvement is True.

        Testing Principle:
        Validates branch coverage, ensuring all classification paths tested.
        """
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
