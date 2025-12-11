"""Tests for filesystem abstraction."""

from pathlib import Path

import pytest

from docscope_mcp.filesystem import (
    DefaultFilesystemAdapter,
    MockFilesystemAdapter,
    PathSecurityValidator,
)


class TestMockFilesystemAdapter:
    """Tests for MockFilesystemAdapter."""

    def test_mock_creation(self) -> None:
        """Test mock adapter creation."""
        mock = MockFilesystemAdapter()
        assert mock.files == {}
        assert mock.directories == set()

    def test_mock_write_read_json(self) -> None:
        """Test JSON write and read."""
        mock = MockFilesystemAdapter()
        data = {"key": "value", "nested": {"inner": 42}}
        mock.write_json(Path("test.json"), data)
        result = mock.read_json(Path("test.json"))
        assert result == data

    def test_mock_write_read_text(self) -> None:
        """Test text write and read."""
        mock = MockFilesystemAdapter()
        content = "Hello, world!"
        mock.write_text(Path("test.txt"), content)
        result = mock.read_text(Path("test.txt"))
        assert result == content

    def test_mock_mkdir(self) -> None:
        """Test directory creation."""
        mock = MockFilesystemAdapter()
        mock.mkdir(Path("a/b/c"))
        assert Path("a/b/c") in mock.directories
        assert Path("a/b") in mock.directories
        assert Path("a") in mock.directories

    def test_mock_exists(self) -> None:
        """Test existence checking."""
        mock = MockFilesystemAdapter()
        assert mock.exists(Path("nonexistent")) is False
        mock.write_text(Path("test.txt"), "content")
        assert mock.exists(Path("test.txt")) is True

    def test_mock_copy_file(self) -> None:
        """Test file copying."""
        mock = MockFilesystemAdapter()
        mock.write_text(Path("src.txt"), "content")
        mock.copy_file(Path("src.txt"), Path("dst.txt"))
        assert mock.read_text(Path("dst.txt")) == "content"

    def test_mock_copy_nonexistent(self) -> None:
        """Test copying nonexistent file raises error."""
        mock = MockFilesystemAdapter()
        with pytest.raises(FileNotFoundError):
            mock.copy_file(Path("nonexistent"), Path("dst.txt"))

    def test_mock_remove(self) -> None:
        """Test file removal."""
        mock = MockFilesystemAdapter()
        mock.write_text(Path("test.txt"), "content")
        mock.remove(Path("test.txt"))
        assert mock.exists(Path("test.txt")) is False

    def test_mock_remove_nonexistent(self) -> None:
        """Test removing nonexistent file raises error."""
        mock = MockFilesystemAdapter()
        with pytest.raises(FileNotFoundError):
            mock.remove(Path("nonexistent"))

    def test_mock_glob(self) -> None:
        """Test glob pattern matching."""
        mock = MockFilesystemAdapter()
        mock.write_text(Path("dir/a.txt"), "a")
        mock.write_text(Path("dir/b.txt"), "b")
        mock.write_text(Path("dir/c.md"), "c")
        results = mock.glob(Path("dir"), "*.txt")
        assert len(results) == 2

    def test_mock_repr(self) -> None:
        """Test string representation."""
        mock = MockFilesystemAdapter()
        mock.write_text(Path("test.txt"), "content")
        repr_str = repr(mock)
        assert "MockFilesystemAdapter" in repr_str
        assert "files=1" in repr_str


class TestDefaultFilesystemAdapter:
    """Tests for DefaultFilesystemAdapter."""

    def test_default_repr(self) -> None:
        """Test string representation."""
        fs = DefaultFilesystemAdapter()
        assert repr(fs) == "DefaultFilesystemAdapter()"


class TestPathSecurityValidator:
    """Tests for PathSecurityValidator."""

    def test_absolute_path_passthrough(self, tmp_path: Path) -> None:
        """Test absolute paths pass through unchanged."""
        result = PathSecurityValidator.validate_workspace_boundary(tmp_path / "file.txt", tmp_path)
        assert result == tmp_path / "file.txt"

    def test_relative_path_resolution(self, tmp_path: Path) -> None:
        """Test relative paths are resolved against workspace."""
        # Create the directory structure
        (tmp_path / "subdir").mkdir()
        result = PathSecurityValidator.validate_workspace_boundary(Path("subdir"), tmp_path)
        assert result == (tmp_path / "subdir").resolve()

    def test_path_traversal_blocked(self, tmp_path: Path) -> None:
        """Test path traversal is blocked."""
        with pytest.raises(ValueError, match="escapes workspace"):
            PathSecurityValidator.validate_workspace_boundary(Path("../../../etc/passwd"), tmp_path)
