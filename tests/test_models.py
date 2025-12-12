"""Tests for docscope-mcp models."""

import pytest

from docscope_mcp.models import (
    DEFAULT_CONFIG,
    AnalysisConfig,
    QualityLevel,
    QualityThresholds,
)


class TestQualityLevel:
    """Tests for QualityLevel enum."""

    def test_quality_levels_exist(self) -> None:
        """Verifies all four quality levels are defined with correct values.

        Tests enum completeness.

        Business context:
        Quality levels map to priority thresholds for documentation improvement.

        Arrangement:
        1. Import QualityLevel enum.

        Action:
        Access each enum value.

        Assertion Strategy:
        Validates all four levels have expected string values.
        """
        assert QualityLevel.EXCELLENT.value == "excellent"
        assert QualityLevel.GOOD.value == "good"
        assert QualityLevel.BASIC.value == "basic"
        assert QualityLevel.POOR.value == "poor"

    def test_quality_level_count(self) -> None:
        """Verifies exactly four quality levels exist.

        Tests enum boundary.

        Business context:
        Adding levels requires updating priority calculation logic.

        Arrangement:
        1. Import QualityLevel enum.

        Action:
        Count enum members.

        Assertion Strategy:
        Validates len(QualityLevel) == 4.
        """
        assert len(QualityLevel) == 4


class TestQualityThresholds:
    """Tests for QualityThresholds dataclass."""

    def test_default_thresholds(self) -> None:
        """Verifies QualityThresholds has sensible default values.

        Tests default configuration.

        Business context:
        Defaults must work for typical Python projects without customization.

        Arrangement:
        1. Create QualityThresholds with no arguments.

        Action:
        Access threshold attributes.

        Assertion Strategy:
        Validates max_brief_lines=1, min_brief_chars=100, complexity defaults.
        """
        thresholds = QualityThresholds()
        assert thresholds.max_brief_lines == 1
        assert thresholds.min_brief_chars == 100
        assert thresholds.complexity_high == 10
        assert thresholds.complexity_medium == 5

    def test_thresholds_immutable(self) -> None:
        """Verifies QualityThresholds is frozen (immutable).

        Tests dataclass frozen=True.

        Business context:
        Prevents accidental modification of shared config during analysis.

        Arrangement:
        1. Create QualityThresholds instance.

        Action:
        Attempt to modify attribute.

        Assertion Strategy:
        Validates AttributeError raised on assignment.
        """
        thresholds = QualityThresholds()
        with pytest.raises(AttributeError):
            thresholds.max_brief_lines = 5  # type: ignore[misc]

    def test_custom_thresholds(self) -> None:
        """Verifies custom threshold values override defaults.

        Tests configuration flexibility.

        Business context:
        Different projects may have stricter documentation requirements.

        Arrangement:
        1. Create QualityThresholds with custom values.

        Action:
        Check both custom and default attributes.

        Assertion Strategy:
        Validates custom values applied, defaults unchanged.
        """
        thresholds = QualityThresholds(
            max_brief_lines=3,
            complexity_high=15,
        )
        assert thresholds.max_brief_lines == 3
        assert thresholds.complexity_high == 15
        # Unchanged defaults
        assert thresholds.min_brief_chars == 100


class TestAnalysisConfig:
    """Tests for AnalysisConfig dataclass."""

    def test_default_config(self) -> None:
        """Verifies AnalysisConfig has sensible default values.

        Tests default configuration.

        Business context:
        Defaults must handle typical file sizes without modification.

        Arrangement:
        1. Create AnalysisConfig with no arguments.

        Action:
        Check size and display limit attributes.

        Assertion Strategy:
        Validates 5MB max size, 10 result limit, 10 char min docstring.
        """
        config = AnalysisConfig()
        assert config.max_code_size == 5 * 1024 * 1024
        assert config.max_results_display == 10
        assert config.min_docstring_length == 10

    def test_default_config_singleton(self) -> None:
        """Verifies DEFAULT_CONFIG module constant is properly initialized.

        Tests singleton availability.

        Business context:
        Shared default config avoids repeated instantiation.

        Arrangement:
        1. Import DEFAULT_CONFIG from models.

        Action:
        Check type and attributes.

        Assertion Strategy:
        Validates config values and thresholds type.
        """
        assert DEFAULT_CONFIG.max_code_size == 5 * 1024 * 1024
        assert isinstance(DEFAULT_CONFIG.thresholds, QualityThresholds)

    def test_config_to_dict(self) -> None:
        """Verifies config converts to dict for JSON serialization.

        Tests to_dict method.

        Business context:
        Config must serialize for MCP protocol responses.

        Arrangement:
        1. Create default AnalysisConfig.

        Action:
        Call to_dict and examine structure.

        Assertion Strategy:
        Validates dict contains expected keys with correct values.
        """
        config = AnalysisConfig()
        config_dict = config.to_dict()
        assert "quality_thresholds" in config_dict
        assert "max_code_size" in config_dict
        assert config_dict["max_code_size"] == 5 * 1024 * 1024

    def test_custom_config(self) -> None:
        """Verifies custom config values override defaults.

        Tests configuration injection.

        Business context:
        Enables per-analysis customization via MCP tool arguments.

        Arrangement:
        1. Create AnalysisConfig with custom values.

        Action:
        Check custom attributes.

        Assertion Strategy:
        Validates custom values applied correctly.
        """
        config = AnalysisConfig(
            max_code_size=1024,
            max_results_display=5,
        )
        assert config.max_code_size == 1024
        assert config.max_results_display == 5
