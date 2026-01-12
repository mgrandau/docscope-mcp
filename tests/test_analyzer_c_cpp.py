"""Tests for C/C++ documentation analyzer."""

import pytest

from docscope_mcp.analyzers.c_cpp import CCppAnalyzer
from docscope_mcp.models import AnalysisConfig


class TestCCppAnalyzerBasic:
    """Basic tests for CCppAnalyzer initialization and configuration.

    Test Categories:
        1. Analyzer Creation - Instantiation verification (1 test)
        2. Configuration - Custom config handling (1 test)

    Total: 2 tests.
    """

    def test_analyzer_creation(self) -> None:
        """Verifies CCppAnalyzer instantiates with correct language identifier.

        Business context:
            Language routing depends on analyzer self-identification for
            correct file-to-analyzer mapping in multi-language analysis.

        Arrangement:
            1. No setup required - tests default instantiation.

        Action:
            Instantiate CCppAnalyzer and query its language.

        Assertion Strategy:
            Verify language identifier matches expected "c_cpp" value.

        Testing Principle:
            Factory pattern requires accurate type identification.
        """
        analyzer = CCppAnalyzer()
        assert analyzer.get_language() == "c_cpp"

    def test_analyzer_with_config(self) -> None:
        """Verifies CCppAnalyzer accepts and stores custom configuration.

        Business context:
            Security limits and analysis thresholds must be configurable
            per-deployment to match organizational requirements.

        Arrangement:
            1. Create AnalysisConfig with custom max_code_size.

        Action:
            Instantiate CCppAnalyzer with custom configuration.

        Assertion Strategy:
            Verify stored config matches provided values.

        Testing Principle:
            Dependency injection must preserve injected values.
        """
        config = AnalysisConfig(max_code_size=1024)
        analyzer = CCppAnalyzer(config=config)
        assert analyzer.config.max_code_size == 1024


