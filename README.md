# docscope-mcp

Model Context Protocol (MCP) server that analyzes code to assess documentation quality and prioritize doc improvements.

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

Once installed, the `analyze_functions` MCP tool is available in VS Code Copilot and other MCP-compatible clients.

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
