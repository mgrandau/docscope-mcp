"""
DocScope MCP Server.

PURPOSE: MCP server for documentation quality analysis across multiple languages.
AI CONTEXT: This package provides an MCP server for analyzing and prioritizing
documentation improvements using AST-based analysis and quality scoring.

PACKAGE STRUCTURE:
- server.py: MCP server with JSON-RPC 2.0 message handling
- models/: Data models for quality assessment and analysis
- analyzers/: Language-specific documentation analyzers
- filesystem.py: Filesystem abstraction for testability

QUICK START:
    # Run MCP server
    python -m docscope_mcp.server

    # Use analyzer directly
    from docscope_mcp.analyzers.python import PythonAnalyzer
    analyzer = PythonAnalyzer()
    results = analyzer.analyze(code, "example.py")

MCP TOOLS:
1. analyze_functions - Analyze code and identify functions needing documentation
"""

from docscope_mcp.__version__ import (
    __author__,
    __copyright__,
    __description__,
    __license__,
    __title__,
    __url__,
    __version__,
    __version_date__,
)

__all__ = [
    "__version__",
    "__version_date__",
    "__title__",
    "__description__",
    "__url__",
    "__author__",
    "__license__",
    "__copyright__",
]
