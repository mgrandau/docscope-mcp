"""
Quality assessment models for documentation analysis.

Defines quality levels, thresholds, indicators, and assessment results.
These models are language-agnostic and used across all language analyzers.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal, TypedDict


class QualityLevel(Enum):
    """Documentation quality tiers mapping numeric scores to categorical assessments.

    Quality Tiers:
    • EXCELLENT (≥0.8): Complete documentation with all required sections
    • GOOD (≥0.6): Solid foundation with minor gaps
    • BASIC (≥0.3): Basic structure present but missing critical sections
    • POOR (<0.3): Minimal or no documentation

    Examples:
        ```python
        if score >= 0.8:
            level = QualityLevel.EXCELLENT
        elif score >= 0.6:
            level = QualityLevel.GOOD
        ```
    """

    EXCELLENT = "excellent"
    GOOD = "good"
    BASIC = "basic"
    POOR = "poor"


@dataclass(frozen=True)
class QualityThresholds:
    """Documentation quality assessment thresholds with configurable defaults.

    Thresholds calibrated based on:
    • Industry standards: PEP 257, Google Style Guide, NumPy docstring conventions
    • Readability research: Cognitive load studies for technical documentation

    Attributes:
        max_brief_lines: Maximum non-empty lines for brief description
        max_brief_lines_extended: Extended threshold when <100 chars
        min_brief_chars: Minimum characters to avoid brief classification
        min_detailed_lines_standard: Non-empty lines for standard function detail
        min_detailed_lines_test: Non-empty lines for test function detail
        min_detailed_chars_standard: Characters for standard detailed content
        min_detailed_chars_test: Characters for test detailed content
        min_comprehensive_chars_standard: Characters for full API docs
        min_comprehensive_chars_standard_terse: Terse notation threshold
        min_comprehensive_chars_test: Characters for test principles
        min_comprehensive_chars_test_terse: Terse test threshold
        complexity_medium: Threshold for medium complexity
        complexity_high: Threshold for high complexity
        max_param_priority_contribution: Cap on parameter count contribution
        min_bullet_points: Bullet points for structured list
        min_paragraph_breaks: Section breaks for structured content
    """

    # Brief description thresholds
    max_brief_lines: int = 1
    max_brief_lines_extended: int = 3
    min_brief_chars: int = 100

    # Detailed description thresholds
    min_detailed_lines_standard: int = 5
    min_detailed_lines_test: int = 10
    min_detailed_chars_standard: int = 200
    min_detailed_chars_test: int = 300

    # Comprehensive documentation thresholds
    min_comprehensive_chars_standard: int = 300
    min_comprehensive_chars_standard_terse: int = 150
    min_comprehensive_chars_test: int = 500
    min_comprehensive_chars_test_terse: int = 200

    # Complexity thresholds
    complexity_medium: int = 5
    complexity_high: int = 10

    # Priority calculation
    max_param_priority_contribution: int = 3

    # Terse notation detection
    min_bullet_points: int = 3
    min_paragraph_breaks: int = 2


# Default thresholds instance
DEFAULT_THRESHOLDS = QualityThresholds()

# Quality score thresholds mapping categorical levels to numeric ranges
QUALITY_SCORE_THRESHOLDS = {"excellent": 0.8, "good": 0.6, "basic": 0.3}


class QualityIndicators(TypedDict, total=False):
    """Individual docstring quality criteria.

    Uses total=False to allow partial indicator sets
    (standard functions have 8, test functions have 11).

    Standard Function Indicators (8):
        brief_description: First line is capitalized sentence ending with period
        detailed_description: Adequate length or terse complete
        args_section: Contains 'Args:' or 'Parameters:' section
        returns_section: Contains 'Returns:' or 'Return:' section
        raises_section: Contains 'Raises:' or 'Raise:' section
        example_section: Contains 'Example:' or 'Examples:' section
        business_context: Mentions business/purpose/context keywords
        implementation_details: Substantial content or terse complete

    Test Function Additional Indicators (3 more):
        arrangement_steps: Mentions Arrange/Setup/Given keywords
        action_description: Mentions Act/When/Execute keywords
        assertion_strategy: Mentions Assert/Then/Verify keywords
        testing_principles: Mentions Testing Principles/Test: keywords
        comprehensive_content: >500 chars or terse >200 chars
    """

    # Standard function indicators
    brief_description: bool
    detailed_description: bool
    args_section: bool
    returns_section: bool
    raises_section: bool
    example_section: bool
    business_context: bool
    implementation_details: bool

    # Test function additional indicators
    arrangement_steps: bool
    action_description: bool
    assertion_strategy: bool
    testing_principles: bool
    comprehensive_content: bool


class QualityAssessment(TypedDict):
    """Docstring quality evaluation results.

    Aggregates quality indicators into score and categorical level.

    Attributes:
        score: Numeric quality score 0.0-1.0 (proportion of indicators present)
        quality: Categorical level ('poor' | 'basic' | 'good' | 'excellent')
        indicators: Dict of individual quality criteria
        missing: List of missing indicator names for improvement guidance
        needs_improvement: True if quality score < excellent threshold
    """

    score: float
    quality: Literal["poor", "basic", "good", "excellent"]
    indicators: QualityIndicators
    missing: list[str]
    needs_improvement: bool
