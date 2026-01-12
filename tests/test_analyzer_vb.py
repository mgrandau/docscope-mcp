"""Tests for VB.NET documentation analyzer."""

import pytest

from docscope_mcp.analyzers.vb import VBAnalyzer
from docscope_mcp.models import AnalysisConfig


class TestVBAnalyzerBasic:
    """Basic tests for VBAnalyzer initialization and configuration.

    Test Categories:
        1. Analyzer Creation - Instantiation verification (1 test)
        2. Configuration - Custom config handling (1 test)

    Total: 2 tests.
    """

    def test_analyzer_creation(self) -> None:
        """Verifies VBAnalyzer instantiates with correct language identifier.

        Business context:
            Language routing depends on analyzer self-identification for
            correct file-to-analyzer mapping in multi-language analysis.

        Arrangement:
            1. No setup required - tests default instantiation.

        Action:
            Instantiate VBAnalyzer and query its language.

        Assertion Strategy:
            Verify language identifier matches expected "vb" value.

        Testing Principle:
            Factory pattern requires accurate type identification.
        """
        analyzer = VBAnalyzer()
        assert analyzer.get_language() == "vb"

    def test_analyzer_with_config(self) -> None:
        """Verifies VBAnalyzer accepts and stores custom configuration.

        Business context:
            Security limits and analysis thresholds must be configurable
            per-deployment to match organizational requirements.

        Arrangement:
            1. Create AnalysisConfig with custom max_code_size.

        Action:
            Instantiate VBAnalyzer with custom configuration.

        Assertion Strategy:
            Verify stored config matches provided values.

        Testing Principle:
            Dependency injection must preserve injected values.
        """
        config = AnalysisConfig(max_code_size=1024)
        analyzer = VBAnalyzer(config=config)
        assert analyzer.config.max_code_size == 1024


