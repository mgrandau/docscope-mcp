"""Tests for MCP server."""

import pytest

from docscope_mcp.server import DocScopeMCPServer, JSONRPCErrorCode


class TestDocScopeMCPServer:
    """Tests for DocScopeMCPServer."""

    def test_server_creation(self) -> None:
        """Test server can be created."""
        server = DocScopeMCPServer()
        assert "analyze_functions" in server.tools
        assert "python" in server.analyzers

    @pytest.mark.asyncio
    async def test_handle_initialize(self) -> None:
        """Test initialize method handling."""
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
        """Test tools/list method handling."""
        server = DocScopeMCPServer()
        message = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
        }
        response = await server.handle_message(message)
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        assert "result" in response
        assert "tools" in response["result"]
        tool_names = [t["name"] for t in response["result"]["tools"]]
        assert "analyze_functions" in tool_names

    @pytest.mark.asyncio
    async def test_handle_tools_call_analyze(self) -> None:
        """Test tools/call with analyze_functions."""
        server = DocScopeMCPServer()
        message = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "analyze_functions",
                "arguments": {
                    "code": "def example(): pass",
                    "file_path": "test.py",
                },
            },
        }
        response = await server.handle_message(message)
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 3
        assert "result" in response
        assert "content" in response["result"]

    @pytest.mark.asyncio
    async def test_handle_unknown_method(self) -> None:
        """Test unknown method handling."""
        server = DocScopeMCPServer()
        message = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "unknown_method",
        }
        response = await server.handle_message(message)
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 4
        assert "error" in response
        assert response["error"]["code"] == JSONRPCErrorCode.METHOD_NOT_FOUND.value

    @pytest.mark.asyncio
    async def test_handle_unknown_tool(self) -> None:
        """Test unknown tool handling."""
        server = DocScopeMCPServer()
        message = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "unknown_tool",
                "arguments": {},
            },
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert response["error"]["code"] == JSONRPCErrorCode.METHOD_NOT_FOUND.value

    @pytest.mark.asyncio
    async def test_handle_missing_code_param(self) -> None:
        """Test missing code parameter handling."""
        server = DocScopeMCPServer()
        message = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "analyze_functions",
                "arguments": {},
            },
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert response["error"]["code"] == JSONRPCErrorCode.INVALID_PARAMS.value

    @pytest.mark.asyncio
    async def test_handle_unsupported_language(self) -> None:
        """Test unsupported language handling."""
        server = DocScopeMCPServer()
        message = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "analyze_functions",
                "arguments": {
                    "code": "fn main() {}",
                    "language": "rust",
                },
            },
        }
        response = await server.handle_message(message)
        assert "error" in response
        assert "unsupported language" in response["error"]["message"].lower()


class TestResultFormatting:
    """Tests for result formatting."""

    def test_format_empty_results(self) -> None:
        """Test formatting empty results."""
        server = DocScopeMCPServer()
        result = server._format_results([])
        assert "all functions have comprehensive docstrings" in result.lower()

    def test_format_results_with_functions(self) -> None:
        """Test formatting results with functions."""
        server = DocScopeMCPServer()
        results = [
            {
                "function_name": "test_func",
                "line_number": 10,
                "priority": 8,
                "current_docstring": "",
                "quality_assessment": {
                    "quality": "poor",
                    "missing": ["docstring"],
                },
            },
        ]
        formatted = server._format_results(results)
        assert "test_func" in formatted
        assert "Line 10" in formatted
        assert "POOR" in formatted
