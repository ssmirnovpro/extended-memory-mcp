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


# Extended Memory MCP Server - Protocol Handler
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
MCP Protocol Handler

Handles Model Context Protocol (MCP) request/response logic.
Separated from main server for better maintainability and testing.
"""

import json
import logging
from typing import Any, Dict, Optional

from extended_memory_mcp.config.tools.descriptions_loader import create_tool_descriptions_loader


def log_request(logger: logging.Logger, method: str, request_id: Any = None):
    """Log incoming MCP request with UTC timestamp (TRACE level)"""
    from datetime import datetime, timezone

    if hasattr(logger, "trace"):
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        logger.trace(f"[{timestamp}] 📥 REQUEST: {method} (ID: {request_id})")


def log_response(logger: logging.Logger, method: str, success: bool, request_id: Any = None):
    """Log MCP response with UTC timestamp (TRACE level)"""
    from datetime import datetime, timezone

    if hasattr(logger, "trace"):
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        status = "✅ SUCCESS" if success else "❌ ERROR"
        logger.trace(f"[{timestamp}] 📤 RESPONSE: {method} {status} (ID: {request_id})")


class MCPProtocolHandler:
    """
    Handles MCP (Model Context Protocol) requests and responses.

    Responsibilities:
    - Parse and route MCP methods
    - Generate protocol-compliant responses
    - Handle errors in MCP format
    - Manage tool schemas and capabilities
    """

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.descriptions_loader = create_tool_descriptions_loader()

    async def handle_request(
        self, method: str, params: Dict[str, Any], tools_handler, server, request_id: Any = None
    ) -> Dict[str, Any]:
        """
        Handle MCP protocol requests.

        Args:
            method: MCP method name
            params: Request parameters
            tools_handler: Memory tools handler for tool execution
            server: Main server instance for startup context
            request_id: Request ID for logging

        Returns:
            Dict with response data or None for notifications
        """
        # Log incoming request
        log_request(self.logger, method, request_id)

        try:
            result = None

            if method == "initialize":
                result = self._handle_initialize()

            elif method == "notifications/initialized":
                result = None  # No response needed for notifications

            elif method == "prompts/get":
                result = self._handle_prompts_get(params)

            elif method == "resources/read":
                result = await self._handle_resources_read(params, server)

            elif method == "resources/list":
                result = self._handle_resources_list()

            elif method == "prompts/list":
                result = self._handle_prompts_list()

            elif method == "tools/list":
                result = self._handle_tools_list()

            elif method == "tools/call":
                result = await self._handle_tools_call(params, tools_handler)

            else:
                raise Exception(f"Unknown method: {method}")

            # Log successful response
            log_response(self.logger, method, True, request_id)
            return result

        except Exception as e:
            # Log error response
            log_response(self.logger, method, False, request_id)
            raise

    def _handle_initialize(self) -> Dict[str, Any]:
        """Handle MCP initialize request"""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {"subscribe": True, "listChanged": True},
                "prompts": {},
            },
            "serverInfo": {"name": "memory-server", "version": "1.0.0"},
            "instructions": "You have access to a persistent memory system that remembers information between conversations. ALWAYS check your memory at the start of conversations by calling load_contexts to see what you remember about the user. When users ask questions that might be answered by your memory (like 'What is my name?', 'What am I working on?', etc.), automatically use load_contexts first. Save important information using save_context.",
        }

    def _handle_prompts_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/get request"""
        prompt_name = params.get("name")
        if prompt_name == "memory_instructions":
            return {
                "description": "Instructions for using persistent memory system",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": "You have access to a PERSISTENT MEMORY SYSTEM. Use load_contexts() when starting conversations or when users ask about themselves, previous work, or personal information. Save important information with save_context().",
                        },
                    }
                ],
            }
        else:
            raise Exception(f"Unknown prompt: {prompt_name}")

    async def _handle_resources_read(self, params: Dict[str, Any], server) -> Dict[str, Any]:
        """Handle resources/read request"""
        uri = params.get("uri")
        if uri == "memory://startup-context":
            startup_context = await server.generate_startup_context()
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(startup_context, indent=2, ensure_ascii=False),
                    }
                ]
            }
        else:
            raise Exception(f"Unknown resource URI: {uri}")

    def _handle_resources_list(self) -> Dict[str, Any]:
        """Handle resources/list request"""
        return {
            "resources": [
                {
                    "uri": "memory://startup-context",
                    "name": "🧠 Startup Memory Context",
                    "description": "Essential context from previous conversations - immediately available",
                    "mimeType": "application/json",
                }
            ]
        }

    def _handle_prompts_list(self) -> Dict[str, Any]:
        """Handle prompts/list request"""
        return {
            "prompts": [
                {
                    "name": "memory_instructions",
                    "description": "Instructions for using the persistent memory system",
                    "arguments": [],
                }
            ]
        }

    def _handle_tools_list(self) -> Dict[str, Any]:
        """Handle tools/list request - returns available memory tools"""
        tools = []

        # List of all available tools
        tool_names = [
            "save_context",
            "load_contexts",
            "forget_context",
            "list_all_projects",
            "get_popular_tags",
        ]

        # Build tools list using descriptions loader
        for tool_name in tool_names:
            description = self.descriptions_loader.load_tool_description(tool_name)
            input_schema = self.descriptions_loader.get_tool_schema(tool_name)

            tools.append(
                {"name": tool_name, "description": description, "inputSchema": input_schema}
            )

        return {"tools": tools}

    async def _handle_tools_call(self, params: Dict[str, Any], tools_handler) -> Dict[str, Any]:
        """Handle tools/call request - delegate to tools handler"""
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})

        # Delegate to tools handler
        return await tools_handler.execute_tool(tool_name, tool_args)


def create_mcp_protocol_handler(logger: logging.Logger) -> MCPProtocolHandler:
    """
    Factory function to create MCP Protocol Handler.

    Args:
        logger: Logger instance for protocol operations

    Returns:
        Configured MCPProtocolHandler instance
    """
    return MCPProtocolHandler(logger)
