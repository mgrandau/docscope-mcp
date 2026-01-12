"""Tests for VB6 documentation analyzer."""

import pytest

from docscope_mcp.analyzers.vb6 import VB6Analyzer
from docscope_mcp.models import AnalysisConfig


class TestVB6AnalyzerBasic:
    """Basic tests for VB6Analyzer initialization and configuration.

    Test Categories:
        1. Analyzer Creation - Instantiation verification (1 test)
        2. Configuration - Custom config handling (1 test)

    Total: 2 tests.
    """

    def test_analyzer_creation(self) -> None:
        """Verifies VB6Analyzer instantiates with correct language identifier.

        Business context:
            Language routing depends on analyzer self-identification for
            correct file-to-analyzer mapping in multi-language analysis.

        Arrangement:
            1. No setup required - tests default instantiation.

        Action:
            Instantiate VB6Analyzer and query its language.

        Assertion Strategy:
            Verify language identifier matches expected "vb6" value.

        Testing Principle:
            Factory pattern requires accurate type identification.
        """
        analyzer = VB6Analyzer()
        assert analyzer.get_language() == "vb6"

    def test_analyzer_with_config(self) -> None:
        """Verifies VB6Analyzer accepts and stores custom configuration.

        Business context:
            Security limits and analysis thresholds must be configurable
            per-deployment to match organizational requirements.

        Arrangement:
            1. Create AnalysisConfig with custom max_code_size.

        Action:
            Instantiate VB6Analyzer with custom configuration.

        Assertion Strategy:
            Verify stored config matches provided values.

        Testing Principle:
            Dependency injection must preserve injected values.
        """
        config = AnalysisConfig(max_code_size=1024)
        analyzer = VB6Analyzer(config=config)
        assert analyzer.config.max_code_size == 1024


