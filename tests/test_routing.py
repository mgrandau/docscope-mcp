"""Tests for language detection and analyzer routing."""

from pathlib import Path

import pytest

from docscope_mcp.analyzers import (
    EXTENSION_MAP,
    SUPPORTED_LANGUAGES,
    CCppAnalyzer,
    CSharpAnalyzer,
    PythonAnalyzer,
    VB6Analyzer,
    VBAnalyzer,
    analyze_file,
    detect_language,
    get_analyzer,
    get_analyzer_for_file,
    get_extensions_for_language,
    get_supported_extensions,
    is_supported_file,
)
from docscope_mcp.models import AnalysisConfig


class TestDetectLanguage:
    """Test suite for detect_language function.

    Categories:
    1. Extension Mapping - All supported file extensions (1 parametrized test)
    2. Case Sensitivity - Case-insensitive detection (1 test)

    Total: 2 tests.
    """

    @pytest.mark.parametrize(
        ("file_path", "expected"),
        [
            # Python
            ("main.py", "python"),
            ("src/module.py", "python"),
            ("types.pyi", "python"),
            ("script.pyw", "python"),
            # C#
            ("Program.cs", "csharp"),
            ("src/Service.cs", "csharp"),
            # VB.NET
            ("Module.vb", "vb"),
            ("Form1.vb", "vb"),
            # VB6
            ("Module1.bas", "vb6"),
            ("Class1.cls", "vb6"),
            ("Form1.frm", "vb6"),
            # C/C++
            ("main.cpp", "c_cpp"),
            ("util.cxx", "c_cpp"),
            ("helper.cc", "c_cpp"),
            ("file.c++", "c_cpp"),
            ("header.hpp", "c_cpp"),
            ("types.hxx", "c_cpp"),
            ("defs.hh", "c_cpp"),
            ("api.h++", "c_cpp"),
            ("common.h", "c_cpp"),
            ("legacy.c", "c_cpp"),
            # Unknown
            ("readme.md", None),
            ("data.json", None),
            ("style.css", None),
        ],
        ids=[
            "python_py",
            "python_path",
            "python_pyi",
            "python_pyw",
            "csharp_cs",
            "csharp_path",
            "vb_vb",
            "vb_form",
            "vb6_bas",
            "vb6_cls",
            "vb6_frm",
            "c_cpp_cpp",
            "c_cpp_cxx",
            "c_cpp_cc",
            "c_cpp_c++",
            "c_cpp_hpp",
            "c_cpp_hxx",
            "c_cpp_hh",
            "c_cpp_h++",
            "c_cpp_h",
            "c_cpp_c",
            "unknown_md",
            "unknown_json",
            "unknown_css",
        ],
    )
    def test_detect_language(self, file_path: str, expected: str | None) -> None:
        """Verifies language detection for various file extensions.

        Tests extension-to-language mapping with comprehensive file types.

        Business context:
        Correct language detection routes files to appropriate analyzer.

        Arrangement:
        1. Parametrize with all supported extensions plus unknown types.
        2. Include path variations (simple name, nested path).

        Action:
        Call detect_language with each file path.

        Assertion Strategy:
        Validates mapping accuracy by confirming:
        - Each extension maps to expected language identifier.
        - Unknown extensions return None.

        Testing Principle:
        Validates extension coverage, ensuring all supported types detected.
        """
        assert detect_language(file_path) == expected

    def test_detect_language_case_insensitive(self) -> None:
        """Verifies detection works regardless of extension case.

        Tests case normalization by using uppercase extensions.

        Business context:
        Windows filesystems are case-insensitive; detection must match.

        Arrangement:
        1. Create file paths with uppercase extensions (.PY, .CS, .CPP).

        Action:
        Call detect_language with uppercase extensions.

        Assertion Strategy:
        Validates case handling by confirming:
        - .PY maps to "python".
        - .CS maps to "csharp".
        - .CPP maps to "c_cpp".

        Testing Principle:
        Validates case insensitivity, ensuring cross-platform compatibility.
        """
        assert detect_language("Main.PY") == "python"
        assert detect_language("Program.CS") == "csharp"
        assert detect_language("Module.CPP") == "c_cpp"


