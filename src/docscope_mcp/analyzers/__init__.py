"""
DocScope Analyzers Package.

Language-specific documentation analyzers.
Each analyzer implements the BaseAnalyzer protocol.

Supported languages:
- Python: AST-based analysis with Google/NumPy docstring support
- C#: Regex-based analysis with XML documentation comment support
- VB.NET: Regex-based analysis with XML documentation comment support
- VB6: Regex-based analysis with traditional comment block support
- C/C++: Regex-based analysis with Doxygen documentation support
"""

from docscope_mcp.analyzers.base import BaseAnalyzer
from docscope_mcp.analyzers.c_cpp import CCppAnalyzer
from docscope_mcp.analyzers.csharp import CSharpAnalyzer
from docscope_mcp.analyzers.priority import PriorityCalculationMixin
from docscope_mcp.analyzers.python import PythonAnalyzer
from docscope_mcp.analyzers.quality import QualityAssessmentMixin
from docscope_mcp.analyzers.routing import (
    EXTENSION_MAP,
    SUPPORTED_LANGUAGES,
    analyze_code,
    analyze_file,
    detect_language,
    get_analyzer,
    get_analyzer_for_file,
    get_extensions_for_language,
    get_supported_extensions,
    is_supported_file,
)
from docscope_mcp.analyzers.vb import VBAnalyzer
from docscope_mcp.analyzers.vb6 import VB6Analyzer

__all__ = [
    # Analyzers
    "BaseAnalyzer",
    "CCppAnalyzer",
    "CSharpAnalyzer",
    "PriorityCalculationMixin",
    "PythonAnalyzer",
    "QualityAssessmentMixin",
    "VB6Analyzer",
    "VBAnalyzer",
    # Routing utilities
    "EXTENSION_MAP",
    "SUPPORTED_LANGUAGES",
    "analyze_code",
    "analyze_file",
    "detect_language",
    "get_analyzer",
    "get_analyzer_for_file",
    "get_extensions_for_language",
    "get_supported_extensions",
    "is_supported_file",
]