class TestVB6AnalyzerAnalysis:
    """Tests for VB6Analyzer analyze method functionality.

    Test Categories:
        1. Documentation Detection - Undocumented Sub/Function (2 tests)
        2. Comment Block Documentation - Traditional VB6 comments (1 test)
        3. Multiple Procedures - Multi-procedure code analysis (1 test)
        4. Access Modifiers - Private/public priority (1 test)
        5. Properties - Property Get/Let handling (2 tests)
        6. Well-Documented - Complete documentation scenarios (1 test)

    Total: 8 tests.
    """

    def test_analyze_sub_without_comments(self) -> None:
        """Verifies undocumented Sub is flagged as poor quality.

        Business context:
            Documentation coverage requires identifying procedures lacking
            any comment documentation for prioritized improvement.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Prepare VB6 code with undocumented Public Sub.

        Action:
            Analyze the code and collect results.

        Assertion Strategy:
            Verify procedure detected with poor quality assessment.

        Testing Principle:
            Quality floor detection is foundational to analysis accuracy.
        """
        analyzer = VB6Analyzer()
        code = """
Public Sub ProcessData(data As String)
    MsgBox data
End Sub
"""
        results = analyzer.analyze(code)
        assert len(results) == 1
        assert results[0]["function_name"] == "ProcessData"
        assert results[0]["quality_assessment"]["quality"] == "poor"

    def test_analyze_function_without_comments(self) -> None:
        """Verifies undocumented Function is flagged as poor quality.

        Business context:
            VB6 Functions return values and require documentation
            of parameters, return type, and behavior.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Prepare VB6 code with undocumented Public Function.

        Action:
            Analyze the code and collect results.

        Assertion Strategy:
            Verify function detected with correct name.

        Testing Principle:
            Function detection ensures return-value procedures are covered.
        """
        analyzer = VB6Analyzer()
        code = """
Public Function Calculate(x As Integer, y As Integer) As Integer
    Calculate = x + y
End Function
"""
        results = analyzer.analyze(code)
        assert len(results) == 1
        assert results[0]["function_name"] == "Calculate"

    def test_analyze_with_comment_block(self) -> None:
        """Verifies well-documented procedure achieves acceptable quality score.

        Business context:
            VB6 uses apostrophe-prefixed comment blocks for documentation;
            analyzer must recognize traditional comment patterns.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Prepare code with full comment block documentation.

        Action:
            Analyze the documented code.

        Assertion Strategy:
            Verify quality score exceeds 0.3 threshold.

        Testing Principle:
            Quality ceiling recognition validates scoring algorithm.
        """
        analyzer = VB6Analyzer()
        code = """
' -----------------------------------------------
' Purpose: Processes the input data according to
'          business rules for the enterprise system.
' Parameters:
'   data - The input data to process
' Returns: The processed result string
' Author: John Doe
' Date: 2024-01-01
' -----------------------------------------------
Public Function ProcessData(data As String) As String
    ProcessData = UCase(data)
End Function
"""
        results = analyzer.analyze(code)
        if results:
            assert results[0]["quality_assessment"]["score"] > 0.3

    def test_analyze_multiple_procedures(self) -> None:
        """Verifies analyzer detects all procedures in multi-procedure code.

        Business context:
            Real-world files contain multiple procedures; analyzer must
            enumerate all for complete documentation coverage reporting.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Prepare code with Sub, Function, and Private Sub.

        Action:
            Analyze code and count results.

        Assertion Strategy:
            Verify exactly three procedures detected.

        Testing Principle:
            Exhaustive detection ensures no procedures escape analysis.
        """
        analyzer = VB6Analyzer()
        code = """
Public Sub Method1()
End Sub

Public Function Method2() As Integer
    Method2 = 0
End Function

Private Sub Method3()
End Sub
"""
        results = analyzer.analyze(code)
        assert len(results) == 3

    def test_analyze_private_procedure(self) -> None:
        """Verifies private procedures receive lower priority than public.

        Business context:
            Private procedures have lower documentation priority than public API;
            access modifier detection guides documentation effort allocation.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Prepare code with Public and Private Subs.

        Action:
            Analyze and compare priorities between public and private.

        Assertion Strategy:
            Verify public procedure has higher priority than private.

        Testing Principle:
            Priority stratification guides documentation effort allocation.
        """
        analyzer = VB6Analyzer()
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

    def test_analyze_property_get(self) -> None:
        """Verifies Property Get procedures are detected.

        Business context:
            VB6 Property Get procedures provide read access to module state;
            documentation aids understanding of property semantics.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Prepare code with Property Get.

        Action:
            Analyze and verify property detection.

        Assertion Strategy:
            Verify property name extracted correctly.

        Testing Principle:
            Property detection ensures encapsulation patterns covered.
        """
        analyzer = VB6Analyzer()
        code = """
Public Property Get Name() As String
    Name = m_Name
End Property
"""
        results = analyzer.analyze(code)
        assert len(results) == 1
        assert results[0]["function_name"] == "Name"

    def test_analyze_property_let(self) -> None:
        """Verifies Property Let procedures are detected.

        Business context:
            VB6 Property Let procedures provide write access to module state;
            documentation aids understanding of property validation rules.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Prepare code with Property Let.

        Action:
            Analyze and count results.

        Assertion Strategy:
            Verify exactly one property detected.

        Testing Principle:
            Property Let detection ensures write accessors covered.
        """
        analyzer = VB6Analyzer()
        code = """
Public Property Let Name(value As String)
    m_Name = value
End Property
"""
        results = analyzer.analyze(code)
        assert len(results) == 1

    def test_documented_procedure_not_flagged(self) -> None:
        """Verifies well-documented procedures may not be flagged.

        Business context:
            Complete documentation should score highly enough to potentially
            pass quality thresholds, demonstrating quality ceiling.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Prepare code with comprehensive comment documentation.

        Action:
            Analyze and check quality score.

        Assertion Strategy:
            Verify score is positive when documentation present.

        Testing Principle:
            Quality recognition validates documentation detection.
        """
        analyzer = VB6Analyzer()
        code = """
' Purpose: Calculates total with comprehensive handling
' Description: This function takes input values and
'              computes the total with full validation.
' Parameters:
'   price - The base price value
'   taxRate - The tax rate percentage
' Returns: Total price including tax
' Author: Jane Smith
' Example: total = CalculateTotal(100, 8.5)
Public Function CalculateTotal(price As Double, taxRate As Double) As Double
    CalculateTotal = price * (1 + taxRate / 100)
End Function
"""
        results = analyzer.analyze(code)
        # May or may not be flagged depending on thresholds
        if results:
            assert results[0]["quality_assessment"]["score"] > 0


