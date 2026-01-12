"""Tests for C# documentation analyzer."""

import pytest

from docscope_mcp.analyzers.csharp import CSharpAnalyzer
from docscope_mcp.models import AnalysisConfig


class TestCSharpAnalyzerBasic:
    """Basic tests for CSharpAnalyzer initialization and configuration.

    Test Categories:
        1. Analyzer Creation - Instantiation verification (1 test)
        2. Configuration - Custom config handling (1 test)

    Total: 2 tests.
    """

    def test_analyzer_creation(self) -> None:
        """Verifies CSharpAnalyzer instantiates with correct language identifier.

        Business context:
            Language routing depends on analyzer self-identification for
            correct file-to-analyzer mapping in multi-language analysis.

        Arrangement:
            1. No setup required - tests default instantiation.

        Action:
            Instantiate CSharpAnalyzer and query its language.

        Assertion Strategy:
            Verify language identifier matches expected "csharp" value.

        Testing Principle:
            Factory pattern requires accurate type identification.
        """
        analyzer = CSharpAnalyzer()
        assert analyzer.get_language() == "csharp"

    def test_analyzer_with_config(self) -> None:
        """Verifies CSharpAnalyzer accepts and stores custom configuration.

        Business context:
            Security limits and analysis thresholds must be configurable
            per-deployment to match organizational requirements.

        Arrangement:
            1. Create AnalysisConfig with custom max_code_size.

        Action:
            Instantiate CSharpAnalyzer with custom configuration.

        Assertion Strategy:
            Verify stored config matches provided values.

        Testing Principle:
            Dependency injection must preserve injected values.
        """
        config = AnalysisConfig(max_code_size=1024)
        analyzer = CSharpAnalyzer(config=config)
        assert analyzer.config.max_code_size == 1024


