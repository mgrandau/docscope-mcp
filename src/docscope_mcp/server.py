"""
DocScope MCP Server.

JSON-RPC 2.0 MCP server for documentation quality analysis.
Supports multiple programming languages via pluggable analyzers.

Architecture:
    Message Handler → Tool Registry → Language Analyzer → Results

Deployment:
    - VS Code MCP extension
    - Claude Desktop
    - Any MCP-compatible client
"""

import asyncio
import json
import logging
import sys
from enum import Enum
from pathlib import Path
from typing import Any

from docscope_mcp.__version__ import __version__
from docscope_mcp.analyzers import (
    SUPPORTED_LANGUAGES,
    analyze_code,
    detect_language,
    get_supported_extensions,
)
from docscope_mcp.filesystem import DefaultFilesystemAdapter, FilesystemAdapter
from docscope_mcp.models import DEFAULT_CONFIG, AnalysisConfig

# MCP Protocol version
MCP_VERSION = "2024-11-05"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


class JSONRPCErrorCode(Enum):
    """Standard JSON-RPC 2.0 error codes.

    Defines error codes per JSON-RPC 2.0 specification for MCP protocol
    error responses. Used in error dicts returned by handle_message.

    Attributes:
        PARSE_ERROR: Invalid JSON received (-32700).
        INVALID_REQUEST: JSON is not valid request object (-32600).
        METHOD_NOT_FOUND: Method does not exist (-32601).
        INVALID_PARAMS: Invalid method parameters (-32602).
        INTERNAL_ERROR: Internal server error (-32603).
    """

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


