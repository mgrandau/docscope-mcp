"""Command-line interface for docscope-mcp.

Provides installation, management, and analysis commands for DocScope.

Commands:
    install: Configure MCP server in VS Code workspace or globally
    uninstall: Remove MCP server configuration
    analyze: Analyze source files for documentation quality

Uses FilesystemAdapter for dependency injection, enabling isolated testing
without mocking Path operations.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, cast

from docscope_mcp.__version__ import __version__
from docscope_mcp.analyzers import SUPPORTED_LANGUAGES, analyze_code, analyze_file
from docscope_mcp.filesystem import DefaultFilesystemAdapter, FilesystemAdapter
from docscope_mcp.models import DEFAULT_CONFIG

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


def get_vscode_mcp_path(
    global_install: bool = False,
    insiders: bool = False,
    workspace: Path | None = None,
) -> Path:
    """Get the path to the MCP configuration file.

    Provides the appropriate mcp.json location based on installation
    scope and VS Code variant. Workspace-level config enables per-project
    MCP servers; user-level config provides global defaults.

    Args:
        global_install: If True, return user-level config path.
                       If False, return workspace .vscode/mcp.json path.
        insiders: If True (with global_install), use Code - Insiders path.
                 Ignored for workspace installs.
        workspace: Workspace directory for path calculation. Defaults to cwd.

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
    if workspace is None:
        workspace = Path.cwd()

    if global_install:
        # User-level VS Code settings - platform-specific paths
        home = Path.home()
        code_dir = "Code - Insiders" if insiders else "Code"

        if sys.platform == WINDOWS_PLATFORM:
            # Windows: %APPDATA%/Code/User/mcp.json
            appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
            return appdata / code_dir / "User" / "mcp.json"
        elif sys.platform == "darwin":
            # macOS: ~/Library/Application Support/Code/User/mcp.json
            return home / "Library" / "Application Support" / code_dir / "User" / "mcp.json"
        else:
            # Linux: ~/.config/Code/User/mcp.json
            return home / ".config" / code_dir / "User" / "mcp.json"
    else:
        # Workspace-level config
        return workspace / ".vscode" / "mcp.json"


def get_assets_dir() -> Path:
    """Get the path to bundled assets directory.

    Returns the path to the assets directory within the installed package.
    Assets include prompt templates (.md files) and utility scripts bundled
    during pip install. Used by copy_assets to deploy files to workspace.

    Args:
        None - uses package installation path.

    Returns:
        Path to the assets directory within installed package.

    Raises:
        FileNotFoundError: If assets directory not found in package.

    Example:
        >>> assets = get_assets_dir()
        >>> (assets / 'prompts').exists()
        True
    """
    # Assets are in package's assets/ subdirectory
    package_dir = Path(__file__).parent
    assets_dir = package_dir / "assets"
    if not assets_dir.exists():
        raise FileNotFoundError(f"Assets directory not found: {assets_dir}")
    return assets_dir