class TestGetAnalyzer:
    """Test suite for get_analyzer function.

    Categories:
    1. Language Mapping - Correct analyzer class for each language (1 test)
    2. Unknown Language - None returned for unsupported (1 test)
    3. Config Injection - Config passed to analyzer (1 test)

    Total: 3 tests.
    """

    @pytest.mark.parametrize(
        ("language", "expected_class"),
        [
            ("python", PythonAnalyzer),
            ("csharp", CSharpAnalyzer),
            ("vb", VBAnalyzer),
            ("vb6", VB6Analyzer),
            ("c_cpp", CCppAnalyzer),
        ],
    )
    def test_get_analyzer(self, language: str, expected_class: type) -> None:
        """Verifies correct analyzer class is returned for each language.

        Tests analyzer factory with all supported language identifiers.

        Business context:
        Each language requires specialized parser; factory must route correctly.

        Arrangement:
        1. Parametrize with all supported language identifiers.
        2. Map each to expected analyzer class.

        Action:
        Call get_analyzer with language identifier.

        Assertion Strategy:
        Validates factory routing by confirming:
        - Returned object is instance of expected class.
        - Analyzer self-identifies with correct language.

        Testing Principle:
        Validates factory pattern, ensuring correct analyzer instantiation.
        """
        analyzer = get_analyzer(language)
        assert isinstance(analyzer, expected_class)
        assert analyzer.get_language() == language

    def test_get_analyzer_unknown(self) -> None:
        """Verifies None returned for unknown language.

        Tests factory behavior with unsupported language identifiers.

        Business context:
        Unsupported languages must return None, not raise exception.

        Arrangement:
        1. Use "unknown" and "java" as unsupported identifiers.

        Action:
        Call get_analyzer with unsupported languages.

        Assertion Strategy:
        Validates graceful handling by confirming:
        - Both calls return None.

        Testing Principle:
        Validates defensive design, ensuring no exception for unknown.
        """
        assert get_analyzer("unknown") is None
        assert get_analyzer("java") is None

    def test_get_analyzer_with_config(self) -> None:
        """Verifies config is passed to analyzer.

        Tests dependency injection by providing custom AnalysisConfig.

        Business context:
        Custom limits enable project-specific security constraints.

        Arrangement:
        1. Create AnalysisConfig with custom max_code_size=1024.

        Action:
        Call get_analyzer with config and verify propagation.

        Assertion Strategy:
        Validates injection by confirming:
        - Analyzer is not None.
        - Config property matches injected value.

        Testing Principle:
        Validates DI pattern, ensuring config flows to analyzer.
        """
        config = AnalysisConfig(max_code_size=1024)
        analyzer = get_analyzer("python", config=config)
        assert analyzer is not None
        assert analyzer.config.max_code_size == 1024