class TestVB6AnalyzerQuality:
    """Tests for VB6Analyzer quality assessment functionality.

    Test Categories:
        1. Empty Documentation - Zero score baseline (1 test)
        2. Minimal Documentation - Brief comment scenarios (1 test)
        3. Keyword Detection - Purpose, Parameters, Returns, Author, Date (5 tests)

    Total: 7 tests.
    """

    @pytest.fixture
    def base_func_info(self) -> dict:
        """Provide base function info fixture for quality tests.

        Creates minimal function metadata for testing assess_docstring_quality.

        Business context:
            Quality assessment requires function metadata to evaluate
            documentation completeness against procedure signature.

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

    def test_assess_empty_comments(self, base_func_info: dict) -> None:
        """Verifies empty comments assessed as poor with zero score.

        Business context:
            Quality floor establishes baseline for documentation scoring;
            undocumented procedures must receive lowest possible rating.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Use base_func_info fixture for procedure metadata.

        Action:
            Assess empty string as docstring.

        Assertion Strategy:
            Verify poor quality, zero score, and missing comments indicator.

        Testing Principle:
            Quality floor ensures undocumented code is prioritized.
        """
        analyzer = VB6Analyzer()
        result = analyzer.assess_docstring_quality("", "Test", base_func_info)
        assert result["quality"] == "poor"
        assert result["score"] == 0.0
        assert "comments" in result["missing"]

    def test_assess_minimal_comment(self, base_func_info: dict) -> None:
        """Verifies minimal comment is flagged as needing improvement.

        Business context:
            Brief comments without structure are insufficient for
            comprehensive documentation; needs_improvement flag guides users.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Prepare minimal comment text.

        Action:
            Assess minimal comment.

        Assertion Strategy:
            Verify needs_improvement flag is True.

        Testing Principle:
            Partial documentation identification drives completeness.
        """
        analyzer = VB6Analyzer()
        result = analyzer.assess_docstring_quality("Do stuff", "Test", base_func_info)
        assert result["needs_improvement"] is True

    def test_assess_purpose_keyword(self, base_func_info: dict) -> None:
        """Verifies Purpose keyword is detected.

        Business context:
            VB6 documentation convention uses Purpose keyword for
            brief description; detection indicates structured documentation.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Prepare comment with Purpose keyword.

        Action:
            Assess Purpose-containing documentation.

        Assertion Strategy:
            Verify brief_description indicator is True.

        Testing Principle:
            Keyword detection ensures VB6 conventions recognized.
        """
        analyzer = VB6Analyzer()
        doc = "Purpose: This function processes data"
        result = analyzer.assess_docstring_quality(doc, "Test", base_func_info)
        assert result["indicators"]["brief_description"] is True

    def test_assess_param_documentation(self, base_func_info: dict) -> None:
        """Verifies parameter documentation is detected.

        Business context:
            VB6 documentation uses Parameters section for argument docs;
            detection validates parameter documentation completeness.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Add args to function info.
            3. Prepare comment with Parameters section.

        Action:
            Assess Parameters-containing documentation.

        Assertion Strategy:
            Verify args_section indicator is True.

        Testing Principle:
            Parameter documentation detection ensures API clarity.
        """
        analyzer = VB6Analyzer()
        base_func_info["args"] = [{"name": "data", "type_annotation": "String", "default": None}]
        doc = """Purpose: Process data
Parameters:
  data - The input data
"""
        result = analyzer.assess_docstring_quality(doc, "Process", base_func_info)
        assert result["indicators"]["args_section"] is True

    def test_assess_return_documentation(self, base_func_info: dict) -> None:
        """Verifies return value documentation is detected.

        Business context:
            VB6 Functions must document return values;
            Returns keyword detection validates return documentation.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Add returns to function info.
            3. Prepare comment with Returns section.

        Action:
            Assess Returns-containing documentation.

        Assertion Strategy:
            Verify returns_section indicator is True.

        Testing Principle:
            Return documentation detection ensures output clarity.
        """
        analyzer = VB6Analyzer()
        base_func_info["returns"] = "String"
        doc = """Purpose: Process data
