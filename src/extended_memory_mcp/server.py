#!/usr/bin/env python3

# Extended Memory MCP Server
# Copyright (c) 2024 Sergey Smirnov
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


# Extended Memory MCP Server
# Copyright (C) 2025 Sergey Smirnov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.


"""
Memory MCP Server - Main server entry point

Lightweight HTTP server implementing Model Context Protocol (MCP) for persistent memory.
Clean architecture with separated concerns:
- HTTP server + JSON-RPC protocol handling
- MCP protocol logic (delegated to protocol handler)
- Memory operations (delegated to tools handler)
- Response formatting (delegated to response builder)
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from extended_memory_mcp.core.errors import (
    ConfigurationError,
    MemoryMCPError,
    StorageError,
    error_handler,
)

# Import storage abstraction
from extended_memory_mcp.core.storage import get_storage_provider
from extended_memory_mcp.core.storage.storage_factory import StorageFactory

# Import component factories
from extended_memory_mcp.formatters.summary_formatter import create_summary_formatter
from extended_memory_mcp.protocol.mcp_protocol_handler import create_mcp_protocol_handler
from extended_memory_mcp.responses.json_rpc_builder import JSONRPCResponseBuilder
from extended_memory_mcp.tools.memory_tools import create_memory_tools_handler


def get_timestamp() -> str:
    """Get current local time for display purposes"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")