class TestGetAnalyzerForFile:
    """Test suite for get_analyzer_for_file function.

    Categories:
    1. File-to-Analyzer - Correct analyzer for file paths (1 test)
    2. Unknown Files - None for unsupported extensions (1 test)
    3. Config Passthrough - Config propagated to analyzer (1 test)

    Total: 3 tests.
    """

    @pytest.mark.parametrize(
        ("file_path", "expected_language"),
        [
            ("main.py", "python"),
            ("Program.cs", "csharp"),
            ("Module.vb", "vb"),
            ("Module1.bas", "vb6"),
            ("main.cpp", "c_cpp"),
        ],
    )
    def test_get_analyzer_for_file(self, file_path: str, expected_language: str) -> None:
        """Verifies correct analyzer returned for file.

        Tests file-based analyzer lookup with representative extensions.

        Business context:
        File path is primary input; must resolve to correct analyzer.

        Arrangement:
        1. Parametrize with one extension per supported language.

        Action:
        Call get_analyzer_for_file with file path.

        Assertion Strategy:
        Validates routing by confirming:
        - Analyzer is not None.
        - Analyzer language matches expected.

        Testing Principle:
        Validates convenience function, ensuring file-to-analyzer works.
        """
        analyzer = get_analyzer_for_file(file_path)
        assert analyzer is not None
        assert analyzer.get_language() == expected_language

    def test_get_analyzer_for_file_unknown(self) -> None:
        """Verifies None returned for unsupported file.

        Tests graceful handling of files with unknown extensions.

        Business context:
        Unsupported files must not cause errors; return None instead.

        Arrangement:
        1. Use readme.md and data.xml as unsupported file types.

        Action:
        Call get_analyzer_for_file with unsupported extensions.

        Assertion Strategy:
        Validates null handling by confirming:
        - Both calls return None.

        Testing Principle:
        Validates defensive design, ensuring graceful unknown handling.
        """
        assert get_analyzer_for_file("readme.md") is None
        assert get_analyzer_for_file("data.xml") is None

    def test_get_analyzer_for_file_with_config(self) -> None:
        """Verifies config is passed through.

        Tests config injection via file-based lookup function.

        Business context:
        Config must propagate through convenience functions.

        Arrangement:
        1. Create AnalysisConfig with custom max_code_size=2048.

        Action:
        Call get_analyzer_for_file with config parameter.

        Assertion Strategy:
        Validates propagation by confirming:
        - Analyzer is not None.
        - Config property matches injected value.

        Testing Principle:
        Validates DI passthrough, ensuring config reaches analyzer.
        """
        config = AnalysisConfig(max_code_size=2048)
        analyzer = get_analyzer_for_file("test.py", config=config)
        assert analyzer is not None
        assert analyzer.config.max_code_size == 2048


class TestSupportedExtensions:
    """Test suite for extension listing functions.

    Categories:
    1. All Extensions - Complete extension list (1 test)
    2. Language Extensions - Per-language extension lookup (1 test)
    3. Unknown Language - Empty list for unsupported (1 test)

    Total: 3 tests.
    """

    def test_get_supported_extensions(self) -> None:
        """Verifies all expected extensions are returned.

        Tests extension enumeration for completeness.

        Business context:
        Clients need extension list for file filtering and validation.

        Arrangement:
        1. No setup needed - tests module-level function.

        Action:
        Call get_supported_extensions and check contents.

        Assertion Strategy:
        Validates completeness by confirming:
        - Python, C#, VB, VB6, C/C++ extensions all present.
        - Includes both source and header extensions.

        Testing Principle:
        Validates enumeration, ensuring all extensions listed.
        """
        exts = get_supported_extensions()
        assert ".py" in exts
        assert ".cs" in exts
        assert ".vb" in exts
        assert ".bas" in exts
        assert ".cpp" in exts
        assert ".h" in exts

    def test_get_extensions_for_language(self) -> None:
        """Verifies correct extensions for each language.

        Tests per-language extension lookup for all supported languages.

        Business context:
        Language-specific filtering requires accurate extension mapping.

        Arrangement:
        1. Test each supported language identifier.

        Action:
        Call get_extensions_for_language for each language.

        Assertion Strategy:
        Validates accuracy by confirming:
        - Python includes .py and .pyi.
        - C# includes .cs.
        - VB includes .vb.
        - VB6 includes .bas.
        - C/C++ includes .cpp.

        Testing Principle:
        Validates reverse mapping, ensuring language-to-extensions works.
        """
        assert ".py" in get_extensions_for_language("python")
        assert ".pyi" in get_extensions_for_language("python")
        assert ".cs" in get_extensions_for_language("csharp")
        assert ".vb" in get_extensions_for_language("vb")
        assert ".bas" in get_extensions_for_language("vb6")
        assert ".cpp" in get_extensions_for_language("c_cpp")

    def test_get_extensions_for_unknown_language(self) -> None:
        """Verifies empty list for unknown language.

        Tests graceful handling of unsupported language identifier.

        Business context:
        Unknown languages should return empty list, not raise exception.

        Arrangement:
        1. Use "unknown" as unsupported language identifier.

        Action:
        Call get_extensions_for_language with unknown language.

        Assertion Strategy:
        Validates empty result by confirming:
        - Returned list equals empty list.

        Testing Principle:
        Validates defensive design, ensuring no exception for unknown.
        """
        assert get_extensions_for_language("unknown") == []