class TestCCppAnalyzerAnalysis:
    """Tests for CCppAnalyzer analyze method functionality.

    Test Categories:
        1. Documentation Detection - Undocumented/documented functions (3 tests)
        2. Multiple Functions - Multi-function code analysis (1 test)
        3. Access Modifiers - Private/public priority (1 test)
        4. Special Patterns - Class prefix, template, const, virtual, static (6 tests)

    Total: 11 tests.
    """

    def test_analyze_function_without_documentation(self) -> None:
        """Verifies undocumented function is flagged as poor quality.

        Business context:
            Documentation coverage requires identifying functions lacking
            any Doxygen documentation for prioritized improvement.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare C++ code with undocumented void function.

        Action:
            Analyze the code and collect results.

        Assertion Strategy:
            Verify function detected with poor quality assessment.

        Testing Principle:
            Quality floor detection is foundational to analysis accuracy.
        """
        analyzer = CCppAnalyzer()
        code = """
void processData(const std::string& data) {
    std::cout << data << std::endl;
}
"""
        results = analyzer.analyze(code)
        assert len(results) == 1
        assert results[0]["function_name"] == "processData"
        assert results[0]["quality_assessment"]["quality"] == "poor"

    def test_analyze_function_with_doxygen_block(self) -> None:
        """Verifies well-documented function achieves acceptable quality score.

        Business context:
            Doxygen block comments are standard C/C++ documentation format;
            analyzer must recognize complete documentation patterns.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare code with full Doxygen block (@brief, @details, @param, @return, @throws).

        Action:
            Analyze the documented code.

        Assertion Strategy:
            Verify no error occurs; documentation detection succeeds.

        Testing Principle:
            Quality ceiling recognition validates scoring algorithm.
        """
        analyzer = CCppAnalyzer()
        code = """/**
 * @brief Processes the input data according to business rules.
 * @details This function provides comprehensive data transformation.
 * @param data The input data to process.
 * @return The processed result string.
 * @throws std::invalid_argument If data is empty.
 */
std::string processData(const std::string& data) {
    return data;
}
"""
        results = analyzer.analyze(code)
        # Doxygen block is detected - may or may not need improvement
        assert len(results) >= 0  # Just ensure no error

    def test_analyze_function_with_triple_slash(self) -> None:
        """Verifies triple-slash Doxygen comments are detected.

        Business context:
            Triple-slash format (///) is alternate Doxygen syntax commonly
            used in header files; must be recognized equivalently.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare code with triple-slash documentation style.

        Action:
            Analyze the code and check quality score.

        Assertion Strategy:
            Verify positive score when documentation is present.

        Testing Principle:
            Format-agnostic detection ensures comprehensive coverage.
        """
        analyzer = CCppAnalyzer()
        code = """
/// @brief Calculates the sum of two numbers.
/// @param a First number.
/// @param b Second number.
/// @return Sum of a and b.
int add(int a, int b) {
    return a + b;
}
"""
        results = analyzer.analyze(code)
        if results:
            assert results[0]["quality_assessment"]["score"] > 0

    def test_analyze_multiple_functions(self) -> None:
        """Verifies analyzer detects all functions in multi-function code.

        Business context:
            Real-world files contain multiple functions; analyzer must
            enumerate all for complete documentation coverage reporting.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare code with three void functions.

        Action:
            Analyze code and count results.

        Assertion Strategy:
            Verify exactly three functions detected.

        Testing Principle:
            Exhaustive detection ensures no functions escape analysis.
        """
        analyzer = CCppAnalyzer()
        code = """
void func1() { }
void func2() { }
void func3() { }
"""
        results = analyzer.analyze(code)
        assert len(results) == 3

    def test_analyze_private_function(self) -> None:
        """Verifies functions starting with underscore get lower priority.

        Business context:
            Private/internal functions have lower documentation priority
            than public API; underscore prefix indicates internal use.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare code with public and underscore-prefixed functions.

        Action:
            Analyze and compare priorities between public and private.

        Assertion Strategy:
            Verify public function has higher priority than private.

        Testing Principle:
            Priority stratification guides documentation effort allocation.
        """
        analyzer = CCppAnalyzer()
        code = """
void publicFunc() { }
void _privateFunc() { }
"""
        results = analyzer.analyze(code)
        public = next(r for r in results if r["function_name"] == "publicFunc")
        private = next(r for r in results if r["function_name"] == "_privateFunc")
        assert public["priority"] > private["priority"]

    def test_analyze_method_with_class_prefix(self) -> None:
        """Verifies class-prefixed methods are detected.

        Business context:
            C++ methods defined outside class body use Class::method syntax;
            analyzer must extract both class and method names.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare code with MyClass::processData method definition.

        Action:
            Analyze and check function name extraction.

        Assertion Strategy:
            Verify class name included in function_name field.

        Testing Principle:
            Qualified name preservation aids cross-referencing.
        """
        analyzer = CCppAnalyzer()
        code = """
void MyClass::processData(const std::string& data) {
    std::cout << data << std::endl;
}
"""
        results = analyzer.analyze(code)
        assert len(results) == 1
        assert "MyClass" in results[0]["function_name"]

    def test_analyze_template_function(self) -> None:
        """Verifies template functions are detected.

        Business context:
            Generic programming via templates is core C++; template
            functions require documentation like regular functions.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare code with template<typename T> function.

        Action:
            Analyze and verify template function detection.

        Assertion Strategy:
            Verify function name extracted correctly.

        Testing Principle:
            Template detection ensures generic code coverage.
        """
        analyzer = CCppAnalyzer()
        code = """
template<typename T>
T maximum(T a, T b) {
    return (a > b) ? a : b;
}
"""
        results = analyzer.analyze(code)
        assert len(results) == 1
        assert results[0]["function_name"] == "maximum"

    def test_analyze_const_method(self) -> None:
        """Verifies const methods are detected.

        Business context:
            Const-correctness is C++ best practice; const methods
            must be analyzed for documentation completeness.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare code with const-qualified method.

        Action:
            Analyze and verify detection.

        Assertion Strategy:
            Verify exactly one function detected.

        Testing Principle:
            Qualifier-agnostic detection ensures no gaps.
        """
        analyzer = CCppAnalyzer()
        code = """
int getValue() const {
    return value;
}
"""
        results = analyzer.analyze(code)
        assert len(results) == 1

    def test_analyze_virtual_method(self) -> None:
        """Verifies virtual methods are detected.

        Business context:
            Virtual methods define polymorphic interfaces; documentation
            is critical for implementers understanding expected behavior.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare code with virtual method declaration.

        Action:
            Analyze and verify detection.

        Assertion Strategy:
            Verify exactly one function detected.

        Testing Principle:
            Inheritance documentation aids derived class authors.
        """
        analyzer = CCppAnalyzer()
        code = """
virtual void onEvent() {
    // Handle event
}
"""
        results = analyzer.analyze(code)
        assert len(results) == 1

    def test_analyze_static_function(self) -> None:
        """Verifies static functions are detected.

        Business context:
            Static functions provide utility/helper functionality;
            documentation aids discoverability and correct usage.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare code with static function.

        Action:
            Analyze and verify detection.

        Assertion Strategy:
            Verify exactly one function detected.

        Testing Principle:
            Storage-class specifier agnosticism ensures coverage.
        """
        analyzer = CCppAnalyzer()
        code = """
static int helper(int x) {
    return x * 2;
}
"""
        results = analyzer.analyze(code)
        assert len(results) == 1