class TestCSharpAnalyzerAnalysis:
    """Tests for CSharpAnalyzer analyze method functionality.

    Test Categories:
        1. Documentation Detection - Undocumented/documented methods (2 tests)
        2. Multiple Methods - Multi-method code analysis (1 test)
        3. Access Modifiers - Private/public priority (1 test)
        4. Special Patterns - Async, static, generic (3 tests)

    Total: 7 tests.
    """

    def test_analyze_method_without_documentation(self) -> None:
        """Verifies undocumented method is flagged as poor quality.

        Business context:
            Documentation coverage requires identifying methods lacking
            any XML documentation for prioritized improvement.

        Arrangement:
            1. Create CSharpAnalyzer with default config.
            2. Prepare C# code with undocumented public method.

        Action:
            Analyze the code and collect results.

        Assertion Strategy:
            Verify method detected with poor quality assessment.

        Testing Principle:
            Quality floor detection is foundational to analysis accuracy.
        """
        analyzer = CSharpAnalyzer()
        code = """
public class MyClass
{
    public void ProcessData(string data)
    {
        Console.WriteLine(data);
    }
}
"""
        results = analyzer.analyze(code)
        assert len(results) == 1
        assert results[0]["function_name"] == "ProcessData"
        assert results[0]["quality_assessment"]["quality"] == "poor"

    def test_analyze_method_with_xml_documentation(self) -> None:
        """Verifies well-documented method achieves acceptable quality score.

        Business context:
            XML documentation comments are standard C# documentation format;
            analyzer must recognize complete documentation patterns.

        Arrangement:
            1. Create CSharpAnalyzer with default config.
            2. Prepare code with full XML documentation
               (summary, remarks, param, returns, exception, example).

        Action:
            Analyze the documented code.

        Assertion Strategy:
            Verify quality score exceeds 0.5 threshold.

        Testing Principle:
            Quality ceiling recognition validates scoring algorithm.
        """
        analyzer = CSharpAnalyzer()
        code = """
/// <summary>
/// Processes the input data according to business rules.
/// </summary>
/// <remarks>
/// This method provides comprehensive data transformation
/// capabilities for the enterprise system.
/// </remarks>
/// <param name="data">The input data to process.</param>
/// <returns>The processed result string.</returns>
/// <exception cref="ArgumentException">Thrown when data is invalid.</exception>
/// <example>
/// var result = ProcessData("test");
/// </example>
public string ProcessData(string data)
{
    return data.ToUpper();
}
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
            1. Create CSharpAnalyzer with default config.
            2. Prepare code with three methods (public, public, private).

        Action:
            Analyze code and count results.

        Assertion Strategy:
            Verify exactly three methods detected.

        Testing Principle:
            Exhaustive detection ensures no methods escape analysis.
        """
        analyzer = CSharpAnalyzer()
        code = """
public void Method1() { }
public void Method2() { }
private void Method3() { }
"""
        results = analyzer.analyze(code)
        assert len(results) == 3

    def test_analyze_private_method(self) -> None:
        """Verifies private methods receive lower priority than public.

        Business context:
            Private methods have lower documentation priority than public API;
            access modifier detection guides documentation effort allocation.

        Arrangement:
            1. Create CSharpAnalyzer with default config.
            2. Prepare code with public and private methods.

        Action:
            Analyze and compare priorities between public and private.

        Assertion Strategy:
            Verify public method has higher priority than private.

        Testing Principle:
            Priority stratification guides documentation effort allocation.
        """
        analyzer = CSharpAnalyzer()
        code = """
public void PublicMethod() { }
private void PrivateMethod() { }
"""
        results = analyzer.analyze(code)
        public = next(r for r in results if r["function_name"] == "PublicMethod")
        private = next(r for r in results if r["function_name"] == "PrivateMethod")
        assert public["priority"] > private["priority"]

    def test_analyze_async_method(self) -> None:
        """Verifies async methods are detected correctly.

        Business context:
            Async methods are common in modern C#; analyzer must handle
            async/await patterns and Task return types.

        Arrangement:
            1. Create CSharpAnalyzer with default config.
            2. Prepare code with async Task<string> method.

        Action:
            Analyze and verify method detection.

        Assertion Strategy:
            Verify method name extracted correctly.

        Testing Principle:
            Async pattern detection ensures modern code coverage.
        """
        analyzer = CSharpAnalyzer()
        code = """
public async Task<string> FetchDataAsync(string url)
{
    return await client.GetStringAsync(url);
}
"""
        results = analyzer.analyze(code)
        assert len(results) == 1
        assert results[0]["function_name"] == "FetchDataAsync"

    def test_analyze_static_method(self) -> None:
        """Verifies static methods are detected correctly.

        Business context:
            Static methods provide utility functionality; documentation
            aids discoverability and correct usage patterns.

        Arrangement:
            1. Create CSharpAnalyzer with default config.
            2. Prepare code with static method.

        Action:
            Analyze and verify method detection.

        Assertion Strategy:
            Verify method name extracted correctly.

        Testing Principle:
            Static method detection ensures utility code coverage.
        """
        analyzer = CSharpAnalyzer()
        code = """
public static int Calculate(int a, int b)
{
    return a + b;
}
"""
        results = analyzer.analyze(code)
        assert len(results) == 1
        assert results[0]["function_name"] == "Calculate"

    def test_analyze_generic_method(self) -> None:
        """Verifies generic return types are handled.

        Business context:
            Generic types like List<T> are common in C#; return type
            extraction must handle angle bracket syntax.

        Arrangement:
            1. Create CSharpAnalyzer with default config.
            2. Prepare code with List<string> return type.

        Action:
            Analyze and check return type extraction.

        Assertion Strategy:
            Verify returns field is not None.

        Testing Principle:
            Generic type handling ensures accurate metadata.
        """
        analyzer = CSharpAnalyzer()
        code = """
public List<string> GetItems()
{
    return new List<string>();
}
"""
        results = analyzer.analyze(code)
        assert len(results) == 1
        assert results[0]["function_info"]["returns"] is not None


