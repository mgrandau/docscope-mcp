"""Command-line interface for docscope-mcp.

Provides installation and management commands for the DocScope MCP server.

Commands:
    install: Configure MCP server in VS Code workspace or globally
    uninstall: Remove MCP server configuration
"""

import argparse
import json
import sys
from pathlib import Path

from docscope_mcp.__version__ import __version__

# Platform constant for cross-platform detection
WINDOWS_PLATFORM = "win32"


def get_venv_python() -> str:
    """Detect .venv Python executable for MCP server configuration.

    Provides cross-platform venv detection for MCP server configuration.
    Ensures the correct Python with installed packages is used when
    VS Code spawns the MCP server process.

    Checks for .venv directory in current working directory and returns
    the full path to its Python executable. Works cross-platform
    (Linux/macOS: bin/python, Windows: Scripts/python.exe).

    Falls back to sys.executable if no .venv is found.

    Note: Returns the venv path without resolving symlinks so that
    the venv's site-packages are used correctly.

    Args:
        None - uses current working directory.

    Returns:
        Full path to Python executable as string.

    Raises:
        No exceptions - always returns valid path.

    Example:
        >>> path = get_venv_python()
        >>> 'python' in path
        True
    """
    venv_dir = Path.cwd() / ".venv"

    if venv_dir.exists():
        # Windows uses Scripts/python.exe, Linux/macOS uses bin/python
        if sys.platform == WINDOWS_PLATFORM:
            venv_python = venv_dir / "Scripts" / "python.exe"
        else:
            venv_python = venv_dir / "bin" / "python"

        if venv_python.exists():
            # Use absolute path but don't resolve symlinks - keep venv path
            return str(venv_python.absolute())

    # Fallback to current Python interpreter
    return sys.executable


def get_mcp_server_config() -> dict[str, object]:
    """Generate MCP server configuration with detected Python path.

    Builds the MCP server configuration dict used by VS Code to spawn
    the DocScope MCP server process. Enables documentation analysis
    tool integration with VS Code Copilot.

    The configuration uses `-m docscope_mcp.server` module execution
    rather than entry point scripts to ensure the venv's site-packages
    are correctly loaded.

    Args:
        None - auto-detects Python path.

    Returns:
        Dict with 'command' (Python path) and 'args' (module invocation).

    Raises:
        No exceptions - always returns valid config dict.

    Example:
        >>> config = get_mcp_server_config()
        >>> config['args']
        ['-m', 'docscope_mcp.server']
    """
    return {
        "command": get_venv_python(),
        "args": ["-m", "docscope_mcp.server"],
    }


def get_vscode_mcp_path(global_install: bool = False, insiders: bool = False) -> Path:
    """Get the path to the MCP configuration file.

    Provides the appropriate mcp.json location based on installation
    scope and VS Code variant. Workspace-level config enables per-project
    MCP servers; user-level config provides global defaults.

    Args:
        global_install: If True, return user-level config path.
                       If False, return workspace .vscode/mcp.json path.
        insiders: If True (with global_install), use Code - Insiders path.
                 Ignored for workspace installs.

    Returns:
        Path to the mcp.json configuration file.

    Raises:
        No exceptions - returns path regardless of existence.

    Example:
        >>> get_vscode_mcp_path(global_install=False)
        PosixPath('.vscode/mcp.json')
        >>> get_vscode_mcp_path(global_install=True, insiders=True)
        PosixPath('/home/user/.config/Code - Insiders/User/mcp.json')
    """
    if global_install:
        # User-level VS Code settings
        home = Path.home()
        code_dir = "Code - Insiders" if insiders else "Code"
        return home / ".config" / code_dir / "User" / "mcp.json"
    else:
        # Workspace-level config
        return Path.cwd() / ".vscode" / "mcp.json"


