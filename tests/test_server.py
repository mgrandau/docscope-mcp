"""Tests for MCP server."""

import pytest

from docscope_mcp.server import DocScopeMCPServer, JSONRPCErrorCode
from tests.mock_filesystem import MockFilesystemAdapter


class TestDocScopeMCPServer:
    """Test suite for DocScopeMCPServer.

    Categories:
    1. Initialization - Server creation, tool registration (1 test)
    2. Protocol Handling - Initialize, tools/list (2 tests)
    3. Tool Execution - analyze_code and analyze_file tools (2 tests)
    4. Error Handling - Unknown methods, tools, params (1 test)
    5. Language Support - Unsupported language error (1 test)

    Total: 7 tests.
    """

    def test_server_creation(self) -> None:
        """Verifies DocScopeMCPServer initializes with tools.

        Tests server construction and tool registration.

        Business context:
        Server must have analyze_code and analyze_file tools registered.

        Arrangement:
        1. No setup needed - tests constructor.

        Action:
        Instantiate DocScopeMCPServer.

        Assertion Strategy:
        Validates registration by confirming:
        - "analyze_code" in tools dict with language param.
        - "analyze_file" in tools dict with file_path param.

        Testing Principle:
        Validates initialization, ensuring tools registered.
        """
        server = DocScopeMCPServer()
        assert "analyze_code" in server.tools
        assert "analyze_file" in server.tools
        assert "language" in str(server.tools["analyze_code"]["inputSchema"])
        assert "file_path" in str(server.tools["analyze_file"]["inputSchema"])

    @pytest.mark.asyncio
    async def test_handle_initialize(self) -> None:
        """Verifies initialize method returns correct protocol version.

        Tests MCP protocol handshake response.

        Business context:
        Protocol version negotiation required for MCP compatibility.

        Arrangement:
        1. Create server instance.
        2. Construct initialize message with protocol version.

        Action:
        Call handle_message with initialize request.

        Assertion Strategy:
        Validates response by confirming:
        - JSON-RPC version is "2.0".
        - Response ID matches request ID.
        - Result contains protocolVersion.

        Testing Principle:
        Validates protocol compliance, ensuring correct handshake.
        """
        server = DocScopeMCPServer()
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
        }
        response = await server.handle_message(message)
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["protocolVersion"] == "2024-11-05"

    @pytest.mark.asyncio
    async def test_handle_tools_list(self) -> None:
        """Verifies tools/list returns registered tools with metadata.

        Tests tool discovery endpoint.

        Business context:
        Clients discover available tools via tools/list method.

        Arrangement:
        1. Create server instance.
        2. Construct tools/list message.

        Action:
        Call handle_message with tools/list request.

        Assertion Strategy:
        Validates response by confirming:
        - JSON-RPC version is "2.0".
        - Result contains tools array.
        - Both "analyze_code" and "analyze_file" in tool names.

        Testing Principle:
        Validates discovery, ensuring tools enumerable.
        """
        server = DocScopeMCPServer()
        message = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        response = await server.handle_message(message)
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        tool_names = [t["name"] for t in response["result"]["tools"]]
        assert "analyze_code" in tool_names
        assert "analyze_file" in tool_names

    @pytest.mark.asyncio
    async def test_handle_tools_call_analyze_code(self) -> None:
        """Verifies analyze_code tool executes and returns content.

        Tests end-to-end tool invocation with code and language.

        Business context:
        Primary server function is analyzing code via tool call.

        Arrangement:
        1. Create server instance.
        2. Construct tools/call message with code and language.

        Action:
        Call handle_message with analyze_code request.

        Assertion Strategy:
        Validates execution by confirming:
        - Result key present in response.
        - Content key present in result.

        Testing Principle:
        Validates execution, ensuring tool returns content.
        """
        server = DocScopeMCPServer()
        message = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "analyze_code",
                "arguments": {"code": "def example(): pass", "language": "python"},
            },
        }
        response = await server.handle_message(message)
        assert "result" in response
        assert "content" in response["result"]

    @pytest.mark.asyncio
    async def test_handle_tools_call_analyze_file(self) -> None:
        """Verifies analyze_file tool reads file and returns content.

        Tests file reading and analysis via tool call.

        Business context:
        analyze_file provides convenience for analyzing files on disk.

        Arrangement:
        1. Create mock filesystem with Python file.
        2. Create server with mock filesystem.
        3. Construct tools/call message with file_path.

        Action:
        Call handle_message with analyze_file request.

        Assertion Strategy:
        Validates execution by confirming:
        - Result key present in response.
        - Content key present in result.

        Testing Principle:
        Validates file reading, ensuring tool reads and analyzes.
        """
        from pathlib import Path

        mock_fs = MockFilesystemAdapter()
        mock_fs.files[Path("test.py")] = "def example(): pass"
        server = DocScopeMCPServer(filesystem=mock_fs)
        message = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "analyze_file",
                "arguments": {"file_path": "test.py"},
            },
        }
        response = await server.handle_message(message)
        assert "result" in response
        assert "content" in response["result"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("method", "params", "expected_error_code"),
        [
            ("unknown_method", None, JSONRPCErrorCode.METHOD_NOT_FOUND),
            (
                "tools/call",
                {"name": "unknown_tool", "arguments": {}},
                JSONRPCErrorCode.METHOD_NOT_FOUND,
            ),
            (
                "tools/call",
                {"name": "analyze_code", "arguments": {}},
                JSONRPCErrorCode.INVALID_PARAMS,
            ),
        ],
        ids=["unknown_method", "unknown_tool", "missing_code_param"],
    )
    async def test_error_responses(
        self, method: str, params: dict | None, expected_error_code: JSONRPCErrorCode
    ) -> None:
        """Verifies error handling for various invalid requests.

        Tests JSON-RPC error codes for different failure modes.

        Business context:
        MCP protocol requires specific error codes for client handling.

        Arrangement:
        1. Parametrize with unknown method, unknown tool, and missing params.
        2. Create server instance.

        Action:
        Call handle_message with invalid request.

        Assertion Strategy:
        Validates error codes by confirming:
        - Error key present in response.
        - Error code matches expected JSON-RPC code.

        Testing Principle:
        Validates error protocol, ensuring correct error codes.
        """
        server = DocScopeMCPServer()
        message = {"jsonrpc": "2.0", "id": 1, "method": method}
        if params:
            message["params"] = params
        response = await server.handle_message(message)
        assert "error" in response
        assert response["error"]["code"] == expected_error_code.value

    @pytest.mark.asyncio
    async def test_handle_unsupported_language(self) -> None:
        """Verifies unsupported language returns descriptive error.

        Tests error message for unknown language parameter.

        Business context:
        Clear error messages help users identify supported languages.

        Arrangement:
        1. Create server instance.
        2. Construct request with unsupported language.

        Action:
        Call handle_message with unsupported language.

        Assertion Strategy:
        Validates message by confirming:
        - Error key present in response.
        - Message mentions unsupported language.

        Testing Principle:
        Validates error messaging, ensuring helpful diagnostics.
        """
        server = DocScopeMCPServer()
        message = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "analyze_code",
                "arguments": {
                    "code": "fn main() {}",
                    "language": "rust",  # Unsupported
                },
            },
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert "unsupported language" in response["error"]["message"].lower()


