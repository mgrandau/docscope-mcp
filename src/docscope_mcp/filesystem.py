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
        """Copy file with metadata preservation."""
        ...

    def mkdir(self, path: Path, parents: bool = True, exist_ok: bool = True) -> None:
        """Create directory with optional parent creation."""
        ...

    def read_json(self, path: Path) -> JSONValue:
        """Read and parse JSON file."""
        ...

    def write_json(self, path: Path, data: dict[str, Any]) -> None:
        """Write dictionary to file as formatted JSON."""
        ...

    def exists(self, path: Path) -> bool:
        """Check if file or directory exists."""
        ...

    def glob(self, path: Path, pattern: str) -> list[Path]:
        """Find all files matching pattern in directory."""
        ...

    def resolve(self, path: Path) -> Path:
        """Resolve path to absolute canonical path."""
        ...

    def validate_path(self, path: Path, workspace: Path) -> Path:
        """Validate and resolve user-provided path for security."""
        ...

    def remove(self, path: Path) -> None:
        """Remove file from filesystem."""
        ...

    def read_text(self, path: Path) -> str:
        """Read text content from file."""
        ...

    def write_text(self, path: Path, content: str) -> None:
        """Write text content to file."""
        ...


class PathSecurityValidator:
    """Validates paths against workspace boundaries for security.

    Prevents path traversal attacks by ensuring user-provided paths
    cannot escape workspace boundaries.
    """

    @staticmethod
    def validate_workspace_boundary(path: Path, workspace: Path) -> Path:
        """Validate path stays within workspace boundaries.

        Absolute paths are returned as-is. Relative paths are resolved
        against workspace and validated. Symlinks are checked for
        targets outside workspace.

        Args:
            path: User-provided path (absolute or relative)
            workspace: Workspace root directory

        Returns:
            Validated absolute path

        Raises:
            ValueError: If path escapes workspace boundaries
        """
        if path.is_absolute():
            return path

        full_path = workspace / path
        workspace_resolved = workspace.resolve()

        # Check symlinks in path
        current = workspace
        for part in path.parts:
            current = current / part

            if current.is_symlink():
                try:
                    target = current.readlink()
                    if not target.is_absolute():
                        target = (current.parent / target).resolve()
                    else:
                        target = target.resolve()

                    try:
                        target.relative_to(workspace_resolved)
                    except ValueError:
                        msg = f"Symlink target escapes workspace: {current} -> {target}"
                        raise ValueError(msg) from None
                except OSError:
                    raise ValueError(f"Cannot validate symlink: {current}") from None

        resolved = full_path.resolve()

        try:
            resolved.relative_to(workspace_resolved)
        except ValueError:
            raise ValueError(f"Path escapes workspace: {path} -> {resolved}") from None

        return resolved


class DefaultFilesystemAdapter:
    """Production filesystem adapter using stdlib.

    Implements FilesystemAdapter Protocol using actual filesystem I/O.
    Thread-safe via underlying stdlib guarantees.
    """

    def __repr__(self) -> str:
        """Return string repr for debugging."""
        return "DefaultFilesystemAdapter()"

    def copy_file(self, src: Path, dst: Path) -> None:
        """Copy file with metadata preservation."""
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    def mkdir(self, path: Path, parents: bool = True, exist_ok: bool = True) -> None:
        """Create directory with optional parent creation."""
        path.mkdir(parents=parents, exist_ok=exist_ok)

    def read_json(self, path: Path) -> JSONValue:
        """Read and parse JSON file."""
        with open(path, encoding="utf-8") as f:
            return cast(JSONValue, json.load(f))

    def write_json(self, path: Path, data: dict[str, Any]) -> None:
        """Write dictionary to file as formatted JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def exists(self, path: Path) -> bool:
        """Check if file or directory exists."""
        return path.exists()

    def glob(self, path: Path, pattern: str) -> list[Path]:
        """Find all files matching pattern in directory."""
        return list(path.glob(pattern))

    def resolve(self, path: Path) -> Path:
        """Resolve path to absolute canonical path."""
        return path.resolve()

    def validate_path(self, path: Path, workspace: Path) -> Path:
        """Validate and resolve user-provided path for security."""
        return PathSecurityValidator.validate_workspace_boundary(path, workspace)

    def remove(self, path: Path) -> None:
        """Remove file from filesystem."""
        os.unlink(path)

    def read_text(self, path: Path) -> str:
        """Read text content from file."""
        return path.read_text(encoding="utf-8")

    def write_text(self, path: Path, content: str) -> None:
        """Write text content to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


class MockFilesystemAdapter:
    """Mock filesystem adapter for testing.

    Stores files in memory for isolated unit tests.

    Attributes:
        files: Dict mapping paths to file contents
        directories: Set of created directory paths
    """

    def __init__(self) -> None:
        """Initialize mock filesystem."""
        self.files: dict[Path, str] = {}
        self.directories: set[Path] = set()

    def __repr__(self) -> str:
        """Return string repr for debugging."""
        return f"MockFilesystemAdapter(files={len(self.files)}, dirs={len(self.directories)})"

    def copy_file(self, src: Path, dst: Path) -> None:
        """Copy file in mock filesystem."""
        if src not in self.files:
            raise FileNotFoundError(f"Source not found: {src}")
        self.files[dst] = self.files[src]
        self.directories.add(dst.parent)

    def mkdir(self, path: Path, parents: bool = True, exist_ok: bool = True) -> None:
        """Create directory in mock filesystem."""
        if path in self.directories and not exist_ok:
            raise FileExistsError(f"Directory exists: {path}")
        self.directories.add(path)
        if parents:
            for parent in path.parents:
                self.directories.add(parent)

    def read_json(self, path: Path) -> JSONValue:
        """Read JSON from mock filesystem."""
        if path not in self.files:
            raise FileNotFoundError(f"File not found: {path}")
        return cast(JSONValue, json.loads(self.files[path]))

    def write_json(self, path: Path, data: dict[str, Any]) -> None:
        """Write JSON to mock filesystem."""
        self.files[path] = json.dumps(data, indent=2)
        self.directories.add(path.parent)

    def exists(self, path: Path) -> bool:
        """Check existence in mock filesystem."""
        return path in self.files or path in self.directories

    def glob(self, path: Path, pattern: str) -> list[Path]:
        """Glob in mock filesystem."""
        import fnmatch

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
        """Resolve path (no-op for mock)."""
        return path

    def validate_path(self, path: Path, _workspace: Path) -> Path:
        """Validate path (pass-through for mock)."""
        return path

    def remove(self, path: Path) -> None:
        """Remove file from mock filesystem."""
        if path not in self.files:
            raise FileNotFoundError(f"File not found: {path}")
        del self.files[path]

    def read_text(self, path: Path) -> str:
        """Read text from mock filesystem."""
        if path not in self.files:
            raise FileNotFoundError(f"File not found: {path}")
        return self.files[path]

    def write_text(self, path: Path, content: str) -> None:
        """Write text to mock filesystem."""
        self.files[path] = content
        self.directories.add(path.parent)
