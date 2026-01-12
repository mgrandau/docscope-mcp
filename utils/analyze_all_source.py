#!/usr/bin/env python3
"""Analyze all source files in the source directory.

This utility script runs the DocScope analyzer against every supported source file
in the src directory, outputting JSON for use as prompt context.

Supported languages: Python, C#, VB.NET, VB6, C++

Usage:
    python utils/analyze_all_source.py
    python utils/analyze_all_source.py --output analysis.json
    python utils/analyze_all_source.py --pretty

Examples:
    # Analyze with custom project root
    main(project_root=Path("/my/project"))
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

# Patterns to exclude from file discovery
EXCLUDED_PATTERNS = ("__pycache__", ".pyc", "node_modules", ".git", "bin", "obj")


def find_source_files(target_dir: Path, supported_extensions: list[str]) -> list[Path]:
    """Find all supported source files in the target directory.

    Recursively discovers source files while filtering out
    cache directories and build artifacts.

    Business context:
    Enables batch analysis of entire codebases by discovering all
    analyzable files. Used as the first step in documentation audits.

    Args:
        target_dir: Path to the directory to scan. Must exist.
        supported_extensions: List of file extensions to include (e.g., ['.py', '.cs']).

    Returns:
        List of paths to source files, sorted alphabetically.
        Excludes __pycache__, node_modules, .git, bin, obj directories.

    Raises:
        OSError: If target_dir is not accessible or doesn't exist.

    Examples:
        >>> files = find_source_files(Path("src"), ['.py', '.cs'])
        >>> [f.suffix for f in files[:2]]
        ['.py', '.py']
    """
    source_files = []
    for ext in supported_extensions:
        pattern = f"*{ext}"
        for src_file in target_dir.rglob(pattern):
            if not any(pattern in str(src_file) for pattern in EXCLUDED_PATTERNS):
                source_files.append(src_file)
    return sorted(source_files)


def analyze_single_file(
    file_path: Path,
    project_root: Path,
    analyze_func: callable,
) -> dict:
    """Analyze a single source file and return structured results.

    Runs documentation quality analysis using the routing layer and formats
    results for JSON output. Handles errors gracefully by returning
    error information instead of raising.

    Business context:
    Core analysis function that produces per-file quality metrics.
    Results feed into aggregate reports for documentation audits.

    Args:
        file_path: Absolute path to the source file to analyze.
        project_root: Root directory for computing relative paths in output.
        analyze_func: The analyze_file function from routing module.

    Returns:
        Dictionary with keys:
        - file: Relative path from project_root
        - language: Detected language or 'unknown'
        - functions_needing_improvement: Count of functions with issues
        - functions: List of function analysis dicts
        - error: (optional) Error message if analysis failed
        - skipped: (optional) True if file type not supported

    Raises:
        ValueError: If file_path is not under project_root.

    Examples:
        >>> result = analyze_single_file(Path("src/main.py"), Path("."), analyze_file)
        >>> result["file"]
        'src/main.py'
        >>> result["language"]
        'python'
    """
    relative_path = str(file_path.relative_to(project_root))

    # Detect language first from file extension
    from docscope_mcp.analyzers.routing import detect_language

    language = detect_language(str(file_path)) or "unknown"

    try:
        results = analyze_func(str(file_path))

        # Check for unsupported file type error
        if results and len(results) == 1 and "error" in results[0]:
            error_msg = results[0]["error"]
            if "Unsupported file type" in error_msg:
                return {
                    "file": relative_path,
                    "language": "unknown",
                    "skipped": True,
                    "reason": error_msg,
                    "functions_needing_improvement": 0,
                    "functions": [],
                }
            return {
                "file": relative_path,
                "language": language,
                "error": error_msg,
                "functions_needing_improvement": 0,
                "functions": [],
            }

        # Clean up results for JSON output
        functions = [
            {
                "name": func.get("function_name", "unknown"),
                "line": func.get("line_number", 0),
                "quality": func.get("quality_assessment", {}).get("quality", "unknown"),
                "priority": func.get("priority", 0),
                "missing": func.get("quality_assessment", {}).get("missing", []),
                "has_docstring": bool(func.get("current_docstring")),
            }
            for func in results
            if "error" not in func
        ]

        return {
            "file": relative_path,
            "language": language,
            "functions_needing_improvement": len(functions),
            "functions": functions,
        }

    except (OSError, UnicodeDecodeError) as e:
        return {
            "file": relative_path,
            "language": "unknown",
            "error": str(e),
            "functions_needing_improvement": 0,
            "functions": [],
        }


def main(
    project_root: Path | None = None,
) -> int:
    """Analyze all source files and output JSON.

    Scans all supported source files in src directory and outputs structured
    JSON for use as context in AI prompts. Supports Python, C#, VB.NET, VB6, C++.

    Args:
        project_root: Root directory of the project. Defaults to parent of utils/.

    Returns:
        Exit code: 0 on success, 1 on error.

    Raises:
        ValueError: If project_root does not contain a src/ directory.
    """
    # Set up project root and imports
    if project_root is None:
        project_root = Path(__file__).parent.parent

    src_dir = project_root / "src"
    if not src_dir.exists():
        raise ValueError(f"Invalid project_root: {project_root} has no src/ directory")

    # Guard against duplicate sys.path entries
    src_path = str(src_dir)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from docscope_mcp.analyzers.routing import (
        analyze_file,
        get_supported_extensions,
    )

    parser = argparse.ArgumentParser(
        description="Analyze documentation quality for all source files in src"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Write JSON output to file (default: stdout)",
    )
    parser.add_argument(
        "--pretty",
        "-p",
        action="store_true",
        help="Pretty-print JSON output with indentation",
    )
    args = parser.parse_args()

    # Get supported extensions and find files
    supported_extensions = get_supported_extensions()
    source_files = find_source_files(src_dir, supported_extensions)

    if not source_files:
        print("No supported source files found in src directory", file=sys.stderr)
        return 1

    # Build JSON report
    report = {
        "report_type": "source_analysis",
        "generated_at": datetime.now(UTC).isoformat(),
        "target_directory": "src",
        "supported_extensions": supported_extensions,
        "files_scanned": len(source_files),
        "summary": {
            "total_files": len(source_files),
            "files_with_issues": 0,
            "files_skipped": 0,
            "files_with_errors": 0,
            "total_functions_to_improve": 0,
            "by_language": {},
        },
        "files": [],
    }

    for src_file in source_files:
        file_result = analyze_single_file(src_file, project_root, analyze_file)
        report["files"].append(file_result)

        # Update summary
        language = file_result.get("language", "unknown")
        if language not in report["summary"]["by_language"]:
            report["summary"]["by_language"][language] = {
                "files": 0,
                "functions_to_improve": 0,
            }
        report["summary"]["by_language"][language]["files"] += 1

        if file_result.get("skipped"):
            report["summary"]["files_skipped"] += 1
        elif file_result.get("error"):
            report["summary"]["files_with_errors"] += 1
        else:
            func_count = file_result["functions_needing_improvement"]
            report["summary"]["by_language"][language]["functions_to_improve"] += func_count
            if func_count > 0:
                report["summary"]["files_with_issues"] += 1
                report["summary"]["total_functions_to_improve"] += func_count

    # Output JSON
    indent = 2 if args.pretty else None
    json_output = json.dumps(report, indent=indent)

    if args.output:
        Path(args.output).write_text(json_output, encoding="utf-8")
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(json_output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
