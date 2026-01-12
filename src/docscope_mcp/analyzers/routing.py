"""
Language detection and analyzer routing.

Provides utilities for detecting programming languages from file extensions
and routing to the appropriate analyzer instance.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, cast

from docscope_mcp.analyzers.c_cpp import CCppAnalyzer
from docscope_mcp.analyzers.csharp import CSharpAnalyzer
from docscope_mcp.analyzers.python import PythonAnalyzer
from docscope_mcp.analyzers.vb import VBAnalyzer
from docscope_mcp.analyzers.vb6 import VB6Analyzer

if TYPE_CHECKING:
    from docscope_mcp.analyzers.base import BaseAnalyzer
    from docscope_mcp.models import AnalysisConfig

# File extension to language mapping
EXTENSION_MAP: Final[dict[str, str]] = {
    # Python
    ".py": "python",
    ".pyi": "python",
    ".pyw": "python",
    # C#
    ".cs": "csharp",
    # VB.NET
    ".vb": "vb",
    # VB6 (Classic Visual Basic)
    ".bas": "vb6",
    ".cls": "vb6",
    ".frm": "vb6",
    # C/C++
    ".c": "c_cpp",
    ".cpp": "c_cpp",
    ".cxx": "c_cpp",
    ".cc": "c_cpp",
    ".c++": "c_cpp",
    ".h": "c_cpp",
    ".hpp": "c_cpp",
    ".hxx": "c_cpp",
    ".hh": "c_cpp",
    ".h++": "c_cpp",
}

# Language to analyzer class mapping
# Note: Each analyzer class accepts (config: AnalysisConfig | None = None)
ANALYZER_MAP: Final[dict[str, type[Any]]] = {
    "python": PythonAnalyzer,
    "csharp": CSharpAnalyzer,
    "vb": VBAnalyzer,
    "vb6": VB6Analyzer,
    "c_cpp": CCppAnalyzer,
}

# Supported languages list
SUPPORTED_LANGUAGES: Final[list[str]] = list(ANALYZER_MAP.keys())


def detect_language(file_path: str) -> str | None:
    """Detect programming language from file path extension.

    Examines the file extension to determine the programming language.
    Returns None if the language is not supported.

    Args:
        file_path: Path to the source file (can be relative or absolute).

    Returns:
        Language identifier string ('python', 'csharp', 'vb', 'vb6', 'c_cpp')
        or None if not recognized.

    Raises:
        No exceptions raised.

    Examples:
        >>> detect_language('src/main.py')
        'python'
        >>> detect_language('Program.cs')
        'csharp'
        >>> detect_language('Module1.bas')
        'vb6'
        >>> detect_language('unknown.xyz')
        None
    """
    ext = Path(file_path).suffix.lower()
    return EXTENSION_MAP.get(ext)


def get_analyzer(
    language: str,
    config: "AnalysisConfig | None" = None,
) -> "BaseAnalyzer | None":
    """Get an analyzer instance for the specified language.

    Creates and returns an analyzer configured for the given language.
    Returns None if the language is not supported.

    Args:
        language: Language identifier ('python', 'csharp', 'vb', 'vb6', 'c_cpp').
        config: Optional analysis configuration to pass to the analyzer.

    Returns:
        Configured analyzer instance or None if language not supported.

    Raises:
        No exceptions raised.

    Examples:
        >>> analyzer = get_analyzer('python')
        >>> analyzer.get_language()
        'python'
        >>> get_analyzer('unknown')
        None
    """
    analyzer_class = ANALYZER_MAP.get(language)
    if analyzer_class is None:
        return None
    return cast("BaseAnalyzer", analyzer_class(config=config))


def get_analyzer_for_file(
    file_path: str,
    config: "AnalysisConfig | None" = None,
) -> "BaseAnalyzer | None":
    """Get an analyzer instance appropriate for the given file.

    Combines language detection and analyzer creation. Examines the file
    extension to determine the language, then returns a configured analyzer.

    Args:
        file_path: Path to the source file.
        config: Optional analysis configuration to pass to the analyzer.

    Returns:
        Configured analyzer instance or None if file type not supported.

    Raises:
        No exceptions raised.

    Examples:
        >>> analyzer = get_analyzer_for_file('src/main.py')
        >>> analyzer.get_language()
        'python'
        >>> analyzer = get_analyzer_for_file('Program.cs')
        >>> analyzer.get_language()
        'csharp'
    """
    language = detect_language(file_path)
    if language is None:
        return None
    return get_analyzer(language, config)


def get_supported_extensions() -> list[str]:
    """Get list of all supported file extensions.

    Returns all file extensions that can be analyzed, enabling callers
    to filter files or validate inputs before analysis.

    Args:
        None - reads from module-level EXTENSION_MAP.

    Returns:
        List of file extensions (including dot) that are supported.

    Raises:
        No exceptions raised.

    Examples:
        >>> exts = get_supported_extensions()
        >>> '.py' in exts
        True
        >>> '.cs' in exts
        True
    """
    return list(EXTENSION_MAP.keys())


def get_extensions_for_language(language: str) -> list[str]:
    """Get file extensions associated with a language.

    Args:
        language: Language identifier.

    Returns:
        List of file extensions for the language, empty if not found.

    Raises:
        No exceptions raised.

    Examples:
        >>> get_extensions_for_language('python')
        ['.py', '.pyi', '.pyw']
        >>> get_extensions_for_language('vb6')
        ['.bas', '.cls', '.frm']
    """
    return [ext for ext, lang in EXTENSION_MAP.items() if lang == language]


def is_supported_file(file_path: str) -> bool:
    """Check if a file type is supported for analysis.

    Args:
        file_path: Path to check.

    Returns:
        True if the file extension is supported, False otherwise.

    Raises:
        No exceptions raised.

    Examples:
        >>> is_supported_file('main.py')
        True
        >>> is_supported_file('readme.md')
        False
    """
    return detect_language(file_path) is not None


def analyze_file(
    file_path: str,
    config: "AnalysisConfig | None" = None,
) -> list[dict[str, Any]]:
    """Convenience function: read file and analyze in one step.

    Reads the file content, detects language from extension, runs
    the appropriate analyzer, and adds file_path to each result.

    Args:
        file_path: Path to the source file to analyze.
        config: Optional analysis configuration.

    Returns:
        List of function analysis results with file_path added,
        or error dict if file cannot be read or language not supported.

    Raises:
        No exceptions raised - errors returned in result list.

    Examples:
        >>> results = analyze_file('src/main.py')
        >>> for r in results:
        ...     print(f"{r['function_name']}: priority {r['priority']}")

        >>> results = analyze_file('unknown.xyz')
        >>> results[0]['error']
        'Unsupported file type: .xyz'
    """
    path = Path(file_path)

    # Detect language
    language = detect_language(file_path)
    if language is None:
        return [{"error": f"Unsupported file type: {path.suffix}"}]

    # Read file content
    try:
        code = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [{"error": f"File not found: {file_path}"}]
    except PermissionError:
        return [{"error": f"Permission denied: {file_path}"}]
    except UnicodeDecodeError:
        return [{"error": f"File is not valid UTF-8: {file_path}"}]

    # Get analyzer and run
    analyzer = get_analyzer(language, config)
    if analyzer is None:
        return [{"error": f"No analyzer for language: {language}"}]

    results = analyzer.analyze(code)

    # Add file_path to each result
    for result in results:
        if "error" not in result:
            result["file_path"] = file_path

    return results


def analyze_code(
    code: str,
    language: str,
    file_path: str = "",
    config: "AnalysisConfig | None" = None,
) -> list[dict[str, Any]]:
    """Analyze code string with explicit language specification.

    For use when you have code in memory and know the language.
    Optionally adds file_path to results for context.

    Args:
        code: Source code string to analyze.
        language: Language identifier ('python', 'csharp', 'vb', 'vb6', 'c_cpp').
        file_path: Optional file path to include in results.
        config: Optional analysis configuration.

    Returns:
        List of function analysis results, or error dict if
        language not supported.

    Examples:
        >>> results = analyze_code('def foo(): pass', 'python')
        >>> results[0]['function_name']
        'foo'

        >>> results = analyze_code('public void Bar() {}', 'csharp', 'Program.cs')
        >>> results[0]['file_path']
        'Program.cs'
    """
    analyzer = get_analyzer(language, config)
    if analyzer is None:
        return [{"error": f"Unsupported language: {language}"}]

    results = analyzer.analyze(code)

    # Add file_path to each result if provided
    if file_path:
        for result in results:
            if "error" not in result:
                result["file_path"] = file_path

    return results
