"""Tests for filesystem abstraction."""

from pathlib import Path

import pytest

from docscope_mcp.filesystem import (
    DefaultFilesystemAdapter,
    PathSecurityValidator,
)
from tests.mock_filesystem import MockFilesystemAdapter


class TestMockFilesystemAdapter:
    """Test suite for MockFilesystemAdapter.

    Categories:
    1. Initialization - Empty state creation (1 test)
    2. JSON Operations - Write/read JSON roundtrip (1 test)
    3. Text Operations - Write/read text roundtrip (1 test)
    4. Directory Operations - mkdir with parents (1 test)
    5. Existence Checks - exists() behavior (1 test)
    6. Copy Operations - File copying (1 test)
    7. Error Handling - FileNotFoundError cases (1 test)
    8. Remove Operations - File deletion (1 test)
    9. Glob Operations - Pattern matching (1 test)
    10. Representation - __repr__ format (1 test)

    Total: 10 tests.
    """

    def test_mock_creation(self) -> None:
        """Verifies MockFilesystemAdapter initializes with empty state.

        Tests initialization by creating new adapter instance.

        Business context:
        Clean mock state prevents test pollution between runs.

        Arrangement:
        1. No setup needed - tests constructor.

        Action:
        Instantiate MockFilesystemAdapter.

        Assertion Strategy:
        Validates empty state by confirming:
        - files dict is empty.
        - directories set is empty.

        Testing Principle:
        Validates clean initialization, ensuring no residual state.
        """
        mock = MockFilesystemAdapter()
        assert mock.files == {}
        assert mock.directories == set()

    def test_mock_write_read_json(self) -> None:
        """Verifies JSON write/read roundtrip preserves data structure.

        Tests serialization by writing and reading complex JSON.

        Business context:
        MCP config files are JSON; roundtrip must be lossless.

        Arrangement:
        1. Create mock adapter.
        2. Define nested data structure with various types.

        Action:
        Write JSON then read it back.

        Assertion Strategy:
        Validates roundtrip by confirming:
        - Read data equals written data exactly.

        Testing Principle:
        Validates serialization, ensuring JSON integrity preserved.
        """
        mock = MockFilesystemAdapter()
        data = {"key": "value", "nested": {"inner": 42}}
        mock.write_json(Path("test.json"), data)
        result = mock.read_json(Path("test.json"))
        assert result == data

    def test_mock_write_read_text(self) -> None:
        """Verifies text write/read roundtrip preserves content.

        Tests text operations by writing and reading string content.

        Business context:
        Code files are text; roundtrip must preserve content exactly.

        Arrangement:
        1. Create mock adapter.
        2. Define text content string.

        Action:
        Write text then read it back.

        Assertion Strategy:
        Validates roundtrip by confirming:
        - Read text equals written text exactly.

        Testing Principle:
        Validates text handling, ensuring no content modification.
        """
        mock = MockFilesystemAdapter()
        content = "Hello, world!"
        mock.write_text(Path("test.txt"), content)
        result = mock.read_text(Path("test.txt"))
        assert result == content

    def test_mock_mkdir(self) -> None:
        """Verifies mkdir creates path and all parent directories.

        Tests recursive directory creation behavior.

        Business context:
        MCP installation creates nested directory structures.

        Arrangement:
        1. Create mock adapter.

        Action:
        Create deeply nested directory path.

        Assertion Strategy:
        Validates recursion by confirming:
        - Full path in directories set.
        - All parent paths also in directories set.

        Testing Principle:
        Validates mkdir -p behavior, ensuring parents created.
        """
        mock = MockFilesystemAdapter()
        mock.mkdir(Path("a/b/c"))
        assert Path("a/b/c") in mock.directories
        assert Path("a/b") in mock.directories
        assert Path("a") in mock.directories

    def test_mock_exists(self) -> None:
        """Verifies exists returns correct boolean for file presence.

        Tests existence check before and after file creation.

        Business context:
        Config operations check existence before read/write.

        Arrangement:
        1. Create mock adapter with no files.

        Action:
        Check nonexistent file, create file, check again.

        Assertion Strategy:
        Validates detection by confirming:
        - Nonexistent file returns False.
        - After creation, returns True.

        Testing Principle:
        Validates existence tracking, ensuring accurate state.
        """
        mock = MockFilesystemAdapter()
        assert mock.exists(Path("nonexistent")) is False
        mock.write_text(Path("test.txt"), "content")
        assert mock.exists(Path("test.txt")) is True

    def test_mock_copy_file(self) -> None:
        """Verifies copy_file duplicates content to new path.

        Tests file copying by creating source and copying to destination.

        Business context:
        Backup operations copy files before modification.

        Arrangement:
        1. Create mock adapter.
        2. Write source file with content.

        Action:
        Copy source to destination path.

        Assertion Strategy:
        Validates copy by confirming:
        - Destination file has same content as source.

        Testing Principle:
        Validates copy semantics, ensuring content duplication.
        """
        mock = MockFilesystemAdapter()
        mock.write_text(Path("src.txt"), "content")
        mock.copy_file(Path("src.txt"), Path("dst.txt"))
        assert mock.read_text(Path("dst.txt")) == "content"

    @pytest.mark.parametrize(
        ("operation", "path", "exception"),
        [
            ("copy", Path("nonexistent"), FileNotFoundError),
            ("remove", Path("nonexistent"), FileNotFoundError),
        ],
        ids=["copy_nonexistent", "remove_nonexistent"],
    )
    def test_mock_file_not_found_errors(
        self, operation: str, path: Path, exception: type[Exception]
    ) -> None:
        """Verifies operations on nonexistent files raise FileNotFoundError.

        Tests error handling for copy and remove on missing files.

        Business context:
        Mock must match real filesystem error behavior for test validity.

        Arrangement:
        1. Parametrize with copy and remove operations.
        2. Use nonexistent file path.

        Action:
        Attempt operation on nonexistent file.

        Assertion Strategy:
        Validates exception by confirming:
        - FileNotFoundError is raised for both operations.

        Testing Principle:
        Validates error parity, ensuring mock matches real filesystem.
        """
        mock = MockFilesystemAdapter()
        with pytest.raises(exception):
            if operation == "copy":
                mock.copy_file(path, Path("dst.txt"))
            else:
                mock.remove(path)

    def test_mock_remove(self) -> None:
        """Verifies remove deletes file from mock filesystem.

        Tests file deletion by creating then removing file.

        Business context:
        Cleanup operations remove files after processing.

        Arrangement:
        1. Create mock adapter.
        2. Write file with content.

        Action:
        Remove the file.

        Assertion Strategy:
        Validates deletion by confirming:
        - File no longer exists after remove.

        Testing Principle:
        Validates removal, ensuring files properly deleted.
        """
        mock = MockFilesystemAdapter()
        mock.write_text(Path("test.txt"), "content")
        mock.remove(Path("test.txt"))
        assert mock.exists(Path("test.txt")) is False

    def test_mock_glob(self) -> None:
        """Verifies glob returns files matching pattern only.

        Tests pattern matching by creating mixed file types.

        Business context:
        File discovery uses glob patterns for filtering.

        Arrangement:
        1. Create mock adapter.
        2. Write files with different extensions in same directory.

        Action:
        Glob for *.txt pattern.

        Assertion Strategy:
        Validates filtering by confirming:
        - Returns exactly 2 files (matching .txt extension).

        Testing Principle:
        Validates glob semantics, ensuring pattern matching works.
        """
        mock = MockFilesystemAdapter()
        mock.write_text(Path("dir/a.txt"), "a")
        mock.write_text(Path("dir/b.txt"), "b")
        mock.write_text(Path("dir/c.md"), "c")
        results = mock.glob(Path("dir"), "*.txt")
        assert len(results) == 2

    def test_mock_repr(self) -> None:
        """Verifies __repr__ shows class name and state counts.

        Tests string representation for debugging output.

        Business context:
        Debuggable repr helps diagnose test failures.

        Arrangement:
        1. Create mock adapter.
        2. Write one file to create state.

        Action:
        Call repr() on mock adapter.

        Assertion Strategy:
        Validates format by confirming:
        - Class name in repr string.
        - File count displayed.

        Testing Principle:
        Validates debuggability, ensuring informative repr.
        """
        mock = MockFilesystemAdapter()
        mock.write_text(Path("test.txt"), "content")
        repr_str = repr(mock)
        assert "MockFilesystemAdapter" in repr_str
        assert "files=1" in repr_str


