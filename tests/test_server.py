"""Tests for MCP server."""

import pytest

from docscope_mcp.server import DocScopeMCPServer, JSONRPCErrorCode


class TestDocScopeMCPServer:
    """Tests for DocScopeMCPServer."""

    def test_server_creation(self) -> None:
        """Verify DocScopeMCPServer initializes with tools and analyzers."""
        server = DocScopeMCPServer()
        assert "analyze_functions" in server.tools
        assert "python" in server.analyzers

    @pytest.mark.asyncio
    async def test_handle_initialize(self) -> None:
        """Verify initialize method returns correct protocol version."""
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
        """Verify tools/list returns registered tools with metadata."""
        server = DocScopeMCPServer()
        message = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        response = await server.handle_message(message)
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        tool_names = [t["name"] for t in response["result"]["tools"]]
        assert "analyze_functions" in tool_names

    @pytest.mark.asyncio
    async def test_handle_tools_call_analyze(self) -> None:
        """Verify analyze_functions tool executes and returns content."""
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
        """Verify error handling for various invalid requests."""
        server = DocScopeMCPServer()
        message = {"jsonrpc": "2.0", "id": 1, "method": method}
        if params:
            message["params"] = params
        response = await server.handle_message(message)
        assert "error" in response
        assert response["error"]["code"] == expected_error_code.value

    @pytest.mark.asyncio
    async def test_handle_unsupported_language(self) -> None:
        """Verify unsupported language returns descriptive error."""
        server = DocScopeMCPServer()
        message = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "analyze_functions",
                "arguments": {"code": "fn main() {}", "language": "rust"},
            },
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert "unsupported language" in response["error"]["message"].lower()


class TestResultFormatting:
    """Tests for result formatting."""

    def test_format_empty_results(self) -> None:
        """Verify empty results produce success message."""
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
        """Verify result formatting for various docstring scenarios."""
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
        """Verify results are truncated at max_results_display."""
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
        """Verify malformed results are skipped gracefully."""
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
    """Tests for analysis edge cases in server."""

    @pytest.mark.asyncio
    async def test_code_too_large_returns_error(self) -> None:
        """Verify code exceeding max size returns error."""
        from docscope_mcp.models import AnalysisConfig

        config = AnalysisConfig(max_code_size=100)
        server = DocScopeMCPServer(config=config)
        large_code = "x = 1\n" * 50

        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "analyze_functions", "arguments": {"code": large_code}},
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert "too large" in response["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_analyzer_error_returns_internal_error(self) -> None:
        """Verify analyzer errors are returned as INTERNAL_ERROR."""
        server = DocScopeMCPServer()
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "analyze_functions", "arguments": {"code": "def broken("}},
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert response["error"]["code"] == JSONRPCErrorCode.INTERNAL_ERROR.value

    @pytest.mark.asyncio
    async def test_unexpected_exception_returns_internal_error(self) -> None:
        """Verify unexpected exceptions are caught and returned as INTERNAL_ERROR."""
        from unittest.mock import patch

        server = DocScopeMCPServer()
        with patch.object(
            server.analyzers["python"], "analyze", side_effect=RuntimeError("Unexpected failure")
        ):
            message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "analyze_functions", "arguments": {"code": "def f(): pass"}},
            }
            response = await server.handle_message(message)
        assert "error" in response
        assert response["error"]["code"] == JSONRPCErrorCode.INTERNAL_ERROR.value
        assert "Unexpected failure" in response["error"]["message"]