class TestResultFormatting:
    """Test suite for result formatting.

    Categories:
    1. Empty Results - Success message for no issues (1 test)
    2. Content Formatting - Various docstring scenarios (1 test)
    3. Truncation - Max results display limit (1 test)
    4. Malformed Results - Graceful handling of bad data (1 test)

    Total: 4 tests.
    """

    def test_format_empty_results(self) -> None:
        """Verifies empty results produce success message.

        Tests output formatting when no documentation issues found.

        Business context:
        Users need confirmation when code is fully documented.

        Arrangement:
        1. Create server instance.

        Action:
        Call _format_results with empty list.

        Assertion Strategy:
        Validates message by confirming:
        - Output contains message about no functions found.

        Testing Principle:
        Validates empty case, ensuring informative feedback.
        """
        server = DocScopeMCPServer()
        result = server._format_results([])
        assert "no functions found" in result.lower()

    @pytest.mark.parametrize(
        ("docstring", "priority", "expected_in_output"),
        [
            ("", 10, ["test_func", "Line 10", "POOR", "No docstring"]),
            ("Brief description only.", 5, ["Current:", "Brief description"]),
            ("A" * 500, 3, ["..."]),  # Long docstring truncated
        ],
        ids=["no_docstring", "with_docstring_preview", "long_docstring_ellipsis"],
    )
    def test_format_results_content(
        self, docstring: str, priority: int, expected_in_output: list[str]
    ) -> None:
        """Verifies result formatting for various docstring scenarios.

        Tests output format with empty, brief, and long docstrings.

        Business context:
        Formatted output guides users to highest-priority improvements.

        Arrangement:
        1. Parametrize with empty, brief, and long (500 char) docstrings.
        2. Create result dict with appropriate quality assessment.

        Action:
        Call _format_results with single result.

        Assertion Strategy:
        Validates format by confirming:
        - Empty docstring shows "No docstring" text.
        - Brief docstring shows preview.
        - Long docstring shows ellipsis (truncated).

        Testing Principle:
        Validates output quality, ensuring readable format.
        """
        server = DocScopeMCPServer()
        results = [
            {
                "function_name": "test_func",
                "line_number": 10,
                "priority": priority,
                "current_docstring": docstring,
                "quality_assessment": {
                    "quality": "poor" if not docstring else "basic",
                    "missing": ["docstring"] if not docstring else [],
                    "needs_improvement": True,
                },
            },
        ]
        formatted = server._format_results(results)
        for expected in expected_in_output:
            assert expected in formatted

    def test_format_results_truncation(self) -> None:
        """Verifies results are truncated at max_results_display.

        Tests output limit when many results present.

        Business context:
        Large result sets need truncation to remain usable.

        Arrangement:
        1. Create 15 result dicts.

        Action:
        Call _format_results with 15 results.

        Assertion Strategy:
        Validates truncation by confirming:
        - Output contains "... and 5 more functions" message.

        Testing Principle:
        Validates UX, ensuring output remains manageable.
        """
        server = DocScopeMCPServer()
        results = [
            {
                "function_name": f"func_{i}",
                "line_number": i * 10,
                "priority": 5,
                "current_docstring": "",
                "quality_assessment": {
                    "quality": "poor",
                    "missing": ["docstring"],
                    "needs_improvement": True,
                },
            }
            for i in range(15)
        ]
        formatted = server._format_results(results)
        assert "... and 5 more functions" in formatted

    def test_format_results_malformed_result_logged(self) -> None:
        """Verifies malformed results are skipped gracefully.

        Tests resilience when result dict missing required keys.

        Business context:
        Analyzer errors should not crash formatting.

        Arrangement:
        1. Create list with one malformed and one valid result.

        Action:
        Call _format_results with mixed results.

        Assertion Strategy:
        Validates resilience by confirming:
        - Valid result appears in output.

        Testing Principle:
        Validates error tolerance, ensuring partial success.
        """
        server = DocScopeMCPServer()
        results = [
            {"incomplete": "result"},
            {
                "function_name": "good_func",
                "line_number": 1,
                "priority": 5,
                "current_docstring": "",
                "quality_assessment": {
                    "quality": "poor",
                    "missing": ["docstring"],
                    "needs_improvement": True,
                },
            },
        ]
        formatted = server._format_results(results)
        assert "good_func" in formatted


