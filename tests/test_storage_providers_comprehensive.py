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
Comprehensive Storage Provider Tests

Complete test coverage for all storage providers ensuring:
- Interface compliance
- Method compatibility
- Error handling
- Data consistency
- Performance characteristics
"""

import pytest
import pytest_asyncio
import asyncio
import tempfile
import os
import json
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch

# Import what we're testing
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "mcp-server"))

from extended_memory_mcp.core.storage.providers.sqlite.sqlite_provider import SQLiteStorageProvider
from extended_memory_mcp.core.storage.providers.redis.redis_provider import RedisStorageProvider, REDIS_AVAILABLE
from extended_memory_mcp.core.storage.interfaces.storage_provider import IStorageProvider


class TestStorageProviderInterfaceCompliance:
    """Ensure all providers implement the complete IStorageProvider interface"""
    
    def get_required_methods(self) -> List[str]:
        """All methods that must be implemented by storage providers"""
        return [
            'initialize',
            'save_context', 
            'load_context',
            'load_contexts',
            'update_context',
            'delete_context', 
            'search_contexts',
            'get_context_tags',
            'list_all_projects_global',
            'get_storage_stats',
            'cleanup_expired',
            'load_init_contexts',
            'forget_context',
            'load_high_importance_contexts', 
            'close'
        ]
    
    @pytest.mark.asyncio
    async def test_sqlite_provider_interface_compliance(self):
        """SQLite provider implements complete interface"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            provider = SQLiteStorageProvider(tmp.name)
            await provider.initialize()
            
            # Check all required methods exist and are callable
            for method_name in self.get_required_methods():
                assert hasattr(provider, method_name), f"SQLiteStorageProvider missing {method_name}"
                method = getattr(provider, method_name)
                assert callable(method), f"{method_name} is not callable"
            
            # Cleanup
            await provider.close()
            os.unlink(tmp.name)
    
    @pytest.mark.asyncio 
    async def test_redis_provider_interface_compliance(self):
        """Redis provider implements complete interface"""
        if not REDIS_AVAILABLE:
            pytest.skip("Redis not available")
            
        # Mock Redis to avoid requiring real server
        with patch('extended_memory_mcp.core.storage.providers.redis.services.connection_service.redis') as mock_redis:
            mock_connection = AsyncMock()
            mock_redis.from_url.return_value = mock_connection
            mock_connection.ping.return_value = True
            
            provider = RedisStorageProvider("localhost", 6379, 15)
            await provider.initialize()
            
            # Check all required methods exist and are callable  
            for method_name in self.get_required_methods():
                assert hasattr(provider, method_name), f"RedisStorageProvider missing {method_name}"
                method = getattr(provider, method_name)
                assert callable(method), f"{method_name} is not callable"
            
            await provider.close()