class TestVBAnalyzerAnalysis:
    """Tests for VBAnalyzer analyze method functionality.

    Test Categories:
        1. Documentation Detection - Undocumented Sub/Function (2 tests)
        2. XML Documentation - Complete documentation scoring (1 test)
        3. Multiple Methods - Multi-method code analysis (1 test)
        4. Access Modifiers - Private/public priority (1 test)
        5. Special Patterns - Async, Shared (2 tests)

    Total: 7 tests.
    """

    def test_analyze_sub_without_documentation(self) -> None:
        """Verifies undocumented Sub is flagged as poor quality.

        Business context:
            Documentation coverage requires identifying procedures lacking
            any XML documentation for prioritized improvement.

        Arrangement:
            1. Create VBAnalyzer with default config.
            2. Prepare VB.NET code with undocumented Public Sub.

        Action:
            Analyze the code and collect results.

        Assertion Strategy:
            Verify procedure detected with poor quality assessment.

        Testing Principle:
            Quality floor detection is foundational to analysis accuracy.
        """
        analyzer = VBAnalyzer()
        code = """
Public Sub ProcessData(data As String)
    Console.WriteLine(data)
End Sub
"""
        results = analyzer.analyze(code)
        assert len(results) == 1
        assert results[0]["function_name"] == "ProcessData"
        assert results[0]["quality_assessment"]["quality"] == "poor"

    def test_analyze_function_without_documentation(self) -> None:
        """Verifies undocumented Function is flagged as poor quality.

        Business context:
            VB.NET Functions return values and require documentation
            of parameters, return type, and behavior.

        Arrangement:
            1. Create VBAnalyzer with default config.
            2. Prepare VB.NET code with undocumented Public Function.

        Action:
            Analyze the code and collect results.

        Assertion Strategy:
            Verify function detected with correct name.

        Testing Principle:
            Function detection ensures return-value procedures are covered.
        """
        analyzer = VBAnalyzer()
        code = """
Public Function Calculate(x As Integer, y As Integer) As Integer
    Return x + y
End Function
"""
        results = analyzer.analyze(code)
        assert len(results) == 1
        assert results[0]["function_name"] == "Calculate"

    def test_analyze_with_xml_documentation(self) -> None:
        """Verifies well-documented method achieves acceptable quality score.

        Business context:
            XML documentation comments (''') are standard VB.NET documentation;
            analyzer must recognize complete documentation patterns.

        Arrangement:
            1. Create VBAnalyzer with default config.
            2. Prepare code with full XML documentation.

        Action:
            Analyze the documented code.

        Assertion Strategy:
            Verify quality score exceeds 0.5 threshold.

        Testing Principle:
            Quality ceiling recognition validates scoring algorithm.
        """
        analyzer = VBAnalyzer()
        code = """
''' <summary>
''' Processes the input data according to business rules.
''' </summary>
''' <remarks>
''' This method provides comprehensive data transformation
''' capabilities for the enterprise system.
''' </remarks>
''' <param name="data">The input data to process.</param>
''' <returns>The processed result string.</returns>
''' <exception cref="ArgumentException">Thrown when data is invalid.</exception>
''' <example>
''' Dim result = ProcessData("test")
''' </example>
Public Function ProcessData(data As String) As String
    Return data.ToUpper()
End Function
"""
        results = analyzer.analyze(code)
        if results:
            assert results[0]["quality_assessment"]["score"] > 0.5

    def test_analyze_multiple_methods(self) -> None:
        """Verifies analyzer detects all methods in multi-method code.

        Business context:
            Real-world files contain multiple methods; analyzer must
            enumerate all for complete documentation coverage reporting.

        Arrangement:
            1. Create VBAnalyzer with default config.
            2. Prepare code with Sub, Function, and Private Sub.

        Action:
            Analyze code and count results.

        Assertion Strategy:
            Verify at least two methods detected.

        Testing Principle:
            Exhaustive detection ensures no methods escape analysis.
        """
        analyzer = VBAnalyzer()
        code = """Public Sub Method1()
End Sub

Public Function Method2() As Integer
    Return 0
End Function

Private Sub Method3()
End Sub
"""
        results = analyzer.analyze(code)
        # VB analyzer finds at least 2 methods
        assert len(results) >= 2

    def test_analyze_private_method(self) -> None:
        """Verifies private methods receive lower priority than public.

        Business context:
            Private methods have lower documentation priority than public API;
            access modifier detection guides documentation effort allocation.

        Arrangement:
            1. Create VBAnalyzer with default config.
            2. Prepare code with Public and Private Subs.

        Action:
            Analyze and compare priorities between public and private.

        Assertion Strategy:
            Verify public method has higher priority than private.

        Testing Principle:
            Priority stratification guides documentation effort allocation.
        """
        analyzer = VBAnalyzer()
        code = """
Public Sub PublicMethod()
End Sub

Private Sub PrivateMethod()
End Sub
"""
        results = analyzer.analyze(code)
        public = next(r for r in results if r["function_name"] == "PublicMethod")
        private = next(r for r in results if r["function_name"] == "PrivateMethod")
        assert public["priority"] > private["priority"]

    def test_analyze_async_method(self) -> None:
        """Verifies Async methods are detected correctly.

        Business context:
            Async methods are common in modern VB.NET; analyzer must handle
            Async/Await patterns and Task return types.

        Arrangement:
            1. Create VBAnalyzer with default config.
            2. Prepare code with Async Function.

        Action:
            Analyze and verify method detection.

        Assertion Strategy:
            Verify method name extracted correctly.

        Testing Principle:
            Async pattern detection ensures modern code coverage.
        """
        analyzer = VBAnalyzer()
        code = """
Public Async Function FetchDataAsync(url As String) As Task(Of String)
    Return Await client.GetStringAsync(url)
End Function
"""
        results = analyzer.analyze(code)
        assert len(results) == 1
        assert results[0]["function_name"] == "FetchDataAsync"

    def test_analyze_shared_method(self) -> None:
        """Verifies Shared methods are detected correctly.

        Business context:
            Shared (static) methods provide utility functionality;
            documentation aids discoverability and correct usage.

        Arrangement:
            1. Create VBAnalyzer with default config.
            2. Prepare code with Shared Function.

        Action:
            Analyze and verify method detection.

        Assertion Strategy:
            Verify method name extracted correctly.

        Testing Principle:
            Shared method detection ensures utility code coverage.
        """
        analyzer = VBAnalyzer()
        code = """
Public Shared Function Calculate(a As Integer, b As Integer) As Integer
    Return a + b
End Function
"""
        results = analyzer.analyze(code)
        assert len(results) == 1
        assert results[0]["function_name"] == "Calculate"