class TestServerAnalysisEdgeCases:
    """Test suite for analysis edge cases in server.

    Categories:
    1. Size Limits - Code exceeding max size (1 test)
    2. Analyzer Errors - Syntax error handling (1 test)
    3. Unexpected Exceptions - Runtime error wrapping (1 test)

    Total: 3 tests.
    """

    @pytest.mark.asyncio
    async def test_code_too_large_returns_error(self) -> None:
        """Verifies code exceeding max size returns error.

        Tests size limit enforcement at server level.

        Business context:
        Large code blocks could exhaust memory; must reject early.

        Arrangement:
        1. Create config with small max_code_size=100.
        2. Create server with restrictive config.
        3. Generate code exceeding limit.

        Action:
        Call handle_message with oversized code.

        Assertion Strategy:
        Validates rejection by confirming:
        - Error key present in response.
        - Message mentions "too large".

        Testing Principle:
        Validates resource protection, ensuring limits enforced.
        """
        from docscope_mcp.models import AnalysisConfig

        config = AnalysisConfig(max_code_size=100)
        server = DocScopeMCPServer(config=config)
        large_code = "x = 1\n" * 50

        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "analyze_code",
                "arguments": {"code": large_code, "language": "python"},
            },
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert "too large" in response["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_analyzer_error_returns_internal_error(self) -> None:
        """Verifies analyzer errors (syntax errors) are returned as INTERNAL_ERROR.

        Tests error code for parser failures.

        Business context:
        Syntax errors are not user errors; return INTERNAL_ERROR.

        Arrangement:
        1. Create server instance.
        2. Construct request with syntactically invalid Python.

        Action:
        Call handle_message with broken code.

        Assertion Strategy:
        Validates error code by confirming:
        - Error key present in response.
        - Error code equals INTERNAL_ERROR.

        Testing Principle:
        Validates error classification, ensuring correct code.
        """
        server = DocScopeMCPServer()
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "analyze_code",
                "arguments": {"code": "def broken(", "language": "python"},
            },
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert response["error"]["code"] == JSONRPCErrorCode.INTERNAL_ERROR.value

    @pytest.mark.asyncio
    async def test_unexpected_exception_returns_internal_error(self) -> None:
        """Verifies unexpected exceptions are caught and returned as INTERNAL_ERROR.

        Tests exception isolation by mocking analyze_code to raise.

        Business context:
        Unexpected failures must not crash server; return structured error.

        Arrangement:
        1. Create server instance.
        2. Patch analyze_code to raise RuntimeError.

        Action:
        Call handle_message with mocked exception.

        Assertion Strategy:
        Validates wrapping by confirming:
        - Error key present in response.
        - Error code equals INTERNAL_ERROR.
        - Message contains exception text.

        Testing Principle:
        Validates exception isolation, ensuring server stability.
        """
        from unittest.mock import patch

        server = DocScopeMCPServer()
        # Mock analyze_code to raise an exception
        with patch(
            "docscope_mcp.server.analyze_code",
            side_effect=RuntimeError("Unexpected failure"),
        ):
            message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "analyze_code",
                    "arguments": {"code": "def f(): pass", "language": "python"},
                },
            }
            response = await server.handle_message(message)
        assert "error" in response
        assert response["error"]["code"] == JSONRPCErrorCode.INTERNAL_ERROR.value
        assert "Unexpected failure" in response["error"]["message"]