class TestSQLiteProviderFunctionality:
    """Test SQLite provider core functionality"""
    
    @pytest_asyncio.fixture
    async def sqlite_provider(self):
        """Create temporary SQLite provider for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            provider = SQLiteStorageProvider(tmp.name)
            await provider.initialize()
            yield provider
            await provider.close()
            try:
                os.unlink(tmp.name)
            except:
                pass
    
    @pytest.mark.asyncio
    async def test_save_and_load_context(self, sqlite_provider):
        """Test basic save/load functionality"""
        # Save a context directly through provider
        context_id = await sqlite_provider.save_context(
            content="Test context content",
            importance_level=7,
            project_id="test_project",
        )
        
        assert context_id is not None
        assert isinstance(context_id, (str, int))
        
        # Load the context back
        loaded_context = await sqlite_provider.load_context(context_id)
        assert loaded_context is not None
        assert loaded_context['content'] == "Test context content"
        assert loaded_context['importance_level'] == 7
        assert loaded_context['project_id'] == "test_project"
    
    @pytest.mark.asyncio
    async def test_load_contexts_by_project(self, sqlite_provider):
        """Test loading contexts filtered by project"""
        # Save contexts for different projects
        await sqlite_provider.save_context(
            content="Project A context",
            importance_level=5,
            project_id="project_a",
        )
        
        await sqlite_provider.save_context(
            content="Project B context",
            importance_level=5,
            project_id="project_b",
        )
        
        # Load contexts for project A only
        contexts_a = await sqlite_provider.load_contexts(
            project_id="project_a",
            importance_threshold=1  # Lower threshold to include our contexts
        )
        assert len(contexts_a) == 1
        assert contexts_a[0]['content'] == "Project A context"
        
        # Load contexts for project B only  
        contexts_b = await sqlite_provider.load_contexts(
            project_id="project_b",
            importance_threshold=1  # Lower threshold to include our contexts
        )
        assert len(contexts_b) == 1
        assert contexts_b[0]['content'] == "Project B context"
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_forget_context(self, sqlite_provider):
        """Test context deletion via forget_context method"""
        # Save a context
        context_id = await sqlite_provider.save_context(
            content="Context to delete",
            importance_level=5,
            project_id="test_project",
        )
        
        # Verify it exists
        loaded = await sqlite_provider.load_context(context_id)
        assert loaded is not None
        
        # Delete it using forget_context
        success = await sqlite_provider.forget_context(context_id)
        assert success is True
        
        # Verify it's gone
        deleted = await sqlite_provider.load_context(context_id)
        assert deleted is None
    
    @pytest.mark.asyncio
    async def test_search_contexts(self, sqlite_provider):
        """Test context searching functionality"""
        # Save contexts with different attributes
        await sqlite_provider.save_context(
            content="Important project milestone",
            importance_level=9,
            project_id="test_project",
        )
        
        await sqlite_provider.save_context(
            content="Technical implementation detail",
            importance_level=6,
            project_id="test_project",
        )
        
        # Search by project
        all_contexts = await sqlite_provider.search_contexts({
            "project_id": "test_project"
        })
        assert len(all_contexts) == 2
        
        # Search by importance level
        important_contexts = await sqlite_provider.search_contexts({
            "project_id": "test_project", 
            "min_importance": 8
        })
        assert len(important_contexts) == 1
        assert "milestone" in important_contexts[0]['content']


class TestRedisProviderFunctionality:
    """Test Redis provider core functionality with mocked Redis"""
    
    @pytest_asyncio.fixture
    async def mock_redis_provider(self):
        """Create Redis provider with mocked connection"""
        if not REDIS_AVAILABLE:
            pytest.skip("Redis not available")
            
        with patch('extended_memory_mcp.core.storage.providers.redis.services.connection_service.redis') as mock_redis:
            # Mock Redis connection
            mock_connection = AsyncMock()
            mock_redis.from_url.return_value = mock_connection
            mock_connection.ping.return_value = True
            
            # Mock Redis operations
            mock_connection.set = AsyncMock(return_value=True)
            mock_connection.get = AsyncMock(return_value='{"test": "data"}')
            mock_connection.keys = AsyncMock(return_value=[])
            mock_connection.hgetall = AsyncMock(return_value={})
            mock_connection.hset = AsyncMock(return_value=1)
            mock_connection.delete = AsyncMock(return_value=1)
            mock_connection.exists = AsyncMock(return_value=0)
            
            provider = RedisStorageProvider("localhost", 6379, 15)
            await provider.initialize()
            
            yield provider, mock_connection
            
            await provider.close()
    
    @pytest.mark.asyncio
    async def test_redis_save_context_calls_redis(self, mock_redis_provider):
        """Test that save_context properly calls Redis operations"""
        provider, mock_connection = mock_redis_provider
        
        # Mock successful save
        mock_connection.set.return_value = True
        mock_connection.hset.return_value = 1
        
        context_id = await provider.save_context(
            content="Test Redis context",
            importance_level=7,
            project_id="redis_test",
        )
        
        assert context_id is not None
        
        # Verify Redis operations were called
        assert mock_connection.set.called
        assert mock_connection.hset.called
    
    @pytest.mark.asyncio
    async def test_redis_error_handling(self, mock_redis_provider):
        """Test Redis provider error handling"""
        provider, mock_connection = mock_redis_provider
        
        # Mock Redis error
        mock_connection.set.side_effect = Exception("Redis connection error")
        
        # Should handle error gracefully
        context_id = await provider.save_context(
            content="Test context",
            importance_level=5,
            project_id="test_project",
        )
        
        # Should return None on error
        assert context_id is None


class TestStorageProviderErrorHandling:
    """Test error handling across all providers"""
    
    @pytest.mark.asyncio
    async def test_sqlite_handles_invalid_database_path(self):
        """Test SQLite provider handles invalid database paths"""
        # Try to create provider with invalid path
        invalid_path = "/invalid/path/that/does/not/exist/database.db"
        
        # Should handle initialization error gracefully
        with pytest.raises((OSError, FileNotFoundError)):
            provider = SQLiteStorageProvider(invalid_path)
            await provider.initialize()
    
    @pytest.mark.asyncio
    async def test_redis_handles_connection_failure(self):
        """Test Redis provider handles connection failures"""
        with patch('extended_memory_mcp.core.storage.providers.redis.services.connection_service.redis') as mock_redis:
            mock_connection = AsyncMock()
            mock_redis.from_url.return_value = mock_connection
            
            # Mock connection failure
            mock_connection.ping.side_effect = Exception("Connection refused")
            
            provider = RedisStorageProvider(host="nonexistent-host", port=6379, db=0)
            
            # Should raise RuntimeError on connection failure
            with pytest.raises(RuntimeError):
                await provider.initialize()


class TestStorageProviderDataConsistency:
    """Test data consistency across save/load cycles"""
    
    @pytest_asyncio.fixture
    async def sqlite_provider(self):
        """Create temporary SQLite provider"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            provider = SQLiteStorageProvider(tmp.name)
            await provider.initialize()
            yield provider
            await provider.close()
            try:
                os.unlink(tmp.name)
            except:
                pass
    
    @pytest.mark.asyncio
    async def test_complex_data_preservation(self, sqlite_provider):
        """Test that complex data structures are preserved"""
        complex_content = {
            "nested": {
                "data": ["item1", "item2"],
                "numbers": [1, 2, 3.14],
                "boolean": True
            },
            "unicode": "test unicode 🎉",
            "special_chars": "quotes 'single' \"double\" & ampersand"
        }
        
        # Save complex content as JSON string
        context_id = await sqlite_provider.save_context(
            content=json.dumps(complex_content),
            importance_level=5,
            project_id="test_project",
            tags=["complex", "data"]
        )
        
        # Load it back
        loaded = await sqlite_provider.load_context(context_id)
        assert loaded is not None
        
        # Parse and verify complex content
        loaded_content = json.loads(loaded['content'])
        assert loaded_content == complex_content
    
    @pytest.mark.asyncio
    async def test_large_content_handling(self, sqlite_provider):
        """Test handling of large content"""
        # Create large content (10KB)
        large_content = "x" * 10240
        
        context_id = await sqlite_provider.save_context(
            content=large_content,
            importance_level=5,
            project_id="test_project",
        )
        
        assert context_id is not None
        
        # Load and verify
        loaded = await sqlite_provider.load_context(context_id)
        assert loaded is not None
        assert len(loaded['content']) == 10240
        assert loaded['content'] == large_content