def copy_assets(
    workspace: Path | None = None,
    fs: FilesystemAdapter | None = None,
) -> tuple[int, list[str]]:
    """Copy bundled prompts and utils to workspace.

    Copies prompt templates to .github/prompts/ and utility scripts
    to utils/ in the workspace directory. Skips files that already
    exist to preserve user customizations.

    Provides AI-friendly analysis prompts (analyze_source.prompt.md,
    analyze_tests.prompt.md) and utility scripts for batch operations.

    Args:
        workspace: Target workspace directory. Defaults to cwd.
        fs: FilesystemAdapter for file operations. Defaults to
            DefaultFilesystemAdapter for production use.

    Returns:
        Tuple of (exit_code, list of copied file descriptions).
        Exit code 0 on success, 1 on failure.
        File descriptions are relative paths like '  .github/prompts/analyze.md'.

    Raises:
        No exceptions - errors returned in tuple.

    Example:
        >>> exit_code, copied = copy_assets()
        >>> if copied:
        ...     print(f'Copied {len(copied)} files')
    """
    if fs is None:
        fs = DefaultFilesystemAdapter()
    if workspace is None:
        workspace = Path.cwd()

    copied: list[str] = []
    try:
        assets_dir = get_assets_dir()
    except FileNotFoundError as e:
        return 1, [f"Warning: {e}"]

    # Copy prompts to .github/prompts/
    prompts_src = assets_dir / "prompts"
    prompts_dst = workspace / ".github" / "prompts"
    if prompts_src.exists():
        fs.mkdir(prompts_dst)
        for src_file in prompts_src.glob("*.md"):
            dst_file = prompts_dst / src_file.name
            if not fs.exists(dst_file):
                fs.copy_file(src_file, dst_file)
                copied.append(f"  .github/prompts/{src_file.name}")

    # Copy utils to utils/
    utils_src = assets_dir / "utils"
    utils_dst = workspace / "utils"
    if utils_src.exists():
        fs.mkdir(utils_dst)
        for src_file in utils_src.glob("*"):
            if src_file.is_file():
                dst_file = utils_dst / src_file.name
                if not fs.exists(dst_file):
                    fs.copy_file(src_file, dst_file)
                    copied.append(f"  utils/{src_file.name}")

    return 0, copied


def install_mcp(
    global_install: bool = False,
    insiders: bool = False,
    workspace: Path | None = None,
    fs: FilesystemAdapter | None = None,
) -> int:
    """Install MCP server configuration to VS Code.

    Creates or updates the mcp.json file with DocScope server config.
    Enables the documentation analysis MCP tool in VS Code's Copilot
    or other MCP-compatible assistants.

    Args:
        global_install: Install to user-level config instead of workspace.
        insiders: Use VS Code Insiders path (only with global_install).
        workspace: Workspace directory for config path. Defaults to cwd.
        fs: FilesystemAdapter for file operations. Defaults to
            DefaultFilesystemAdapter for production use.

    Returns:
        Exit code: 0 for success, 1 for failure.

    Raises:
        No exceptions - errors printed to stderr, returns exit code.

    Example:
        >>> install_mcp(global_install=False)
        0
    """
    if fs is None:
        fs = DefaultFilesystemAdapter()
    if workspace is None:
        workspace = Path.cwd()

    mcp_path = get_vscode_mcp_path(global_install, insiders, workspace)
    if global_install:
        variant = "Insiders" if insiders else "stable"
        location = f"global ({variant})"
    else:
        location = "workspace"

    # Ensure directory exists
    fs.mkdir(mcp_path.parent)

    # Load existing config or create new
    config: dict[str, Any]
    if fs.exists(mcp_path):
        try:
            raw_config = fs.read_json(mcp_path)
            if isinstance(raw_config, dict):
                config = cast(dict[str, Any], raw_config)
            else:
                config = {"servers": {}}
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
    fs.write_json(mcp_path, config)

    print(f"✓ DocScope MCP server installed ({location})")
    print(f"  Config: {mcp_path}")

    # Copy assets for workspace installs only
    if not global_install:
        exit_code, copied = copy_assets(workspace=workspace, fs=fs)
        if copied:
            print()
            print("Assets copied:")
            for item in copied:
                print(item)

    print()
    print("Reload VS Code window to activate the MCP server.")
    return 0


