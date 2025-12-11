"""
DocScope MCP Models.

Core data structures for documentation quality analysis.
Language-agnostic models enabling multi-language extensibility.
"""

from docscope_mcp.models.analysis import (
    ArgInfo,
    FunctionAnalysis,
    FunctionInfo,
)
from docscope_mcp.models.config import (
    DEFAULT_CONFIG,
    AnalysisConfig,
)
from docscope_mcp.models.quality import (
    QualityAssessment,
    QualityIndicators,
    QualityLevel,
    QualityThresholds,
)

__all__ = [
    # Quality models
    "QualityAssessment",
    "QualityIndicators",
    "QualityLevel",
    "QualityThresholds",
    # Analysis models
    "ArgInfo",
    "FunctionInfo",
    "FunctionAnalysis",
    # Configuration
    "AnalysisConfig",
    "DEFAULT_CONFIG",
]