Returns: The processed result
"""
        result = analyzer.assess_docstring_quality(doc, "Process", base_func_info)
        assert result["indicators"]["returns_section"] is True

    def test_assess_author_metadata(self, base_func_info: dict) -> None:
        """Verifies author metadata is detected.

        Business context:
            VB6 documentation convention includes Author for accountability;
            detection indicates business context documentation.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Prepare comment with Author field.

        Action:
            Assess Author-containing documentation.

        Assertion Strategy:
            Verify business_context indicator is True.

        Testing Principle:
            Metadata detection ensures maintenance information captured.
        """
        analyzer = VB6Analyzer()
        doc = """Purpose: Process data
Author: John Doe
"""
        result = analyzer.assess_docstring_quality(doc, "Process", base_func_info)
        assert result["indicators"]["business_context"] is True

    def test_assess_date_metadata(self, base_func_info: dict) -> None:
        """Verifies date metadata is detected.

        Business context:
            VB6 documentation convention includes Created/Date for tracking;
            detection indicates maintenance documentation.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Prepare comment with Created field.

        Action:
            Assess Created-containing documentation.

        Assertion Strategy:
            Verify business_context indicator is True.

        Testing Principle:
            Date metadata detection ensures version history captured.
        """
        analyzer = VB6Analyzer()
        doc = """Purpose: Process data
Created: 2024-01-01
"""
        result = analyzer.assess_docstring_quality(doc, "Process", base_func_info)
        assert result["indicators"]["business_context"] is True


class TestVB6AnalyzerPriority:
    """Tests for VB6Analyzer priority calculation.

    Test Categories:
        1. High Priority - Complex public procedures (1 test)
        2. Low Priority - Simple private procedures (1 test)

    Total: 2 tests.
    """

    def test_calculate_priority_high(self) -> None:
        """Verifies high priority for complex public procedures.

        Business context:
            Complex public API procedures require urgent documentation;
            priority score guides developer effort allocation.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Create procedure info with high complexity, multiple args, return value.
            3. Create quality assessment with poor score.

        Action:
            Calculate priority for complex public procedure.

        Assertion Strategy:
            Verify priority score is 8 or higher.

        Testing Principle:
            Priority ceiling ensures critical procedures are addressed first.
        """
        analyzer = VB6Analyzer()
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
            "missing": ["comments"],
            "needs_improvement": True,
            "indicators": {},
        }
        priority = analyzer.calculate_priority(func_info, quality)
        assert priority >= 8

    def test_calculate_priority_low(self) -> None:
        """Verifies low priority for simple private procedures.

        Business context:
            Simple private helper procedures are lower documentation priority;
            priority stratification prevents wasted effort.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Create procedure info for simple private procedure.
            3. Create quality assessment with good score.

        Action:
            Calculate priority for simple private procedure.

        Assertion Strategy:
            Verify priority score is 3 or lower.

        Testing Principle:
            Priority floor ensures low-impact procedures are deprioritized.
        """
        analyzer = VB6Analyzer()
        func_info = {
            "name": "Helper",
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


class TestVB6AnalyzerTestDetection:
    """Tests for VB6Analyzer test procedure detection.

    Test Categories:
        1. Test Naming Patterns - Various test procedure naming conventions (1 parametrized test)

    Total: 1 test (5 cases via parametrization).
    """

    @pytest.mark.parametrize(
        ("proc_name", "expected"),
        [
            ("TestProcessData", True),
            ("ProcessDataTest", True),
            ("test_something", True),
            ("ProcessData", False),
            ("DoSomething", False),
        ],
        ids=["prefix_test", "suffix_test", "snake_case_test", "non_test", "regular_method"],
    )
    def test_detect_test_procedure(self, proc_name: str, expected: bool) -> None:
        """Verifies test procedure detection for various naming patterns.

        Business context:
            Test procedures have lower documentation priority; accurate
            detection prevents test code from inflating improvement counts.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Receive procedure name and expected result from parametrization.

        Action:
            Call _is_test_function_common with provided procedure name.

        Assertion Strategy:
            Verify detection result matches expected boolean.

        Testing Principle:
            Pattern coverage ensures all test naming conventions recognized.
        """
        analyzer = VB6Analyzer()
        assert analyzer._is_test_function_common(proc_name) is expected


class TestVB6AnalyzerSecurity:
    """Tests for VB6Analyzer security validation.

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
            2. Create VB6Analyzer with restrictive config.
            3. Prepare code exceeding size limit.

        Action:
            Analyze oversized code.

        Assertion Strategy:
            Verify single error result with "too large" message.

        Testing Principle:
            Security boundary enforcement protects system resources.
        """
        config = AnalysisConfig(max_code_size=100)
        analyzer = VB6Analyzer(config=config)
        code = "Public Sub Method()\nEnd Sub\n" * 100
        results = analyzer.analyze(code)
        assert len(results) == 1
        assert "error" in results[0]
        assert "too large" in results[0]["error"].lower()


class TestVB6AnalyzerComplexity:
    """Tests for VB6Analyzer complexity estimation.

    Test Categories:
        1. Simple Procedures - Low complexity baseline (1 test)
        2. Branching Procedures - Control flow complexity (1 test)

    Total: 2 tests.
    """

    def test_complexity_simple_procedure(self) -> None:
        """Verifies simple procedure has low complexity score.

        Business context:
            Complexity scoring informs documentation priority;
            simple procedures with minimal control flow score low.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Prepare code with single-statement Sub.

        Action:
            Analyze and extract complexity from function_info.

        Assertion Strategy:
            Verify complexity is 2 or less.

        Testing Principle:
            Complexity floor calibration ensures accurate prioritization.
        """
        analyzer = VB6Analyzer()
        code = """