def uninstall_mcp(
    global_install: bool = False,
    insiders: bool = False,
    workspace: Path | None = None,
    fs: FilesystemAdapter | None = None,
) -> int:
    """Remove MCP server configuration from VS Code.

    Removes the DocScope server entry from mcp.json while preserving
    other server configurations. Disables the documentation analysis
    tool without affecting other MCP servers.

    Args:
        global_install: Remove from user-level config instead of workspace.
        insiders: Use VS Code Insiders path (only with global_install).
        workspace: Workspace directory for config path. Defaults to cwd.
        fs: FilesystemAdapter for file operations. Defaults to
            DefaultFilesystemAdapter for production use.

    Returns:
        Exit code: 0 for success, 1 for failure.

    Raises:
        No exceptions - errors printed to stderr, returns exit code.

    Example:
        >>> uninstall_mcp(global_install=False)
        0
    """
    if fs is None:
        fs = DefaultFilesystemAdapter()
    if workspace is None:
        workspace = Path.cwd()

    mcp_path = get_vscode_mcp_path(global_install, insiders, workspace)
    if global_install:
        variant = "Insiders" if insiders else "stable"
        location = f"global ({variant})"
    else:
        location = "workspace"

    if not fs.exists(mcp_path):
        print(f"No MCP config found at {mcp_path}")
        return 0

    config: dict[str, Any]
    try:
        raw_config = fs.read_json(mcp_path)
        config = cast(dict[str, Any], raw_config) if isinstance(raw_config, dict) else {}  # noqa: SIM108
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {mcp_path}", file=sys.stderr)
        return 1

    # Remove docscope-mcp server
    if "servers" in config and "docscope-mcp" in config["servers"]:
        del config["servers"]["docscope-mcp"]

        # Write updated config
        fs.write_json(mcp_path, config)

        print(f"✓ DocScope MCP server removed ({location})")
    else:
        print(f"DocScope MCP server not found in {location} config")

    return 0


def _format_analysis_results(
    results: list[dict[str, Any]],
    config: Any = None,
) -> str:
    """Format analysis results into human-readable report.

    Transforms raw analysis dicts into formatted text output.
    Shows all functions with their quality levels and provides
    actionable improvement guidance for those needing work.

    Args:
        results: List of function analysis dicts from analyzer.
        config: Optional AnalysisConfig for display limits.

    Returns:
        Formatted report string with all functions and quality levels.
        Returns message if no functions found.

    Raises:
        No exceptions raised.

    Example:
        >>> text = _format_analysis_results([])
        >>> 'No functions found' in text
        True
    """
    if config is None:
        config = DEFAULT_CONFIG

    if not results:
        return "No functions found in the analyzed code."

    # Check for errors
    if results and "error" in results[0]:
        return f"Error: {results[0]['error']}"

    lines = ["Functions analyzed:"]
    lines.append("=" * 60)
    lines.append("NOTE: Quality assessment analyzes FULL docstrings.")
    lines.append("")

    max_display = config.max_results_display
    for i, func in enumerate(results[:max_display], 1):
        try:
            name = func["function_name"]
            line = func["line_number"]
            quality = func["quality_assessment"]["quality"]
            priority = func["priority"]
            needs_improvement = func["quality_assessment"]["needs_improvement"]
            file_path = func.get("file_path", "")

            location = f"[Line {line}]"
            if file_path:
                location = f"[{file_path}:{line}]"

            lines.append(f"{i}. {name}() {location}")
            lines.append(f"   Quality: {quality.upper()} | Priority: {priority}")

            if needs_improvement:
                missing = ", ".join(
                    func["quality_assessment"]["missing"][: config.max_missing_elements_display]
                )
                lines.append(f"   Missing: {missing}")
            else:
                lines.append("   Complete: All required elements present")

            if func.get("current_docstring"):
                preview = (
                    func["current_docstring"][: config.docstring_preview_length]
                    .replace("\n", " ")
                    .strip()
                )
                suffix = (
                    "..."
                    if len(func["current_docstring"]) > config.docstring_preview_length
                    else ""
                )
                lines.append(f"   Current: {preview}{suffix}")
            else:
                lines.append("   Current: No docstring")
            lines.append("")

        except KeyError:
            continue

    if len(results) > max_display:
        remaining = len(results) - max_display
        lines.append(f"... and {remaining} more functions")

    return "\n".join(lines)