class TestAnalyzeCodeValidation:
    """Tests for analyze_code parameter validation.

    Test Categories:
        1. Missing Parameters - code, language (2 tests)
        2. Invalid Types - non-string code, non-string language (2 tests)
        3. Invalid Language - unsupported language value (1 test)

    Total: 5 tests.
    """

    @pytest.mark.asyncio
    async def test_missing_code_returns_error(self) -> None:
        """Verifies missing code parameter returns INVALID_PARAMS error."""
        server = DocScopeMCPServer()
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "analyze_code",
                "arguments": {"language": "python"},
            },
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert response["error"]["code"] == JSONRPCErrorCode.INVALID_PARAMS.value
        assert "code" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_missing_language_returns_error(self) -> None:
        """Verifies missing language parameter returns INVALID_PARAMS error."""
        server = DocScopeMCPServer()
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "analyze_code",
                "arguments": {"code": "def f(): pass"},
            },
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert response["error"]["code"] == JSONRPCErrorCode.INVALID_PARAMS.value
        assert "language" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_invalid_code_type_returns_error(self) -> None:
        """Verifies non-string code returns INVALID_PARAMS error."""
        server = DocScopeMCPServer()
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "analyze_code",
                "arguments": {"code": 123, "language": "python"},
            },
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert response["error"]["code"] == JSONRPCErrorCode.INVALID_PARAMS.value
        assert "code" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_invalid_language_type_returns_error(self) -> None:
        """Verifies non-string language returns INVALID_PARAMS error."""
        server = DocScopeMCPServer()
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "analyze_code",
                "arguments": {"code": "def f(): pass", "language": 123},
            },
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert response["error"]["code"] == JSONRPCErrorCode.INVALID_PARAMS.value
        assert "language" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_unsupported_language_returns_error(self) -> None:
        """Verifies unsupported language value returns INVALID_PARAMS error."""
        server = DocScopeMCPServer()
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "analyze_code",
                "arguments": {"code": "fn main() {}", "language": "rust"},
            },
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert response["error"]["code"] == JSONRPCErrorCode.INVALID_PARAMS.value
        assert "Unsupported language" in response["error"]["message"]


