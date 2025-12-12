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
from typing import Any

from docscope_mcp.__version__ import __version__
from docscope_mcp.analyzers.python import PythonAnalyzer
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
    programming languages. Currently supports Python with extensibility
    for additional languages.

    MCP Protocol Implementation:
    - initialize: Establish connection and negotiate capabilities
    - tools/list: Advertise available analysis tools
    - tools/call: Execute documentation analysis

    Attributes:
        tools: Registry of available tools with schemas
        analyzers: Language-specific analyzer instances
        config: Analysis configuration
        logger: Logger instance
    """

    def __init__(
        self,
        config: AnalysisConfig | None = None,
        logger_instance: logging.Logger | None = None,
    ) -> None:
        """Initialize MCP server with tool registry and analyzers.

        Creates server instance with configured analyzers and tool definitions.
        Provides dependency injection for testing and customization of
        analysis behavior in MCP tool responses.

        Args:
            config: Analysis configuration. Defaults to DEFAULT_CONFIG.
            logger_instance: Logger instance. Defaults to module logger.

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

        # Initialize analyzers
        self.analyzers = {
            "python": PythonAnalyzer(config=self.config, logger=self.logger),
        }

        # Tool registry
        self.tools = {
            "analyze_functions": {
                "name": "analyze_functions",
                "description": (
                    "Analyze source code functions and identify those needing "
                    "documentation improvement based on quality standards"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Source code containing functions to analyze",
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Optional file path for context",
                            "default": "",
                        },
                        "language": {
                            "type": "string",
                            "description": "Programming language (default: python)",
                            "default": "python",
                            "enum": list(self.analyzers.keys()),
                        },
                    },
                    "required": ["code"],
                },
            },
        }

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
            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "result": {
                    "protocolVersion": MCP_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "docscope-mcp-server",
                        "version": __version__,
                    },
                },
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "result": {"tools": list(self.tools.values())},
            }

        elif method == "tools/call":
            params = message.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name == "analyze_functions":
                return await self._execute_analyze_functions(arguments, message_id)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "error": {
                        "code": JSONRPCErrorCode.METHOD_NOT_FOUND.value,
                        "message": f"Unknown tool: {tool_name}",
                    },
                }

        else:
            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "error": {
                    "code": JSONRPCErrorCode.METHOD_NOT_FOUND.value,
                    "message": f"Unknown method: {method}",
                },
            }

    async def _execute_analyze_functions(
        self, arguments: dict[str, Any], message_id: Any
    ) -> dict[str, Any]:
        """Execute analyze_functions MCP tool.

        Validates inputs, runs language analyzer, and formats results.
        Implements the core MCP tool that provides documentation analysis.

        Args:
            arguments: Tool arguments (code, file_path, language).
            message_id: Request ID for response correlation.

        Returns:
            JSON-RPC 2.0 response with analysis results or error.

        Raises:
            No exceptions - errors returned in JSON-RPC error format.

        Example:
            >>> response = await server._execute_analyze_functions(
            ...     {'code': 'def f(): pass'}, 1
            ... )
            >>> 'result' in response
            True
        """
        try:
            code = arguments.get("code", "")
            file_path = arguments.get("file_path", "")
            language = arguments.get("language", "python")

            # Validate code parameter
            if not code or not isinstance(code, str):
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "error": {
                        "code": JSONRPCErrorCode.INVALID_PARAMS.value,
                        "message": "'code' is required and must be a string",
                    },
                }

            # Validate code size
            max_size = self.config.max_code_size
            if len(code) > max_size:
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "error": {
                        "code": JSONRPCErrorCode.INVALID_PARAMS.value,
                        "message": f"Code too large (max {max_size // 1024}KB)",
                    },
                }

            # Get analyzer for language
            analyzer = self.analyzers.get(language)
            if not analyzer:
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "error": {
                        "code": JSONRPCErrorCode.INVALID_PARAMS.value,
                        "message": f"Unsupported language: {language}",
                    },
                }

            # Execute analysis
            results = analyzer.analyze(code, file_path)

            # Handle errors
            if results and "error" in results[0]:
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "error": {
                        "code": JSONRPCErrorCode.INTERNAL_ERROR.value,
                        "message": f"Analysis failed: {results[0]['error']}",
                    },
                }

            # Format results
            result_text = self._format_results(results)

            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "result": {"content": [{"type": "text", "text": result_text}]},
            }

        except Exception as e:
            self.logger.exception(f"Error in analyze_functions: {e}")
            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "error": {
                    "code": JSONRPCErrorCode.INTERNAL_ERROR.value,
                    "message": f"Internal error: {e!s}",
                },
            }

    def _format_results(self, results: list[dict[str, Any]]) -> str:
        """Format analysis results into human-readable report.

        Transforms raw analysis dicts into formatted text output for
        MCP tool response. Provides prioritized list with quality info
        and actionable improvement guidance.

        Args:
            results: List of function analysis dicts from analyzer.

        Returns:
            Formatted report string with prioritized functions.
            Returns success message if results list is empty.

        Raises:
            KeyError: If result dict missing expected fields (logged).

        Example:
            >>> server = DocScopeMCPServer()
            >>> text = server._format_results([])
            >>> 'Great!' in text
            True
            >>> text = server._format_results([{'function_name': 'foo', ...}])
            >>> 'foo()' in text
            True
        """
        if not results:
            return (
                "Great! All functions have comprehensive docstrings "
                "that meet high quality standards."
            )

        lines = ["Functions needing better docstrings (prioritized):"]
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
                missing = ", ".join(
                    func["quality_assessment"]["missing"][
                        : self.config.max_missing_elements_display
                    ]
                )

                lines.append(f"{i}. {name}() [Line {line}]")
                lines.append(f"   Quality: {quality.upper()} | Priority: {priority}")
                lines.append(f"   Missing: {missing}")

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
