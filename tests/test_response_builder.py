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
Tests for JSON-RPC Response Builder

Tests the JSON-RPC 2.0 response formatting logic.
"""

import json
import pytest
from io import StringIO
from unittest.mock import patch, MagicMock

from extended_memory_mcp.responses.json_rpc_builder import JSONRPCResponseBuilder, create_json_rpc_response_builder


class TestJSONRPCResponseBuilder:
    """Test suite for JSONRPCResponseBuilder"""
    
    def test_build_success_response(self):
        """Test building success response"""
        result = {"message": "Success", "data": [1, 2, 3]}
        response = JSONRPCResponseBuilder.build_success_response(
            request_id="test-123",
            result=result
        )
        
        assert response == {
            "jsonrpc": "2.0",
            "id": "test-123",
            "result": result
        }
    
    def test_build_success_response_none_id(self):
        """Test success response with None ID (notifications)"""
        result = {"status": "ok"}
        response = JSONRPCResponseBuilder.build_success_response(
            request_id=None,
            result=result
        )
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] is None
        assert response["result"] == result
    
    def test_build_error_response_basic(self):
        """Test building basic error response"""
        response = JSONRPCResponseBuilder.build_error_response(
            request_id="error-123",
            error_code=-32603,
            error_message="Internal error"
        )
        
        expected = {
            "jsonrpc": "2.0",
            "id": "error-123",
            "error": {
                "code": -32603,
                "message": "Internal error"
            }
        }
        assert response == expected
    
    def test_build_error_response_with_data(self):
        """Test error response with additional data"""
        response = JSONRPCResponseBuilder.build_error_response(
            request_id=42,
            error_code=-32600,
            error_message="Invalid Request",
            error_data="Missing required field 'method'"
        )
        
        assert response["error"]["data"] == "Missing required field 'method'"
        assert response["error"]["code"] == -32600
        assert response["error"]["message"] == "Invalid Request"
    
    def test_build_parse_error_response(self):
        """Test parse error response"""
        response = JSONRPCResponseBuilder.build_parse_error_response(
            error_data="Invalid JSON at character 15"
        )
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 0  # Default ID for parse errors
        assert response["error"]["code"] == JSONRPCResponseBuilder.PARSE_ERROR
        assert response["error"]["message"] == "Parse error"
        assert response["error"]["data"] == "Invalid JSON at character 15"
    
    def test_build_internal_error_response(self):
        """Test internal error response"""
        response = JSONRPCResponseBuilder.build_internal_error_response(
            request_id="internal-test",
            error_data="Database connection failed"
        )
        
        assert response["id"] == "internal-test"
        assert response["error"]["code"] == JSONRPCResponseBuilder.INTERNAL_ERROR
        assert response["error"]["message"] == "Internal error"
        assert response["error"]["data"] == "Database connection failed"
    
    def test_build_method_not_found_response(self):
        """Test method not found error response"""
        response = JSONRPCResponseBuilder.build_method_not_found_response(
            request_id="method-test",
            method_name="unknown_method"
        )
        
        assert response["id"] == "method-test"
        assert response["error"]["code"] == JSONRPCResponseBuilder.METHOD_NOT_FOUND
        assert response["error"]["message"] == "Method not found"
        assert response["error"]["data"] == "Unknown method: unknown_method"
    
    def test_format_response_json(self):
        """Test JSON formatting"""
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"unicode": "тест", "number": 42}
        }
        
        json_str = JSONRPCResponseBuilder.format_response_json(response)
        
        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed == response
        
        # Should preserve unicode
        assert "тест" in json_str
    
    @patch('builtins.print')
    def test_send_success_response(self, mock_print):
        """Test sending success response to stdout"""
        result = {"status": "completed"}
        
        JSONRPCResponseBuilder.send_success_response("send-test", result)
        
        mock_print.assert_called_once()
        args, kwargs = mock_print.call_args
        
        # Check that flush=True was passed
        assert kwargs.get('flush') is True
        
        # Check JSON content
        json_output = args[0]
        parsed = json.loads(json_output)
        assert parsed["jsonrpc"] == "2.0"
        assert parsed["id"] == "send-test"
        assert parsed["result"] == result
    
    @patch('builtins.print')
    def test_send_error_response(self, mock_print):
        """Test sending error response to stdout"""
        JSONRPCResponseBuilder.send_error_response(
            request_id="error-send",
            error_code=-32601,
            error_message="Method not found",
            error_data="test_method"
        )
        
        mock_print.assert_called_once()
        args, kwargs = mock_print.call_args
        
        assert kwargs.get('flush') is True
        
        json_output = args[0]
        parsed = json.loads(json_output)
        assert parsed["error"]["code"] == -32601
        assert parsed["error"]["message"] == "Method not found"
        assert parsed["error"]["data"] == "test_method"
    
    @patch('builtins.print')
    def test_send_parse_error(self, mock_print):
        """Test sending parse error to stdout"""
        JSONRPCResponseBuilder.send_parse_error("Malformed JSON")
        
        mock_print.assert_called_once()
        args, kwargs = mock_print.call_args
        
        json_output = args[0]
        parsed = json.loads(json_output)
        assert parsed["id"] == 0
        assert parsed["error"]["code"] == JSONRPCResponseBuilder.PARSE_ERROR
        assert parsed["error"]["data"] == "Malformed JSON"
    
    @patch('builtins.print')
    def test_send_internal_error(self, mock_print):
        """Test sending internal error to stdout"""
        JSONRPCResponseBuilder.send_internal_error("internal-456", "Connection timeout")
        
        mock_print.assert_called_once()
        args, kwargs = mock_print.call_args
        
        json_output = args[0]
        parsed = json.loads(json_output)
        assert parsed["id"] == "internal-456"
        assert parsed["error"]["code"] == JSONRPCResponseBuilder.INTERNAL_ERROR
        assert parsed["error"]["data"] == "Connection timeout"
    
    def test_error_code_constants(self):
        """Test that error code constants are correct"""
        assert JSONRPCResponseBuilder.PARSE_ERROR == -32700
        assert JSONRPCResponseBuilder.INVALID_REQUEST == -32600
        assert JSONRPCResponseBuilder.METHOD_NOT_FOUND == -32601
        assert JSONRPCResponseBuilder.INVALID_PARAMS == -32602
        assert JSONRPCResponseBuilder.INTERNAL_ERROR == -32603
    
    def test_response_builder_no_error_data(self):
        """Test error response without optional data"""
        response = JSONRPCResponseBuilder.build_error_response(
            request_id=100,
            error_code=-32602,
            error_message="Invalid params"
        )
        
        # Should not include 'data' field when not provided
        assert "data" not in response["error"]
        assert len(response["error"]) == 2  # Only code and message


class TestResponseBuilderFactory:
    """Test the factory function"""
    
    def test_create_json_rpc_response_builder(self):
        """Test factory function creates proper instance"""
        builder = create_json_rpc_response_builder()
        
        assert isinstance(builder, JSONRPCResponseBuilder)
    
    def test_response_builder_is_stateless(self):
        """Test that response builder doesn't maintain state"""
        builder1 = create_json_rpc_response_builder()
        builder2 = create_json_rpc_response_builder()
        
        # Both should work the same way
        response1 = builder1.build_success_response(1, {"test": 1})
        response2 = builder2.build_success_response(1, {"test": 1})
        
        assert response1 == response2


