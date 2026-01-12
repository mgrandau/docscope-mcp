"""Basic tests for docscope-mcp."""

import re

from docscope_mcp import __version__
from docscope_mcp.analyzers.python import PythonAnalyzer
from docscope_mcp.server import DocScopeMCPServer

# Semantic versioning pattern: MAJOR.MINOR.PATCH with optional pre-release/build
SEMVER_PATTERN = re.compile(
    r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+)?$"
)


def test_version() -> None:
    """Verifies package version is a valid semantic version string.

    Tests version string export and format.

    Business context:
    Package version is used by pip, PDM, and MCP protocol initialization.
    Must follow semantic versioning (MAJOR.MINOR.PATCH).

    Arrangement:
    1. Import __version__ from package.

    Action:
    Validate version string matches semver pattern.

    Assertion Strategy:
    Validates __version__ is a non-empty string matching semver format.
    """
    assert isinstance(__version__, str), "__version__ must be a string"
    assert __version__, "__version__ must not be empty"
    assert SEMVER_PATTERN.match(
        __version__
    ), f"__version__ '{__version__}' is not a valid semver string"


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
    Server must register analyze_code and analyze_file tools for VS Code integration.

    Arrangement:
    1. Import DocScopeMCPServer from package.

    Action:
    Create server and check tools dict.

    Assertion Strategy:
    Validates 'analyze_code' and 'analyze_file' in server.tools.
    """
    server = DocScopeMCPServer()
    assert "analyze_code" in server.tools
    assert "analyze_file" in server.tools