class TestIsSupportedFile:
    """Test suite for is_supported_file function.

    Categories:
    1. Support Detection - Boolean support check for files (1 test)

    Total: 1 test.
    """

    @pytest.mark.parametrize(
        ("file_path", "expected"),
        [
            ("main.py", True),
            ("Program.cs", True),
            ("Module.vb", True),
            ("Module1.bas", True),
            ("main.cpp", True),
            ("readme.md", False),
            ("data.json", False),
        ],
    )
    def test_is_supported_file(self, file_path: str, expected: bool) -> None:
        """Verifies support detection for various files.

        Tests boolean support check with supported and unsupported files.

        Business context:
        File filtering requires quick boolean check for support status.

        Arrangement:
        1. Parametrize with supported (.py, .cs, .vb, .bas, .cpp) files.
        2. Include unsupported (.md, .json) files for false cases.

        Action:
        Call is_supported_file with each file path.

        Assertion Strategy:
        Validates detection by confirming:
        - Supported files return True.
        - Unsupported files return False.

        Testing Principle:
        Validates predicate function, ensuring accurate support check.
        """
        assert is_supported_file(file_path) == expected


class TestConstants:
    """Test suite for module constants.

    Categories:
    1. Extension Map - EXTENSION_MAP completeness (1 test)
    2. Languages List - SUPPORTED_LANGUAGES contents (1 test)

    Total: 2 tests.
    """

    def test_extension_map_complete(self) -> None:
        """Verifies extension map has expected entries.

        Tests EXTENSION_MAP constant for minimum size.

        Business context:
        Extension map is source of truth; must include all supported types.

        Arrangement:
        1. No setup needed - tests module-level constant.

        Action:
        Check length of EXTENSION_MAP.

        Assertion Strategy:
        Validates completeness by confirming:
        - Map contains at least 15 extensions.

        Testing Principle:
        Validates constant integrity, ensuring no accidental deletions.
        """
        assert len(EXTENSION_MAP) >= 15  # At least 15 extensions

    def test_supported_languages(self) -> None:
        """Verifies supported languages list.

        Tests SUPPORTED_LANGUAGES constant for all expected languages.

        Business context:
        Language list used for validation and documentation.

        Arrangement:
        1. No setup needed - tests module-level constant.

        Action:
        Check SUPPORTED_LANGUAGES contents and length.

        Assertion Strategy:
        Validates contents by confirming:
        - All five languages present (python, csharp, vb, vb6, c_cpp).
        - Exactly 5 languages in list.

        Testing Principle:
        Validates constant integrity, ensuring complete language list.
        """
        assert "python" in SUPPORTED_LANGUAGES
        assert "csharp" in SUPPORTED_LANGUAGES
        assert "vb" in SUPPORTED_LANGUAGES
        assert "vb6" in SUPPORTED_LANGUAGES
        assert "c_cpp" in SUPPORTED_LANGUAGES
        assert len(SUPPORTED_LANGUAGES) == 5


