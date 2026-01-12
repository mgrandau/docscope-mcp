"""Tests for MCP server."""

import pytest

from docscope_mcp.server import DocScopeMCPServer, JSONRPCErrorCode


class TestDocScopeMCPServer:
    """Test suite for DocScopeMCPServer.

    Categories:
    1. Initialization - Server creation, tool registration (1 test)
    2. Protocol Handling - Initialize, tools/list (2 tests)
    3. Tool Execution - analyze_functions tool (1 test)
    4. Error Handling - Unknown methods, tools, params (1 test)
    5. Language Support - Unsupported language error (1 test)

    Total: 6 tests.
    """

    def test_server_creation(self) -> None:
        """Verifies DocScopeMCPServer initializes with tools.

        Tests server construction and tool registration.

        Business context:
        Server must have analyze_functions tool registered at startup.

        Arrangement:
        1. No setup needed - tests constructor.

        Action:
        Instantiate DocScopeMCPServer.

        Assertion Strategy:
        Validates registration by confirming:
        - "analyze_functions" in tools dict.
        - Tool schema includes file_path parameter.

        Testing Principle:
        Validates initialization, ensuring tools registered.
        """
        server = DocScopeMCPServer()
        assert "analyze_functions" in server.tools
        # Analyzers are now created on-demand via routing, not pre-instantiated
        assert "file_path" in str(server.tools["analyze_functions"]["inputSchema"])

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
        - "analyze_functions" in tool names.

        Testing Principle:
        Validates discovery, ensuring tools enumerable.
        """
        server = DocScopeMCPServer()
        message = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        response = await server.handle_message(message)
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        tool_names = [t["name"] for t in response["result"]["tools"]]
        assert "analyze_functions" in tool_names

    @pytest.mark.asyncio
    async def test_handle_tools_call_analyze(self) -> None:
        """Verifies analyze_functions tool executes and returns content.

        Tests end-to-end tool invocation.

        Business context:
        Primary server function is analyzing code via tool call.

        Arrangement:
        1. Create server instance.
        2. Construct tools/call message with code and file_path.

        Action:
        Call handle_message with analyze_functions request.

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
                "name": "analyze_functions",
                "arguments": {"code": "def example(): pass", "file_path": "test.py"},
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
                {"name": "analyze_functions", "arguments": {}},
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

        Tests error message for unknown file extensions.

        Business context:
        Clear error messages help users identify supported languages.

        Arrangement:
        1. Create server instance.
        2. Construct request with .rs (Rust) file extension.

        Action:
        Call handle_message with unsupported file type.

        Assertion Strategy:
        Validates message by confirming:
        - Error key present in response.
        - Message mentions language detection failure.

        Testing Principle:
        Validates error messaging, ensuring helpful diagnostics.
        """
        server = DocScopeMCPServer()
        message = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "analyze_functions",
                "arguments": {
                    "code": "fn main() {}",
                    "file_path": "main.rs",  # Unknown extension
                },
            },
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert "cannot detect language" in response["error"]["message"].lower()


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
        - Output contains success message about comprehensive docstrings.

        Testing Principle:
        Validates success case, ensuring positive feedback.
        """
        server = DocScopeMCPServer()
        result = server._format_results([])
        assert "all functions have comprehensive docstrings" in result.lower()

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
                "quality_assessment": {"quality": "poor", "missing": ["docstring"]},
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
                "quality_assessment": {"quality": "poor", "missing": ["docstring"]},
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
                "name": "analyze_functions",
                "arguments": {"code": large_code, "file_path": "test.py"},
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
                "name": "analyze_functions",
                "arguments": {"code": "def broken(", "file_path": "test.py"},
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
                    "name": "analyze_functions",
                    "arguments": {"code": "def f(): pass", "file_path": "test.py"},
                },
            }
            response = await server.handle_message(message)
        assert "error" in response
        assert response["error"]["code"] == JSONRPCErrorCode.INTERNAL_ERROR.value
        assert "Unexpected failure" in response["error"]["message"]


class TestServerValidationEdgeCases:
    """Tests for server parameter validation edge cases.

    Test Categories:
        1. File Path Validation - Missing/invalid file_path (2 tests)
        2. Language Detection - Unsupported extension error (1 test)

    Total: 3 tests.
    """

    @pytest.mark.asyncio
    async def test_missing_file_path_returns_error(self) -> None:
        """Verifies missing file_path parameter returns INVALID_PARAMS error.

        Business context:
            file_path is required for language auto-detection;
            missing it must return clear validation error.

        Arrangement:
            1. Create server instance.
            2. Construct request without file_path parameter.

        Action:
            Call handle_message with missing file_path.

        Assertion Strategy:
            Verify INVALID_PARAMS error with descriptive message.

        Testing Principle:
            Parameter validation enables better error messages.
        """
        server = DocScopeMCPServer()
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "analyze_functions",
                "arguments": {"code": "def f(): pass"},
                # file_path intentionally omitted
            },
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert response["error"]["code"] == JSONRPCErrorCode.INVALID_PARAMS.value
        assert "file_path" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_invalid_file_path_type_returns_error(self) -> None:
        """Verifies non-string file_path returns INVALID_PARAMS error.

        Business context:
            file_path must be string for path operations;
            invalid types must be rejected with clear error.

        Arrangement:
            1. Create server instance.
            2. Construct request with non-string file_path.

        Action:
            Call handle_message with invalid file_path type.

        Assertion Strategy:
            Verify INVALID_PARAMS error with descriptive message.

        Testing Principle:
            Type validation prevents downstream errors.
        """
        server = DocScopeMCPServer()
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "analyze_functions",
                "arguments": {"code": "def f(): pass", "file_path": 123},
            },
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert response["error"]["code"] == JSONRPCErrorCode.INVALID_PARAMS.value
        assert "file_path" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_unsupported_extension_returns_error(self) -> None:
        """Verifies unsupported file extension returns INVALID_PARAMS error.

        Business context:
            Files with unsupported extensions cannot be analyzed;
            error should list supported extensions for guidance.

        Arrangement:
            1. Create server instance.
            2. Construct request with unsupported file extension.

        Action:
            Call handle_message with .txt file.

        Assertion Strategy:
            Verify INVALID_PARAMS error mentioning supported extensions.

        Testing Principle:
            Actionable errors help users fix issues.
        """
        server = DocScopeMCPServer()
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "analyze_functions",
                "arguments": {"code": "some text", "file_path": "readme.txt"},
            },
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert response["error"]["code"] == JSONRPCErrorCode.INVALID_PARAMS.value
        assert "Cannot detect language" in response["error"]["message"]
        # Should mention supported extensions
        assert ".py" in response["error"]["message"] or "Supported" in response["error"]["message"]
