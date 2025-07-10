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


# Extended Memory MCP Server - JSON-RPC Response Builder
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
JSON-RPC Response Builder

Handles JSON-RPC 2.0 response formatting for MCP protocol.
Separated from main server for better maintainability and testing.
"""

import json
from typing import Any, Dict, Optional


class JSONRPCResponseBuilder:
    """
    Builds JSON-RPC 2.0 compliant responses.

    Responsibilities:
    - Format success responses
    - Format error responses
    - Handle different error codes and types
    - Ensure JSON-RPC 2.0 compliance
    """

    # JSON-RPC 2.0 Error Codes
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    @staticmethod
    def build_success_response(request_id: Any, result: Any) -> Dict[str, Any]:
        """
        Build JSON-RPC 2.0 success response.

        Args:
            request_id: Request ID (can be None for notifications)
            result: Result data to include in response

        Returns:
            Dict with JSON-RPC 2.0 success response
        """
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    @staticmethod
    def build_error_response(
        request_id: Any, error_code: int, error_message: str, error_data: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Build JSON-RPC 2.0 error response.

        Args:
            request_id: Request ID (can be None)
            error_code: JSON-RPC error code
            error_message: Human readable error message
            error_data: Optional additional error data

        Returns:
            Dict with JSON-RPC 2.0 error response
        """
        error_obj = {"code": error_code, "message": error_message}

        if error_data is not None:
            error_obj["data"] = error_data

        return {"jsonrpc": "2.0", "id": request_id, "error": error_obj}

    @classmethod
    def build_parse_error_response(cls, error_data: Optional[str] = None) -> Dict[str, Any]:
        """
        Build parse error response (invalid JSON).

        Args:
            error_data: Optional error details

        Returns:
            Dict with parse error response
        """
        return cls.build_error_response(
            request_id=0,  # Use default ID for parse errors
            error_code=cls.PARSE_ERROR,
            error_message="Parse error",
            error_data=error_data,
        )

    @classmethod
    def build_internal_error_response(
        cls, request_id: Any, error_data: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build internal error response.

        Args:
            request_id: Request ID from original request
            error_data: Optional error details

        Returns:
            Dict with internal error response
        """
        return cls.build_error_response(
            request_id=request_id,
            error_code=cls.INTERNAL_ERROR,
            error_message="Internal error",
            error_data=error_data,
        )

    @classmethod
    def build_method_not_found_response(cls, request_id: Any, method_name: str) -> Dict[str, Any]:
        """
        Build method not found error response.

        Args:
            request_id: Request ID from original request
            method_name: Name of the unknown method

        Returns:
            Dict with method not found error response
        """
        return cls.build_error_response(
            request_id=request_id,
            error_code=cls.METHOD_NOT_FOUND,
            error_message="Method not found",
            error_data=f"Unknown method: {method_name}",
        )

    @staticmethod
    def format_response_json(response: Dict[str, Any]) -> str:
        """
        Format response as JSON string.

        Args:
            response: Response dictionary

        Returns:
            JSON string representation
        """
        return json.dumps(response, ensure_ascii=False)

    @classmethod
    def send_success_response(cls, request_id: Any, result: Any) -> None:
        """
        Send success response to stdout (for MCP protocol).

        Args:
            request_id: Request ID
            result: Result data
        """
        response = cls.build_success_response(request_id, result)
        json_response = cls.format_response_json(response)
        print(json_response, flush=True)

    @classmethod
    def send_error_response(
        cls, request_id: Any, error_code: int, error_message: str, error_data: Optional[Any] = None
    ) -> None:
        """
        Send error response to stdout (for MCP protocol).

        Args:
            request_id: Request ID
            error_code: JSON-RPC error code
            error_message: Error message
            error_data: Optional error data
        """
        response = cls.build_error_response(request_id, error_code, error_message, error_data)
        json_response = cls.format_response_json(response)
        print(json_response, flush=True)

    @classmethod
    def send_parse_error(cls, error_details: Optional[str] = None) -> None:
        """
        Send parse error response to stdout.

        Args:
            error_details: Optional error details
        """
        response = cls.build_parse_error_response(error_details)
        json_response = cls.format_response_json(response)
        print(json_response, flush=True)

    @classmethod
    def send_internal_error(cls, request_id: Any, error_details: Optional[str] = None) -> None:
        """
        Send internal error response to stdout.

        Args:
            request_id: Request ID
            error_details: Optional error details
        """
        response = cls.build_internal_error_response(request_id, error_details)
        json_response = cls.format_response_json(response)
        print(json_response, flush=True)


def create_json_rpc_response_builder() -> JSONRPCResponseBuilder:
    """
    Factory function to create JSON-RPC Response Builder.

    Returns:
        JSONRPCResponseBuilder instance
    """
    return JSONRPCResponseBuilder()