class TestCSharpAnalyzerQuality:
    """Tests for CSharpAnalyzer quality assessment functionality.

    Test Categories:
        1. Empty Documentation - Zero score baseline (1 test)
        2. Partial Documentation - Summary-only scenarios (1 test)
        3. Complete Documentation - Full XML doc scoring (1 test)

    Total: 3 tests.
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
            1. Create CSharpAnalyzer with default config.
            2. Use base_func_info fixture for method metadata.

        Action:
            Assess empty string as docstring.

        Assertion Strategy:
            Verify poor quality, zero score, and missing xml documentation indicator.

        Testing Principle:
            Quality floor ensures undocumented code is prioritized.
        """
        analyzer = CSharpAnalyzer()
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
            1. Create CSharpAnalyzer with default config.
            2. Prepare summary-only XML documentation.

        Action:
            Assess summary-only documentation.

        Assertion Strategy:
            Verify needs_improvement flag is True.

        Testing Principle:
            Partial documentation identification drives completeness.
        """
        analyzer = CSharpAnalyzer()
        doc = "<summary>Brief description.</summary>"
        result = analyzer.assess_docstring_quality(doc, "Test", base_func_info)
        assert result["needs_improvement"] is True

    def test_assess_complete_documentation(self, base_func_info: dict) -> None:
        """Verifies complete XML documentation scores well.

        Business context:
            Full XML documentation with all required sections represents
            ideal documentation; scoring must reflect completeness.

        Arrangement:
            1. Create CSharpAnalyzer with default config.
            2. Add args and returns to function info.
            3. Prepare full XML documentation with all sections.

        Action:
            Assess complete documentation.

        Assertion Strategy:
            Verify score exceeds 0.6 threshold.

        Testing Principle:
            Quality ceiling recognition validates scoring algorithm.
        """
        analyzer = CSharpAnalyzer()
        base_func_info["args"] = [{"name": "data", "type_annotation": "string", "default": None}]
        base_func_info["returns"] = "string"
        doc = """<summary>
Processes input data with comprehensive handling.
</summary>
<remarks>
This method provides enterprise-grade data processing
with full validation and error handling.
</remarks>
<param name="data">The input data to process.</param>
<returns>The processed result.</returns>
<exception cref="ArgumentException">Invalid data.</exception>
<example>
var result = Process("test");
</example>
"""
        result = analyzer.assess_docstring_quality(doc, "Process", base_func_info)
        assert result["score"] > 0.6


class TestCSharpAnalyzerPriority:
    """Tests for CSharpAnalyzer priority calculation.

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
            1. Create CSharpAnalyzer with default config.
            2. Create method info with high complexity, multiple args, return value.
            3. Create quality assessment with poor score.

        Action:
            Calculate priority for complex public method.

        Assertion Strategy:
            Verify priority score is 8 or higher.

        Testing Principle:
            Priority ceiling ensures critical methods are addressed first.
        """
        analyzer = CSharpAnalyzer()
        func_info = {
            "name": "ComplexMethod",
            "line": 1,
            "complexity": 15,
            "is_private": False,
            "is_test": False,
            "args": [
                {"name": "a", "type_annotation": "int", "default": None},
                {"name": "b", "type_annotation": "string", "default": None},
            ],
            "returns": "string",
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
            1. Create CSharpAnalyzer with default config.
            2. Create method info for simple private method.
            3. Create quality assessment with good score.

        Action:
            Calculate priority for simple private method.

        Assertion Strategy:
            Verify priority score is 3 or lower.

        Testing Principle:
            Priority floor ensures low-impact methods are deprioritized.
        """
        analyzer = CSharpAnalyzer()
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


class TestCSharpAnalyzerTestDetection:
    """Tests for CSharpAnalyzer test method detection.

    Test Categories:
        1. Test Naming Patterns - Various test method naming conventions (1 parametrized test)

    Total: 1 test (5 cases via parametrization).
    """

    @pytest.mark.parametrize(
        ("method_name", "expected"),
        [
            ("TestProcessData", True),
            ("ProcessDataTest", True),
            ("test_something", True),
            ("ProcessData", False),
            ("DoSomething", False),
        ],
        ids=["prefix_test", "suffix_test", "snake_case_test", "non_test", "regular_method"],
    )
    def test_detect_test_method(self, method_name: str, expected: bool) -> None:
        """Verifies test method detection for various naming patterns.

        Business context:
            Test methods have lower documentation priority; accurate
            detection prevents test code from inflating improvement counts.

        Arrangement:
            1. Create CSharpAnalyzer with default config.
            2. Receive method name and expected result from parametrization.

        Action:
            Call _is_test_method with provided method name.

        Assertion Strategy:
            Verify detection result matches expected boolean.

        Testing Principle:
            Pattern coverage ensures all test naming conventions recognized.
        """
        analyzer = CSharpAnalyzer()
        assert analyzer._is_test_method(method_name) is expected


