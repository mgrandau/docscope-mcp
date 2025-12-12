"""Tests for filesystem abstraction."""

from pathlib import Path

import pytest

from docscope_mcp.filesystem import (
    DefaultFilesystemAdapter,
    PathSecurityValidator,
)
from tests.mock_filesystem import MockFilesystemAdapter


class TestMockFilesystemAdapter:
    """Tests for MockFilesystemAdapter."""

    def test_mock_creation(self) -> None:
        """Verify MockFilesystemAdapter initializes with empty state."""
        mock = MockFilesystemAdapter()
        assert mock.files == {}
        assert mock.directories == set()

    def test_mock_write_read_json(self) -> None:
        """Verify JSON write/read roundtrip preserves data structure."""
        mock = MockFilesystemAdapter()
        data = {"key": "value", "nested": {"inner": 42}}
        mock.write_json(Path("test.json"), data)
        result = mock.read_json(Path("test.json"))
        assert result == data

    def test_mock_write_read_text(self) -> None:
        """Verify text write/read roundtrip preserves content."""
        mock = MockFilesystemAdapter()
        content = "Hello, world!"
        mock.write_text(Path("test.txt"), content)
        result = mock.read_text(Path("test.txt"))
        assert result == content

    def test_mock_mkdir(self) -> None:
        """Verify mkdir creates path and all parent directories."""
        mock = MockFilesystemAdapter()
        mock.mkdir(Path("a/b/c"))
        assert Path("a/b/c") in mock.directories
        assert Path("a/b") in mock.directories
        assert Path("a") in mock.directories

    def test_mock_exists(self) -> None:
        """Verify exists returns correct boolean for file presence."""
        mock = MockFilesystemAdapter()
        assert mock.exists(Path("nonexistent")) is False
        mock.write_text(Path("test.txt"), "content")
        assert mock.exists(Path("test.txt")) is True

    def test_mock_copy_file(self) -> None:
        """Verify copy_file duplicates content to new path."""
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
        """Verify operations on nonexistent files raise FileNotFoundError."""
        mock = MockFilesystemAdapter()
        with pytest.raises(exception):
            if operation == "copy":
                mock.copy_file(path, Path("dst.txt"))
            else:
                mock.remove(path)

    def test_mock_remove(self) -> None:
        """Verify remove deletes file from mock filesystem."""
        mock = MockFilesystemAdapter()
        mock.write_text(Path("test.txt"), "content")
        mock.remove(Path("test.txt"))
        assert mock.exists(Path("test.txt")) is False

    def test_mock_glob(self) -> None:
        """Verify glob returns files matching pattern only."""
        mock = MockFilesystemAdapter()
        mock.write_text(Path("dir/a.txt"), "a")
        mock.write_text(Path("dir/b.txt"), "b")
        mock.write_text(Path("dir/c.md"), "c")
        results = mock.glob(Path("dir"), "*.txt")
        assert len(results) == 2

    def test_mock_repr(self) -> None:
        """Verify __repr__ shows class name and state counts."""
        mock = MockFilesystemAdapter()
        mock.write_text(Path("test.txt"), "content")
        repr_str = repr(mock)
        assert "MockFilesystemAdapter" in repr_str
        assert "files=1" in repr_str


class TestDefaultFilesystemAdapter:
    """Tests for DefaultFilesystemAdapter."""

    def test_default_repr(self) -> None:
        """Verify DefaultFilesystemAdapter has correct repr."""
        fs = DefaultFilesystemAdapter()
        assert repr(fs) == "DefaultFilesystemAdapter()"


class TestPathSecurityValidator:
    """Tests for PathSecurityValidator."""

    def test_absolute_path_passthrough(self) -> None:
        """Verify absolute paths are returned unchanged."""
        workspace = Path("/project")
        file_path = Path("/project/file.txt")
        result = PathSecurityValidator.validate_workspace_boundary(file_path, workspace)
        assert result == file_path

    def test_path_traversal_blocked(self) -> None:
        """Verify path traversal attacks are blocked with ValueError."""
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
        """Verify symlink validation handles various target scenarios."""
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
        """Verify OSError reading symlink raises ValueError."""
        mock = MockFilesystemAdapter()
        workspace = Path("/workspace")
        mock.symlinks[workspace / "broken"] = Path("target")
        mock.symlink_errors.add(workspace / "broken")

        with pytest.raises(ValueError, match="Cannot validate symlink"):
            mock.validate_path(Path("broken/file.txt"), workspace)
