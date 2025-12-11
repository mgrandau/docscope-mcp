"""
Analysis result models for documentation analysis.

Defines function metadata and analysis results.
These models are language-agnostic where possible.
"""

from typing import TypedDict

from docscope_mcp.models.quality import QualityAssessment


class ArgInfo(TypedDict):
    """Function argument metadata.

    Attributes:
        name: Parameter name (e.g., 'self', 'value', 'config')
        type_annotation: Type hint string if present, None if untyped
        default: Default value string if present, None if required
    """

    name: str
    type_annotation: str | None
    default: str | None


class FunctionInfo(TypedDict):
    """Function metadata extracted from source analysis.

    Attributes:
        name: Function/method name without class prefix
        line: Line number where function is defined (1-indexed)
        complexity: Cyclomatic complexity score
        is_private: True if name starts with underscore
        is_test: True if name/module matches test patterns
        args: List of parameter metadata
        returns: Return type annotation string if present
        decorators: List of decorator names applied to function
        current_docstring: Existing docstring text or empty string
    """

    name: str
    line: int
    complexity: int
    is_private: bool
    is_test: bool
    args: list[ArgInfo]
    returns: str | None
    decorators: list[str]
    current_docstring: str


class FunctionAnalysis(TypedDict):
    """Complete function analysis result.

    Combines function metadata, quality assessment, and priority score.

    Attributes:
        name: Function name
        line: Line number where defined
        is_private: Whether name starts with underscore
        is_test: Whether matches test function patterns
        complexity: Cyclomatic complexity score
        param_count: Number of parameters (excluding 'self')
        has_return: Whether function has return type annotation
        current_docstring: Existing docstring text or empty string
        quality_assessment: Full quality evaluation
        priority: Priority score (higher = more urgent improvement needed)
    """

    name: str
    line: int
    is_private: bool
    is_test: bool
    complexity: int
    param_count: int
    has_return: bool
    current_docstring: str
    quality_assessment: QualityAssessment
    priority: int
