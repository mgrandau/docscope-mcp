"""Basic tests for docscope-mcp."""

from docscope_mcp import __version__
from docscope_mcp.analyzers.python import PythonAnalyzer
from docscope_mcp.server import DocScopeMCPServer


def test_version() -> None:
    """Test that version is defined."""
    assert __version__ == "0.1.0"


def test_python_analyzer_available() -> None:
    """Test Python analyzer can be imported and created."""
    analyzer = PythonAnalyzer()
    assert analyzer.get_language() == "python"


def test_server_available() -> None:
    """Test MCP server can be imported and created."""
    server = DocScopeMCPServer()
    assert "analyze_functions" in server.tools
