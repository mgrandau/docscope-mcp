"""Mock filesystem adapter for isolated unit testing.

Provides an in-memory filesystem implementation that enables testing
file operations without actual I/O or temporary directories.

Usage:
    >>> from tests.mock_filesystem import MockFilesystemAdapter
    >>> fs = MockFilesystemAdapter()
    >>> fs.write_text(Path('test.txt'), 'content')
    >>> fs.read_text(Path('test.txt'))
    'content'
"""

from __future__ import annotations

import fnmatch
import json
from pathlib import Path
from typing import Any, cast

# Type alias for JSON data structures
type JSONValue = dict[str, "JSONValue"] | list["JSONValue"] | str | int | float | bool | None


class MockFilesystemAdapter:
    """Mock filesystem adapter for isolated unit testing.

    Stores files in memory dictionaries instead of actual filesystem.
    Enables testing file operations without I/O side effects or temp
    files. Implements same interface as DefaultFilesystemAdapter.

    This adapter enables dependency injection for testing MCP tools
    that need filesystem operations without touching real files.

    Attributes:
        files: Dict mapping Path to file content strings.
        directories: Set of created directory paths.
        symlinks: Dict mapping symlink Path to target Path.
        symlink_errors: Set of paths that raise OSError on readlink.

    Example:
        >>> fs = MockFilesystemAdapter()
        >>> fs.files[Path('test.json')] = '{"key": "value"}'
        >>> data = fs.read_json(Path('test.json'))
    """

    def __init__(self) -> None:
        """Initialize empty mock filesystem.

        Creates empty files dict and directories set for storing
        mock filesystem state during tests.

        Args:
            None - no parameters required.

        Returns:
            None - initializes instance attributes.

        Raises:
            No exceptions raised.

        Example:
            >>> fs = MockFilesystemAdapter()
            >>> assert len(fs.files) == 0
        """
        self.files: dict[Path, str] = {}
        self.directories: set[Path] = set()
        self.symlinks: dict[Path, Path] = {}
        self.symlink_errors: set[Path] = set()
        self._workspace: Path = Path("/workspace")

    def __repr__(self) -> str:
        """Return string representation showing state counts.

        Provides human-readable identifier for debugging mock state.

        Args:
            None - uses implicit self.

        Returns:
            String with file and directory counts for debugging.

        Raises:
            No exceptions raised.

        Example:
            >>> fs = MockFilesystemAdapter()
            >>> print(fs)  # MockFilesystemAdapter(files=0, dirs=0)
        """
        return f"MockFilesystemAdapter(files={len(self.files)}, dirs={len(self.directories)})"

    def copy_file(self, src: Path, dst: Path) -> None:
        """Copy file content in mock filesystem.

        Copies content string from src to dst in files dict.
        Adds dst parent to directories set.

        Args:
            src: Source path (must exist in files dict).
            dst: Destination path.

        Returns:
            None - modifies files dict as side effect.

        Raises:
            FileNotFoundError: If src not in files dict.

        Example:
            >>> fs.files[Path('a.txt')] = 'content'
            >>> fs.copy_file(Path('a.txt'), Path('b.txt'))
        """
        if src not in self.files:
            raise FileNotFoundError(f"Source not found: {src}")
        self.files[dst] = self.files[src]
        self.directories.add(dst.parent)

    def mkdir(self, path: Path, parents: bool = True, exist_ok: bool = True) -> None:
        """Create directory in mock filesystem.

        Adds path to directories set for testing MCP tool directory
        creation without real filesystem I/O.

        Args:
            path: Directory path to create.
            parents: Add parent paths if True (default: True).
            exist_ok: Ignore existing if True (default: True).

        Returns:
            None - modifies directories set as side effect.

        Raises:
            FileExistsError: If exist_ok=False and path exists.

        Example:
            >>> fs.mkdir(Path('a/b/c'))
            >>> Path('a/b') in fs.directories  # True
        """
        if path in self.directories and not exist_ok:
            raise FileExistsError(f"Directory exists: {path}")
        self.directories.add(path)
        if parents:
            for parent in path.parents:
                self.directories.add(parent)

    def read_json(self, path: Path) -> JSONValue:
        """Read and parse JSON from mock filesystem.

        Parses JSON string stored in files dict at path.

        Args:
            path: Path key in files dict.

        Returns:
            Parsed JSON value.

        Raises:
            FileNotFoundError: If path not in files dict.
            json.JSONDecodeError: If invalid JSON string.

        Example:
            >>> fs.files[Path('a.json')] = '{"k": 1}'
            >>> fs.read_json(Path('a.json'))  # {'k': 1}
        """
        if path not in self.files:
            raise FileNotFoundError(f"File not found: {path}")
        return cast(JSONValue, json.loads(self.files[path]))

    def write_json(self, path: Path, data: dict[str, Any]) -> None:
        """Write JSON string to mock filesystem.

        Serializes dict to JSON and stores in files dict.

        Args:
            path: Path key for files dict.
            data: Dict to serialize.

        Returns:
            None - modifies files dict as side effect.

        Raises:
            TypeError: If data contains non-serializable types.

        Example:
            >>> fs.write_json(Path('out.json'), {'k': 1})
        """
        self.files[path] = json.dumps(data, indent=2)
        self.directories.add(path.parent)

    def exists(self, path: Path) -> bool:
        """Check if path exists in mock filesystem.

        Tests mock path existence for testing MCP tool conditional
        logic without real filesystem dependencies.

        Args:
            path: Path to check.

        Returns:
            True if in files or directories, False otherwise.

        Raises:
            No exceptions - always returns bool.

        Example:
            >>> fs.files[Path('a.txt')] = ''
            >>> fs.exists(Path('a.txt'))  # True
        """
        return path in self.files or path in self.directories

    def glob(self, path: Path, pattern: str) -> list[Path]:
        """Find files matching pattern in mock filesystem.

        Uses fnmatch to filter files dict keys by pattern. Enables
        testing of batch file operations without real filesystem I/O.

        Args:
            path: Base path to search from.
            pattern: Glob pattern to match.

        Returns:
            List of matching paths from files dict.

        Raises:
            No exceptions raised - returns empty list for unmatched.

        Example:
            >>> fs.files[Path('src/a.py')] = ''
            >>> fs.glob(Path('src'), '*.py')  # [Path('src/a.py')]
        """
        results = []
        for file_path in self.files:
            try:
                relative = file_path.relative_to(path)
                if fnmatch.fnmatch(str(relative), pattern):
                    results.append(file_path)
            except ValueError:
                continue
        return results

    def resolve(self, path: Path) -> Path:
        """Return path as absolute (mock resolution).

        Mock implementation returns path made absolute relative to
        mock workspace. Enables testing path logic.

        Args:
            path: Path to resolve.

        Returns:
            Absolute path.

        Raises:
            No exceptions - always returns path.

        Example:
            >>> fs.resolve(Path('a'))  # Path('/workspace/a')
        """
        if path.is_absolute():
            return path
        return self._workspace / path

    def is_symlink(self, path: Path) -> bool:
        """Check if path is a mock symlink.

        Returns True if path is registered in symlinks dict.

        Args:
            path: Path to check.

        Returns:
            True if in symlinks dict, False otherwise.

        Example:
            >>> fs.symlinks[Path('/workspace/link')] = Path('target')
            >>> fs.is_symlink(Path('/workspace/link'))  # True
        """
        return path in self.symlinks

    def readlink(self, path: Path) -> Path:
        """Read mock symlink target.

        Returns target from symlinks dict or raises OSError.

        Args:
            path: Symlink path to read.

        Returns:
            Target path from symlinks dict.

        Raises:
            OSError: If path in symlink_errors or not in symlinks.

        Example:
            >>> fs.symlinks[Path('/workspace/link')] = Path('target')
            >>> fs.readlink(Path('/workspace/link'))  # Path('target')
        """
        if path in self.symlink_errors:
            raise OSError(f"Cannot read symlink: {path}")
        if path not in self.symlinks:
            raise OSError(f"Not a symlink: {path}")
        return self.symlinks[path]

    def validate_path(self, path: Path, workspace: Path) -> Path:
        """Validate path stays within workspace using mock symlinks.

        Uses PathSecurityValidator with self as adapter, enabling
        full symlink validation testing without real filesystem.

        Args:
            path: Path to validate.
            workspace: Workspace boundary.

        Returns:
            Validated absolute path.

        Raises:
            ValueError: If path escapes workspace.

        Example:
            >>> fs.validate_path(Path('a'), Path('/workspace'))
        """
        from docscope_mcp.filesystem import PathSecurityValidator

        # Set workspace for resolve operations
        self._workspace = workspace
        return PathSecurityValidator.validate_workspace_boundary(path, workspace, self)

    def remove(self, path: Path) -> None:
        """Remove file from mock filesystem.

        Deletes path key from files dict for testing cleanup operations.

        Args:
            path: Path to remove.

        Returns:
            None - modifies files dict as side effect.

        Raises:
            FileNotFoundError: If path not in files dict.

        Example:
            >>> fs.files[Path('a.txt')] = ''
            >>> fs.remove(Path('a.txt'))
        """
        if path not in self.files:
            raise FileNotFoundError(f"File not found: {path}")
        del self.files[path]

    def read_text(self, path: Path) -> str:
        """Read text content from mock filesystem.

        Args:
            path: Path key in files dict.

        Returns:
            Content string stored at path.

        Raises:
            FileNotFoundError: If path not in files dict.

        Example:
            >>> fs.files[Path('a.txt')] = 'hello'
            >>> fs.read_text(Path('a.txt'))  # 'hello'
        """
        if path not in self.files:
            raise FileNotFoundError(f"File not found: {path}")
        return self.files[path]

    def write_text(self, path: Path, content: str) -> None:
        """Write text content to mock filesystem.

        Stores content string in files dict at path for testing.

        Args:
            path: Path key for files dict.
            content: String to store.

        Returns:
            None - modifies files dict as side effect.

        Raises:
            No exceptions raised.

        Example:
            >>> fs.write_text(Path('a.txt'), 'hello')
        """
        self.files[path] = content
        self.directories.add(path.parent)