def get_utc_timestamp() -> str:
    """Get current UTC time for logging"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


class MemoryMCPServer:
    """
    Memory MCP Server - Clean architecture implementation

    Responsibilities:
    - HTTP server initialization and configuration
    - Component orchestration (storage, tools, protocol)
    - Startup context generation for immediate Claude access
    """

    def __init__(self):
        self.base_path = Path(__file__).parent

        # Core components (initialized in initialize method)
        self.storage_provider = None
        self.summary_formatter = create_summary_formatter()
        self.protocol_handler = create_mcp_protocol_handler(
            logger=None
        )  # Logger set after _setup_logging
        self.tools_handler = None

        # Current active project (synchronized with tools handler)
        self._current_project = None

        self._setup_logging()

    @property
    def current_project(self):
        """Get current project, sync with tools handler if available"""
        if self.tools_handler:
            return self.tools_handler.current_project
        return self._current_project

    @current_project.setter
    def current_project(self, value):
        """Set current project, sync with tools handler if available"""
        self._current_project = value
        if self.tools_handler:
            self.tools_handler.current_project = value

    def _get_connection_info(self) -> Dict[str, str]:
        """Get connection information for logging"""
        try:
            return {
                "connection_string": StorageFactory.get_connection_string(),
                "provider": StorageFactory.get_provider_info().get("provider", "unknown"),
                "database_path": StorageFactory.get_provider_info()
                .get("config", {})
                .get("database_path", "N/A"),
            }
        except Exception as e:
            # Use structured error handling but continue with fallback
            error_handler.handle_error(
                e, context={"method": "_get_connection_info"}, operation="get_connection_info"
            )
            return {
                "connection_string": f"Error: {e}",
                "provider": "unknown",
                "database_path": "N/A",
            }

    def _setup_logging(self):
        """Setup logging with configurable level via LOG_LEVEL environment variable"""
        # Add custom TRACE level (lower than DEBUG)
        TRACE_LEVEL = 5
        logging.addLevelName(TRACE_LEVEL, "TRACE")

        # Setup logger with trace method
        self.logger = logging.getLogger("MemoryMCP")

        def trace(msg, *args, **kwargs):
            if self.logger.isEnabledFor(TRACE_LEVEL):
                self.logger._log(TRACE_LEVEL, msg, args, **kwargs)

        self.logger.trace = trace

        # Configure log level from environment/config
        from extended_memory_mcp.core.config import get_env_default

        log_level_str = get_env_default("LOG_LEVEL", "INFO").upper()
        level_mapping = {
            "TRACE": TRACE_LEVEL,
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }

        log_level = level_mapping.get(log_level_str, logging.INFO)
        self.logger.setLevel(log_level)

        # Setup handler for stderr (MCP debugging)
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.logger.info(f"Logging level set to: {log_level_str} ({log_level})")

        # Set logger for protocol handler
        if self.protocol_handler:
            self.protocol_handler.logger = self.logger

    async def initialize(self):
        """Initialize the server and all components"""
        self.logger.info("Initializing Memory MCP Server...")

        # Log connection info
        conn_info = self._get_connection_info()
        self.logger.info(f"Storage provider: {conn_info['provider']}")
        self.logger.info(f"Connection: {conn_info['connection_string']}")
        self.logger.info(f"Database path: {conn_info['database_path']}")

        # Initialize storage provider using StorageFactory
        try:
            self.storage_provider = await get_storage_provider()
            self.logger.info(
                f"✅ Storage provider initialized: {type(self.storage_provider).__name__}"
            )
        except Exception as e:
            # Use structured error handling for storage initialization
            storage_error = error_handler.handle_error(
                e,
                context={
                    "connection_string": conn_info.get("connection_string", "unknown"),
                    "provider": conn_info.get("provider", "unknown"),
                    "database_path": conn_info.get("database_path", "unknown"),
                },
                operation="storage_provider_initialization",
            )

            # Convert to appropriate error type
            if "connection" in str(e).lower() or "redis" in str(e).lower():
                raise StorageError(
                    f"Failed to connect to storage: {storage_error.message}",
                    context=storage_error.context,
                    original_error=e,
                )
            else:
                raise ConfigurationError(
                    f"Storage configuration error: {storage_error.message}",
                    context=storage_error.context,
                    original_error=e,
                )

        # Initialize tools handler with all dependencies
        self.tools_handler = create_memory_tools_handler(
            storage_provider=self.storage_provider,
            summary_formatter=self.summary_formatter,
            logger=self.logger,
        )

        self.logger.info("✅ Memory MCP Server initialized successfully")

    # Proxy methods for tests
    async def save_context(self, *args, **kwargs):
        return await self.tools_handler.save_context(*args, **kwargs)

    async def load_contexts(self, *args, **kwargs):
        return await self.tools_handler.load_contexts(*args, **kwargs)

    async def forget_context(self, *args, **kwargs):
        return await self.tools_handler.forget_context(*args, **kwargs)

    async def list_all_projects(self, *args, **kwargs):
        return await self.tools_handler.list_all_projects_global(*args, **kwargs)

    async def generate_startup_context(self) -> Dict[str, Any]:
        """Generate startup memory context for immediate Claude availability"""
        try:
            # Load high-importance contexts for speed (limit 5)
            contexts = await self.storage_provider.load_high_importance_contexts(limit=5)
            projects = await self.storage_provider.list_projects()

            return {
                "user_name": "User",
                "active_project": self.current_project or "memory_mcp",
                "available_projects": [p.get("id") for p in projects],
                "high_importance_contexts": [
                    {
                        "id": ctx.get("id"),
                        "content": ctx.get("content", "")[:200]
                        + ("..." if len(ctx.get("content", "")) > 200 else ""),
                        "importance": ctx.get("importance_level"),
                        "project": ctx.get("project_id"),
                    }
                    for ctx in contexts
                ],
                "total_contexts": len(contexts),
                "loaded_at": get_timestamp(),
                "message": "🎯 Memory system ready! Essential context pre-loaded for immediate access.",
                "instructions": "This is your startup memory context. You can see essential information immediately without tool calls. Use load_contexts for more detailed memory retrieval.",
            }
        except Exception as e:
            # Structured error handling for startup context generation
            memory_error = error_handler.handle_error(
                e,
                context={"method": "get_startup_context", "limit": limit},
                operation="startup_context_generation",
            )

            return {
                "user_name": "User",
                "message": "Memory system available but startup context generation failed",
                "error": memory_error.message,
                "instructions": "Use load_contexts tool to access memory",
                "error_details": {
                    "category": memory_error.category.value,
                    "severity": memory_error.severity.value,
                },
            }


async def handle_mcp_request(
    server: MemoryMCPServer, method: str, params: Dict[str, Any], request_id: Any = None
) -> Dict[str, Any]:
    """Handle MCP protocol requests - delegate to protocol handler"""
    return await server.protocol_handler.handle_request(
        method=method,
        params=params,
        tools_handler=server.tools_handler,
        server=server,
        request_id=request_id,
    )


async def main():
    """Main server loop - HTTP + JSON-RPC + MCP protocol"""
    server = MemoryMCPServer()
    await server.initialize()

    # MCP protocol: JSON responses to stdout, logging to stderr
    try:
        while True:
            # Read JSON-RPC request from stdin
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break

            line = line.strip()
            if not line:
                continue

            try:
                # Parse JSON-RPC request
                request = json.loads(line)
                method = request.get("method", "")
                params = request.get("params", {})
                request_id = request.get("id")

                # Ensure ID is not None (Claude Desktop compatibility)
                if request_id is None:
                    request_id = 0

                try:
                    # Handle MCP request
                    result = await handle_mcp_request(server, method, params, request_id)

                    # Send response for non-notifications
                    if result is not None:
                        JSONRPCResponseBuilder.send_success_response(request_id, result)

                except Exception as e:
                    # Structured error handling for MCP request processing
                    memory_error = error_handler.handle_error(
                        e,
                        context={"method": method, "params": params, "request_id": request_id},
                        operation="mcp_request_processing",
                    )

                    # Send appropriate error response based on error type
                    error_message = f"[{memory_error.category.value}] {memory_error.message}"
                    JSONRPCResponseBuilder.send_internal_error(request_id, error_message)

            except json.JSONDecodeError as e:
                JSONRPCResponseBuilder.send_parse_error(str(e))

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    asyncio.run(main())


def mcp_server_entry():
    """Entry point for pip installations - starts MCP server"""
    asyncio.run(main())