class TestJSONRPCCompliance:
    """Test JSON-RPC 2.0 specification compliance"""
    
    def test_jsonrpc_version_always_present(self):
        """Test that jsonrpc version is always 2.0"""
        success_response = JSONRPCResponseBuilder.build_success_response(1, {})
        error_response = JSONRPCResponseBuilder.build_error_response(1, -32603, "Error")
        
        assert success_response["jsonrpc"] == "2.0"
        assert error_response["jsonrpc"] == "2.0"
    
    def test_id_preservation(self):
        """Test that request ID is preserved in responses"""
        test_ids = [None, 0, 1, "string-id", {"complex": "id"}]
        
        for test_id in test_ids:
            success_response = JSONRPCResponseBuilder.build_success_response(test_id, {})
            error_response = JSONRPCResponseBuilder.build_error_response(test_id, -32603, "Error")
            
            assert success_response["id"] == test_id
            assert error_response["id"] == test_id
    
    def test_error_object_structure(self):
        """Test that error objects have required structure"""
        response = JSONRPCResponseBuilder.build_error_response(
            request_id=1,
            error_code=-32601,
            error_message="Method not found",
            error_data="additional info"
        )
        
        error = response["error"]
        assert isinstance(error["code"], int)
        assert isinstance(error["message"], str)
        assert "data" in error  # Optional but present in this case
        
        # Test without data
        response_no_data = JSONRPCResponseBuilder.build_error_response(
            request_id=1,
            error_code=-32601,
            error_message="Method not found"
        )
        
        error_no_data = response_no_data["error"]
        assert "data" not in error_no_data