def install_mcp(global_install: bool = False, insiders: bool = False) -> int:
    """Install MCP server configuration to VS Code.

    Creates or updates the mcp.json file with DocScope server config.
    Enables the documentation analysis MCP tool in VS Code's Copilot
    or other MCP-compatible assistants.

    Args:
        global_install: Install to user-level config instead of workspace.
        insiders: Use VS Code Insiders path (only with global_install).

    Returns:
        Exit code: 0 for success, 1 for failure.

    Raises:
        No exceptions - errors printed to stderr, returns exit code.

    Example:
        >>> install_mcp(global_install=False)
        0
    """
    mcp_path = get_vscode_mcp_path(global_install, insiders)
    if global_install:
        variant = "Insiders" if insiders else "stable"
        location = f"global ({variant})"
    else:
        location = "workspace"

    # Ensure directory exists
    mcp_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config or create new
    if mcp_path.exists():
        try:
            with open(mcp_path) as f:
                config = json.load(f)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in {mcp_path}", file=sys.stderr)
            return 1
    else:
        config = {"servers": {}}

    # Ensure servers key exists
    if "servers" not in config:
        config["servers"] = {}

    # Add/update docscope-mcp server
    config["servers"]["docscope-mcp"] = get_mcp_server_config()

    # Write config
    with open(mcp_path, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")

    print(f"✓ DocScope MCP server installed ({location})")
    print(f"  Config: {mcp_path}")
    print()
    print("Reload VS Code window to activate the MCP server.")
    return 0


def uninstall_mcp(global_install: bool = False, insiders: bool = False) -> int:
    """Remove MCP server configuration from VS Code.

    Removes the DocScope server entry from mcp.json while preserving
    other server configurations. Disables the documentation analysis
    tool without affecting other MCP servers.

    Args:
        global_install: Remove from user-level config instead of workspace.
        insiders: Use VS Code Insiders path (only with global_install).

    Returns:
        Exit code: 0 for success, 1 for failure.

    Raises:
        No exceptions - errors printed to stderr, returns exit code.

    Example:
        >>> uninstall_mcp(global_install=False)
        0
    """
    mcp_path = get_vscode_mcp_path(global_install, insiders)
    if global_install:
        variant = "Insiders" if insiders else "stable"
        location = f"global ({variant})"
    else:
        location = "workspace"

    if not mcp_path.exists():
        print(f"No MCP config found at {mcp_path}")
        return 0

    try:
        with open(mcp_path) as f:
            config = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {mcp_path}", file=sys.stderr)
        return 1

    # Remove docscope-mcp server
    if "servers" in config and "docscope-mcp" in config["servers"]:
        del config["servers"]["docscope-mcp"]

        # Write updated config
        with open(mcp_path, "w") as f:
            json.dump(config, f, indent=2)
            f.write("\n")

        print(f"✓ DocScope MCP server removed ({location})")
    else:
        print(f"DocScope MCP server not found in {location} config")

    return 0


def main() -> int:
    """CLI entry point for docscope-mcp commands.

    Parses command-line arguments and dispatches to install/uninstall
    handlers. Provides --version flag and help documentation.

    Commands:
        install: Add DocScope MCP server to VS Code config
        uninstall: Remove DocScope MCP server from config

    Flags:
        --global, -g: Target user-level config instead of workspace
        --version, -v: Show version and exit

    Args:
        None - reads from sys.argv.

    Returns:
        Exit code: 0 for success, non-zero for failure.

    Raises:
        SystemExit: On --version or argument errors (via argparse).

    Example:
        >>> # Programmatic usage:
        >>> import sys
        >>> sys.argv = ['docscope-mcp', 'install']
        >>> exit_code = main()
        >>> exit_code == 0
        True
    """
    parser = argparse.ArgumentParser(
        prog="docscope-mcp",
        description="DocScope MCP Server - Documentation quality analysis",
    )
    parser.add_argument("--version", "-v", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Install command
    install_parser = subparsers.add_parser("install", help="Install MCP server configuration")
    install_parser.add_argument(
        "--global",
        "-g",
        dest="global_install",
        action="store_true",
        help="Install to user-level VS Code config instead of workspace",
    )
    install_parser.add_argument(
        "--insiders",
        "-i",
        dest="insiders",
        action="store_true",
        help="Use VS Code Insiders config path (only with --global)",
    )

    # Uninstall command
    uninstall_parser = subparsers.add_parser("uninstall", help="Remove MCP server configuration")
    uninstall_parser.add_argument(
        "--global",
        "-g",
        dest="global_install",
        action="store_true",
        help="Remove from user-level VS Code config instead of workspace",
    )
    uninstall_parser.add_argument(
        "--insiders",
        "-i",
        dest="insiders",
        action="store_true",
        help="Use VS Code Insiders config path (only with --global)",
    )

    args = parser.parse_args()

    if args.command == "install":
        return install_mcp(global_install=args.global_install, insiders=args.insiders)
    elif args.command == "uninstall":
        return uninstall_mcp(global_install=args.global_install, insiders=args.insiders)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
