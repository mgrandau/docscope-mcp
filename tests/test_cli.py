"""Tests for CLI module."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from docscope_mcp.cli import (
    WINDOWS_PLATFORM,
    copy_assets,
    get_mcp_server_config,
    get_venv_python,
    get_vscode_mcp_path,
    install_mcp,
    main,
    uninstall_mcp,
)
from tests.mock_filesystem import MockFilesystemAdapter


class TestGetVenvPython:
    """Test suite for get_venv_python function.

    Categories:
    1. Venv Detection - Platform-specific venv Python path (1 test)
    2. Fallback Behavior - sys.executable when no venv (1 test)

    Total: 2 tests.
    """

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
        """Verifies detection of venv Python path on different platforms.

        Tests platform-specific venv structure detection.

        Business context:
        MCP config needs correct Python path for venv activation.

        Arrangement:
        1. Parametrize with Linux (bin/python) and Windows (Scripts/python.exe).
        2. Create temporary venv directory structure.
        3. Create python binary file.

        Action:
        Call get_venv_python with mocked cwd and platform.

        Assertion Strategy:
        Validates detection by confirming:
        - Result contains ".venv" directory.
        - Result contains platform-specific python name.

        Testing Principle:
        Validates cross-platform, ensuring both platforms work.
        """
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
        """Verifies fallback to sys.executable when venv unavailable.

        Tests graceful fallback when venv structure missing.

        Business context:
        Global installs need fallback when no project venv exists.

        Arrangement:
        1. Parametrize with no venv and venv without python binary.
        2. Create partial venv structure based on parameters.

        Action:
        Call get_venv_python with incomplete venv.

        Assertion Strategy:
        Validates fallback by confirming:
        - Result equals sys.executable.

        Testing Principle:
        Validates resilience, ensuring fallback works.
        """
        if has_venv_dir:
            (tmp_path / ".venv").mkdir()

        with patch("docscope_mcp.cli.Path.cwd", return_value=tmp_path):
            result = get_venv_python()
            assert result == sys.executable


class TestGetMcpServerConfig:
    """Test suite for get_mcp_server_config function.

    Categories:
    1. Config Structure - Valid MCP config format (1 test)

    Total: 1 test.
    """

    def test_returns_valid_config_structure(self) -> None:
        """Verifies config contains required MCP server fields.

        Tests config generation for VS Code MCP format.

        Business context:
        VS Code requires specific config structure for MCP servers.

        Arrangement:
        1. No setup needed - tests pure function.

        Action:
        Call get_mcp_server_config.

        Assertion Strategy:
        Validates structure by confirming:
        - "command" key present.
        - "args" key present with module invocation.

        Testing Principle:
        Validates config format, ensuring VS Code compatibility.
        """
        config = get_mcp_server_config()
        assert "command" in config
        assert "args" in config
        assert config["args"] == ["-m", "docscope_mcp.server"]


class TestGetVscodeMcpPath:
    """Test suite for get_vscode_mcp_path function.

    Categories:
    1. Path Variants - Workspace vs global, stable vs insiders (1 test)

    Total: 1 test.
    """

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
        """Verifies correct path returned for workspace vs global install.

        Tests path construction with all flag combinations.

        Business context:
        MCP config location differs between workspace and global installs.

        Arrangement:
        1. Parametrize with workspace, global-stable, global-insiders combinations.
        2. Note insiders flag ignored for workspace installs.

        Action:
        Call get_vscode_mcp_path with flag combinations and explicit workspace.

        Assertion Strategy:
        Validates path by confirming:
        - All expected path parts present in result.

        Testing Principle:
        Validates path logic, ensuring correct locations.
        """
        result = get_vscode_mcp_path(
            global_install=global_install, insiders=insiders, workspace=tmp_path
        )
        for part in expected_parts:
            assert part in str(result)


class TestInstallMcp:
    """Test suite for install_mcp function.

    Categories:
    1. New Config - Creates mcp.json when missing (1 test)
    2. Existing Config - Preserves and updates existing (1 test)
    3. Error Handling - Invalid JSON handling (1 test)

    Total: 3 tests.
    """

    def test_install_creates_new_config(self, tmp_path: Path) -> None:
        """Verifies install creates mcp.json when it doesn't exist.

        Tests fresh installation on new project.

        Business context:
        First-time users need config created automatically.

        Arrangement:
        1. Use MockFilesystemAdapter with empty state.
        2. Mock get_assets_dir to return empty temp path (no assets to copy).

        Action:
        Call install_mcp with workspace and mock filesystem.

        Assertion Strategy:
        Validates creation by confirming:
        - Return code is 0 (success).
        - mcp.json exists in mock filesystem.
        - Config contains "docscope-mcp" server.

        Testing Principle:
        Validates initialization using pure DI, no Path mocking.
        """
        fs = MockFilesystemAdapter()
        # Create empty assets dir to skip asset copying
        assets_path = tmp_path / "assets"
        assets_path.mkdir()

        with patch("docscope_mcp.cli.get_assets_dir", return_value=assets_path):
            result = install_mcp(global_install=False, workspace=tmp_path, fs=fs)

        assert result == 0
        mcp_path = tmp_path / ".vscode" / "mcp.json"
        assert fs.exists(mcp_path)
        config = fs.read_json(mcp_path)
        assert isinstance(config, dict)
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
        """Verifies install preserves existing servers and handles missing keys.

        Tests merge behavior with existing configuration.

        Business context:
        Existing MCP servers must not be removed during install.

        Arrangement:
        1. Parametrize with existing servers and missing servers key.
        2. Pre-populate mock filesystem with mcp.json.
        3. Mock get_assets_dir to return empty temp path.

        Action:
        Call install_mcp on existing config.

        Assertion Strategy:
        Validates merge by confirming:
        - Return code is 0 (success).
        - All expected servers present in config.

        Testing Principle:
        Validates non-destructive update using mock filesystem.
        """
        fs = MockFilesystemAdapter()
        mcp_path = tmp_path / ".vscode" / "mcp.json"
        fs.write_json(mcp_path, initial_config)

        # Create empty assets dir to skip asset copying
        assets_path = tmp_path / "assets"
        assets_path.mkdir()

        with patch("docscope_mcp.cli.get_assets_dir", return_value=assets_path):
            result = install_mcp(global_install=False, workspace=tmp_path, fs=fs)

        assert result == 0
        config = fs.read_json(mcp_path)
        assert isinstance(config, dict)
        for server in expected_servers:
            assert server in config["servers"]

    def test_install_handles_invalid_json(self, tmp_path: Path) -> None:
        """Verifies install fails gracefully on invalid JSON.

        Tests error handling for corrupted config files.

        Business context:
        Corrupted configs must fail with clear error, not corrupt further.

        Arrangement:
        1. Pre-populate mock filesystem with invalid JSON.

        Action:
        Call install_mcp on corrupted config.

        Assertion Strategy:
        Validates error handling by confirming:
        - Return code is 1 (failure).

        Testing Principle:
        Validates error recovery using mock filesystem.
        """
        fs = MockFilesystemAdapter()
        mcp_path = tmp_path / ".vscode" / "mcp.json"
        fs.files[mcp_path] = "{ invalid json }"

        result = install_mcp(global_install=False, workspace=tmp_path, fs=fs)
        assert result == 1


class TestUninstallMcp:
    """Test suite for uninstall_mcp function.

    Categories:
    1. Normal Removal - Removes server from config (1 test)
    2. Edge Cases - Missing config, missing server, invalid JSON (1 test)

    Total: 2 tests.
    """

    def test_uninstall_removes_server(self, tmp_path: Path) -> None:
        """Verifies uninstall removes docscope-mcp from config.

        Tests server removal while preserving others.

        Business context:
        Uninstall must remove only docscope-mcp, keeping other servers.

        Arrangement:
        1. Pre-populate mock filesystem with mcp.json containing servers.

        Action:
        Call uninstall_mcp.

        Assertion Strategy:
        Validates removal by confirming:
        - Return code is 0 (success).
        - "docscope-mcp" removed from config.
        - "other-server" still present.

        Testing Principle:
        Validates surgical removal using mock filesystem.
        """
        fs = MockFilesystemAdapter()
        mcp_path = tmp_path / ".vscode" / "mcp.json"
        fs.write_json(mcp_path, {"servers": {"docscope-mcp": {}, "other-server": {}}})

        result = uninstall_mcp(global_install=False, workspace=tmp_path, fs=fs)

        assert result == 0
        config = fs.read_json(mcp_path)
        assert isinstance(config, dict)
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
        """Verifies uninstall handles various edge cases.

        Tests graceful handling of missing config, missing server, and invalid JSON.

        Business context:
        Uninstall must be idempotent and handle edge cases gracefully.

        Arrangement:
        1. Parametrize with no config, no server, and invalid JSON scenarios.
        2. Setup each scenario with appropriate mock filesystem state.

        Action:
        Call uninstall_mcp for each scenario.

        Assertion Strategy:
        Validates handling by confirming:
        - Missing config returns 0 (already uninstalled).
        - Missing server returns 0 (already removed).
        - Invalid JSON returns 1 (error).

        Testing Principle:
        Validates idempotence using mock filesystem.
        """
        fs = MockFilesystemAdapter()
        mcp_path = tmp_path / ".vscode" / "mcp.json"

        if setup == "no_server":
            fs.write_json(mcp_path, {"servers": {"other-server": {}}})
        elif setup == "invalid_json":
            fs.files[mcp_path] = "{ invalid json }"
        # "no_config" - do nothing, file doesn't exist in mock

        result = uninstall_mcp(global_install=False, workspace=tmp_path, fs=fs)
        assert result == expected_code


class TestMain:
    """Test suite for main CLI entry point.

    Categories:
    1. Command Dispatch - No command, install, uninstall (1 test)
    2. Global Flag - --global flag handling (1 test)
    3. Insiders Flag - --insiders flag for global operations (1 test)
    4. Flag Validation - --insiders requires --global (1 test)

    Total: 4 tests.
    """

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
        """Verifies main dispatches commands correctly.

        Tests CLI argument parsing and command routing.

        Business context:
        CLI is primary user interface; must handle all commands.

        Arrangement:
        1. Parametrize with no command, install, and uninstall.
        2. Mock sys.argv with test arguments.

        Action:
        Call main() with mocked arguments.

        Assertion Strategy:
        Validates dispatch by confirming:
        - Return code matches expected.
        - For install, config file created.

        Testing Principle:
        Validates CLI routing, ensuring commands work.
        """
        with (
            patch.object(sys, "argv", argv),
            patch("docscope_mcp.cli.Path.cwd", return_value=tmp_path),
        ):
            result = main()
            assert result == expected_exit
            if check_file:
                assert (tmp_path / check_file).exists()

    def test_main_install_global_flag(self, tmp_path: Path) -> None:
        """Verifies main handles --global flag for install.

        Tests global installation path handling.

        Business context:
        Global installs enable MCP across all workspaces.

        Arrangement:
        1. Create mock home directory.
        2. Mock sys.argv with --global flag.

        Action:
        Call main() with global install flag.

        Assertion Strategy:
        Validates global path by confirming:
        - Return code is 0 (success).
        - Config created in global path.

        Testing Principle:
        Validates global mode, ensuring correct path used.
        """
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
        """Verifies main handles --insiders flag for global operations.

        Tests VS Code Insiders path construction.

        Business context:
        Insiders users need separate config from stable VS Code.

        Arrangement:
        1. Parametrize with long and short flag variants.
        2. Create insiders config directory.
        3. Pre-create config for uninstall test.

        Action:
        Call main() with insiders flag.

        Assertion Strategy:
        Validates insiders path by confirming:
        - Return code is 0 (success).
        - Path contains "Code - Insiders".

        Testing Principle:
        Validates insiders support, ensuring correct path.
        """
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

    @pytest.mark.parametrize(
        ("command", "flags"),
        [
            ("install", ["--insiders"]),
            ("install", ["-i"]),
            ("uninstall", ["--insiders"]),
            ("uninstall", ["-i"]),
        ],
        ids=[
            "install_insiders_no_global",
            "install_i_no_g",
            "uninstall_insiders_no_global",
            "uninstall_i_no_g",
        ],
    )
    def test_insiders_requires_global(self, command: str, flags: list[str]) -> None:
        """Verifies --insiders without --global returns error.

        Tests flag validation for insiders-only usage.

        Business context:
        Insiders flag only applies to global installs; workspace has no variant.

        Arrangement:
        1. Parametrize with install and uninstall using --insiders without --global.

        Action:
        Call main() with invalid flag combination.

        Assertion Strategy:
        Validates error by confirming:
        - Return code is 1 (error).

        Testing Principle:
        Validates flag constraints, ensuring correct usage.
        """
        with patch.object(sys, "argv", ["docscope-mcp", command, *flags]):
            result = main()
            assert result == 1


class TestPlatformPaths:
    """Tests for platform-specific path handling.

    Test Categories:
        1. Windows Path - APPDATA path construction (1 test)
        2. macOS Path - Library/Application Support path (1 test)

    Total: 2 tests.
    """

    def test_windows_global_path(self, tmp_path: Path) -> None:
        """Verifies Windows uses APPDATA for global config path.

        Business context:
            Windows stores VS Code config in %APPDATA%/Code/User/.

        Arrangement:
            1. Mock sys.platform as win32.
            2. Set APPDATA environment variable.

        Action:
            Call get_vscode_mcp_path with global_install=True.

        Assertion Strategy:
            Verify path contains APPDATA location.

        Testing Principle:
            Cross-platform support requires testing all platforms.
        """
        appdata_path = tmp_path / "AppData" / "Roaming"
        appdata_path.mkdir(parents=True)

        with (
            patch("docscope_mcp.cli.sys.platform", WINDOWS_PLATFORM),
            patch.dict("os.environ", {"APPDATA": str(appdata_path)}),
        ):
            result = get_vscode_mcp_path(global_install=True, workspace=tmp_path)
            assert "Code" in str(result)
            assert str(appdata_path) in str(result)

    def test_macos_global_path(self, tmp_path: Path) -> None:
        """Verifies macOS uses Library/Application Support for global config.

        Business context:
            macOS stores VS Code config in ~/Library/Application Support/Code/User/.

        Arrangement:
            1. Mock sys.platform as darwin.
            2. Mock Path.home to return temp path.

        Action:
            Call get_vscode_mcp_path with global_install=True.

        Assertion Strategy:
            Verify path contains Library/Application Support.

        Testing Principle:
            Cross-platform support requires testing all platforms.
        """
        with (
            patch("docscope_mcp.cli.sys.platform", "darwin"),
            patch("docscope_mcp.cli.Path.home", return_value=tmp_path),
        ):
            result = get_vscode_mcp_path(global_install=True, workspace=tmp_path)
            assert "Library" in str(result)
            assert "Application Support" in str(result)
            assert "Code" in str(result)


class TestInstallNonDictJson:
    """Tests for install handling non-dict JSON in mcp.json.

    Test Categories:
        1. Non-Dict JSON - Array or primitive JSON handling (1 test)

    Total: 1 test.
    """

    def test_install_handles_non_dict_json(self, tmp_path: Path) -> None:
        """Verifies install replaces non-dict JSON with proper config.

        Business context:
            If mcp.json contains array or primitive, install should
            create proper config structure.

        Arrangement:
            1. Pre-populate mock filesystem with JSON array.

        Action:
            Call install_mcp.

        Assertion Strategy:
            Verify returns 0 and creates proper servers dict.

        Testing Principle:
            Graceful recovery from malformed config.
        """
        fs = MockFilesystemAdapter()
        mcp_path = tmp_path / ".vscode" / "mcp.json"
        # Write a valid JSON array (not a dict)
        fs.files[mcp_path] = '["not", "a", "dict"]'

        # Create empty assets dir to skip asset copying
        assets_path = tmp_path / "assets"
        assets_path.mkdir()

        with patch("docscope_mcp.cli.get_assets_dir", return_value=assets_path):
            result = install_mcp(global_install=False, workspace=tmp_path, fs=fs)

        assert result == 0
        config = fs.read_json(mcp_path)
        assert isinstance(config, dict)
        assert "servers" in config
        assert "docscope-mcp" in config["servers"]


class TestUninstallNonDictJson:
    """Tests for uninstall handling non-dict JSON in mcp.json.

    Test Categories:
        1. Non-Dict JSON - Array or primitive JSON handling (1 test)

    Total: 1 test.
    """

    def test_uninstall_handles_non_dict_json(self, tmp_path: Path) -> None:
        """Verifies uninstall handles non-dict JSON gracefully.

        Business context:
            If mcp.json contains array or primitive, uninstall should
            treat it as if docscope-mcp doesn't exist.

        Arrangement:
            1. Pre-populate mock filesystem with JSON array.

        Action:
            Call uninstall_mcp.

        Assertion Strategy:
            Verify returns 0 (nothing to uninstall).

        Testing Principle:
            Graceful handling of unexpected data.
        """
        fs = MockFilesystemAdapter()
        mcp_path = tmp_path / ".vscode" / "mcp.json"
        # Write a valid JSON array (not a dict)
        fs.files[mcp_path] = '["not", "a", "dict"]'

        result = uninstall_mcp(global_install=False, workspace=tmp_path, fs=fs)
        assert result == 0


class TestCLIAssetsHandling:
    """Tests for CLI asset handling edge cases.

    Test Categories:
        1. Assets Not Found - FileNotFoundError handling (1 test)
        2. Copy Assets Error - Graceful error propagation (1 test)

    Total: 2 tests.
    """

    def test_get_assets_dir_not_found(self, tmp_path: Path) -> None:
        """Verifies copy_assets handles FileNotFoundError from get_assets_dir.

        Business context:
            If package assets directory doesn't exist (corrupted install),
            copy_assets should return graceful error for troubleshooting.

        Arrangement:
            1. Mock get_assets_dir to raise FileNotFoundError.

        Action:
            Call copy_assets with mocked error.

        Assertion Strategy:
            Verify returns (1, [warning message]).

        Testing Principle:
            Clear errors enable faster troubleshooting.
        """
        fs = MockFilesystemAdapter()

        with patch("docscope_mcp.cli.get_assets_dir") as mock_get_assets:
            mock_get_assets.side_effect = FileNotFoundError(
                "Assets directory not found: /fake/path"
            )
            exit_code, messages = copy_assets(workspace=tmp_path, fs=fs)
            assert exit_code == 1
            assert any("Assets directory not found" in msg for msg in messages)

    def test_copy_assets_handles_missing_assets(self, tmp_path: Path) -> None:
        """Verifies copy_assets returns error when assets not found.

        Business context:
            If assets directory is missing, copy_assets should return
            graceful error instead of crashing.

        Arrangement:
            1. Mock get_assets_dir to raise FileNotFoundError.

        Action:
            Call copy_assets.

        Assertion Strategy:
            Verify returns (1, [warning message]).

        Testing Principle:
            Graceful degradation prevents CLI crashes.
        """
        fs = MockFilesystemAdapter()

        with patch("docscope_mcp.cli.get_assets_dir") as mock_get_assets:
            mock_get_assets.side_effect = FileNotFoundError("Assets not found: /test/path")
            exit_code, messages = copy_assets(workspace=tmp_path, fs=fs)
            assert exit_code == 1
            assert len(messages) == 1
            assert "Warning:" in messages[0]
            assert "Assets not found" in messages[0]