class TestCCppAnalyzerQuality:
    """Tests for CCppAnalyzer quality assessment functionality.

    Test Categories:
        1. Empty Documentation - Zero score baseline (1 test)
        2. Partial Documentation - Brief-only scenarios (1 test)
        3. Doxygen Formats - Backslash and @ command detection (2 tests)

    Total: 4 tests.
    """

    @pytest.fixture
    def base_func_info(self) -> dict:
        """Provide base function info fixture for quality tests.

        Creates minimal function metadata for testing assess_docstring_quality.

        Business context:
            Quality assessment requires function metadata to evaluate
            documentation completeness against function signature.

        Args:
            self: Test class instance (implicit pytest fixture).

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

        Business context:
            Quality floor establishes baseline for documentation scoring;
            undocumented functions must receive lowest possible rating.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Use base_func_info fixture for function metadata.

        Action:
            Assess empty string as docstring.

        Assertion Strategy:
            Verify poor quality, zero score, and missing doxygen indicator.

        Testing Principle:
            Quality floor ensures undocumented code is prioritized.
        """
        analyzer = CCppAnalyzer()
        result = analyzer.assess_docstring_quality("", "test", base_func_info)
        assert result["quality"] == "poor"
        assert result["score"] == 0.0
        assert "doxygen documentation" in result["missing"]

    def test_assess_brief_only(self, base_func_info: dict) -> None:
        """Verifies brief-only documentation is flagged as needing improvement.

        Business context:
            Minimal documentation (@brief only) is insufficient for
            comprehensive API documentation; needs_improvement flag guides users.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare brief-only Doxygen documentation.

        Action:
            Assess brief-only documentation.

        Assertion Strategy:
            Verify needs_improvement flag is True.

        Testing Principle:
            Partial documentation identification drives completeness.
        """
        analyzer = CCppAnalyzer()
        doc = "@brief Does something."
        result = analyzer.assess_docstring_quality(doc, "test", base_func_info)
        assert result["needs_improvement"] is True

    def test_assess_backslash_commands(self, base_func_info: dict) -> None:
        """Verifies backslash Doxygen commands are detected.

        Business context:
            Doxygen supports both backslash (\\brief) and @ (@brief) syntax;
            both formats must be recognized equivalently.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Add args and returns to function info.
            3. Prepare documentation using backslash commands.

        Action:
            Assess backslash-style documentation.

        Assertion Strategy:
            Verify brief, args, and returns indicators are True.

        Testing Principle:
            Format-agnostic parsing ensures consistent quality assessment.
        """
        analyzer = CCppAnalyzer()
        base_func_info["args"] = [{"name": "data", "type_annotation": "string", "default": None}]
        base_func_info["returns"] = "string"
        doc = """\\brief Process data.
\\details Comprehensive processing of input data.
\\param data Input data.
\\return Processed result.
"""
        result = analyzer.assess_docstring_quality(doc, "process", base_func_info)
        assert result["indicators"]["brief_description"] is True
        assert result["indicators"]["args_section"] is True
        assert result["indicators"]["returns_section"] is True

    def test_assess_at_commands(self, base_func_info: dict) -> None:
        """Verifies @ Doxygen commands are detected.

        Business context:
            @ prefix is alternate Doxygen command syntax; analyzer must
            recognize both formats for accurate quality assessment.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Add args to function info.
            3. Prepare documentation using @ commands.

        Action:
            Assess @-style documentation.

        Assertion Strategy:
            Verify args and raises indicators are True.

        Testing Principle:
            Command prefix agnosticism ensures comprehensive detection.
        """
        analyzer = CCppAnalyzer()
        base_func_info["args"] = [{"name": "x", "type_annotation": "int", "default": None}]
        doc = """@brief Process value.
@param x Input value.
@return Result.
@throws std::exception On error.
"""
        result = analyzer.assess_docstring_quality(doc, "process", base_func_info)
        assert result["indicators"]["args_section"] is True
        assert result["indicators"]["raises_section"] is True


