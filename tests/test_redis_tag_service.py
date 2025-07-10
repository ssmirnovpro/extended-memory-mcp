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

"""
Tests for Redis Tag Service
Tests basic tag operations and error handling
"""

import sys
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Add mcp-server to path for imports
project_root = Path(__file__).parent.parent / "mcp-server"
sys.path.append(str(project_root))

from extended_memory_mcp.core.storage.providers.redis.services.tag_service import RedisTagService
from extended_memory_mcp.core.storage.providers.redis.services.connection_service import RedisConnectionService


class TestRedisTagService:
    """Test Redis tag service operations"""

    @pytest.fixture
    def mock_connection_service(self):
        """Create mock connection service"""
        connection_service = MagicMock(spec=RedisConnectionService)
        connection_service.make_key = MagicMock(
            side_effect=lambda prefix, key: f"test:{prefix}:{key}"
        )
        return connection_service

    @pytest.fixture
    def tag_service(self, mock_connection_service):
        """Create tag service with mock connection"""
        return RedisTagService(mock_connection_service)

    @pytest.mark.asyncio
    async def test_get_context_tags_success(self, tag_service, mock_connection_service):
        """Test successful retrieval of context tags"""
        # Setup mock Redis connection
        mock_redis = AsyncMock()
        mock_connection_service.get_connection = AsyncMock(return_value=mock_redis)
        
        # Mock context data with tags
        context_data = {
            "id": "123",
            "content": "Test content",
            "tags": ["python", "backend", "api"]
        }
        mock_redis.get.return_value = json.dumps(context_data)
        
        # Test
        result = await tag_service.get_context_tags("123")
        
        # Verify
        assert result == ["python", "backend", "api"]
        mock_connection_service.make_key.assert_called_once_with("context", "123")
        mock_redis.get.assert_called_once_with("test:context:123")

    @pytest.mark.asyncio
    async def test_get_context_tags_no_context(self, tag_service, mock_connection_service):
        """Test get_context_tags when context doesn't exist"""
        # Setup mock Redis connection
        mock_redis = AsyncMock()
        mock_connection_service.get_connection = AsyncMock(return_value=mock_redis)
        mock_redis.get.return_value = None  # Context not found
        
        # Test
        result = await tag_service.get_context_tags("nonexistent")
        
        # Verify
        assert result == []
        mock_redis.get.assert_called_once_with("test:context:nonexistent")

    @pytest.mark.asyncio
    async def test_get_context_tags_no_tags_field(self, tag_service, mock_connection_service):
        """Test get_context_tags when context has no tags field"""
        # Setup mock Redis connection
        mock_redis = AsyncMock()
        mock_connection_service.get_connection = AsyncMock(return_value=mock_redis)
        
        # Mock context data without tags
        context_data = {
            "id": "123",
            "content": "Test content"
        }
        mock_redis.get.return_value = json.dumps(context_data)
        
        # Test
        result = await tag_service.get_context_tags("123")
        
        # Verify
        assert result == []

    @pytest.mark.asyncio
    async def test_get_context_tags_invalid_json(self, tag_service, mock_connection_service):
        """Test get_context_tags with invalid JSON data"""
        # Setup mock Redis connection
        mock_redis = AsyncMock()
        mock_connection_service.get_connection = AsyncMock(return_value=mock_redis)
        mock_redis.get.return_value = "invalid json data"
        
        # Test - should handle exception gracefully
        result = await tag_service.get_context_tags("123")
        
        # Should return empty list on error
        assert result == []

    @pytest.mark.asyncio
    async def test_get_context_tags_connection_error(self, tag_service, mock_connection_service):
        """Test get_context_tags with Redis connection error"""
        # Setup mock connection to raise exception
        mock_connection_service.get_connection = AsyncMock(
            side_effect=Exception("Redis connection failed")
        )
        
        # Test - should handle exception gracefully
        result = await tag_service.get_context_tags("123")
        
        # Should return empty list on error
        assert result == []

    @pytest.mark.asyncio
    async def test_get_context_tags_empty_tags(self, tag_service, mock_connection_service):
        """Test get_context_tags when tags field is empty list"""
        # Setup mock Redis connection
        mock_redis = AsyncMock()
        mock_connection_service.get_connection = AsyncMock(return_value=mock_redis)
        
        # Mock context data with empty tags
        context_data = {
            "id": "123",
            "content": "Test content",
            "tags": []
        }
        mock_redis.get.return_value = json.dumps(context_data)
        
        # Test
        result = await tag_service.get_context_tags("123")
        
        # Verify
        assert result == []

    @pytest.mark.asyncio
    async def test_get_context_tags_with_various_data_types(self, tag_service, mock_connection_service):
        """Test get_context_tags handles various tag data types"""
        # Setup mock Redis connection
        mock_redis = AsyncMock()
        mock_connection_service.get_connection = AsyncMock(return_value=mock_redis)
        
        # Mock context data with mixed tag types (should be handled gracefully)
        context_data = {
            "id": "123",
            "content": "Test content",
            "tags": ["string_tag", 123, None, "another_string"]  # Mixed types
        }
        mock_redis.get.return_value = json.dumps(context_data)
        
        # Test
        result = await tag_service.get_context_tags("123")
        
        # Should return the original list as-is (service doesn't validate types)
        assert result == ["string_tag", 123, None, "another_string"]

    @pytest.mark.asyncio
    async def test_make_key_usage(self, tag_service, mock_connection_service):
        """Test that make_key is called with correct parameters"""
        # Setup mock Redis connection
        mock_redis = AsyncMock()
        mock_connection_service.get_connection = AsyncMock(return_value=mock_redis)
        mock_redis.get.return_value = '{"tags": ["test"]}'
        
        # Test with different context IDs
        test_ids = ["123", "abc", "test-context", "context_with_underscores"]
        
        for context_id in test_ids:
            await tag_service.get_context_tags(context_id)
            
        # Verify make_key was called correctly for each ID
        expected_calls = [
            (("context", context_id),) for context_id in test_ids
        ]
        
        actual_calls = mock_connection_service.make_key.call_args_list
        assert len(actual_calls) == len(expected_calls)
        
        for i, expected in enumerate(expected_calls):
            assert actual_calls[i].args == expected[0]

    @pytest.mark.asyncio
    async def test_error_handling_preserves_service_state(self, tag_service, mock_connection_service):
        """Test that errors don't affect service state"""
        # Setup mock Redis connection that fails first time, succeeds second
        mock_redis = AsyncMock()
        mock_connection_service.get_connection = AsyncMock(return_value=mock_redis)
        
        # First call fails
        mock_redis.get.side_effect = Exception("Redis error")
        result1 = await tag_service.get_context_tags("123")
        assert result1 == []
        
        # Second call succeeds
        mock_redis.get.side_effect = None
        mock_redis.get.return_value = '{"tags": ["success"]}'
        result2 = await tag_service.get_context_tags("123")
        assert result2 == ["success"]
        
        # Service should still be functional
        assert tag_service.connection == mock_connection_service

    @pytest.mark.asyncio
    async def test_concurrent_tag_requests(self, tag_service, mock_connection_service):
        """Test concurrent tag requests don't interfere with each other"""
        import asyncio
        
        # Setup mock Redis connection
        mock_redis = AsyncMock()
        mock_connection_service.get_connection = AsyncMock(return_value=mock_redis)
        
        # Mock different responses for different context IDs
        def mock_get(key):
            if "context1" in key:
                return '{"tags": ["tag1"]}'
            elif "context2" in key:
                return '{"tags": ["tag2"]}'
            else:
                return '{"tags": []}'
        
        mock_redis.get.side_effect = mock_get
        
        # Make concurrent requests
        tasks = [
            tag_service.get_context_tags("context1"),
            tag_service.get_context_tags("context2"),
            tag_service.get_context_tags("context3")
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify each got correct tags
        assert results[0] == ["tag1"]
        assert results[1] == ["tag2"] 
        assert results[2] == []
        
        # Verify all requests were made
        assert mock_redis.get.call_count == 3
