"""Basic tests for docscope-mcp."""

from docscope_mcp import __version__
from docscope_mcp.analyzers.python import PythonAnalyzer
from docscope_mcp.server import DocScopeMCPServer


def test_version() -> None:
    """Verifies package version is correctly defined.

    Tests version string export.

    Business context:
    Package version is used by pip, PDM, and MCP protocol initialization.

    Arrangement:
    1. Import __version__ from package.

    Action:
    Compare version string to expected value.

    Assertion Strategy:
    Validates version equals '1.0.0' (current release).
    """
    assert __version__ == "1.0.0"


def test_python_analyzer_available() -> None:
    """Verifies PythonAnalyzer is importable and functional.

    Tests package exports work correctly.

    Business context:
    Analyzer is the core component for documentation quality assessment.

    Arrangement:
    1. Import PythonAnalyzer from package.

    Action:
    Create analyzer and check language.

    Assertion Strategy:
    Validates get_language() returns 'python'.
    """
    analyzer = PythonAnalyzer()
    assert analyzer.get_language() == "python"


def test_server_available() -> None:
    """Verifies DocScopeMCPServer is importable and registers tools.

    Tests MCP server initialization.

    Business context:
    Server must register analyze_functions tool for VS Code integration.

    Arrangement:
    1. Import DocScopeMCPServer from package.

    Action:
    Create server and check tools dict.

    Assertion Strategy:
    Validates 'analyze_functions' in server.tools.
    """
    server = DocScopeMCPServer()
    assert "analyze_functions" in server.tools
