"""C/C++ Documentation Analyzer Package.

Provides C/C++-specific documentation analysis using regex-based parsing
and multi-criteria quality assessment for Doxygen-style documentation.
"""

from docscope_mcp.analyzers.c_cpp.analyzer import CCppAnalyzer

__all__ = ["CCppAnalyzer"]
