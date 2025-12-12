# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-11

### Added

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

### Added

- Initial development release
- Core analyzer functionality
- Basic MCP server implementation
