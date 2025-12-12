# Contributing to DocScope MCP

Thank you for your interest in contributing to DocScope MCP!

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/mgrandau/docscope-mcp.git
   cd docscope-mcp
   ```

2. **Install PDM** (if not already installed)
   ```bash
   pip install pdm
   ```

3. **Install dependencies**
   ```bash
   pdm install --dev
   ```

4. **Install pre-commit hooks**
   ```bash
   pdm run pre-commit install
   ```

## Development Workflow

### Running Tests

```bash
# Run all tests
pdm run test

# Run with coverage
pdm run test-cov

# Run specific test file
pdm run pytest tests/test_analyzer.py -v
```

### Code Quality

```bash
# Lint code
pdm run lint

# Format code
pdm run format

# Type check
pdm run typecheck

# Security scan
pdm run security

# Run all checks
pdm run check-all
```

### Syncing Assets

Before building, sync prompts and utils to assets directory:

```bash
pdm run sync-assets
```

## Code Standards

- **Type hints**: All functions must have complete type annotations
- **Docstrings**: Follow Google style with Args/Returns/Raises/Example
- **Tests**: Maintain 80%+ coverage (currently 98%)
- **Linting**: Code must pass ruff, mypy, and bandit checks

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with tests
3. Run `pdm run check-all` to verify
4. Submit PR with clear description
5. Address review feedback

## Architecture

See architecture documentation in:
- [src/docscope_mcp/README.md](src/docscope_mcp/README.md) - Core package
- [tests/README.md](tests/README.md) - Test suite
- [utils/README.md](utils/README.md) - Batch utilities

## Questions?

Open an issue for questions or discussion.
