"""
Configuration models for DocScope MCP.

Defines analysis configuration and defaults.
"""

from dataclasses import dataclass, field
from typing import Any

from docscope_mcp.models.quality import (
    QUALITY_SCORE_THRESHOLDS,
    QualityThresholds,
)


@dataclass
class AnalysisConfig:
    """Configuration for documentation analysis.

    Attributes:
        quality_thresholds: Score thresholds for quality levels
        thresholds: Detailed quality assessment thresholds
        max_code_size: Maximum code size in bytes (5MB default)
        max_results_display: Maximum results to display
        min_docstring_length: Minimum docstring length to consider meaningful
        max_ast_nodes: Maximum AST nodes allowed (DoS protection)
        max_ast_depth: Maximum nesting depth (DoS protection)
        ast_parse_timeout: Seconds before parse timeout
        max_file_path_length: Maximum file path length
    """

    quality_thresholds: dict[str, float] = field(
        default_factory=lambda: dict(QUALITY_SCORE_THRESHOLDS)
    )
    thresholds: QualityThresholds = field(default_factory=QualityThresholds)

    # Size limits
    max_code_size: int = 5 * 1024 * 1024  # 5MB
    max_results_display: int = 10
    min_docstring_length: int = 10

    # AST DoS protection limits
    max_ast_nodes: int = 50000
    max_ast_depth: int = 100
    ast_parse_timeout: int = 5

    # File path validation
    max_file_path_length: int = 4096

    # Display formatting
    docstring_preview_length: int = 300
    max_missing_elements_display: int = 3

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary for compatibility."""
        return {
            "quality_thresholds": self.quality_thresholds,
            "max_code_size": self.max_code_size,
            "max_results_display": self.max_results_display,
            "min_docstring_length": self.min_docstring_length,
        }


# Default configuration instance
DEFAULT_CONFIG = AnalysisConfig()
