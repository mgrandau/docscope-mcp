"""
Filesystem abstraction layer for testable operations.

Provides Protocol-based dependency injection enabling isolated unit testing
of file operations without actual filesystem I/O.

Features:
    - Protocol-based interface (structural typing)
    - Production adapter with shutil/pathlib/json
    - Type-safe method signatures
    - Cross-platform path handling
    - Security validation for path traversal

Usage:
    ```python
    # Production use
    fs = DefaultFilesystemAdapter()
    fs.mkdir(Path('.github/prompts'))
    fs.copy_file(src, dst)

    # Testing use
    mock_fs = MockFilesystemAdapter()
    mock_fs.files[Path('test.json')] = '{"key": "value"}'
    ```
"""

import json
import os
import shutil
from pathlib import Path
from typing import Any, Protocol, cast

# Type alias for JSON data structures
type JSONValue = dict[str, "JSONValue"] | list["JSONValue"] | str | int | float | bool | None


class FilesystemAdapter(Protocol):
    """Protocol defining filesystem operations for dependency injection.

    Implementations must provide all methods with matching signatures.
    Use Protocol for structural typing (duck typing with type safety).
    """

    def copy_file(self, src: Path, dst: Path) -> None:
        """Copy file from source to destination with metadata preservation.

        Copies file content and metadata (timestamps, permissions). Creates
        parent directories if needed. Enables safe file duplication for
        backup and template operations.

        Args:
            src: Source file path. Must exist and be readable.
            dst: Destination file path. Parent dirs created if missing.

        Returns:
            None - copies file as side effect.

        Raises:
            FileNotFoundError: If src does not exist.
            PermissionError: If src unreadable or dst unwritable.

        Example:
            >>> fs.copy_file(Path('template.md'), Path('output/doc.md'))
        """
        ...

    def mkdir(self, path: Path, parents: bool = True, exist_ok: bool = True) -> None:
        """Create directory with optional parent creation.

        Creates directory structure for storing files. Enables MCP tools
        to create output directories for analysis results and config files.
        Defaults to idempotent operation for automation scripts.

        Args:
            path: Directory path to create.
            parents: Create parent directories if True (default: True).
            exist_ok: Ignore if exists if True (default: True).

        Returns:
            None - creates directory as side effect.

        Raises:
            PermissionError: If path is not writable.
            FileExistsError: If exist_ok=False and path exists.

        Example:
            >>> fs.mkdir(Path('.github/prompts'))
        """
        ...

    def read_json(self, path: Path) -> JSONValue:
        """Read and parse JSON file to Python data structure.

        Loads JSON configuration files into native Python types. Returns
        typed JSONValue (dict, list, or primitives) for type-safe access.
        Essential for loading config files in MCP tools.

        Args:
            path: Path to JSON file. Must be valid UTF-8 encoded JSON.

        Returns:
            Parsed JSON as dict, list, str, int, float, bool, or None.

        Raises:
            FileNotFoundError: If path does not exist.
            json.JSONDecodeError: If file contains invalid JSON.

        Example:
            >>> config = fs.read_json(Path('mcp.json'))
            >>> servers = config.get('servers', {})
        """
        ...

    def write_json(self, path: Path, data: dict[str, Any]) -> None:
        """Write dictionary to file as formatted JSON.

        Serializes Python dict to JSON with 2-space indentation. Creates
        parent directories if needed. Used for saving configuration and
        state files in MCP tools.

        Args:
            path: Output file path. Parent dirs created if missing.
            data: Dictionary to serialize. Must be JSON-serializable.

        Returns:
            None - writes file as side effect.

        Raises:
            TypeError: If data contains non-JSON-serializable types.
            PermissionError: If path is not writable.

        Example:
            >>> fs.write_json(Path('config.json'), {'key': 'value'})
        """
        ...

    def exists(self, path: Path) -> bool:
        """Check if file or directory exists at path.

        Tests path existence for conditional file operations. Enables MCP
        tools to check for config files before reading and avoid errors
        on missing files.

        Args:
            path: Path to check for existence.

        Returns:
            True if path exists, False otherwise.

        Raises:
            No exceptions - returns False for inaccessible paths.

        Example:
            >>> if fs.exists(Path('config.json')):
            ...     config = fs.read_json(Path('config.json'))
        """
        ...

    def glob(self, path: Path, pattern: str) -> list[Path]:
        """Find all files matching glob pattern in directory.

        Searches directory for files matching shell-style wildcards.
        Supports * (any chars), ? (single char), ** (recursive). Used
        for batch file discovery in analysis tools.

        Args:
            path: Base directory to search from.
            pattern: Glob pattern (e.g., '*.py', '**/*.md').

        Returns:
            List of matching Path objects. Empty list if no matches.

        Raises:
            PermissionError: If path is not readable.

        Example:
            >>> py_files = fs.glob(Path('src'), '**/*.py')
        """
        ...

    def resolve(self, path: Path) -> Path:
        """Resolve path to absolute canonical path.

        Converts relative path to absolute, resolving symlinks and
        normalizing path separators. Essential for security validation
        ensuring paths stay within workspace boundaries.

        Args:
            path: Path to resolve (relative or absolute).

        Returns:
            Absolute canonical Path with symlinks resolved.

        Raises:
            No exceptions - returns path even if target missing.

        Example:
            >>> abs_path = fs.resolve(Path('./src/../src/file.py'))
        """
        ...

    def is_symlink(self, path: Path) -> bool:
        """Check if path is a symbolic link.

        Tests whether path points to a symlink for security validation.
        Used by validate_path to detect symlink-based path traversal.

        Args:
            path: Path to check.

        Returns:
            True if path is a symlink, False otherwise.

        Raises:
            No exceptions - returns False for non-existent paths.

        Example:
            >>> if fs.is_symlink(Path('link')):
            ...     target = fs.readlink(Path('link'))
        """
        ...

    def readlink(self, path: Path) -> Path:
        """Read the target of a symbolic link.

        Returns the path that the symlink points to. Used for security
        validation to ensure symlink targets stay within workspace.

        Args:
            path: Symlink path to read.

        Returns:
            Path that the symlink points to (may be relative or absolute).

        Raises:
            OSError: If path is not a symlink or cannot be read.

        Example:
            >>> target = fs.readlink(Path('link'))
        """
        ...

    def validate_path(self, path: Path, workspace: Path) -> Path:
        """Validate user-provided path stays within workspace bounds.

        Security check preventing path traversal attacks. Ensures paths
        cannot escape workspace via ../ or symlinks. Critical for MCP
        tools accepting user file paths.

        Args:
            path: User-provided path to validate.
            workspace: Workspace root that path must stay within.

        Returns:
            Validated absolute path if safe.

        Raises:
            ValueError: If path escapes workspace boundaries.

        Example:
            >>> safe_path = fs.validate_path(Path('src/file.py'), workspace)
        """
        ...

    def remove(self, path: Path) -> None:
        """Remove file from filesystem.

        Deletes single file at path. Does not remove directories. Used
        for cleanup operations and file replacement workflows.

        Args:
            path: File path to remove. Must be a file, not directory.

        Returns:
            None - removes file as side effect.

        Raises:
            FileNotFoundError: If path does not exist.
            IsADirectoryError: If path is a directory.
            PermissionError: If file is not deletable.

        Example:
            >>> fs.remove(Path('temp/output.json'))
        """
        ...

    def read_text(self, path: Path) -> str:
        """Read text content from file as UTF-8 string.

        Loads entire file content as string. Uses UTF-8 encoding for
        cross-platform compatibility. Essential for reading source code
        and text files in analysis tools.

        Args:
            path: Path to text file. Must be UTF-8 encoded.

        Returns:
            Complete file content as string.

        Raises:
            FileNotFoundError: If path does not exist.
            UnicodeDecodeError: If file is not valid UTF-8.

        Example:
            >>> code = fs.read_text(Path('src/module.py'))
        """
        ...

    def write_text(self, path: Path, content: str) -> None:
        """Write text content to file as UTF-8.

        Writes string to file, creating parent directories if needed.
        Overwrites existing content. Used for generating output files
        and saving analysis results.

        Args:
            path: Output file path. Parent dirs created if missing.
            content: Text content to write.

        Returns:
            None - writes file as side effect.

        Raises:
            PermissionError: If path is not writable.

        Example:
            >>> fs.write_text(Path('output/report.md'), report_content)
        """
        ...