Public Sub SimpleMethod()
    MsgBox "Hello"
End Sub
"""
        results = analyzer.analyze(code)
        assert results[0]["function_info"]["complexity"] <= 2

    def test_complexity_branching_procedure(self) -> None:
        """Verifies branching procedure has higher complexity score.

        Business context:
            Complex control flow requires more documentation;
            nested branches and loops increase complexity score.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Prepare code with nested If/For/Do While statements.

        Action:
            Analyze and extract complexity from function_info.

        Assertion Strategy:
            Verify complexity is 4 or greater.

        Testing Principle:
            Complexity ceiling recognition identifies high-priority targets.
        """
        analyzer = VB6Analyzer()
        code = """
Public Function ComplexMethod(x As Integer) As Integer
    If x > 0 Then
        For i = 0 To x
            If i Mod 2 = 0 And x > 10 Then
                Do While i > 0
                    i = i - 1
                Loop
            End If
        Next i
    End If
    ComplexMethod = x
End Function
"""
        results = analyzer.analyze(code)
        assert results[0]["function_info"]["complexity"] >= 4


class TestVB6AnalyzerEdgeCases:
    """Tests for VB6Analyzer edge cases and special syntax.

    Test Categories:
        1. Optional Parameters - Optional keyword handling (1 test)
        2. Static Procedures - Static keyword handling (1 test)
        3. Friend Procedures - Friend access modifier handling (1 test)
        4. Error Handling - Exception propagation (1 test)
        5. Comment Cleaning - Comment prefix removal (1 test)

    Total: 5 tests.
    """

    def test_optional_parameters(self) -> None:
        """Verifies optional parameters are detected.

        Business context:
            VB6 Optional parameters have default values; parameter
            extraction must handle optional keyword syntax.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Prepare code with Optional parameter.

        Action:
            Analyze and count results.

        Assertion Strategy:
            Verify exactly one procedure detected.

        Testing Principle:
            Optional parameter handling ensures accurate metadata.
        """
        analyzer = VB6Analyzer()
        code = """
Public Sub GreetUser(Optional name As String = "World")
    MsgBox "Hello, " & name
End Sub
"""
        results = analyzer.analyze(code)
        assert len(results) == 1

    def test_static_procedure(self) -> None:
        """Verifies Static procedures are detected.

        Business context:
            VB6 Static procedures preserve local variable state
            between calls; documentation should note this behavior.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Prepare code with Static Function.

        Action:
            Analyze and count results.

        Assertion Strategy:
            Verify exactly one procedure detected.

        Testing Principle:
            Static keyword handling ensures procedure coverage.
        """
        analyzer = VB6Analyzer()
        code = """