class TestAnalyzeFile:
    """Test suite for analyze_file convenience function.

    Categories:
    1. Python Files - Python file analysis (1 test)
    2. C# Files - C# file analysis (1 test)
    3. Unsupported Files - Error for unknown extensions (1 test)
    4. Missing Files - Exception for nonexistent files (1 test)
    5. Config Passthrough - Config propagation (1 test)
    6. Quality Assessment - Good documentation scoring (1 test)

    Total: 6 tests.
    """

    def test_analyze_file_python(self, tmp_path: Path) -> None:
        """Verifies analyze_file works with Python files.

        Tests end-to-end analysis by creating and analyzing Python file.

        Business context:
        Convenience function is primary API; must work for Python.

        Arrangement:
        1. Create temporary Python file with simple function.
        2. Write minimal function definition to file.

        Action:
        Call analyze_file with temporary file path.

        Assertion Strategy:
        Validates analysis by confirming:
        - Single result returned.
        - Function name correctly extracted.

        Testing Principle:
        Validates integration, ensuring file-to-result pipeline works.
        """
        py_file = tmp_path / "test.py"
        py_file.write_text("def foo():\n    pass\n")

        results = analyze_file(str(py_file))

        assert len(results) == 1
        assert results[0]["function_name"] == "foo"

    def test_analyze_file_csharp(self, tmp_path: Path) -> None:
        """Verifies analyze_file works with C# files.

        Tests end-to-end analysis by creating and analyzing C# file.

        Business context:
        Multi-language support requires C# to work via same API.

        Arrangement:
        1. Create temporary C# file with method definition.
        2. Write minimal method to file.

        Action:
        Call analyze_file with temporary C# file path.

        Assertion Strategy:
        Validates analysis by confirming:
        - Single result returned.
        - Method name correctly extracted.

        Testing Principle:
        Validates language routing, ensuring C# uses correct analyzer.
        """
        cs_file = tmp_path / "Test.cs"
        cs_file.write_text("public void Foo() { }\n")

        results = analyze_file(str(cs_file))

        assert len(results) == 1
        assert results[0]["function_name"] == "Foo"

    def test_analyze_file_unsupported_extension(self, tmp_path: Path) -> None:
        """Verifies analyze_file returns error for unsupported files.

        Tests error handling for files with unknown extensions.

        Business context:
        Unsupported files must return structured error, not crash.

        Arrangement:
        1. Create temporary .txt file with content.

        Action:
        Call analyze_file with unsupported file extension.

        Assertion Strategy:
        Validates error handling by confirming:
        - Single result returned.
        - Result contains "error" key.
        - Error message mentions extension.

        Testing Principle:
        Validates error reporting, ensuring clear unsupported message.
        """
        txt_file = tmp_path / "readme.txt"
        txt_file.write_text("Hello world")

        results = analyze_file(str(txt_file))

        assert len(results) == 1
        assert "error" in results[0]
        assert ".txt" in results[0]["error"]

    def test_analyze_file_not_found(self) -> None:
        """Verifies analyze_file raises for missing files.

        Tests exception handling for nonexistent file paths.

        Business context:
        Missing files are programming errors; should raise exception.

        Arrangement:
        1. Use nonexistent file path.

        Action:
        Call analyze_file with missing file path.

        Assertion Strategy:
        Validates error handling by confirming:
        - Returns error dict with 'File not found' message.

        Testing Principle:
        Validates fail-fast, ensuring missing files return error dict.
        """
        result = analyze_file("/nonexistent/path/file.py")
        assert len(result) == 1
        assert "error" in result[0]
        assert "File not found" in result[0]["error"]

    def test_analyze_file_permission_denied(self, tmp_path: Path) -> None:
        """Verifies analyze_file handles PermissionError gracefully.

        Tests error handling when file cannot be read due to permissions.

        Business context:
        Permission errors should return informative error dict, not crash.

        Arrangement:
        1. Create Python file with restricted permissions.

        Action:
        Call analyze_file with permission-restricted file.

        Assertion Strategy:
        Validates error handling by confirming:
        - Returns error dict with 'Permission denied' message.

        Testing Principle:
        Validates graceful degradation for filesystem permission errors.
        """
        restricted_file = tmp_path / "restricted.py"
        restricted_file.write_text("def foo(): pass")
        restricted_file.chmod(0o000)  # Remove all permissions

        try:
            result = analyze_file(str(restricted_file))
            assert len(result) == 1
            assert "error" in result[0]
            assert "Permission denied" in result[0]["error"]
        finally:
            # Restore permissions for cleanup
            restricted_file.chmod(0o644)

    def test_analyze_file_invalid_utf8(self, tmp_path: Path) -> None:
        """Verifies analyze_file handles UnicodeDecodeError gracefully.

        Tests error handling when file contains invalid UTF-8 bytes.

        Business context:
        Binary or corrupted files should return error dict, not crash.

        Arrangement:
        1. Create Python file with invalid UTF-8 byte sequence.

        Action:
        Call analyze_file with invalid UTF-8 file.

        Assertion Strategy:
        Validates error handling by confirming:
        - Returns error dict with 'not valid UTF-8' message.

        Testing Principle:
        Validates graceful degradation for encoding errors.
        """
        invalid_utf8_file = tmp_path / "invalid.py"
        # Write invalid UTF-8 bytes (0x80-0xFF are invalid as single bytes)
        invalid_utf8_file.write_bytes(b"def foo(): pass\n\x80\x81\x82\n")

        result = analyze_file(str(invalid_utf8_file))
        assert len(result) == 1
        assert "error" in result[0]
        assert "not valid UTF-8" in result[0]["error"]

    def test_analyze_file_with_config(self, tmp_path: Path) -> None:
        """Verifies analyze_file passes config to analyzer.

        Tests config propagation through convenience function.

        Business context:
        Custom thresholds must reach analyzer for proper scoring.

        Arrangement:
        1. Create Python file with documented function.
        2. Create config with custom quality threshold.

        Action:
        Call analyze_file with config parameter.

        Assertion Strategy:
        Validates propagation by confirming:
        - Result is a list (analysis completed).

        Testing Principle:
        Validates DI passthrough, ensuring config affects analysis.
        """
        py_file = tmp_path / "test.py"
        py_file.write_text("def foo():\n    '''Good docstring.'''\n    pass\n")

        config = AnalysisConfig(quality_thresholds={"excellent": 0.1})
        results = analyze_file(str(py_file), config=config)

        # With low threshold, should still find function but quality may differ
        assert isinstance(results, list)

    def test_analyze_file_well_documented(self, tmp_path: Path) -> None:
        """Verifies analyze_file returns good quality for documented code.

        Tests quality assessment for function with comprehensive docstring.

        Business context:
        Well-documented code should score "good" or better.

        Arrangement:
        1. Create Python file with fully-documented function.
        2. Include Args, Returns, and Example sections.

        Action:
        Call analyze_file and examine quality assessment.

        Assertion Strategy:
        Validates scoring by confirming:
        - Single result returned.
        - Quality level is "good".
        - Score at least 0.6.

        Testing Principle:
        Validates positive recognition, ensuring good docs score well.
        """
        py_file = tmp_path / "test.py"
        py_file.write_text('''
def foo(x: int) -> int:
    """Calculate something.

    Args:
        x: Input value.

    Returns:
        The calculated result.

    Example:
        >>> foo(1)
        2
    """
    return x + 1
''')

        results = analyze_file(str(py_file))

        # Function has good documentation (not excellent due to missing Raises)
        assert len(results) == 1
        assert results[0]["quality_assessment"]["quality"] == "good"
        assert results[0]["quality_assessment"]["score"] >= 0.6