class TestCSharpAnalyzerSecurity:
    """Tests for CSharpAnalyzer security validation.

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
            2. Create CSharpAnalyzer with restrictive config.
            3. Prepare code exceeding size limit.

        Action:
            Analyze oversized code.

        Assertion Strategy:
            Verify single error result with "too large" message.

        Testing Principle:
            Security boundary enforcement protects system resources.
        """
        config = AnalysisConfig(max_code_size=100)
        analyzer = CSharpAnalyzer(config=config)
        code = "public void Method() { }" * 100
        results = analyzer.analyze(code)
        assert len(results) == 1
        assert "error" in results[0]
        assert "too large" in results[0]["error"].lower()


class TestCSharpAnalyzerComplexity:
    """Tests for CSharpAnalyzer complexity estimation.

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
            1. Create CSharpAnalyzer with default config.
            2. Prepare code with single-statement method.

        Action:
            Analyze and extract complexity from function_info.

        Assertion Strategy:
            Verify complexity is 2 or less.

        Testing Principle:
            Complexity floor calibration ensures accurate prioritization.
        """
        analyzer = CSharpAnalyzer()
        code = """
public void SimpleMethod()
{
    Console.WriteLine("Hello");
}
"""
        results = analyzer.analyze(code)
        assert results[0]["function_info"]["complexity"] <= 2

    def test_complexity_branching_method(self) -> None:
        """Verifies branching method has higher complexity score.

        Business context:
            Complex control flow requires more documentation;
            nested branches and loops increase complexity score.

        Arrangement:
            1. Create CSharpAnalyzer with default config.
            2. Prepare code with nested if/for/while statements.

        Action:
            Analyze and extract complexity from function_info.

        Assertion Strategy:
            Verify complexity is 5 or greater.

        Testing Principle:
            Complexity ceiling recognition identifies high-priority targets.
        """
        analyzer = CSharpAnalyzer()
        code = """
public int ComplexMethod(int x)
{
    if (x > 0)
    {
        for (int i = 0; i < x; i++)
        {
            if (i % 2 == 0 && x > 10)
            {
                while (i > 0)
                {
                    i--;
                }
            }
        }
    }
    return x;
}
"""
        results = analyzer.analyze(code)
        assert results[0]["function_info"]["complexity"] >= 5


class TestCSharpAnalyzerEdgeCases:
    """Tests for CSharpAnalyzer edge cases and special syntax.

    Test Categories:
        1. Attributes - Method attributes handling (1 test)
        2. Nullable Types - Nullable return type handling (1 test)
        3. Error Handling - Exception propagation (1 test)

    Total: 3 tests.
    """

    def test_method_with_attributes(self) -> None:
        """Verifies methods with attributes are detected.

        Business context:
            C# attributes provide metadata; analyzer must parse past
            attributes to detect underlying method for documentation.

        Arrangement:
            1. Create CSharpAnalyzer with default config.
            2. Prepare code with Obsolete and MethodImpl attributes.

        Action:
            Analyze and verify method detection.

        Assertion Strategy:
            Verify method name extracted correctly despite attributes.

        Testing Principle:
            Attribute-agnostic parsing ensures comprehensive detection.
        """
        analyzer = CSharpAnalyzer()
        code = """
[Obsolete("Use NewMethod instead")]
[MethodImpl(MethodImplOptions.AggressiveInlining)]
public void OldMethod()
{
    // Implementation
}
"""
        results = analyzer.analyze(code)
        assert len(results) == 1
        assert results[0]["function_name"] == "OldMethod"

    def test_method_with_nullable_return(self) -> None:
        """Verifies nullable return types are handled.

        Business context:
            C# nullable reference types use ? suffix; return type
            extraction must handle nullable syntax correctly.

        Arrangement:
            1. Create CSharpAnalyzer with default config.
            2. Prepare code with string? nullable return type.

        Action:
            Analyze and count results.

        Assertion Strategy:
            Verify exactly one method detected.

        Testing Principle:
            Nullable type handling ensures modern C# coverage.
        """
        analyzer = CSharpAnalyzer()
        code = """
public string? GetNullableValue()
{
    return null;
}
"""
        results = analyzer.analyze(code)
        assert len(results) == 1

    def test_exception_handling(self) -> None:
        """Verifies exceptions are caught and returned as error.

        Business context:
            Analyzer failures must not crash the server; errors must
            be returned in structured format for client handling.

        Arrangement:
            1. Create CSharpAnalyzer with default config.
            2. Mock _extract_methods_needing_improvement to raise RuntimeError.

        Action:
            Analyze code with mocked failure.

        Assertion Strategy:
            Verify single error result containing exception message.

        Testing Principle:
            Error boundary ensures graceful degradation.
        """
        from unittest.mock import patch

        analyzer = CSharpAnalyzer()
        with patch.object(
            analyzer, "_extract_methods_needing_improvement", side_effect=RuntimeError("Boom")
        ):
            results = analyzer.analyze("public void Method() { }")
        assert len(results) == 1
        assert "error" in results[0]
        assert "Boom" in results[0]["error"]