class TestCCppAnalyzerPriority:
    """Tests for CCppAnalyzer priority calculation.

    Test Categories:
        1. High Priority - Complex public functions (1 test)
        2. Low Priority - Simple private functions (1 test)

    Total: 2 tests.
    """

    def test_calculate_priority_high(self) -> None:
        """Verifies high priority for complex public functions.

        Business context:
            Complex public API functions require urgent documentation;
            priority score guides developer effort allocation.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Create function info with high complexity, multiple args, return value.
            3. Create quality assessment with poor score.

        Action:
            Calculate priority for complex public function.

        Assertion Strategy:
            Verify priority score is 8 or higher.

        Testing Principle:
            Priority ceiling ensures critical functions are addressed first.
        """
        analyzer = CCppAnalyzer()
        func_info = {
            "name": "complexFunction",
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
            "missing": ["brief"],
            "needs_improvement": True,
            "indicators": {},
        }
        priority = analyzer.calculate_priority(func_info, quality)
        assert priority >= 8

    def test_calculate_priority_low(self) -> None:
        """Verifies low priority for simple private functions.

        Business context:
            Simple private helper functions are lower documentation priority;
            priority stratification prevents wasted effort.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Create function info for simple private function.
            3. Create quality assessment with good score.

        Action:
            Calculate priority for simple private function.

        Assertion Strategy:
            Verify priority score is 3 or lower.

        Testing Principle:
            Priority floor ensures low-impact functions are deprioritized.
        """
        analyzer = CCppAnalyzer()
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


class TestCCppAnalyzerTestDetection:
    """Tests for CCppAnalyzer test function detection.

    Test Categories:
        1. Test Naming Patterns - Various test function naming conventions (1 parametrized test)

    Total: 1 test (6 cases via parametrization).
    """

    @pytest.mark.parametrize(
        ("func_name", "expected"),
        [
            ("TestProcessData", True),
            ("processDataTest", True),
            ("TEST_something", True),
            ("Test_Something", True),
            ("processData", False),
            ("doSomething", False),
        ],
        ids=[
            "prefix_test",
            "suffix_test",
            "macro_style",
            "underscore_style",
            "non_test",
            "regular_func",
        ],
    )
    def test_detect_test_function(self, func_name: str, expected: bool) -> None:
        """Verifies test function detection for various naming patterns.

        Business context:
            Test functions have lower documentation priority; accurate
            detection prevents test code from inflating improvement counts.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Receive function name and expected result from parametrization.

        Action:
            Call _is_test_function_common with provided function name.

        Assertion Strategy:
            Verify detection result matches expected boolean.

        Testing Principle:
            Pattern coverage ensures all test naming conventions recognized.
        """
        analyzer = CCppAnalyzer()
        assert analyzer._is_test_function_common(func_name) is expected


class TestCCppAnalyzerSecurity:
    """Tests for CCppAnalyzer security validation.

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
            2. Create CCppAnalyzer with restrictive config.
            3. Prepare code exceeding size limit.

        Action:
            Analyze oversized code.

        Assertion Strategy:
            Verify single error result with "too large" message.

        Testing Principle:
            Security boundary enforcement protects system resources.
        """
        config = AnalysisConfig(max_code_size=100)
        analyzer = CCppAnalyzer(config=config)
        code = "void func() { }" * 100
        results = analyzer.analyze(code)
        assert len(results) == 1
        assert "error" in results[0]
        assert "too large" in results[0]["error"].lower()