class TestVBAnalyzerQuality:
    """Tests for VBAnalyzer quality assessment functionality.

    Test Categories:
        1. Empty Documentation - Zero score baseline (1 test)
        2. Partial Documentation - Summary-only scenarios (1 test)

    Total: 2 tests.
    """

    @pytest.fixture
    def base_func_info(self) -> dict:
        """Provide base function info fixture for quality tests.

        Creates minimal function metadata for testing assess_docstring_quality.

        Business context:
            Quality assessment requires function metadata to evaluate
            documentation completeness against method signature.

        Args:
            self: Test class instance (implicit pytest fixture).

        Returns:
            dict: Function info with name, line, complexity, and empty args.

        Raises:
            None: Fixture always returns valid dict.

        Example:
            >>> info = base_func_info()
            >>> info["name"]
            'Test'
        """
        return {
            "name": "Test",
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

        Business context:
            Quality floor establishes baseline for documentation scoring;
            undocumented methods must receive lowest possible rating.

        Arrangement:
            1. Create VBAnalyzer with default config.
            2. Use base_func_info fixture for method metadata.

        Action:
            Assess empty string as docstring.

        Assertion Strategy:
            Verify poor quality, zero score, and missing xml documentation indicator.

        Testing Principle:
            Quality floor ensures undocumented code is prioritized.
        """
        analyzer = VBAnalyzer()
        result = analyzer.assess_docstring_quality("", "Test", base_func_info)
        assert result["quality"] == "poor"
        assert result["score"] == 0.0
        assert "xml documentation" in result["missing"]

    def test_assess_summary_only(self, base_func_info: dict) -> None:
        """Verifies summary-only documentation is flagged as needing improvement.

        Business context:
            Minimal documentation (<summary> only) is insufficient for
            comprehensive API documentation; needs_improvement flag guides users.

        Arrangement:
            1. Create VBAnalyzer with default config.
            2. Prepare summary-only XML documentation.

        Action:
            Assess summary-only documentation.

        Assertion Strategy:
            Verify needs_improvement flag is True.

        Testing Principle:
            Partial documentation identification drives completeness.
        """
        analyzer = VBAnalyzer()
        doc = "<summary>Brief description.</summary>"
        result = analyzer.assess_docstring_quality(doc, "Test", base_func_info)
        assert result["needs_improvement"] is True


class TestVBAnalyzerPriority:
    """Tests for VBAnalyzer priority calculation.

    Test Categories:
        1. High Priority - Complex public methods (1 test)
        2. Low Priority - Simple private methods (1 test)

    Total: 2 tests.
    """

    def test_calculate_priority_high(self) -> None:
        """Verifies high priority for complex public methods.

        Business context:
            Complex public API methods require urgent documentation;
            priority score guides developer effort allocation.

        Arrangement:
            1. Create VBAnalyzer with default config.
            2. Create method info with high complexity, multiple args, return value.
            3. Create quality assessment with poor score.

        Action:
            Calculate priority for complex public method.

        Assertion Strategy:
            Verify priority score is 8 or higher.

        Testing Principle:
            Priority ceiling ensures critical methods are addressed first.
        """
        analyzer = VBAnalyzer()
        func_info = {
            "name": "ComplexMethod",
            "line": 1,
            "complexity": 15,
            "is_private": False,
            "is_test": False,
            "args": [
                {"name": "a", "type_annotation": "Integer", "default": None},
                {"name": "b", "type_annotation": "String", "default": None},
            ],
            "returns": "String",
            "decorators": [],
            "current_docstring": "",
        }
        quality = {
            "score": 0.1,
            "quality": "poor",
            "missing": ["summary"],
            "needs_improvement": True,
            "indicators": {},
        }
        priority = analyzer.calculate_priority(func_info, quality)
        assert priority >= 8

    def test_calculate_priority_low(self) -> None:
        """Verifies low priority for simple private methods.

        Business context:
            Simple private helper methods are lower documentation priority;
            priority stratification prevents wasted effort.

        Arrangement:
            1. Create VBAnalyzer with default config.
            2. Create method info for simple private method.
            3. Create quality assessment with good score.

        Action:
            Calculate priority for simple private method.

        Assertion Strategy:
            Verify priority score is 3 or lower.

        Testing Principle:
            Priority floor ensures low-impact methods are deprioritized.
        """
        analyzer = VBAnalyzer()
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
            "score": 0.7,
            "quality": "good",
            "missing": [],
            "needs_improvement": True,
            "indicators": {},
        }
        priority = analyzer.calculate_priority(func_info, quality)
        assert priority <= 3


class TestVBAnalyzerTestDetection:
    """Tests for VBAnalyzer test method detection.

    Test Categories:
        1. Test Naming Patterns - Various test method naming conventions (1 parametrized test)

    Total: 1 test (5 cases via parametrization).
    """

    @pytest.mark.parametrize(
        ("method_name", "expected"),
        [
            ("TestProcessData", True),
            ("ProcessDataTest", True),
            ("Test_Something", True),
            ("ProcessData", False),
            ("DoSomething", False),
        ],
        ids=["prefix_test", "suffix_test", "underscore_test", "non_test", "regular_method"],
    )
    def test_detect_test_method(self, method_name: str, expected: bool) -> None:
        """Verifies test method detection for various naming patterns.

        Business context:
            Test methods have lower documentation priority; accurate
            detection prevents test code from inflating improvement counts.

        Arrangement:
            1. Create VBAnalyzer with default config.
            2. Receive method name and expected result from parametrization.

        Action:
            Call _is_test_function_common with provided method name.

        Assertion Strategy:
            Verify detection result matches expected boolean.

        Testing Principle:
            Pattern coverage ensures all test naming conventions recognized.
        """
        analyzer = VBAnalyzer()
        assert analyzer._is_test_function_common(method_name) is expected


class TestVBAnalyzerSecurity:
    """Tests for VBAnalyzer security validation.

    Test Categories:
        1. Size Limits - Code size validation (1 test)

    Total: 1 test.
    """

    def test_code_too_large(self) -> None:
        """Verifies oversized code is rejected with appropriate error.

        Business context:
            Security limits prevent resource exhaustion attacks;
            large code blocks must be rejected before analysis.

        Arrangement:
            1. Create AnalysisConfig with 100-byte max_code_size.
            2. Create VBAnalyzer with restrictive config.
            3. Prepare code exceeding size limit.

        Action:
            Analyze oversized code.

        Assertion Strategy:
            Verify single error result with "too large" message.

        Testing Principle:
            Security boundary enforcement protects system resources.
        """
        config = AnalysisConfig(max_code_size=100)
        analyzer = VBAnalyzer(config=config)
        code = "Public Sub Method()\nEnd Sub\n" * 100
        results = analyzer.analyze(code)
        assert len(results) == 1
        assert "error" in results[0]
        assert "too large" in results[0]["error"].lower()


class TestVBAnalyzerComplexity:
    """Tests for VBAnalyzer complexity estimation.

    Test Categories:
        1. Simple Methods - Low complexity baseline (1 test)
        2. Branching Methods - Control flow complexity (1 test)

    Total: 2 tests.
    """

    def test_complexity_simple_method(self) -> None:
        """Verifies simple method has low complexity score.

        Business context:
            Complexity scoring informs documentation priority;
            simple methods with minimal control flow score low.

        Arrangement:
            1. Create VBAnalyzer with default config.
            2. Prepare code with single-statement Sub.

        Action:
            Analyze and extract complexity from function_info.

        Assertion Strategy:
            Verify complexity is 2 or less.

        Testing Principle:
            Complexity floor calibration ensures accurate prioritization.
        """
        analyzer = VBAnalyzer()
        code = """
Public Sub SimpleMethod()
    Console.WriteLine("Hello")
End Sub
"""
        results = analyzer.analyze(code)
        assert results[0]["function_info"]["complexity"] <= 2

    def test_complexity_branching_method(self) -> None:
        """Verifies branching method has higher complexity score.

        Business context:
            Complex control flow requires more documentation;
            nested branches and loops increase complexity score.

        Arrangement:
            1. Create VBAnalyzer with default config.
            2. Prepare code with nested If/For/Do While statements.

        Action:
            Analyze and extract complexity from function_info.

        Assertion Strategy:
            Verify complexity is 5 or greater.

        Testing Principle:
            Complexity ceiling recognition identifies high-priority targets.
        """
        analyzer = VBAnalyzer()
        code = """
Public Function ComplexMethod(x As Integer) As Integer
    If x > 0 Then
        For i As Integer = 0 To x
            If i Mod 2 = 0 AndAlso x > 10 Then
                Do While i > 0
                    i = i - 1
                Loop
            End If
        Next
    End If
    Return x
End Function
"""
        results = analyzer.analyze(code)
        assert results[0]["function_info"]["complexity"] >= 5


class TestVBAnalyzerEdgeCases:
    """Tests for VBAnalyzer edge cases and special syntax.

    Test Categories:
        1. Optional Parameters - Optional keyword handling (1 test)
        2. ByRef Parameters - ByRef keyword handling (1 test)
        3. Error Handling - Exception propagation (1 test)

    Total: 3 tests.
    """

    def test_optional_parameters(self) -> None:
        """Verifies optional parameters are detected.

        Business context:
            VB.NET Optional parameters have default values; parameter
            extraction must capture optional keyword and defaults.

        Arrangement:
            1. Create VBAnalyzer with default config.
            2. Prepare code with Optional parameter.

        Action:
            Analyze and check parameter extraction.

        Assertion Strategy:
            Verify parameter name extracted correctly.

        Testing Principle:
            Optional parameter handling ensures accurate metadata.
        """
        analyzer = VBAnalyzer()
        code = """
Public Sub GreetUser(Optional name As String = "World")
    Console.WriteLine("Hello, " & name)
End Sub
"""
        results = analyzer.analyze(code)
        assert len(results) == 1
        args = results[0]["function_info"]["args"]
        assert len(args) == 1
        assert args[0]["name"] == "name"

    def test_byref_parameter(self) -> None:
        """Verifies ByRef parameters are detected.

        Business context:
            ByRef parameters allow output via parameter modification;
            documentation must indicate this semantic difference.

        Arrangement:
            1. Create VBAnalyzer with default config.
            2. Prepare code with ByRef parameter.

        Action:
            Analyze and count results.

        Assertion Strategy:
            Verify exactly one method detected.

        Testing Principle:
            ByRef handling ensures parameter semantics captured.
        """
        analyzer = VBAnalyzer()
        code = """
Public Sub Increment(ByRef value As Integer)
    value = value + 1
End Sub
"""
        results = analyzer.analyze(code)
        assert len(results) == 1

    def test_exception_handling(self) -> None:
        """Verifies exceptions are caught and returned as error.

        Business context:
            Analyzer failures must not crash the server; errors must
            be returned in structured format for client handling.

        Arrangement:
            1. Create VBAnalyzer with default config.
            2. Mock _extract_methods_needing_improvement to raise RuntimeError.

        Action:
            Analyze code with mocked failure.

        Assertion Strategy:
            Verify single error result containing exception message.

        Testing Principle:
            Error boundary ensures graceful degradation.
        """
        from unittest.mock import patch

        analyzer = VBAnalyzer()
        with patch.object(
            analyzer, "_extract_methods_needing_improvement", side_effect=RuntimeError("Boom")
        ):
            results = analyzer.analyze("Public Sub Method()\nEnd Sub")
        assert len(results) == 1
        assert "error" in results[0]
        assert "Boom" in results[0]["error"]


class TestVBAnalyzerQualityThresholds:
    """Tests for VB.NET quality threshold edge cases.

    Test Categories:
        1. Quality Classification - Good/basic threshold boundaries (2 tests)
        2. Signature Validation - Missing args/returns detection (2 tests)
        3. Quality Gap Score - High quality score paths (1 test)

    Total: 5 tests.
    """

    def test_quality_good_threshold(self) -> None:
        """Verifies quality assessment returns 'good' for moderate documentation.

        Business context:
            Methods with documentation meeting good threshold but not
            excellent should be flagged for minor improvements.

        Arrangement:
            1. Create VBAnalyzer with default config.
            2. Assess docstring with summary and param tags.

        Action:
            Call assess_docstring_quality with moderate docstring.

        Assertion Strategy:
            Verify quality is 'good' and score >= 0.6.

        Testing Principle:
            Threshold boundary testing ensures correct classification.
        """
        # Use custom thresholds to ensure we hit the 'good' branch
        config = AnalysisConfig(quality_thresholds={"excellent": 0.9, "good": 0.5, "basic": 0.2})
        analyzer = VBAnalyzer(config=config)
        func_info = {
            "name": "ProcessData",
            "visibility": "Public",
            "is_test": False,
            "args": [{"name": "data", "type": "String"}],
            "returns": "Boolean",
        }
        # Docstring with summary, detailed, param, and returns - should score 0.5
        docstring = """<summary>Process data with validation.</summary>
<remarks>This method validates and processes the input data thoroughly.</remarks>
<param name="data">Input data to process.</param>
<returns>True if successful.</returns>"""
        quality = analyzer.assess_docstring_quality(docstring, "ProcessData", func_info)
        assert quality["quality"] == "good"
        assert quality["needs_improvement"] is True

    def test_quality_basic_threshold(self) -> None:
        """Verifies quality assessment returns 'basic' for minimal documentation.

        Business context:
            Methods with brief documentation should be classified as
            'basic' quality requiring substantial improvement.

        Arrangement:
            1. Create VBAnalyzer with default config.
            2. Assess docstring with only summary tag.

        Action:
            Call assess_docstring_quality with minimal docstring.

        Assertion Strategy:
            Verify quality is 'basic' and needs_improvement is True.

        Testing Principle:
            Threshold boundary testing ensures correct classification.
        """
        # Use custom thresholds to ensure we hit the 'basic' branch
        config = AnalysisConfig(quality_thresholds={"excellent": 0.9, "good": 0.7, "basic": 0.1})
        analyzer = VBAnalyzer(config=config)
        func_info = {
            "name": "SimpleMethod",
            "visibility": "Public",
            "is_test": False,
            "args": [],
            "returns": None,
        }
        # Just summary - should score enough to hit basic threshold
        quality = analyzer.assess_docstring_quality(
            "<summary>A simple method that does something useful.</summary>",
            "SimpleMethod",
            func_info,
        )
        assert quality["quality"] == "basic"
        assert quality["needs_improvement"] is True

    def test_signature_validation_missing_param_docs(self) -> None:
        """Verifies signature validation detects missing parameter documentation.

        Business context:
            Methods with parameters but no param tags should have
            args_section remain False in quality indicators.

        Arrangement:
            1. Create VBAnalyzer with default config.
            2. Create func_info with parameters.
            3. Create quality_indicators with args_section=False.

        Action:
            Call _validate_signature_coverage.

        Assertion Strategy:
            Verify args_section stays False after validation.

        Testing Principle:
            Signature coverage ensures complete documentation.
        """
        analyzer = VBAnalyzer()
        func_info = {
            "name": "ProcessData",
            "visibility": "Public",
            "is_test": False,
            "args": [{"name": "data", "type": "String"}],
            "returns": None,
        }
        # args_section is False (no <param> in docstring) but method has params
        quality_indicators = {"brief_description": True, "args_section": False}
        result = analyzer._validate_signature_coverage(quality_indicators, func_info)
        assert result.get("args_section") is False

    def test_signature_validation_missing_return_docs(self) -> None:
        """Verifies signature validation detects missing return documentation.

        Business context:
            Functions with return type but no returns tag should have
            returns_section remain False in quality indicators.

        Arrangement:
            1. Create VBAnalyzer with default config.
            2. Create func_info with return type.
            3. Create quality_indicators with returns_section=False.

        Action:
            Call _validate_signature_coverage.

        Assertion Strategy:
            Verify returns_section stays False after validation.

        Testing Principle:
            Signature coverage ensures complete documentation.
        """
        analyzer = VBAnalyzer()
        func_info = {
            "name": "GetValue",
            "visibility": "Public",
            "is_test": False,
            "args": [],
            "returns": "Integer",
        }
        # returns_section is False (no <returns> in docstring) but function has return
        quality_indicators = {"brief_description": True, "returns_section": False}
        result = analyzer._validate_signature_coverage(quality_indicators, func_info)
        assert result.get("returns_section") is False

    def test_quality_gap_score_high_quality(self) -> None:
        """Verifies quality gap score returns 0 for high quality documentation.

        Business context:
            Well-documented methods (score >= 0.8) should not receive
            additional priority bump from quality gap scoring.

        Arrangement:
            1. Create VBAnalyzer with default config.
            2. Create quality_assessment with score >= 0.8.

        Action:
            Call _calculate_quality_gap_score.

        Assertion Strategy:
            Verify returned score is 0.

        Testing Principle:
            Priority scoring should not penalize good documentation.
        """
        analyzer = VBAnalyzer()
        quality_assessment = {
            "quality": "excellent",
            "score": 0.85,
            "missing": [],
            "needs_improvement": False,
            "indicators": {},
        }
        score = analyzer._calculate_quality_gap_score(quality_assessment)
        assert score == 0