class DocScopeMCPServer:
    """MCP server for documentation quality analysis.

    Provides tools for analyzing documentation quality across multiple
    programming languages. Automatically detects language from file
    extension. Supports Python, C#, VB.NET, VB6, and C++.

    MCP Protocol Implementation:
    - initialize: Establish connection and negotiate capabilities
    - tools/list: Advertise available analysis tools
    - tools/call: Execute documentation analysis

    Attributes:
        tools: Registry of available tools with schemas
        config: Analysis configuration
        logger: Logger instance
    """

    def __init__(
        self,
        config: AnalysisConfig | None = None,
        logger_instance: logging.Logger | None = None,
        filesystem: FilesystemAdapter | None = None,
    ) -> None:
        """Initialize MCP server with tool registry.

        Creates server instance with configured tool definitions.
        Analyzers are created on-demand based on language.

        Args:
            config: Analysis configuration. Defaults to DEFAULT_CONFIG.
            logger_instance: Logger instance. Defaults to module logger.
            filesystem: Filesystem adapter for file operations.
                        Defaults to DefaultFilesystemAdapter.

        Returns:
            None - initializes instance attributes.

        Raises:
            No exceptions raised.

        Example:
            >>> server = DocScopeMCPServer()
            >>> server = DocScopeMCPServer(config=custom_config)
        """
        self.config = config or DEFAULT_CONFIG
        self.logger = logger_instance or logger
        self.fs: FilesystemAdapter = filesystem or DefaultFilesystemAdapter()

        # Build supported extensions description
        ext_list = ", ".join(get_supported_extensions())
        lang_list = ", ".join(SUPPORTED_LANGUAGES)

        # Tool registry
        self.tools = {
            "analyze_code": {
                "name": "analyze_code",
                "description": (
                    "Analyze source code string for functions needing "
                    "documentation improvement. Use when you have code content "
                    "in memory and know the language."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Source code containing functions to analyze",
                        },
                        "language": {
                            "type": "string",
                            "description": f"Programming language. One of: {lang_list}",
                            "enum": SUPPORTED_LANGUAGES,
                        },
                    },
                    "required": ["code", "language"],
                },
            },
            "analyze_file": {
                "name": "analyze_file",
                "description": (
                    "Analyze a source file for functions needing documentation "
                    "improvement. Reads file from disk and auto-detects language "
                    f"from extension. Supported: {ext_list}"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": (
                                "Path to source file. Language detected from extension."
                            ),
                        },
                    },
                    "required": ["file_path"],
                },
            },
        }

    # ==================== JSON-RPC RESPONSE BUILDERS ====================

    def _success_response(self, message_id: Any, result: Any) -> dict[str, Any]:
        """Build JSON-RPC 2.0 success response.

        Creates standardized success response dict for MCP protocol.
        Centralizes response format to ensure consistency.

        Args:
            message_id: Request ID for response correlation.
            result: Response payload (any JSON-serializable value).

        Returns:
            JSON-RPC 2.0 response dict with jsonrpc, id, and result.

        Raises:
            No exceptions raised.

        Example:
            >>> server._success_response(1, {"tools": []})
            {'jsonrpc': '2.0', 'id': 1, 'result': {'tools': []}}
        """
        return {"jsonrpc": "2.0", "id": message_id, "result": result}

    def _error_response(
        self, message_id: Any, code: JSONRPCErrorCode, message: str
    ) -> dict[str, Any]:
        """Build JSON-RPC 2.0 error response.

        Creates standardized error response dict for MCP protocol.
        Uses JSONRPCErrorCode enum for standard error codes.

        Args:
            message_id: Request ID for response correlation.
            code: JSON-RPC error code from JSONRPCErrorCode enum.
            message: Human-readable error description.

        Returns:
            JSON-RPC 2.0 error response dict.

        Raises:
            No exceptions raised.

        Example:
            >>> server._error_response(1, JSONRPCErrorCode.INVALID_PARAMS, "Missing 'code'")
            {'jsonrpc': '2.0', 'id': 1, 'error': {'code': -32602, 'message': "Missing 'code'"}}
        """
        return {
            "jsonrpc": "2.0",
            "id": message_id,
            "error": {"code": code.value, "message": message},
        }

    def _tool_result_response(self, message_id: Any, text: str) -> dict[str, Any]:
        """Build JSON-RPC 2.0 tool result response with text content.

        Creates standardized tool result for MCP tools/call responses.
        Wraps text in content array format expected by MCP clients.

        Args:
            message_id: Request ID for response correlation.
            text: Text content to return from tool execution.

        Returns:
            JSON-RPC 2.0 response with content array containing text.

        Raises:
            No exceptions raised.

        Example:
            >>> server._tool_result_response(1, "Analysis complete")
            {'jsonrpc': '2.0', 'id': 1, 'result': {'content': [{'type': 'text', 'text': '...'}]}}
        """
        return self._success_response(message_id, {"content": [{"type": "text", "text": text}]})

    # ==================== MESSAGE HANDLING ====================

    async def handle_message(self, message: dict[str, Any]) -> dict[str, Any]:
        """Route incoming JSON-RPC 2.0 messages to appropriate handlers.

        Central dispatcher implementing MCP protocol message routing.
        Handles initialize, tools/list, and tools/call methods per
        MCP specification.

        Args:
            message: Incoming JSON-RPC 2.0 message dict with
                     method, id, and optional params.

        Returns:
            JSON-RPC 2.0 compliant response dict with result or error.

        Raises:
            No exceptions - errors returned in JSON-RPC error format.

        Example:
            >>> response = await server.handle_message({
            ...     'jsonrpc': '2.0',
            ...     'id': 1,
            ...     'method': 'tools/list'
            ... })
            >>> 'result' in response
            True
        """
        method = message.get("method")
        message_id = message.get("id")

        if method == "initialize":
            return self._success_response(
                message_id,
                {
                    "protocolVersion": MCP_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "docscope-mcp-server",
                        "version": __version__,
                    },
                },
            )

        elif method == "tools/list":
            return self._success_response(message_id, {"tools": list(self.tools.values())})

        elif method == "tools/call":
            params = message.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name == "analyze_code":
                return await self._execute_analyze_code(arguments, message_id)
            elif tool_name == "analyze_file":
                return await self._execute_analyze_file(arguments, message_id)
            else:
                return self._error_response(
                    message_id,
                    JSONRPCErrorCode.METHOD_NOT_FOUND,
                    f"Unknown tool: {tool_name}",
                )

        else:
            return self._error_response(
                message_id,
                JSONRPCErrorCode.METHOD_NOT_FOUND,
                f"Unknown method: {method}",
            )

    async def _execute_analyze_code(
        self, arguments: dict[str, Any], message_id: Any
    ) -> dict[str, Any]:
        """Execute analyze_code MCP tool.

        Validates inputs and runs analyzer on provided code string.
        Language must be explicitly specified.

        Args:
            arguments: Tool arguments (code, language).
            message_id: Request ID for response correlation.

        Returns:
            JSON-RPC 2.0 response with analysis results or error.

        Raises:
            No exceptions - errors returned in JSON-RPC error format.

        Example:
            >>> response = await server._execute_analyze_code(
            ...     {'code': 'def f(): pass', 'language': 'python'}, 1
            ... )
            >>> 'result' in response
            True
        """
        try:
            code = arguments.get("code", "")
            language = arguments.get("language", "")

            # Validate code parameter
            if not code or not isinstance(code, str):
                return self._error_response(
                    message_id,
                    JSONRPCErrorCode.INVALID_PARAMS,
                    "'code' is required and must be a string",
                )

            # Validate language parameter
            if not language or not isinstance(language, str):
                return self._error_response(
                    message_id,
                    JSONRPCErrorCode.INVALID_PARAMS,
                    "'language' is required and must be a string",
                )

            if language not in SUPPORTED_LANGUAGES:
                lang_list = ", ".join(SUPPORTED_LANGUAGES)
                return self._error_response(
                    message_id,
                    JSONRPCErrorCode.INVALID_PARAMS,
                    f"Unsupported language: {language}. Use: {lang_list}",
                )

            # Validate code size
            max_size = self.config.max_code_size
            if len(code) > max_size:
                return self._error_response(
                    message_id,
                    JSONRPCErrorCode.INVALID_PARAMS,
                    f"Code too large (max {max_size // 1024}KB)",
                )

            # Execute analysis
            results = analyze_code(code, language, file_path="", config=self.config)

            # Handle errors
            if results and "error" in results[0]:
                return self._error_response(
                    message_id,
                    JSONRPCErrorCode.INTERNAL_ERROR,
                    f"Analysis failed: {results[0]['error']}",
                )

            # Format results
            result_text = self._format_results(results)

            return self._tool_result_response(message_id, result_text)

        except Exception as e:
            self.logger.exception(f"Error in analyze_code: {e}")
            return self._error_response(
                message_id,
                JSONRPCErrorCode.INTERNAL_ERROR,
                f"Internal error: {e!s}",
            )

    async def _execute_analyze_file(
        self, arguments: dict[str, Any], message_id: Any
    ) -> dict[str, Any]:
        """Execute analyze_file MCP tool.

        Reads file from disk, detects language from extension,
        and runs appropriate analyzer.

        Args:
            arguments: Tool arguments (file_path).
            message_id: Request ID for response correlation.

        Returns:
            JSON-RPC 2.0 response with analysis results or error.

        Raises:
            No exceptions - errors returned in JSON-RPC error format.

        Example:
            >>> response = await server._execute_analyze_file(
            ...     {'file_path': 'src/main.py'}, 1
            ... )
            >>> 'result' in response
            True
        """
        try:
            file_path = arguments.get("file_path", "")

            # Validate file_path parameter
            if not file_path or not isinstance(file_path, str):
                return self._error_response(
                    message_id,
                    JSONRPCErrorCode.INVALID_PARAMS,
                    "'file_path' is required and must be a string",
                )

            # Detect language from extension
            language = detect_language(file_path)
            if not language:
                ext_list = ", ".join(get_supported_extensions())
                return self._error_response(
                    message_id,
                    JSONRPCErrorCode.INVALID_PARAMS,
                    f"Cannot detect language from '{file_path}'. "
                    f"Supported extensions: {ext_list}",
                )

            # Read file
            path = Path(file_path)
            if not self.fs.exists(path):
                return self._error_response(
                    message_id,
                    JSONRPCErrorCode.INVALID_PARAMS,
                    f"File not found: {file_path}",
                )

            try:
                code = self.fs.read_text(path)
            except PermissionError:
                return self._error_response(
                    message_id,
                    JSONRPCErrorCode.INVALID_PARAMS,
                    f"Permission denied: {file_path}",
                )
            except UnicodeDecodeError:
                return self._error_response(
                    message_id,
                    JSONRPCErrorCode.INVALID_PARAMS,
                    f"File is not valid UTF-8: {file_path}",
                )

            # Validate code size
            max_size = self.config.max_code_size
            if len(code) > max_size:
                return self._error_response(
                    message_id,
                    JSONRPCErrorCode.INVALID_PARAMS,
                    f"File too large (max {max_size // 1024}KB)",
                )

            # Execute analysis
            results = analyze_code(code, language, file_path, config=self.config)

            # Handle errors
            if results and "error" in results[0]:
                return self._error_response(
                    message_id,
                    JSONRPCErrorCode.INTERNAL_ERROR,
                    f"Analysis failed: {results[0]['error']}",
                )

            # Format results
            result_text = self._format_results(results)

            return self._tool_result_response(message_id, result_text)

        except Exception as e:
            self.logger.exception(f"Error in analyze_file: {e}")
            return self._error_response(
                message_id,
                JSONRPCErrorCode.INTERNAL_ERROR,
                f"Internal error: {e!s}",
            )

    def _format_results(self, results: list[dict[str, Any]]) -> str:
        """Format analysis results into human-readable report.

        Transforms raw analysis dicts into formatted text output for
        MCP tool response. Shows all functions with their quality levels
        and provides actionable improvement guidance for those needing work.

        Args:
            results: List of function analysis dicts from analyzer.

        Returns:
            Formatted report string with all functions and quality levels.
            Returns message if no functions found.

        Raises:
            KeyError: If result dict missing expected fields (logged).

        Example:
            >>> server = DocScopeMCPServer()
            >>> text = server._format_results([])
            >>> 'No functions found' in text
            True
            >>> text = server._format_results([{'function_name': 'foo', ...}])
            >>> 'foo()' in text
            True
        """
        if not results:
            return "No functions found in the analyzed code."

        lines = ["Functions analyzed:"]
        lines.append("=" * 60)
        lines.append("NOTE: Quality assessment analyzes FULL docstrings.")
        lines.append("")

        max_display = self.config.max_results_display
        for i, func in enumerate(results[:max_display], 1):
            try:
                name = func["function_name"]
                line = func["line_number"]
                quality = func["quality_assessment"]["quality"]
                priority = func["priority"]
                needs_improvement = func["quality_assessment"]["needs_improvement"]

                lines.append(f"{i}. {name}() [Line {line}]")
                lines.append(f"   Quality: {quality.upper()} | Priority: {priority}")

                if needs_improvement:
                    missing = ", ".join(
                        func["quality_assessment"]["missing"][
                            : self.config.max_missing_elements_display
                        ]
                    )
                    lines.append(f"   Missing: {missing}")
                else:
                    lines.append("   Complete: All required elements present")

                if func.get("current_docstring"):
                    preview = (
                        func["current_docstring"][: self.config.docstring_preview_length]
                        .replace("\n", " ")
                        .strip()
                    )
                    suffix = (
                        "..."
                        if len(func["current_docstring"]) > self.config.docstring_preview_length
                        else ""
                    )
                    lines.append(f"   Current: {preview}{suffix}")
                else:
                    lines.append("   Current: No docstring")
                lines.append("")

            except KeyError as e:
                self.logger.warning(f"Malformed result at {i}: missing {e}")
                continue

        if len(results) > max_display:
            remaining = len(results) - max_display
            lines.append(f"... and {remaining} more functions")

        return "\n".join(lines)

    async def run(self) -> None:  # pragma: no cover
        """Execute MCP server stdio event loop.

        Main server loop implementing MCP stdio transport. Reads JSON-RPC
        messages from stdin, dispatches to handle_message, and writes
        responses to stdout. Runs until EOF or unrecoverable error.

        This is the entry point called by the MCP client (VS Code) after
        spawning the server process. Provides the documentation analysis
        capability to AI assistants.

        Args:
            None - uses stdin/stdout for communication.

        Returns:
            None - runs until terminated.

        Raises:
            No exceptions - errors logged and loop continues or exits.

        Example:
            >>> server = DocScopeMCPServer()
            >>> await server.run()  # Blocks until EOF
        """
        self.logger.info("Starting DocScope MCP Server...")

        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)

                if not line:
                    self.logger.info("EOF detected, shutting down")
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    message = json.loads(line)
                    response = await self.handle_message(message)
                    print(json.dumps(response), flush=True)

                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": JSONRPCErrorCode.PARSE_ERROR.value,
                            "message": "Parse error",
                        },
                    }
                    print(json.dumps(error_response), flush=True)

            except Exception as e:
                self.logger.error(f"Error processing message: {e}")
                break


async def main() -> None:  # pragma: no cover
    """Entry point for MCP server process.

    Creates DocScopeMCPServer instance and runs the stdio event loop.
    Called when module is executed directly or via entry point.

    Args:
        None - configures server with defaults.

    Returns:
        None - runs until EOF on stdin.

    Raises:
        No exceptions - errors handled internally.

    Example:
        >>> # From command line:
        >>> # python -m docscope_mcp.server
    """
    server = DocScopeMCPServer()
    await server.run()


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())