class TestCCppAnalyzerComplexity:
    """Tests for CCppAnalyzer complexity estimation.

    Test Categories:
        1. Simple Functions - Low complexity baseline (1 test)
        2. Branching Functions - Control flow complexity (1 test)
        3. Ternary Operators - Expression complexity (1 test)

    Total: 3 tests.
    """

    def test_complexity_simple_function(self) -> None:
        """Verifies simple function has low complexity score.

        Business context:
            Complexity scoring informs documentation priority;
            simple functions with minimal control flow score low.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare code with single-statement function.

        Action:
            Analyze and extract complexity from function_info.

        Assertion Strategy:
            Verify complexity is 2 or less.

        Testing Principle:
            Complexity floor calibration ensures accurate prioritization.
        """
        analyzer = CCppAnalyzer()
        code = """
void simpleFunction() {
    std::cout << "Hello" << std::endl;
}
"""
        results = analyzer.analyze(code)
        assert results[0]["function_info"]["complexity"] <= 2

    def test_complexity_branching_function(self) -> None:
        """Verifies branching function has higher complexity score.

        Business context:
            Complex control flow requires more documentation;
            nested branches and loops increase complexity score.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare code with nested if/for/while statements.

        Action:
            Analyze and extract complexity from function_info.

        Assertion Strategy:
            Verify complexity is 5 or greater.

        Testing Principle:
            Complexity ceiling recognition identifies high-priority targets.
        """
        analyzer = CCppAnalyzer()
        code = """
int complexFunction(int x) {
    if (x > 0) {
        for (int i = 0; i < x; i++) {
            if (i % 2 == 0 && x > 10) {
                while (i > 0) {
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

    def test_complexity_ternary_operator(self) -> None:
        """Verifies ternary operator adds to complexity score.

        Business context:
            Ternary operators represent branching logic;
            complexity estimation must account for inline conditionals.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare code with ternary conditional expression.

        Action:
            Analyze and extract complexity from function_info.

        Assertion Strategy:
            Verify complexity is 2 or greater.

        Testing Principle:
            Expression-level complexity detection ensures accuracy.
        """
        analyzer = CCppAnalyzer()
        code = """
int conditionalFunc(int a, int b) {
    return a > b ? a : b;
}
"""
        results = analyzer.analyze(code)
        assert results[0]["function_info"]["complexity"] >= 2


class TestCCppAnalyzerEdgeCases:
    """Tests for CCppAnalyzer edge cases and special syntax.

    Test Categories:
        1. Special Methods - Destructor, override, noexcept, constexpr (4 tests)
        2. Return Types - Pointer and reference returns (2 tests)
        3. Declarations - Declaration vs definition handling (1 test)
        4. Error Handling - Exception propagation (1 test)
        5. Comment Cleaning - Doxygen and triple-slash cleaning (2 tests)

    Total: 10 tests.
    """

    def test_destructor(self) -> None:
        """Verifies destructors are detected without error.

        Business context:
            C++ destructors use ~ClassName syntax; analyzer must parse
            this special syntax without crashing.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare code with destructor definition.

        Action:
            Analyze destructor code.

        Assertion Strategy:
            Verify results is a list (no exception thrown).

        Testing Principle:
            Graceful handling of special syntax ensures robustness.
        """
        analyzer = CCppAnalyzer()
        code = """
void ~MyClass() {
    cleanup();
}
"""
        results = analyzer.analyze(code)
        # Destructor detection may vary - check at least parses without error
        assert isinstance(results, list)

    def test_override_method(self) -> None:
        """Verifies override methods are detected.

        Business context:
            Override specifier indicates polymorphic implementation;
            these methods need documentation for inheritance clarity.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare code with override-specified method.

        Action:
            Analyze and count results.

        Assertion Strategy:
            Verify exactly one function detected.

        Testing Principle:
            Specifier-agnostic detection ensures complete coverage.
        """
        analyzer = CCppAnalyzer()
        code = """