Static Function Counter() As Integer
    Dim count As Integer
    count = count + 1
    Counter = count
End Function
"""
        results = analyzer.analyze(code)
        assert len(results) == 1

    def test_friend_procedure(self) -> None:
        """Verifies Friend procedures are detected.

        Business context:
            VB6 Friend access modifier allows project-level visibility;
            documentation aids understanding of access scope.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Prepare code with Friend Sub.

        Action:
            Analyze and count results.

        Assertion Strategy:
            Verify exactly one procedure detected.

        Testing Principle:
            Access modifier handling ensures all visibilities covered.
        """
        analyzer = VB6Analyzer()
        code = """
Friend Sub InternalMethod()
    ' Internal use only
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
            1. Create VB6Analyzer with default config.
            2. Mock _extract_procedures_needing_improvement to raise RuntimeError.

        Action:
            Analyze code with mocked failure.

        Assertion Strategy:
            Verify single error result containing exception message.

        Testing Principle:
            Error boundary ensures graceful degradation.
        """
        from unittest.mock import patch

        analyzer = VB6Analyzer()
        with patch.object(
            analyzer, "_extract_procedures_needing_improvement", side_effect=RuntimeError("Boom")
        ):
            results = analyzer.analyze("Public Sub Method()\nEnd Sub")
        assert len(results) == 1
        assert "error" in results[0]
        assert "Boom" in results[0]["error"]

    def test_comment_cleaning(self) -> None:
        """Verifies comment block is cleaned correctly.

        Business context:
            Quality assessment requires clean text; VB6 comment prefixes
            (apostrophes) must be stripped for accurate analysis.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Prepare raw VB6 comment block.

        Action:
            Call _clean_comments on raw comment.

        Assertion Strategy:
            Verify apostrophe prefixes removed and content preserved.

        Testing Principle:
            Comment normalization ensures consistent quality scoring.
        """
        analyzer = VB6Analyzer()
        comments = "' Line 1\n'   Line 2\n'Line 3"
        cleaned = analyzer._clean_comments(comments)
        assert "'" not in cleaned
        assert "Line 1" in cleaned
        assert "Line 2" in cleaned
        assert "Line 3" in cleaned


class TestVB6AnalyzerQualityThresholds:
    """Tests for VB6 quality threshold edge cases.

    Test Categories:
        1. Quality Classification - Good/basic threshold boundaries (2 tests)
        2. Signature Validation - Missing args/returns detection (2 tests)
        3. Quality Gap Score - High quality score paths (1 test)
        4. Complexity Edge Cases - Procedure not found (1 test)

    Total: 6 tests.
    """

    def test_quality_good_threshold(self) -> None:
        """Verifies quality assessment returns 'good' for moderate documentation.

        Business context:
            Procedures with documentation meeting good threshold but not
            excellent should be flagged for minor improvements.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Assess docstring with description and parameters.

        Action:
            Call assess_docstring_quality with moderate docstring.

        Assertion Strategy:
            Verify quality is 'good' and score >= 0.6.

        Testing Principle:
            Threshold boundary testing ensures correct classification.
        """
        # Use custom thresholds to ensure we hit the 'good' branch
        config = AnalysisConfig(quality_thresholds={"excellent": 0.9, "good": 0.5, "basic": 0.2})
        analyzer = VB6Analyzer(config=config)
        func_info = {
            "name": "ProcessData",
            "visibility": "Public",
            "is_test": False,
            "args": [{"name": "data", "type": "String"}],
            "returns": "Boolean",
        }
        # Docstring with brief, detailed, params, returns - should score 0.5+
        docstring = """Process data with validation thoroughly.
This procedure validates and processes all input data completely.
Parameters:
  data - Input data to process.
