"""Tests for CLI module."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from docscope_mcp.cli import (
    WINDOWS_PLATFORM,
    get_mcp_server_config,
    get_venv_python,
    get_vscode_mcp_path,
    install_mcp,
    main,
    uninstall_mcp,
)


class TestGetVenvPython:
    """Tests for get_venv_python function."""

    @pytest.mark.parametrize(
        ("platform", "venv_subpath", "python_name", "expected_contains"),
        [
            ("linux", "bin", "python", [".venv", "python"]),
            (WINDOWS_PLATFORM, "Scripts", "python.exe", [".venv", "python.exe"]),
        ],
        ids=["linux_venv", "windows_venv"],
    )
    def test_detects_venv_python(
        self,
        tmp_path: Path,
        platform: str,
        venv_subpath: str,
        python_name: str,
        expected_contains: list[str],
    ) -> None:
        """Verify detection of venv Python path on different platforms."""
        venv_dir = tmp_path / ".venv" / venv_subpath
        venv_dir.mkdir(parents=True)
        venv_python = venv_dir / python_name
        venv_python.touch()

        with (
            patch("docscope_mcp.cli.Path.cwd", return_value=tmp_path),
            patch("docscope_mcp.cli.sys.platform", platform),
        ):
            result = get_venv_python()
            for expected in expected_contains:
                assert expected in result

    @pytest.mark.parametrize(
        ("has_venv_dir", "has_python"),
        [
            (False, False),  # No .venv at all
            (True, False),  # .venv exists but no python binary
        ],
        ids=["no_venv", "venv_no_python"],
    )
    def test_fallback_to_sys_executable(
        self,
        tmp_path: Path,
        has_venv_dir: bool,
        has_python: bool,  # noqa: ARG002
    ) -> None:
        """Verify fallback to sys.executable when venv unavailable."""
        if has_venv_dir:
            (tmp_path / ".venv").mkdir()

        with patch("docscope_mcp.cli.Path.cwd", return_value=tmp_path):
            result = get_venv_python()
            assert result == sys.executable


class TestGetMcpServerConfig:
    """Tests for get_mcp_server_config function."""

    def test_returns_valid_config_structure(self) -> None:
        """Verify config contains required MCP server fields."""
        config = get_mcp_server_config()
        assert "command" in config
        assert "args" in config
        assert config["args"] == ["-m", "docscope_mcp.server"]


class TestGetVscodeMcpPath:
    """Tests for get_vscode_mcp_path function."""

    @pytest.mark.parametrize(
        ("global_install", "insiders", "expected_parts"),
        [
            (False, False, [".vscode", "mcp.json"]),
            (True, False, [".config", "Code", "User", "mcp.json"]),
            (True, True, [".config", "Code - Insiders", "User", "mcp.json"]),
            (False, True, [".vscode", "mcp.json"]),  # insiders ignored for workspace
        ],
        ids=["workspace_path", "global_stable", "global_insiders", "workspace_insiders_ignored"],
    )
    def test_vscode_mcp_path(
        self, tmp_path: Path, global_install: bool, insiders: bool, expected_parts: list[str]
    ) -> None:
        """Verify correct path returned for workspace vs global install."""
        with patch("docscope_mcp.cli.Path.cwd", return_value=tmp_path):
            result = get_vscode_mcp_path(global_install=global_install, insiders=insiders)
            for part in expected_parts:
                assert part in str(result)


class TestInstallMcp:
    """Tests for install_mcp function."""

    def test_install_creates_new_config(self, tmp_path: Path) -> None:
        """Verify install creates mcp.json when it doesn't exist."""
        with patch("docscope_mcp.cli.Path.cwd", return_value=tmp_path):
            result = install_mcp(global_install=False)

            assert result == 0
            mcp_path = tmp_path / ".vscode" / "mcp.json"
            assert mcp_path.exists()
            config = json.loads(mcp_path.read_text())
            assert "docscope-mcp" in config["servers"]

    @pytest.mark.parametrize(
        ("initial_config", "expected_servers"),
        [
            ({"servers": {"other-server": {}}}, ["other-server", "docscope-mcp"]),
            ({"other_key": "value"}, ["docscope-mcp"]),
        ],
        ids=["preserves_existing", "adds_servers_key"],
    )
    def test_install_updates_existing_config(
        self, tmp_path: Path, initial_config: dict, expected_servers: list[str]
    ) -> None:
        """Verify install preserves existing servers and handles missing keys."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        mcp_path = vscode_dir / "mcp.json"
        mcp_path.write_text(json.dumps(initial_config))

        with patch("docscope_mcp.cli.Path.cwd", return_value=tmp_path):
            result = install_mcp(global_install=False)

            assert result == 0
            config = json.loads(mcp_path.read_text())
            for server in expected_servers:
                assert server in config["servers"]

    def test_install_handles_invalid_json(self, tmp_path: Path) -> None:
        """Verify install fails gracefully on invalid JSON."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "mcp.json").write_text("{ invalid json }")

        with patch("docscope_mcp.cli.Path.cwd", return_value=tmp_path):
            result = install_mcp(global_install=False)
            assert result == 1