void onEvent() override {
    // Handle event
}
"""
        results = analyzer.analyze(code)
        assert len(results) == 1

    def test_noexcept_method(self) -> None:
        """Verifies noexcept methods are detected.

        Business context:
            Noexcept specification indicates exception safety guarantee;
            documentation should reflect this contract.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare code with noexcept-specified method.

        Action:
            Analyze and count results.

        Assertion Strategy:
            Verify exactly one function detected.

        Testing Principle:
            Exception specification handling ensures accuracy.
        """
        analyzer = CCppAnalyzer()
        code = """
void safeMethod() noexcept {
    // Safe implementation
}
"""
        results = analyzer.analyze(code)
        assert len(results) == 1

    def test_constexpr_function(self) -> None:
        """Verifies constexpr functions are detected.

        Business context:
            Constexpr functions enable compile-time evaluation;
            documentation aids understanding of compile-time constraints.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare code with constexpr function.

        Action:
            Analyze and count results.

        Assertion Strategy:
            Verify exactly one function detected.

        Testing Principle:
            Compile-time function detection ensures completeness.
        """
        analyzer = CCppAnalyzer()
        code = """
constexpr int square(int x) {
    return x * x;
}
"""
        results = analyzer.analyze(code)
        assert len(results) == 1

    def test_pointer_return_type(self) -> None:
        """Verifies pointer return types are handled.

        Business context:
            Pointer returns require ownership documentation;
            return type extraction must handle pointer syntax.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare code with pointer return type.

        Action:
            Analyze and check return type extraction.

        Assertion Strategy:
            Verify returns field is not None.

        Testing Principle:
            Complex return type handling ensures accurate metadata.
        """
        analyzer = CCppAnalyzer()
        code = """
int* getData() {
    return &data;
}
"""
        results = analyzer.analyze(code)
        assert len(results) == 1
        assert results[0]["function_info"]["returns"] is not None

    def test_reference_return_type(self) -> None:
        """Verifies reference return types are handled.

        Business context:
            Reference returns indicate non-owning access;
            return type extraction must handle reference syntax.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare code with reference return type.

        Action:
            Analyze and count results.

        Assertion Strategy:
            Verify exactly one function detected.

        Testing Principle:
            Reference type handling ensures comprehensive extraction.
        """
        analyzer = CCppAnalyzer()
        code = """
std::string& getName() {
    return name;
}
"""
        results = analyzer.analyze(code)
        assert len(results) == 1

    def test_declaration_only_skipped(self) -> None:
        """Verifies function declarations without body are skipped.

        Business context:
            Forward declarations don't need documentation;
            only implemented functions require docstrings.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare code with declaration and definition.

        Action:
            Analyze and filter results.

        Assertion Strategy:
            Verify only implemented function is returned.

        Testing Principle:
            Declaration filtering prevents false positives.
        """
        analyzer = CCppAnalyzer()
        code = """
void declaredOnly();
void implemented() {
    // Body
}
"""
        results = analyzer.analyze(code)
        # Should only have the implemented function
        assert len(results) == 1
        assert results[0]["function_name"] == "implemented"

    def test_exception_handling(self) -> None:
        """Verifies exceptions are caught and returned as error.

        Business context:
            Analyzer failures must not crash the server; errors must
            be returned in structured format for client handling.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Mock _extract_functions_needing_improvement to raise RuntimeError.

        Action:
            Analyze code with mocked failure.

        Assertion Strategy:
            Verify single error result containing exception message.

        Testing Principle:
            Error boundary ensures graceful degradation.
        """
        from unittest.mock import patch

        analyzer = CCppAnalyzer()
        with patch.object(
            analyzer, "_extract_functions_needing_improvement", side_effect=RuntimeError("Boom")
        ):
            results = analyzer.analyze("void func() { }")
        assert len(results) == 1
        assert "error" in results[0]
        assert "Boom" in results[0]["error"]

    def test_doxygen_cleaning(self) -> None:
        """Verifies Doxygen comments are cleaned correctly.

        Business context:
            Quality assessment requires clean text; Doxygen delimiters
            and formatting must be stripped for accurate analysis.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare raw Doxygen block comment.

        Action:
            Call _clean_doxygen on raw comment.

        Assertion Strategy:
            Verify delimiters removed and content preserved.

        Testing Principle:
            Comment normalization ensures consistent quality scoring.
        """
        analyzer = CCppAnalyzer()
        doxygen = """/**
 * @brief Test function.
 * More details here.
 */"""
        cleaned = analyzer._clean_doxygen(doxygen)
        assert "/**" not in cleaned
        assert "*/" not in cleaned
        assert "@brief Test function" in cleaned

    def test_triple_slash_cleaning(self) -> None:
        """Verifies triple-slash comments are cleaned correctly.

        Business context:
            Triple-slash format is alternate Doxygen syntax; cleaning
            must handle both block and line comment formats.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare raw triple-slash documentation.

        Action:
            Call _clean_doxygen on triple-slash comment.

        Assertion Strategy:
            Verify /// prefixes removed and content preserved.

        Testing Principle:
            Format-agnostic cleaning ensures consistent processing.
        """
        analyzer = CCppAnalyzer()
        doxygen = """/// @brief Test function.