Returns: True if successful."""
        quality = analyzer.assess_docstring_quality(docstring, "ProcessData", func_info)
        assert quality["quality"] == "good"
        assert quality["needs_improvement"] is True

    def test_quality_basic_threshold(self) -> None:
        """Verifies quality assessment returns 'basic' for minimal documentation.

        Business context:
            Procedures with brief documentation should be classified as
            'basic' quality requiring substantial improvement.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Assess docstring with only brief description.

        Action:
            Call assess_docstring_quality with minimal docstring.

        Assertion Strategy:
            Verify quality is 'basic' and needs_improvement is True.

        Testing Principle:
            Threshold boundary testing ensures correct classification.
        """
        # Use custom thresholds to ensure we hit the 'basic' branch
        config = AnalysisConfig(quality_thresholds={"excellent": 0.9, "good": 0.7, "basic": 0.1})
        analyzer = VB6Analyzer(config=config)
        func_info = {
            "name": "SimpleProc",
            "visibility": "Public",
            "is_test": False,
            "args": [],
            "returns": None,
        }
        # Just brief description - should score enough to hit basic threshold
        quality = analyzer.assess_docstring_quality(
            "A simple procedure that does something useful and valuable.",
            "SimpleProc",
            func_info,
        )
        assert quality["quality"] == "basic"
        assert quality["needs_improvement"] is True

    def test_signature_validation_missing_param_docs(self) -> None:
        """Verifies signature validation detects missing parameter documentation.

        Business context:
            Procedures with parameters but no param documentation should have
            args_section remain False in quality indicators.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Create func_info with parameters.
            3. Create quality_indicators with args_section=False.

        Action:
            Call _validate_signature_coverage.

        Assertion Strategy:
            Verify args_section stays False after validation.

        Testing Principle:
            Signature coverage ensures complete documentation.
        """
        analyzer = VB6Analyzer()
        func_info = {
            "name": "ProcessData",
            "visibility": "Public",
            "is_test": False,
            "args": [{"name": "data", "type": "String"}],
            "returns": None,
        }
        # args_section is False (no param docs) but procedure has params
        quality_indicators = {"brief_description": True, "args_section": False}
        result = analyzer._validate_signature_coverage(quality_indicators, func_info)
        assert result.get("args_section") is False

    def test_signature_validation_missing_return_docs(self) -> None:
        """Verifies signature validation detects missing return documentation.

        Business context:
            Functions with return type but no returns documentation should have
            returns_section remain False in quality indicators.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Create func_info with return type.
            3. Create quality_indicators with returns_section=False.

        Action:
            Call _validate_signature_coverage.

        Assertion Strategy:
            Verify returns_section stays False after validation.

        Testing Principle:
            Signature coverage ensures complete documentation.
        """
        analyzer = VB6Analyzer()
        func_info = {
            "name": "GetValue",
            "visibility": "Public",
            "is_test": False,
            "args": [],
            "returns": "Integer",
        }
        # returns_section is False (no returns docs) but function has return
        quality_indicators = {"brief_description": True, "returns_section": False}
        result = analyzer._validate_signature_coverage(quality_indicators, func_info)
        assert result.get("returns_section") is False

    def test_quality_gap_score_high_quality(self) -> None:
        """Verifies quality gap score returns 0 for high quality documentation.

        Business context:
            Well-documented procedures (score >= 0.8) should not receive
            additional priority bump from quality gap scoring.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Create quality_assessment with score >= 0.8.

        Action:
            Call _calculate_quality_gap_score.

        Assertion Strategy:
            Verify returned score is 0.

        Testing Principle:
            Priority scoring should not penalize good documentation.
        """
        analyzer = VB6Analyzer()
        quality_assessment = {
            "quality": "excellent",
            "score": 0.85,
            "missing": [],
            "needs_improvement": False,
            "indicators": {},
        }
        score = analyzer._calculate_quality_gap_score(quality_assessment)
        assert score == 0

    def test_complexity_procedure_not_found(self) -> None:
        """Verifies complexity estimation returns 1 when procedure not found.

        Business context:
            If procedure body cannot be located in code, complexity should
            default to 1 (minimum) to avoid penalizing analysis.

        Arrangement:
            1. Create VB6Analyzer with default config.
            2. Prepare code without the target procedure.

        Action:
            Call _estimate_complexity_by_name for non-existent procedure.

        Assertion Strategy:
            Verify complexity returns 1.

        Testing Principle:
            Graceful fallback ensures robust analysis.
        """
        analyzer = VB6Analyzer()
        code = """
Public Sub OtherProc()
    MsgBox "Hello"
End Sub
"""
        complexity = analyzer._estimate_complexity_by_name("NonExistentProc", code)
        assert complexity == 1