class TestDefaultFilesystemAdapter:
    """Test suite for DefaultFilesystemAdapter.

    Categories:
    1. Representation - __repr__ format (1 test)

    Total: 1 test.
    """

    def test_default_repr(self) -> None:
        """Verifies DefaultFilesystemAdapter has correct repr.

        Tests string representation for identification.

        Business context:
        Distinguishing adapters in logs aids debugging.

        Arrangement:
        1. Create DefaultFilesystemAdapter instance.

        Action:
        Call repr() on adapter.

        Assertion Strategy:
        Validates format by confirming:
        - Repr equals expected class name format.

        Testing Principle:
        Validates identification, ensuring adapter identifiable.
        """
        fs = DefaultFilesystemAdapter()
        assert repr(fs) == "DefaultFilesystemAdapter()"


class TestPathSecurityValidator:
    """Test suite for PathSecurityValidator.

    Categories:
    1. Path Passthrough - Absolute paths unchanged (1 test)
    2. Traversal Blocking - Path traversal prevention (1 test)
    3. Symlink Validation - Symlink target scenarios (1 test)
    4. Symlink Errors - OSError handling (1 test)

    Total: 4 tests.
    """

    def test_absolute_path_passthrough(self) -> None:
        """Verifies absolute paths are returned unchanged.

        Tests passthrough for paths already within workspace.

        Business context:
        Valid absolute paths should not be modified by validator.

        Arrangement:
        1. Define workspace as /project.
        2. Define file path within workspace.

        Action:
        Validate workspace boundary with absolute path.

        Assertion Strategy:
        Validates passthrough by confirming:
        - Result equals input path exactly.

        Testing Principle:
        Validates identity, ensuring valid paths unchanged.
        """
        workspace = Path("/project")
        file_path = Path("/project/file.txt")
        result = PathSecurityValidator.validate_workspace_boundary(file_path, workspace)
        assert result == file_path

    def test_path_traversal_blocked(self) -> None:
        """Verifies path traversal attacks are blocked with ValueError.

        Tests security by attempting directory traversal escape.

        Business context:
        Path traversal is critical security vulnerability; must be blocked.

        Arrangement:
        1. Define workspace as /project.
        2. Create path with ../ traversal to escape workspace.

        Action:
        Attempt validation with traversal path.

        Assertion Strategy:
        Validates blocking by confirming:
        - ValueError raised with "escapes workspace" message.

        Testing Principle:
        Validates security boundary, ensuring traversal blocked.
        """
        workspace = Path("/project")
        with pytest.raises(ValueError, match="escapes workspace"):
            PathSecurityValidator.validate_workspace_boundary(
                Path("../../../etc/passwd"), workspace
            )

    @pytest.mark.parametrize(
        ("symlink_target", "is_absolute", "should_raise", "error_match"),
        [
            (Path("real"), False, False, None),  # Relative inside
            (Path("/workspace/real"), True, False, None),  # Absolute inside
            (Path("/etc"), True, True, "Symlink target escapes"),  # Escapes
        ],
        ids=["relative_inside", "absolute_inside", "escapes_workspace"],
    )
    def test_symlink_validation_via_adapter(
        self,
        symlink_target: Path,
        is_absolute: bool,  # noqa: ARG002
        should_raise: bool,
        error_match: str | None,
    ) -> None:
        """Verifies symlink validation handles various target scenarios.

        Tests symlink security with relative, absolute, and escaping targets.

        Business context:
        Symlinks can bypass path restrictions; must validate targets.

        Arrangement:
        1. Parametrize with relative-inside, absolute-inside, and escaping targets.
        2. Create mock adapter with symlink pointing to target.

        Action:
        Validate path that traverses through symlink.

        Assertion Strategy:
        Validates security by confirming:
        - Inside targets pass validation.
        - Escaping targets raise ValueError.

        Testing Principle:
        Validates symlink security, ensuring escapes blocked.
        """
        mock = MockFilesystemAdapter()
        workspace = Path("/workspace")
        mock.symlinks[workspace / "link"] = symlink_target

        if should_raise:
            with pytest.raises(ValueError, match=error_match):
                mock.validate_path(Path("link/file.txt"), workspace)
        else:
            result = mock.validate_path(Path("link/file.txt"), workspace)
            assert result == workspace / "link" / "file.txt"

    def test_symlink_oserror_via_adapter(self) -> None:
        """Verifies OSError reading symlink raises ValueError.

        Tests error handling when symlink target cannot be read.

        Business context:
        Broken symlinks must fail validation safely.

        Arrangement:
        1. Create mock adapter with symlink.
        2. Add symlink to error set to simulate OSError.

        Action:
        Attempt validation through broken symlink.

        Assertion Strategy:
        Validates error handling by confirming:
        - ValueError raised with "Cannot validate symlink" message.

        Testing Principle:
        Validates error handling, ensuring broken symlinks rejected.
        """
        mock = MockFilesystemAdapter()
        workspace = Path("/workspace")
        mock.symlinks[workspace / "broken"] = Path("target")
        mock.symlink_errors.add(workspace / "broken")

        with pytest.raises(ValueError, match="Cannot validate symlink"):
            mock.validate_path(Path("broken/file.txt"), workspace)
