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
        """Test all quality levels are defined."""
        assert QualityLevel.EXCELLENT.value == "excellent"
        assert QualityLevel.GOOD.value == "good"
        assert QualityLevel.BASIC.value == "basic"
        assert QualityLevel.POOR.value == "poor"

    def test_quality_level_count(self) -> None:
        """Test correct number of quality levels."""
        assert len(QualityLevel) == 4


class TestQualityThresholds:
    """Tests for QualityThresholds dataclass."""

    def test_default_thresholds(self) -> None:
        """Test default threshold values."""
        thresholds = QualityThresholds()
        assert thresholds.max_brief_lines == 1
        assert thresholds.min_brief_chars == 100
        assert thresholds.complexity_high == 10
        assert thresholds.complexity_medium == 5

    def test_thresholds_immutable(self) -> None:
        """Test thresholds are frozen (immutable)."""
        thresholds = QualityThresholds()
        with pytest.raises(AttributeError):
            thresholds.max_brief_lines = 5  # type: ignore[misc]

    def test_custom_thresholds(self) -> None:
        """Test custom threshold values."""
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
        """Test default configuration values."""
        config = AnalysisConfig()
        assert config.max_code_size == 5 * 1024 * 1024
        assert config.max_results_display == 10
        assert config.min_docstring_length == 10

    def test_default_config_singleton(self) -> None:
        """Test DEFAULT_CONFIG is properly initialized."""
        assert DEFAULT_CONFIG.max_code_size == 5 * 1024 * 1024
        assert isinstance(DEFAULT_CONFIG.thresholds, QualityThresholds)

    def test_config_to_dict(self) -> None:
        """Test config conversion to dictionary."""
        config = AnalysisConfig()
        config_dict = config.to_dict()
        assert "quality_thresholds" in config_dict
        assert "max_code_size" in config_dict
        assert config_dict["max_code_size"] == 5 * 1024 * 1024

    def test_custom_config(self) -> None:
        """Test custom configuration."""
        config = AnalysisConfig(
            max_code_size=1024,
            max_results_display=5,
        )
        assert config.max_code_size == 1024
        assert config.max_results_display == 5