def run_analyze(
    files: list[str] | None = None,
    code: str | None = None,
    language: str | None = None,
    output_format: str = "text",
) -> int:
    """Analyze source files or code for documentation quality.

    Provides CLI-equivalent functionality to the MCP server's analyze
    tools. Supports analyzing files from disk or inline code strings.

    Args:
        files: List of file paths to analyze. Mutually exclusive with code.
        code: Source code string to analyze. Requires language parameter.
        language: Programming language for code analysis.
                  Required when code is provided.
        output_format: Output format - 'text' (human-readable) or 'json'.

    Returns:
        Exit code: 0 for success, 1 for failure.

    Raises:
        No exceptions - errors printed to stderr, returns exit code.

    Example:
        >>> run_analyze(files=['src/main.py'])
        0
        >>> run_analyze(code='def foo(): pass', language='python')
        0
    """
    all_results: list[dict[str, Any]] = []

    # Validate mutual exclusivity
    if code and files:
        print("Error: Cannot specify both --code and file paths", file=sys.stderr)
        return 1

    if code:
        # Analyze inline code
        if not language:
            print("Error: --language is required when using --code", file=sys.stderr)
            return 1

        if language not in SUPPORTED_LANGUAGES:
            lang_list = ", ".join(SUPPORTED_LANGUAGES)
            print(f"Error: Unsupported language '{language}'. Use: {lang_list}", file=sys.stderr)
            return 1

        results = analyze_code(code, language, file_path="<stdin>", config=DEFAULT_CONFIG)
        all_results.extend(results)

    elif files:
        # Analyze files
        for file_path in files:
            results = analyze_file(file_path, config=DEFAULT_CONFIG)
            all_results.extend(results)

    else:
        print("Error: Provide file path(s) or use --code with --language", file=sys.stderr)
        return 1

    # Check for errors in results
    has_error = any("error" in r for r in all_results)

    # Output results
    if output_format == "json":
        print(json.dumps(all_results, indent=2))
    else:
        print(_format_analysis_results(all_results))

    # Return 1 if any errors occurred, 0 otherwise
    return 1 if has_error and not any("function_name" in r for r in all_results) else 0


def main() -> int:
    """CLI entry point for docscope-mcp commands.

    Parses command-line arguments and dispatches to install/uninstall/analyze
    handlers. Provides --version flag and help documentation.

    Commands:
        install: Add DocScope MCP server to VS Code config
        uninstall: Remove DocScope MCP server from config
        analyze: Analyze source files for documentation quality

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

    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze source files for documentation quality",
    )
    analyze_parser.add_argument(
        "files",
        nargs="*",
        help="Source file(s) to analyze",
    )
    analyze_parser.add_argument(
        "--code",
        "-c",
        dest="code",
        help="Analyze inline code string (requires --language)",
    )
    analyze_parser.add_argument(
        "--language",
        "-l",
        dest="language",
        choices=SUPPORTED_LANGUAGES,
        help=f"Language for inline code. One of: {', '.join(SUPPORTED_LANGUAGES)}",
    )
    analyze_parser.add_argument(
        "--format",
        "-f",
        dest="output_format",
        choices=["text", "json"],
        default="text",
        help="Output format: text (default) or json",
    )

    args = parser.parse_args()

    if args.command == "install":
        if args.insiders and not args.global_install:
            print("Error: --insiders requires --global", file=sys.stderr)
            return 1
        return install_mcp(global_install=args.global_install, insiders=args.insiders)
    elif args.command == "uninstall":
        if args.insiders and not args.global_install:
            print("Error: --insiders requires --global", file=sys.stderr)
            return 1
        return uninstall_mcp(global_install=args.global_install, insiders=args.insiders)
    elif args.command == "analyze":
        return run_analyze(
            files=args.files if args.files else None,
            code=args.code,
            language=args.language,
            output_format=args.output_format,
        )
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
