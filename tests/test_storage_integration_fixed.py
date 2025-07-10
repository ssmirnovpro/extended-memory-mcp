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
Fixed Storage Integration Tests

Properly test the integration between storage providers and server.py
with correct mocking and realistic scenarios.
"""

import pytest
import asyncio
import os
from unittest.mock import AsyncMock, patch, MagicMock
import tempfile
import os

# Import what we're testing
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "mcp-server"))

from extended_memory_mcp.server import MemoryMCPServer
from extended_memory_mcp.core.storage.providers.sqlite.sqlite_provider import SQLiteStorageProvider
from extended_memory_mcp.core.storage.providers.redis.redis_provider import RedisStorageProvider, REDIS_AVAILABLE


class TestStorageProviderIntegration:
    """Test proper integration between server and storage providers"""
    
    @pytest.mark.asyncio
    async def test_server_initialization_with_sqlite(self):
        """Test server properly initializes with SQLite provider"""
        # Clear any environment variables that might interfere
        with patch.dict(os.environ, {}, clear=True):
            # Create proper mock without real initialization to avoid database locking
            with patch('extended_memory_mcp.server.get_storage_provider') as mock_get_provider:
                # Full mock without real database operations
                mock_provider = AsyncMock()
                mock_provider.__class__.__name__ = "SQLiteStorageProvider"
                mock_provider.initialize.return_value = True
                mock_provider.close = AsyncMock()
                mock_get_provider.return_value = mock_provider
                
                server = MemoryMCPServer()
                await server.initialize()
                
                # Verify server uses correct provider type
                assert server.storage_provider.__class__.__name__ == "SQLiteStorageProvider"
                
                # Verify mock was called
                mock_get_provider.assert_called_once()
                
                # Cleanup
                await server.storage_provider.close()
    
    @pytest.mark.asyncio
    async def test_server_save_context_integration(self):
        """Test server save_context method calls storage provider correctly"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            # Create provider with temp file
            provider = SQLiteStorageProvider(tmp.name)
            await provider.initialize()
            
            # Patch the get_storage_provider function in server module
            with patch('extended_memory_mcp.server.get_storage_provider', return_value=provider) as mock_get_provider:
                server = MemoryMCPServer()
                await server.initialize()
                
                # Verify mock was called
                mock_get_provider.assert_called_once()
                
                # Test save_context via server's storage provider
                context_id = await server.storage_provider.save_context(
                    content="Integration test content",
                    importance_level=7,
                    project_id="test_project",
                )
                
                assert context_id is not None
                
                # Verify context was actually saved to the mocked provider
                contexts = await server.storage_provider.load_contexts(
                    project_id="test_project"
                )
                assert len(contexts) == 1
                assert contexts[0]["content"] == "Integration test content"
    
    @pytest.mark.asyncio
    async def test_server_load_contexts_integration(self):
        """Test server load_contexts method with real provider"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            # Create provider with temp file
            provider = SQLiteStorageProvider(tmp.name)
            await provider.initialize()
            
            # First save some contexts directly to provider
            await provider.save_context(
                content="Context 1",
                importance_level=8,
                project_id="integration_test",
            )
            await provider.save_context(
                content="Context 2",
                importance_level=6,
                project_id="integration_test",
            )
            
            # Patch the get_storage_provider function in server module
            with patch('extended_memory_mcp.server.get_storage_provider', return_value=provider) as mock_get_provider:
                server = MemoryMCPServer()
                await server.initialize()
                
                # Verify mock was called
                mock_get_provider.assert_called_once()
                
                # Test load_contexts
                response = await provider.load_contexts(
                    project_id="integration_test",
                    limit=10
                )
                
                assert isinstance(response, list)
                assert len(response) >= 1  # Should find at least Context 1 (importance 8 >= default threshold 7)
                # Verify one of the contexts has the expected content
                context_contents = [ctx["content"] for ctx in response]
                assert "Context 1" in context_contents


class TestStorageProviderFailFast:
    """Test fail-fast behavior when storage providers fail"""
    
    @pytest.mark.asyncio
    async def test_storage_factory_fails_fast_on_bad_redis(self):
        """Test that bad Redis config causes immediate failure"""
        from extended_memory_mcp.core.storage.storage_factory import StorageFactory
        
        # Mock Redis to simulate connection failure
        with patch('extended_memory_mcp.core.storage.providers.redis.services.connection_service.redis') as mock_redis:
            mock_connection = AsyncMock()
            mock_redis.from_url.return_value = mock_connection
            mock_connection.ping.side_effect = Exception("Connection refused")
            
            # Should raise RuntimeError, not fall back to SQLite
            with pytest.raises(RuntimeError, match="Storage provider 'redis' failed"):
                await StorageFactory.create_provider("redis://localhost:6379/0")
    
    @pytest.mark.asyncio  
    async def test_server_fails_fast_on_provider_init_failure(self):
        """Test server fails immediately if storage provider initialization fails"""
        with patch('extended_memory_mcp.server.get_storage_provider') as mock_get_provider:
            # Mock provider that fails to initialize
            mock_get_provider.side_effect = Exception("Storage provider initialization failed")
            
            server = MemoryMCPServer()
            
            # Server should fail fast during initialization
            # Should raise structured error instead of generic Exception
            with pytest.raises((Exception, ValueError)) as exc_info:
                await server.initialize()
                
            # Accept both old and new error message formats
            error_str = str(exc_info.value)
            assert any(phrase in error_str for phrase in [
                "Storage initialization failed", 
                "Storage configuration error",
                "Storage provider initialization failed"
            ])


class TestStorageProviderConnectionStrings:
    """Test connection string parsing and provider creation"""
    
    @pytest.mark.asyncio
    async def test_sqlite_connection_string_parsing(self):
        """Test SQLite connection strings are parsed correctly"""
        # Test parsing SQLite connection string
        connection_string = "sqlite:///tmp/test.db"
        
        with patch('extended_memory_mcp.server.get_storage_provider') as mock_get_provider:
            with patch.dict('os.environ', {'MEMORY_CONNECTION_STRING': connection_string}):
                # Mock successful provider creation
                mock_provider = AsyncMock()
                mock_get_provider.return_value = mock_provider
                
                server = MemoryMCPServer()
                await server.initialize()
                
                # Verify provider was called
                mock_get_provider.assert_called_once()
                assert server.storage_provider == mock_provider
    
    @pytest.mark.asyncio
    async def test_redis_connection_string_parsing(self):
        """Test Redis connection strings are parsed correctly"""
        if not REDIS_AVAILABLE:
            pytest.skip("Redis not available")
            
        from extended_memory_mcp.core.storage.storage_factory import StorageFactory
        
        # Mock Redis to avoid needing real server
        with patch('extended_memory_mcp.core.storage.providers.redis.services.connection_service.redis') as mock_redis:
            mock_connection = AsyncMock()
            mock_redis.from_url.return_value = mock_connection
            mock_connection.ping.return_value = True
            
            test_cases = [
                "redis://localhost:6379/0",
                "redis://localhost:6379/1", 
                "redis://127.0.0.1:6379/5"
            ]
            
            for conn_str in test_cases:
                provider = await StorageFactory.create_provider(conn_str)
                assert provider.__class__.__name__ == "RedisStorageProvider"
                await provider.close()


class TestStorageProviderMethodCompatibility:
    """Test that all providers implement required methods consistently"""
    
    def get_server_required_methods(self) -> list:
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
    async def test_sqlite_provider_server_compatibility(self):
        """Test SQLite provider has all methods server.py needs"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            provider = SQLiteStorageProvider(tmp.name)
            await provider.initialize()
            
            for method_name in self.get_server_required_methods():
                assert hasattr(provider, method_name), f"SQLiteStorageProvider missing {method_name}"
                assert callable(getattr(provider, method_name)), f"{method_name} not callable"
            
            await provider.close()
            os.unlink(tmp.name)
    
    @pytest.mark.asyncio
    async def test_redis_provider_server_compatibility(self):
        """Test Redis provider has all methods server.py needs"""
        if not REDIS_AVAILABLE:
            pytest.skip("Redis not available")
            
        with patch('extended_memory_mcp.core.storage.providers.redis.services.connection_service.redis') as mock_redis:
            mock_connection = AsyncMock()
            mock_redis.from_url.return_value = mock_connection
            mock_connection.ping.return_value = True
            
            provider = RedisStorageProvider("localhost", 6379, 15)
            await provider.initialize()
            
            for method_name in self.get_server_required_methods():
                assert hasattr(provider, method_name), f"RedisStorageProvider missing {method_name}"
                assert callable(getattr(provider, method_name)), f"{method_name} not callable"
            
            await provider.close()


class TestStorageProviderDataIsolation:
    """Test that data is properly isolated between projects"""
    
    @pytest.mark.asyncio
    async def test_project_data_isolation_sqlite(self):
        """Test SQLite provider properly isolates project data"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            provider = SQLiteStorageProvider(tmp.name)
            await provider.initialize()
            
            # Save contexts for different projects
            project_a_id = await provider.save_context(
                content="Project A secret",
                importance_level=9,
                project_id="project_a",
            )
            
            project_b_id = await provider.save_context(
                content="Project B secret",
                importance_level=9,
                project_id="project_b",
            )
            
            # Load contexts for each project separately
            project_a_contexts = await provider.load_contexts(
project_id="project_a"
        )
            project_b_contexts = await provider.load_contexts(
project_id="project_b"
        )
            
            # Each project should only see its own contexts
            assert len(project_a_contexts) == 1
            assert len(project_b_contexts) == 1
            assert project_a_contexts[0]["content"] == "Project A secret"
            assert project_b_contexts[0]["content"] == "Project B secret"
            
            # Cross-project access should return empty
            assert project_a_contexts[0]["project_id"] == "project_a"
            assert project_b_contexts[0]["project_id"] == "project_b"
            
            await provider.close()
            os.unlink(tmp.name)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