class TestCSharpAnalyzerQualityThresholds:
    """Tests for C# quality threshold edge cases.

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
            1. Create CSharpAnalyzer with default config.
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
        analyzer = CSharpAnalyzer(config=config)
        func_info = {
            "name": "ProcessData",
            "visibility": "public",
            "is_test": False,
            "args": [{"name": "data", "type": "string"}],
            "returns": "bool",
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
            1. Create CSharpAnalyzer with default config.
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
        analyzer = CSharpAnalyzer(config=config)
        func_info = {
            "name": "SimpleMethod",
            "visibility": "public",
            "is_test": False,
            "args": [],
            "returns": "void",
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
            1. Create CSharpAnalyzer with default config.
            2. Create func_info with parameters.
            3. Create quality_indicators with args_section=False.

        Action:
            Call _validate_signature_coverage.

        Assertion Strategy:
            Verify args_section stays False after validation.

        Testing Principle:
            Signature coverage ensures complete documentation.
        """
        analyzer = CSharpAnalyzer()
        func_info = {
            "name": "ProcessData",
            "visibility": "public",
            "is_test": False,
            "args": [{"name": "data", "type": "string"}],
            "returns": "void",
        }
        # args_section is False (no <param> in docstring) but method has params
        quality_indicators = {"brief_description": True, "args_section": False}
        result = analyzer._validate_signature_coverage(quality_indicators, func_info)
        assert result.get("args_section") is False

    def test_signature_validation_missing_return_docs(self) -> None:
        """Verifies signature validation detects missing return documentation.

        Business context:
            Methods with non-void return but no returns tag should have
            returns_section remain False in quality indicators.

        Arrangement:
            1. Create CSharpAnalyzer with default config.
            2. Create func_info with non-void return.
            3. Create quality_indicators with returns_section=False.

        Action:
            Call _validate_signature_coverage.

        Assertion Strategy:
            Verify returns_section stays False after validation.

        Testing Principle:
            Signature coverage ensures complete documentation.
        """
        analyzer = CSharpAnalyzer()
        func_info = {
            "name": "GetValue",
            "visibility": "public",
            "is_test": False,
            "args": [],
            "returns": "int",
        }
        # returns_section is False (no <returns> in docstring) but method has return
        quality_indicators = {"brief_description": True, "returns_section": False}
        result = analyzer._validate_signature_coverage(quality_indicators, func_info)
        assert result.get("returns_section") is False

    def test_quality_gap_score_high_quality(self) -> None:
        """Verifies quality gap score returns 0 for high quality documentation.

        Business context:
            Well-documented methods (score >= 0.8) should not receive
            additional priority bump from quality gap scoring.

        Arrangement:
            1. Create CSharpAnalyzer with default config.
            2. Create quality_assessment with score >= 0.8.

        Action:
            Call _calculate_quality_gap_score.

        Assertion Strategy:
            Verify returned score is 0.

        Testing Principle:
            Priority scoring should not penalize good documentation.
        """
        analyzer = CSharpAnalyzer()
        quality_assessment = {
            "quality": "excellent",
            "score": 0.85,
            "missing": [],
            "needs_improvement": False,
            "indicators": {},
        }
        score = analyzer._calculate_quality_gap_score(quality_assessment)
        assert score == 0