class PathSecurityValidator:
    """Validates paths against workspace boundaries for security.

    Prevents path traversal attacks by ensuring user-provided paths
    cannot escape workspace boundaries. Uses FilesystemAdapter for
    symlink operations to enable testability.
    """

    @staticmethod
    def validate_workspace_boundary(
        path: Path,
        workspace: Path,
        fs: "FilesystemAdapter | None" = None,
    ) -> Path:
        """Validate path stays within workspace boundaries.

        Security-critical method preventing path traversal attacks in MCP
        tools. Ensures user-provided file paths cannot escape workspace
        via ../ sequences or symlinks pointing outside workspace.

        Absolute paths are returned as-is. Relative paths are resolved
        against workspace and validated. Symlinks are checked for
        targets outside workspace.

        Args:
            path: User-provided path (absolute or relative).
            workspace: Workspace root directory boundary.
            fs: Optional FilesystemAdapter for symlink operations.
                If None, uses Path methods directly.

        Returns:
            Validated absolute path safe to access.

        Raises:
            ValueError: If path escapes workspace boundaries.
            ValueError: If symlink target cannot be validated.

        Example:
            >>> from pathlib import Path
            >>> ws = Path('/project')
            >>> safe = PathSecurityValidator.validate_workspace_boundary(
            ...     Path('src/file.py'), ws
            ... )
            >>> str(safe).endswith('src/file.py')
            True
        """
        if path.is_absolute():
            return path

        full_path = workspace / path
        workspace_resolved = workspace.resolve()

        # Use adapter methods if provided, otherwise use Path methods
        def is_symlink(p: Path) -> bool:
            return fs.is_symlink(p) if fs else p.is_symlink()

        def readlink(p: Path) -> Path:
            return fs.readlink(p) if fs else p.readlink()

        def resolve(p: Path) -> Path:
            return fs.resolve(p) if fs else p.resolve()

        # Check symlinks in path
        current = workspace
        for part in path.parts:
            current = current / part

            if is_symlink(current):
                try:
                    target = readlink(current)
                    if not target.is_absolute():
                        target = resolve(current.parent / target)
                    else:
                        target = resolve(target)

                    try:
                        target.relative_to(workspace_resolved)
                    except ValueError:
                        msg = f"Symlink target escapes workspace: {current} -> {target}"
                        raise ValueError(msg) from None
                except OSError:
                    raise ValueError(f"Cannot validate symlink: {current}") from None

        resolved = resolve(full_path)

        try:
            resolved.relative_to(workspace_resolved)
        except ValueError:
            raise ValueError(f"Path escapes workspace: {path} -> {resolved}") from None

        return resolved


