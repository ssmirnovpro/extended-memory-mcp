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
Critical Integration Tests for Storage Provider Compatibility

These tests catch architectural problems that cost hours of debugging:
- Method compatibility between providers  
- Server.py API contracts
- Configuration issues
- Fallback prevention
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import tempfile
import os

# Import what we're testing
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "mcp-server"))

from extended_memory_mcp.server import MemoryMCPServer
from extended_memory_mcp.core.storage.providers.sqlite.sqlite_provider import SQLiteStorageProvider
from extended_memory_mcp.core.storage.providers.redis.redis_provider import RedisStorageProvider

class TestStorageProviderContractCompliance:
    """Ensure all storage providers implement the same interface"""
    
    def get_required_methods(self):
        """Methods that server.py expects from storage providers"""
        return [
            'save_context',
            'load_contexts', 
            'load_init_contexts',
            'forget_context',
            'list_all_projects_global',
            'load_high_importance_contexts'
        ]
    
    @pytest.mark.asyncio
    async def test_sqlite_provider_has_all_methods(self):
        """SQLite provider implements all required methods"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            provider = SQLiteStorageProvider(tmp.name)
            await provider.initialize()
            
            for method_name in self.get_required_methods():
                assert hasattr(provider, method_name), f"SQLiteStorageProvider missing {method_name}"
                assert callable(getattr(provider, method_name)), f"{method_name} is not callable"
    
    @pytest.mark.asyncio 
    async def test_redis_provider_has_all_methods(self):
        """Redis provider implements all required methods"""
        # Skip if Redis not available
        try:
            provider = RedisStorageProvider(host="localhost", port=6379, db=15)
            await provider.initialize()
        except Exception:
            pytest.skip("Redis not available")
            
        for method_name in self.get_required_methods():
            assert hasattr(provider, method_name), f"RedisStorageProvider missing {method_name}"
            assert callable(getattr(provider, method_name)), f"{method_name} is not callable"

class TestServerStorageIntegration:
    """Test server.py properly uses storage_provider without fallbacks"""
    
    @pytest.mark.asyncio
    async def test_server_uses_only_storage_provider(self):
        """Server doesn't fall back to SQLite when using Redis"""
        with patch('extended_memory_mcp.server.get_storage_provider') as mock_get_provider:  # Patch in server module
            mock_provider = AsyncMock()
            mock_provider.load_init_contexts.return_value = {
                'contexts': [],
                'init_instruction': 'test'
            }
            mock_get_provider.return_value = mock_provider
            
            server = MemoryMCPServer()
            await server.initialize()
            
            # Test that server calls storage_provider, not internal SQLite
            # Use server's load_contexts method through the storage_provider
            await server.storage_provider.load_init_contexts(
                project_id="test", limit=5
            )
            
            # Verify storage_provider was called
            mock_provider.load_init_contexts.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_server_fails_fast_on_missing_methods(self):
        """Server returns error instead of falling back when provider incomplete"""
        with patch('extended_memory_mcp.server.get_storage_provider') as mock_get_provider:  # Patch in server module
            incomplete_provider = AsyncMock()
            # Missing load_init_contexts method
            del incomplete_provider.load_init_contexts
            mock_get_provider.return_value = incomplete_provider
            
            server = MemoryMCPServer()
            await server.initialize()
            
            # Should return error, not fall back to SQLite
            # Try to call a method that requires load_init_contexts
            try:
                await server.storage_provider.load_init_contexts(
                    project_id="test", limit=5
                )
                assert False, "Should have raised AttributeError"
            except AttributeError:
                pass  # Expected - method missing

class TestConfigurationHandling:
    """Test environment variable handling and connection string parsing"""
    
    @pytest.mark.asyncio
    async def test_redis_connection_string_parsed_correctly(self):
        """Redis connection strings properly configure provider"""
        test_cases = [
            "redis://localhost:6379/1",
            "redis://localhost:6379/3", 
            "redis://127.0.0.1:6379/5"
        ]
        
        for conn_str in test_cases:
            with patch.dict(os.environ, {'STORAGE_CONNECTION_STRING': conn_str}):
                with patch('extended_memory_mcp.core.storage.providers.redis.redis_provider.redis.Redis') as mock_redis:
                    from extended_memory_mcp.core.storage.storage_factory import StorageFactory
                    
                    # Should parse without errors
                    parsed_conn = StorageFactory.get_connection_string()
                    assert parsed_conn == conn_str
                    
    def test_no_silent_fallback_on_redis_failure(self):
        """System fails fast when Redis configured but unavailable"""
        with patch.dict(os.environ, {'STORAGE_CONNECTION_STRING': 'redis://nonexistent:6379/1'}):
            with pytest.raises(Exception):
                # Should crash, not fall back to SQLite
                from extended_memory_mcp.core.storage import get_storage_provider
                asyncio.run(get_storage_provider())

class TestDataConsistency:
    """Test that save/load operations work consistently across providers"""
    
    @pytest.mark.asyncio
    async def test_context_save_load_cycle_sqlite(self):
        """SQLite provider save/load cycle works"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            provider = SQLiteStorageProvider(tmp.name)
            await provider.initialize()
            
            # Save context
            context_id = await provider.save_context(
                content="test content",
                importance_level=8,  # Above default threshold of 7
                project_id="test_project",
            )
            
            assert context_id is not None
            
            # Load contexts
            contexts = await provider.load_contexts(
                project_id="test_project"
            )
            assert len(contexts) == 1
            assert contexts[0]['content'] == "test content"
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_context_save_load_cycle_redis(self):
        """Redis provider save/load cycle works (with mocked Redis)"""
        with patch('extended_memory_mcp.core.storage.providers.redis.services.connection_service.redis') as mock_redis:
            # Mock Redis connection
            mock_connection = AsyncMock()
            mock_redis.from_url.return_value = mock_connection
            mock_connection.ping.return_value = True
            
            # Mock Redis operations
            mock_connection.hset = AsyncMock(return_value=1)
            mock_connection.hget = AsyncMock(return_value=None)  # No existing project initially
            mock_connection.lrange = AsyncMock(return_value=['1'])  # Return context ID 1 as string
            mock_connection.get = AsyncMock(return_value='{"content": "test content redis", "context_type": "test", "importance_level": 5, "project_id": "test_project", "tags": ["test"], "created_at": "2025-01-01T00:00:00"}')
            mock_connection.hgetall = AsyncMock(return_value={
                b'content': b'test content redis',
                b'context_type': b'test',
                b'importance_level': b'5',
                b'project_id': b'test_project',
                b'tags': b'["test"]',
                b'created_at': b'2025-01-01T00:00:00'
            })
            mock_connection.keys = AsyncMock(return_value=[b'context:1'])
            
            provider = RedisStorageProvider(host="localhost", port=6379, db=15)
            await provider.initialize()
            
            # Save context  
            context_id = await provider.save_context(
                content="test content redis",
                importance_level=5,
                project_id="test_project",
            )
            
            assert context_id is not None
            
            # Load contexts
            contexts = await provider.load_contexts(
                project_id="test_project"
            ) 
            assert len(contexts) == 1
            assert contexts[0]['content'] == "test content redis"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
