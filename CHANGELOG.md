# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-01-12

Multi-language support release: adds C#, VB.NET, VB6, and C/C++ analyzers alongside existing Python support.

### Added

- **C# Analyzer**: Regex-based analyzer for C# XML documentation comments
- **VB.NET Analyzer**: Regex-based analyzer for VB.NET XML documentation comments
- **VB6 Analyzer**: Regex-based analyzer for VB6/VBA comment blocks
- **C/C++ Analyzer**: Regex-based analyzer for Doxygen-style documentation
- `PriorityCalculationMixin` - shared priority scoring logic for all analyzers
- `QualityAssessmentMixin` - shared quality assessment logic for all analyzers (DRY refactor)
- `_validate_signature_coverage()` method in `QualityAssessmentMixin` - unified signature validation
- `FunctionAnalysisResult` TypedDict for type-safe analysis results
- Quality gap thresholds (`quality_gap_poor`, `quality_gap_basic`, `quality_gap_good`) in `QualityThresholds`
- `analyzers/README.md` with package documentation and AI task map
- CLI dependency injection via `FilesystemAdapter` for isolated testing
- Configuration validation in `AnalysisConfig.__post_init__()` for thresholds and limits

### Changed

- All analyzers now inherit from `QualityAssessmentMixin` and `PriorityCalculationMixin` (eliminates ~800 lines of duplication)
- `_sort_by_priority()` moved to `PriorityCalculationMixin`
- Quality scoring logic (`_calculate_indicator_score`, `_determine_quality_level`, `_identify_missing_elements`) moved to `QualityAssessmentMixin`
- Unified test function detection via `_is_test_function_common()` in `QualityAssessmentMixin`
- `_validate_signature_coverage()` moved from individual analyzers to `QualityAssessmentMixin`
- Quality gap scoring now uses configurable thresholds instead of hardcoded values
- `AnalysisConfig.to_dict()` now includes `thresholds` field
- CLI functions (`install_mcp`, `uninstall_mcp`, `copy_assets`) now accept optional `fs` and `workspace` parameters
- CLI tests refactored to use `MockFilesystemAdapter` instead of patching `Path.cwd`
- VB6Analyzer now uses `config.min_docstring_length` instead of hardcoded value

### Removed

- `_is_test_method()` from CSharpAnalyzer, VBAnalyzer (replaced by mixin's `_is_test_function_common()`)
- `_is_test_procedure()` from VB6Analyzer (replaced by mixin's `_is_test_function_common()`)
- `_is_test_function()` from CCppAnalyzer (replaced by mixin's `_is_test_function_common()`)
- Duplicate `_validate_signature_coverage()` implementations from all analyzers

### Fixed

- `__init__.py` docstring now correctly references `analyze_code` and `analyze_file` tools

## [1.0.0] - 2025-12-11

### Added (1.0.0)

- **MCP Server**: JSON-RPC 2.0 server for documentation quality analysis
- **Python Analyzer**: AST-based analyzer with multi-criteria quality assessment
- **CLI Tools**: `docscope-mcp install/uninstall` for VS Code configuration
- **VS Code Insiders Support**: `--insiders` flag for global installs
- **Asset Bundling**: Prompts and utils copied on workspace install
- **Architecture Documentation**: AI-readable contracts in component READMEs
- **Quality Scoring**: Configurable thresholds for excellent/good/basic/poor
- **Priority Calculation**: Factor-based ranking for documentation urgency
- **Security Protections**: Code size limits, AST depth limits, parse timeouts
- **Test Suite**: 111 tests with 98% coverage
- **CI/CD**: GitHub Actions workflow for lint, typecheck, security, tests

### Security

- Path traversal protection via `PathSecurityValidator`
- Symlink target validation against workspace boundaries
- DoS protection via configurable size/depth/timeout limits

## [0.1.0] - 2025-12-01

### Added (0.1.0)

- Initial development release
- Core analyzer functionality
- Basic MCP server implementation