class DefaultFilesystemAdapter:  # pragma: no cover
    """Production filesystem adapter using Python stdlib.

    Implements FilesystemAdapter Protocol using actual filesystem I/O
    via pathlib, shutil, and json modules. Provides real file operations
    for production use while maintaining testability via Protocol.

    This adapter enables dependency injection for filesystem operations,
    allowing MCP tools to be tested with MockFilesystemAdapter while
    using real I/O in production.

    Attributes:
        None - stateless adapter using stdlib functions.

    Example:
        >>> fs = DefaultFilesystemAdapter()
        >>> fs.mkdir(Path('.github/prompts'))
        >>> fs.write_json(Path('config.json'), {'key': 'value'})
    """

    def __repr__(self) -> str:
        """Return string representation for debugging.

        Provides human-readable identifier for logging and debugging
        MCP tool filesystem operations.

        Args:
            None - uses implicit self.

        Returns:
            String 'DefaultFilesystemAdapter()' for log output.

        Raises:
            No exceptions raised.

        Example:
            >>> print(DefaultFilesystemAdapter())
            DefaultFilesystemAdapter()
        """
        return "DefaultFilesystemAdapter()"

    def copy_file(self, src: Path, dst: Path) -> None:
        """Copy file from source to destination with metadata.

        Uses shutil.copy2 to preserve timestamps and permissions.
        Creates destination parent directories automatically.

        Args:
            src: Source file path. Must exist and be readable.
            dst: Destination path. Parent dirs created if missing.

        Returns:
            None - copies file as side effect.

        Raises:
            FileNotFoundError: If src does not exist.
            PermissionError: If src unreadable or dst unwritable.

        Example:
            >>> fs.copy_file(Path('template.md'), Path('docs/new.md'))
        """
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    def mkdir(self, path: Path, parents: bool = True, exist_ok: bool = True) -> None:
        """Create directory with optional parent creation.

        Wraps pathlib.Path.mkdir with sensible defaults for MCP tools
        needing to create output directories for analysis results.

        Args:
            path: Directory path to create.
            parents: Create parent dirs if True (default: True).
            exist_ok: Ignore existing if True (default: True).

        Returns:
            None - creates directory as side effect.

        Raises:
            PermissionError: If path is not writable.
            FileExistsError: If exist_ok=False and path exists.

        Example:
            >>> fs.mkdir(Path('output/reports'))
        """
        path.mkdir(parents=parents, exist_ok=exist_ok)

    def read_json(self, path: Path) -> JSONValue:
        """Read and parse JSON file to Python data structure.

        Opens file with UTF-8 encoding and parses JSON content.
        Returns typed JSONValue for downstream processing.

        Args:
            path: Path to JSON file.

        Returns:
            Parsed JSON as dict, list, str, int, float, bool, or None.

        Raises:
            FileNotFoundError: If path does not exist.
            json.JSONDecodeError: If invalid JSON content.

        Example:
            >>> data = fs.read_json(Path('package.json'))
        """
        with open(path, encoding="utf-8") as f:
            return cast(JSONValue, json.load(f))

    def write_json(self, path: Path, data: dict[str, Any]) -> None:
        """Write dictionary to file as formatted JSON.

        Serializes dict to JSON with 2-space indentation for
        readability. Creates parent directories if needed.

        Args:
            path: Output file path.
            data: Dictionary to serialize as JSON.

        Returns:
            None - writes file as side effect.

        Raises:
            TypeError: If data contains non-serializable types.
            PermissionError: If path is not writable.

        Example:
            >>> fs.write_json(Path('out.json'), {'servers': {}})
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def exists(self, path: Path) -> bool:
        """Check if file or directory exists.

        Tests path existence for conditional MCP tool operations.
        Used to check for config files before reading.

        Args:
            path: Path to check.

        Returns:
            True if path exists, False otherwise.

        Raises:
            No exceptions - returns False for inaccessible paths.

        Example:
            >>> if fs.exists(Path('config.json')): ...
        """
        return path.exists()

    def glob(self, path: Path, pattern: str) -> list[Path]:
        """Find files matching glob pattern in directory.

        Searches directory for files matching shell-style wildcards.
        Essential for batch file discovery in MCP analysis tools that
        need to process multiple source files.

        Args:
            path: Base directory to search.
            pattern: Glob pattern (e.g., '*.py', '**/*.md').

        Returns:
            List of matching paths. Empty if no matches.

        Raises:
            PermissionError: If path is not readable.

        Example:
            >>> files = fs.glob(Path('src'), '**/*.py')
        """
        return list(path.glob(pattern))

    def resolve(self, path: Path) -> Path:
        """Resolve to absolute canonical path.

        Converts path to absolute for security validation in MCP tools
        ensuring user-provided paths stay within workspace.

        Args:
            path: Path to resolve.

        Returns:
            Absolute path with symlinks resolved.

        Raises:
            No exceptions - returns path even if target missing.

        Example:
            >>> abs_path = fs.resolve(Path('./src'))
        """
        return path.resolve()

    def is_symlink(self, path: Path) -> bool:
        """Check if path is a symbolic link.

        Args:
            path: Path to check.

        Returns:
            True if symlink, False otherwise.

        Example:
            >>> fs.is_symlink(Path('link'))
        """
        return path.is_symlink()

    def readlink(self, path: Path) -> Path:
        """Read symlink target.

        Args:
            path: Symlink to read.

        Returns:
            Target path.

        Raises:
            OSError: If not a symlink.

        Example:
            >>> fs.readlink(Path('link'))
        """
        return path.readlink()

    def validate_path(self, path: Path, workspace: Path) -> Path:
        """Validate path stays within workspace boundaries.

        Security check preventing path traversal attacks via
        ../ or symlinks escaping workspace.

        Args:
            path: User-provided path to validate.
            workspace: Workspace root boundary.

        Returns:
            Validated absolute path.

        Raises:
            ValueError: If path escapes workspace.

        Example:
            >>> safe = fs.validate_path(Path('src/f.py'), ws)
        """
        return PathSecurityValidator.validate_workspace_boundary(path, workspace, self)

    def remove(self, path: Path) -> None:
        """Remove file from filesystem.

        Deletes single file for cleanup and replacement workflows.

        Args:
            path: File to remove (not directory).

        Returns:
            None - removes file as side effect.

        Raises:
            FileNotFoundError: If path does not exist.
            IsADirectoryError: If path is a directory.

        Example:
            >>> fs.remove(Path('temp.txt'))
        """
        os.unlink(path)

    def read_text(self, path: Path) -> str:
        """Read file content as UTF-8 string.

        Args:
            path: Path to text file.

        Returns:
            Complete file content as string.

        Raises:
            FileNotFoundError: If path does not exist.
            UnicodeDecodeError: If not valid UTF-8.

        Example:
            >>> code = fs.read_text(Path('main.py'))
        """
        return path.read_text(encoding="utf-8")

    def write_text(self, path: Path, content: str) -> None:
        """Write string to file as UTF-8.

        Creates parent directories if needed. Used for generating
        output files and saving analysis results.

        Args:
            path: Output file path.
            content: Text to write.

        Returns:
            None - writes file as side effect.

        Raises:
            PermissionError: If path not writable.

        Example:
            >>> fs.write_text(Path('out.txt'), 'content')
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