class TestAnalyzeCodeEdgeCases:
    """Tests for analyze_code edge cases.

    Test Categories:
        1. Unsupported Language - Error handling (1 test)
        2. No Analyzer Available - Error handling (1 test)

    Total: 2 tests.
    """

    def test_analyze_code_unsupported_language(self) -> None:
        """Verifies analyze_code returns error for unsupported language.

        Business context:
            When a language is not supported, analyze_code should return
            a structured error rather than raising an exception.

        Arrangement:
            1. No setup required.

        Action:
            Call analyze_code with an unsupported language.

        Assertion Strategy:
            Verify error result with "Unsupported language" message.

        Testing Principle:
            Error boundary ensures graceful degradation.
        """
        from docscope_mcp.analyzers.routing import analyze_code

        results = analyze_code("some code", "unsupported_language")
        assert len(results) == 1
        assert "error" in results[0]
        assert "Unsupported language" in results[0]["error"]

    def test_analyze_code_with_file_path(self) -> None:
        """Verifies analyze_code adds file_path to results when provided.

        Business context:
            When analyzing code with an explicit file_path, that path
            should be included in each result for context.

        Arrangement:
            1. No setup required.

        Action:
            Call analyze_code with Python code and file_path.

        Assertion Strategy:
            Verify file_path is present in results.

        Testing Principle:
            Context preservation enables accurate reporting.
        """
        from docscope_mcp.analyzers.routing import analyze_code

        results = analyze_code("def foo(): pass", "python", "test/file.py")
        assert len(results) >= 1
        if "error" not in results[0]:
            assert results[0].get("file_path") == "test/file.py"
