# docscope-mcp

[![GitHub release](https://img.shields.io/github/v/release/mgrandau/docscope-mcp)](https://github.com/mgrandau/docscope-mcp/releases) [![CI](https://github.com/mgrandau/docscope-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/mgrandau/docscope-mcp/actions/workflows/ci.yml) [![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/) [![Type: mypy](https://img.shields.io/badge/type-mypy-blue.svg)](https://mypy-lang.org/) [![Security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

Scan your codebase and find the documentation that's missing, wrong, or outdated.

## 🧭 Intent

Code documentation serves two audiences: humans reading it later, and AI agents reading it now. This tool pushes toward **deliberate over-documentation** — a higher degree of documentation than normally called for, placing rich context directly adjacent to the code.

This matters especially for unit tests: in Python, docstrings surface in test failure output, so a well-documented test function gives you the *why* alongside the *what failed*. More broadly, the premise is that function-level documentation is the closest context to the code itself — closer than README files, architecture docs, or wikis. By enriching every function with detailed docstrings, you make the codebase self-describing for both humans and AI agents working within limited context windows.

The tool scans a codebase, scores every function's documentation quality, ranks them by priority, and surfaces the worst gaps — so you fix what matters instead of guessing. It makes documentation quality **measurable and triageable.**

The design follows the [Human-AI Intent Transfer Principles](https://mgrandau.medium.com/human-ai-intent-transfer-principles-b6e7404e3d26?source=friends_link&sk=858917bd3f4a686974ed6b6c9c059ac8): the MCP interface keeps analysis in the conversation flow (intent leads), the quality scores make assessment inspectable, and the priority rankings calibrate effort by consequence.

These principles shaped the project itself: the [project plan](docs/PROJECT_PLAN.md) documents goals and risk posture per phase, and the [journal](docs/journal/2025-12-11.md) captures the design tradeoffs — including why regex parsing was chosen over external AST libraries despite its known accuracy limits.

## Installation

```bash
pip install git+https://github.com/mgrandau/docscope-mcp.git
```

Then configure VS Code to use the MCP server:

```bash
docscope-mcp install
```

This adds the server to `.vscode/mcp.json` in your current workspace. Reload VS Code to activate.

Workspace installs also copy:

- **Prompts** → `.github/prompts/` (AI prompt templates for code analysis)
- **Utils** → `utils/` (batch analysis scripts)

### Global Install (Optional)

To install globally for all VS Code workspaces:

```bash
# VS Code (stable)
docscope-mcp install --global

# VS Code Insiders
docscope-mcp install --global --insiders
```

## Usage

### MCP Server (VS Code Copilot)

Once installed, the `analyze_functions` MCP tool is available in VS Code Copilot and other MCP-compatible clients.

### CLI Analysis

Analyze source files directly from the command line, useful for CI/CD pipelines, scripts, and terminal-based workflows:

```bash
# Analyze a single file
docscope-mcp analyze src/main.py

# Analyze multiple files
docscope-mcp analyze src/*.py

# JSON output for pipelines
docscope-mcp analyze src/main.py --format json

# Analyze inline code (requires --language)
docscope-mcp analyze --code "def foo(): pass" --language python

# Short flags
docscope-mcp analyze -c "def foo(): pass" -l python -f json
```

**Supported languages**: `python`, `csharp`, `vb`, `vb6`, `c_cpp`

## Uninstall

```bash
# Workspace
docscope-mcp uninstall

# Global (stable)
docscope-mcp uninstall --global

# Global (Insiders)
docscope-mcp uninstall --global --insiders
```

## Architecture Documentation

For AI-readable architectural contracts and detailed component documentation:

| Doc | Purpose |
|-----|---------|
| [src/docscope_mcp/README.md](src/docscope_mcp/README.md) | Core package architecture (server, analyzers, models) |
| [tests/README.md](tests/README.md) | Test suite architecture, MockFilesystemAdapter |
| [utils/README.md](utils/README.md) | Batch analysis utilities |

## 💬 Community

💬 [Join the Discord community](https://discord.gg/2KqjHvh5)