class TestStorageProviderPerformance:
    """Test performance characteristics of storage providers"""
    
    @pytest_asyncio.fixture
    async def sqlite_provider(self):
        """Create temporary SQLite provider"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            provider = SQLiteStorageProvider(tmp.name)
            await provider.initialize()
            yield provider
            await provider.close()
            try:
                os.unlink(tmp.name)
            except:
                pass
    
    @pytest.mark.asyncio
    async def test_bulk_save_performance(self, sqlite_provider):
        """Test performance with multiple contexts"""
        import time
        
        start_time = time.time()
        
        # Save 50 contexts
        context_ids = []
        for i in range(50):
            context_id = await sqlite_provider.save_context(
                content=f"Context number {i}",
                importance_level=5,
                project_id="performance_project",
            )
            context_ids.append(context_id)
        
        save_time = time.time() - start_time
        
        # Should complete within reasonable time (< 5 seconds)
        assert save_time < 5.0, f"Bulk save took too long: {save_time}s"
        assert len(context_ids) == 50
        assert all(cid is not None for cid in context_ids)
        
        # Test bulk load performance
        start_time = time.time()
        
        contexts = await sqlite_provider.load_contexts(
            project_id="performance_project",
            limit=50,
            importance_threshold=1  # Lower threshold to include our contexts
        )
        
        load_time = time.time() - start_time
        
        # Should load within reasonable time (< 2 seconds)
        assert load_time < 2.0, f"Bulk load took too long: {load_time}s"
        assert len(contexts) == 50
        
        # Should load quickly (< 1 second)
        assert load_time < 1.0, f"Bulk load took too long: {load_time}s"
        assert len(contexts) == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