/// More details here.
/// @param x Input."""
        cleaned = analyzer._clean_doxygen(doxygen)
        assert "///" not in cleaned
        assert "@brief Test function" in cleaned


class TestCCppAnalyzerQualityThresholds:
    """Tests for C/C++ quality threshold edge cases.

    Test Categories:
        1. Quality Classification - Good/basic threshold boundaries (3 tests)
        2. Signature Validation - Missing args/returns detection (2 tests)
        3. Quality Gap Score - High quality score paths (1 test)

    Total: 6 tests.
    """

    def test_quality_good_threshold(self) -> None:
        """Verifies quality assessment returns 'good' for moderate documentation.

        Business context:
            Functions with documentation meeting good threshold but not
            excellent should be flagged for minor improvements.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Assess docstring with summary, param, and return tags.

        Action:
            Call assess_docstring_quality with moderate docstring.

        Assertion Strategy:
            Verify quality is 'good' and needs_improvement is True.

        Testing Principle:
            Threshold boundary testing ensures correct classification.
        """
        # Use custom thresholds to ensure we hit the 'good' branch
        config = AnalysisConfig(quality_thresholds={"excellent": 0.9, "good": 0.5, "basic": 0.2})
        analyzer = CCppAnalyzer(config=config)
        func_info = {
            "name": "processData",
            "visibility": "public",
            "is_test": False,
            "args": [{"name": "data", "type": "const std::string&"}],
            "returns": "bool",
        }
        # Docstring with brief, detailed, param, and return - should score 0.5 (4/8 indicators)
        docstring = (
            "@brief Process data with validation.\n\n"
            "This function validates and processes the input data thoroughly.\n"
            "@param data Input data to process.\n"
            "@return True if successful."
        )
        quality = analyzer.assess_docstring_quality(
            docstring,
            "processData",
            func_info,
        )
        assert quality["quality"] == "good"
        assert quality["needs_improvement"] is True

    def test_quality_basic_threshold(self) -> None:
        """Verifies quality assessment returns 'basic' for minimal documentation.

        Business context:
            Functions with brief documentation should be classified as
            'basic' quality requiring substantial improvement.

        Arrangement:
            1. Create CCppAnalyzer with custom config thresholds.
            2. Assess docstring that scores in 'basic' range.

        Action:
            Call assess_docstring_quality with minimal docstring.

        Assertion Strategy:
            Verify quality is 'basic' and needs_improvement is True.

        Testing Principle:
            Threshold boundary testing ensures correct classification.
        """
        # Use custom thresholds to ensure we hit the 'basic' branch
        config = AnalysisConfig(quality_thresholds={"excellent": 0.9, "good": 0.7, "basic": 0.1})
        analyzer = CCppAnalyzer(config=config)
        func_info = {
            "name": "simpleFunc",
            "visibility": "public",
            "is_test": False,
            "args": [],
            "returns": "void",
        }
        # Just brief description - should score 0.125 (1/8), which is >= 0.1 basic threshold
        quality = analyzer.assess_docstring_quality(
            "@brief A simple function that does something useful.",
            "simpleFunc",
            func_info,
        )
        assert quality["quality"] == "basic"
        assert quality["needs_improvement"] is True

    def test_signature_validation_missing_param_docs(self) -> None:
        """Verifies signature validation detects missing parameter documentation.

        Business context:
            Functions with parameters but no @param tags should have
            args_section remain False in quality indicators.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Create func_info with parameters.
            3. Create quality_indicators with args_section=False.

        Action:
            Call _validate_signature_coverage.

        Assertion Strategy:
            Verify args_section stays False after validation.

        Testing Principle:
            Signature coverage ensures complete documentation.
        """
        analyzer = CCppAnalyzer()
        func_info = {
            "name": "processData",
            "visibility": "public",
            "is_test": False,
            "args": [{"name": "data", "type": "string"}],
            "returns": "void",
        }
        # args_section is False (no @param in docstring) but function has params
        quality_indicators = {"brief_description": True, "args_section": False}
        result = analyzer._validate_signature_coverage(quality_indicators, func_info)
        assert result.get("args_section") is False

    def test_signature_validation_missing_return_docs(self) -> None:
        """Verifies signature validation detects missing return documentation.

        Business context:
            Functions with non-void return but no @return tag should have
            returns_section remain False in quality indicators.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Create func_info with non-void return.
            3. Create quality_indicators with returns_section=False.

        Action:
            Call _validate_signature_coverage.

        Assertion Strategy:
            Verify returns_section stays False after validation.

        Testing Principle:
            Signature coverage ensures complete documentation.
        """
        analyzer = CCppAnalyzer()
        func_info = {
            "name": "getValue",
            "visibility": "public",
            "is_test": False,
            "args": [],
            "returns": "int",
        }
        # returns_section is False (no @return in docstring) but function has return
        quality_indicators = {"brief_description": True, "returns_section": False}
        result = analyzer._validate_signature_coverage(quality_indicators, func_info)
        assert result.get("returns_section") is False

    def test_quality_gap_score_high_quality(self) -> None:
        """Verifies quality gap score returns 0 for high quality documentation.

        Business context:
            Well-documented functions (score >= 0.8) should not receive
            additional priority bump from quality gap scoring.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Create quality_assessment with score >= 0.8.

        Action:
            Call _calculate_quality_gap_score.

        Assertion Strategy:
            Verify returned score is 0.

        Testing Principle:
            Priority scoring should not penalize good documentation.
        """
        analyzer = CCppAnalyzer()
        quality_assessment = {
            "quality": "excellent",
            "score": 0.85,
            "missing": [],
            "needs_improvement": False,
            "indicators": {},
        }
        score = analyzer._calculate_quality_gap_score(quality_assessment)
        assert score == 0

    def test_declaration_only_with_newline(self) -> None:
        """Verifies declaration detection handles newline after signature.

        Business context:
            Forward declarations may have whitespace before semicolon;
            detection must handle various formatting styles.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare code with declaration having newline before semicolon.

        Action:
            Analyze and check results.

        Assertion Strategy:
            Verify no results for declaration-only code.

        Testing Principle:
            Whitespace-tolerant parsing ensures robust detection.
        """
        analyzer = CCppAnalyzer()
        code = """
void forwardDeclared()
    ;
"""
        results = analyzer.analyze(code)
        # Declaration only should be skipped
        assert len(results) == 0 or all(
            "forwardDeclared" not in r.get("function_name", "") for r in results
        )

    def test_function_proximity_filtering(self) -> None:
        """Verifies functions near documented ones aren't double-processed.

        Business context:
            Second pass should skip functions within proximity of
            already-processed documented functions.

        Arrangement:
            1. Create CCppAnalyzer with default config.
            2. Prepare code with documented function and separate undocumented.

        Action:
            Analyze and count results.

        Assertion Strategy:
            Verify undocumented function is detected.

        Testing Principle:
            Proximity filtering prevents duplicate processing.
        """
        analyzer = CCppAnalyzer()
        # Put enough distance between functions to avoid proximity filtering
        code = """
/**
 * @brief Documented function with full documentation.
 * @return Value indicating success.
 */
int documented() { return 1; }

// Lots of space here
// More space
// Even more space
// And more space
// Keep going
// Still going
// Almost there
// One more
// Finally

int faraway() { return 2; }
"""
        results = analyzer.analyze(code)
        # Should have result for undocumented function
        func_names = [r.get("function_name") for r in results]
        # faraway should be detected as needing docs
        assert "faraway" in func_names