class TestUninstallMcp:
    """Tests for uninstall_mcp function."""

    def test_uninstall_removes_server(self, tmp_path: Path) -> None:
        """Verify uninstall removes docscope-mcp from config."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        mcp_path = vscode_dir / "mcp.json"
        mcp_path.write_text(json.dumps({"servers": {"docscope-mcp": {}, "other-server": {}}}))

        with patch("docscope_mcp.cli.Path.cwd", return_value=tmp_path):
            result = uninstall_mcp(global_install=False)

            assert result == 0
            config = json.loads(mcp_path.read_text())
            assert "docscope-mcp" not in config["servers"]
            assert "other-server" in config["servers"]

    @pytest.mark.parametrize(
        ("setup", "expected_code"),
        [
            ("no_config", 0),
            ("no_server", 0),
            ("invalid_json", 1),
        ],
        ids=["missing_config", "missing_server", "invalid_json"],
    )
    def test_uninstall_edge_cases(self, tmp_path: Path, setup: str, expected_code: int) -> None:
        """Verify uninstall handles various edge cases."""
        vscode_dir = tmp_path / ".vscode"

        if setup == "no_server":
            vscode_dir.mkdir()
            (vscode_dir / "mcp.json").write_text(json.dumps({"servers": {"other-server": {}}}))
        elif setup == "invalid_json":
            vscode_dir.mkdir()
            (vscode_dir / "mcp.json").write_text("{ invalid json }")
        # "no_config" - do nothing, dir doesn't exist

        with patch("docscope_mcp.cli.Path.cwd", return_value=tmp_path):
            result = uninstall_mcp(global_install=False)
            assert result == expected_code


class TestMain:
    """Tests for main CLI entry point."""

    @pytest.mark.parametrize(
        ("argv", "expected_exit", "check_file"),
        [
            (["docscope-mcp"], 0, None),
            (["docscope-mcp", "install"], 0, ".vscode/mcp.json"),
            (["docscope-mcp", "uninstall"], 0, None),
        ],
        ids=["no_command", "install", "uninstall"],
    )
    def test_main_commands(
        self, tmp_path: Path, argv: list[str], expected_exit: int, check_file: str | None
    ) -> None:
        """Verify main dispatches commands correctly."""
        with (
            patch.object(sys, "argv", argv),
            patch("docscope_mcp.cli.Path.cwd", return_value=tmp_path),
        ):
            result = main()
            assert result == expected_exit
            if check_file:
                assert (tmp_path / check_file).exists()

    def test_main_install_global_flag(self, tmp_path: Path) -> None:
        """Verify main handles --global flag for install."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()

        with (
            patch.object(sys, "argv", ["docscope-mcp", "install", "--global"]),
            patch("docscope_mcp.cli.Path.home", return_value=home_dir),
        ):
            result = main()
            assert result == 0
            global_path = home_dir / ".config" / "Code" / "User" / "mcp.json"
            assert global_path.exists()

    @pytest.mark.parametrize(
        ("command", "flags", "expected_path_part"),
        [
            ("install", ["--global", "--insiders"], "Code - Insiders"),
            ("install", ["-g", "-i"], "Code - Insiders"),
            ("uninstall", ["--global", "--insiders"], "Code - Insiders"),
        ],
        ids=["install_insiders_long", "install_insiders_short", "uninstall_insiders"],
    )
    def test_main_insiders_flag(
        self, tmp_path: Path, command: str, flags: list[str], expected_path_part: str
    ) -> None:
        """Verify main handles --insiders flag for global operations."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        insiders_path = home_dir / ".config" / "Code - Insiders" / "User"
        insiders_path.mkdir(parents=True)

        # Pre-create config for uninstall test
        if command == "uninstall":
            mcp_json = insiders_path / "mcp.json"
            mcp_json.write_text(json.dumps({"servers": {"docscope-mcp": {}}}))

        with (
            patch.object(sys, "argv", ["docscope-mcp", command, *flags]),
            patch("docscope_mcp.cli.Path.home", return_value=home_dir),
        ):
            result = main()
            assert result == 0
            assert expected_path_part in str(insiders_path)