class TestAnalyzeFileValidation:
    """Tests for analyze_file parameter validation.

    Test Categories:
        1. Missing Parameters - file_path (1 test)
        2. Invalid Types - non-string file_path (1 test)
        3. File Errors - not found, permission denied, invalid encoding (3 tests)
        4. Unsupported Extension - unknown file type (1 test)

    Total: 6 tests.
    """

    @pytest.mark.asyncio
    async def test_missing_file_path_returns_error(self) -> None:
        """Verifies missing file_path returns INVALID_PARAMS error."""
        server = DocScopeMCPServer()
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "analyze_file",
                "arguments": {},
            },
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert response["error"]["code"] == JSONRPCErrorCode.INVALID_PARAMS.value
        assert "file_path" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_invalid_file_path_type_returns_error(self) -> None:
        """Verifies non-string file_path returns INVALID_PARAMS error."""
        server = DocScopeMCPServer()
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "analyze_file",
                "arguments": {"file_path": 123},
            },
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert response["error"]["code"] == JSONRPCErrorCode.INVALID_PARAMS.value
        assert "file_path" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_file_not_found_returns_error(self) -> None:
        """Verifies missing file returns INVALID_PARAMS error."""
        mock_fs = MockFilesystemAdapter()
        server = DocScopeMCPServer(filesystem=mock_fs)
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "analyze_file",
                "arguments": {"file_path": "nonexistent.py"},
            },
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert response["error"]["code"] == JSONRPCErrorCode.INVALID_PARAMS.value
        assert "not found" in response["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_unsupported_extension_returns_error(self) -> None:
        """Verifies unsupported file extension returns INVALID_PARAMS error."""
        from pathlib import Path

        mock_fs = MockFilesystemAdapter()
        mock_fs.files[Path("readme.txt")] = "some text"
        server = DocScopeMCPServer(filesystem=mock_fs)
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "analyze_file",
                "arguments": {"file_path": "readme.txt"},
            },
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert response["error"]["code"] == JSONRPCErrorCode.INVALID_PARAMS.value
        assert "Cannot detect language" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_file_too_large_returns_error(self) -> None:
        """Verifies file exceeding max size returns error."""
        from pathlib import Path

        from docscope_mcp.models import AnalysisConfig

        mock_fs = MockFilesystemAdapter()
        mock_fs.files[Path("large.py")] = "x = 1\n" * 100
        config = AnalysisConfig(max_code_size=100)
        server = DocScopeMCPServer(config=config, filesystem=mock_fs)
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "analyze_file",
                "arguments": {"file_path": "large.py"},
            },
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert "too large" in response["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_permission_denied_returns_error(self) -> None:
        """Verifies permission denied returns INVALID_PARAMS error."""
        from pathlib import Path
        from unittest.mock import Mock

        mock_fs = MockFilesystemAdapter()
        mock_fs.files[Path("secret.py")] = "def secret(): pass"
        mock_fs.read_text = Mock(side_effect=PermissionError("denied"))
        server = DocScopeMCPServer(filesystem=mock_fs)
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "analyze_file",
                "arguments": {"file_path": "secret.py"},
            },
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert response["error"]["code"] == JSONRPCErrorCode.INVALID_PARAMS.value
        assert "Permission denied" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_invalid_encoding_returns_error(self) -> None:
        """Verifies invalid UTF-8 file returns INVALID_PARAMS error."""
        from pathlib import Path
        from unittest.mock import Mock

        mock_fs = MockFilesystemAdapter()
        mock_fs.files[Path("binary.py")] = "..."
        mock_fs.read_text = Mock(side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, ""))
        server = DocScopeMCPServer(filesystem=mock_fs)
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "analyze_file",
                "arguments": {"file_path": "binary.py"},
            },
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert response["error"]["code"] == JSONRPCErrorCode.INVALID_PARAMS.value
        assert "UTF-8" in response["error"]["message"]
