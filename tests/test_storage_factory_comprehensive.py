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
Comprehensive Storage Factory Tests

Tests the storage factory's provider creation, configuration handling,
fail-fast behavior, and error scenarios.
"""

import pytest
import os
import tempfile
import uuid
from unittest.mock import patch, AsyncMock
from pathlib import Path

# Import what we're testing
import sys
sys.path.append(str(Path(__file__).parent.parent / "mcp-server"))

from extended_memory_mcp.core.storage.storage_factory import StorageFactory
from extended_memory_mcp.core.storage.providers.sqlite.sqlite_provider import SQLiteStorageProvider
from extended_memory_mcp.core.storage.providers.redis.redis_provider import RedisStorageProvider, REDIS_AVAILABLE


class TestStorageFactoryConfiguration:
    """Test storage factory configuration handling"""
    
    def test_get_connection_string_from_env(self):
        """Test connection string retrieval from environment"""
        test_conn_str = "redis://localhost:6379/5"
        
        with patch.dict(os.environ, {'STORAGE_CONNECTION_STRING': test_conn_str}):
            result = StorageFactory.get_connection_string()
            assert result == test_conn_str
    
    def test_get_connection_string_defaults_when_no_env(self):
        """Test default connection string when no environment variable"""
        # Clear environment variable
        with patch.dict(os.environ, {}, clear=True):
            result = StorageFactory.get_connection_string()
            
            # Should return default SQLite connection
            assert result.startswith("sqlite:///")
            assert "memory.db" in result
    
    def test_get_provider_info(self):
        """Test provider info extraction"""
        test_cases = [
            ("sqlite:///test.db", "sqlite"),
            ("redis://localhost:6379/0", "redis"),
            ("postgresql://localhost/db", "postgresql")
        ]
        
        for conn_str, expected_provider in test_cases:
            with patch.dict(os.environ, {'STORAGE_CONNECTION_STRING': conn_str}):
                info = StorageFactory.get_provider_info()
                assert info["provider"] == expected_provider
                # Note: connection_string is not returned by get_provider_info()
                assert "config" in info


class TestStorageFactoryProviderCreation:
    """Test storage factory provider creation"""
    
    @pytest.mark.asyncio
    async def test_create_sqlite_provider(self):
        """Test SQLite provider creation"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            conn_str = f"sqlite:///{tmp.name}"
            
            provider = await StorageFactory.create_provider(conn_str)
            
            assert isinstance(provider, SQLiteStorageProvider)
            assert provider.__class__.__name__ == "SQLiteStorageProvider"
            
            await provider.close()
            os.unlink(tmp.name)
    
    @pytest.mark.asyncio
    async def test_create_redis_provider_with_mock(self):
        """Test Redis provider creation with mocked Redis"""
        if not REDIS_AVAILABLE:
            pytest.skip("Redis not available")
            
        with patch('extended_memory_mcp.core.storage.providers.redis.services.connection_service.redis') as mock_redis:
            mock_connection = AsyncMock()
            mock_redis.from_url.return_value = mock_connection
            mock_connection.ping.return_value = True
            
            conn_str = "redis://localhost:6379/0"
            provider = await StorageFactory.create_provider(conn_str)
            
            assert isinstance(provider, RedisStorageProvider)
            assert provider.__class__.__name__ == "RedisStorageProvider"
            
            await provider.close()
    
    @pytest.mark.asyncio
    async def test_create_provider_without_connection_string(self):
        """Test provider creation using default connection string"""
        # Use unique temp file to avoid database locking
        with tempfile.NamedTemporaryFile(suffix=f'.test.{uuid.uuid4().hex[:8]}.db', delete=False) as tmp:
            try:
                # Clear environment and override with unique test database
                with patch.dict(os.environ, {'STORAGE_CONNECTION_STRING': f'sqlite:///{tmp.name}'}, clear=True):
                    provider = await StorageFactory.create_provider()
                    
                    # Should create SQLite provider with test path
                    assert isinstance(provider, SQLiteStorageProvider)
                    
                    await provider.close()
            finally:
                # Guaranteed cleanup
                try:
                    os.unlink(tmp.name)
                except (FileNotFoundError, PermissionError):
                    pass  # File already cleaned up or locked
    
    @pytest.mark.asyncio
    async def test_unsupported_provider_raises_error(self):
        """Test that unsupported providers raise ValueError"""
        with pytest.raises(ValueError, match="Invalid connection string.*Unsupported scheme"):
            await StorageFactory.create_provider("mongodb://localhost:27017/test")


class TestStorageFactoryFailFast:
    """Test fail-fast behavior in storage factory"""
    
    @pytest.mark.asyncio
    async def test_redis_connection_failure_raises_runtime_error(self):
        """Test that Redis connection failures raise RuntimeError"""
        if not REDIS_AVAILABLE:
            pytest.skip("Redis not available")
            
        with patch('extended_memory_mcp.core.storage.providers.redis.services.connection_service.redis') as mock_redis:
            mock_connection = AsyncMock()
            mock_redis.from_url.return_value = mock_connection
            mock_connection.ping.side_effect = Exception("Connection refused")
            
            with pytest.raises(RuntimeError, match="Storage provider 'redis' failed"):
                await StorageFactory.create_provider("redis://nonexistent:6379/0")
    
    @pytest.mark.asyncio
    async def test_sqlite_invalid_path_raises_runtime_error(self):
        """Test that SQLite invalid paths raise RuntimeError"""
        invalid_path = "/invalid/readonly/path/database.db"
        
        with pytest.raises(RuntimeError, match="Storage provider 'sqlite' failed"):
            await StorageFactory.create_provider(f"sqlite:///{invalid_path}")
    
    @pytest.mark.asyncio
    async def test_no_silent_fallback_on_provider_failure(self):
        """Test that provider failures don't silently fall back"""
        if not REDIS_AVAILABLE:
            pytest.skip("Redis not available")
            
        # Mock Redis to fail
        with patch('extended_memory_mcp.core.storage.providers.redis.services.connection_service.redis') as mock_redis:
            mock_connection = AsyncMock()
            mock_redis.from_url.return_value = mock_connection
            mock_connection.ping.side_effect = Exception("Redis server down")
            
            # Should raise RuntimeError, not return SQLite provider
            with pytest.raises(RuntimeError):
                await StorageFactory.create_provider("redis://localhost:6379/0")


class TestStorageFactoryEnvironmentHandling:
    """Test environment variable handling in storage factory"""
    
    def test_environment_variable_precedence(self):
        """Test that STORAGE_CONNECTION_STRING takes precedence"""
        env_conn_str = "redis://env-server:6379/1"
        
        with patch.dict(os.environ, {'STORAGE_CONNECTION_STRING': env_conn_str}):
            result = StorageFactory.get_connection_string()
            assert result == env_conn_str
    
    def test_environment_variable_validation(self):
        """Test validation of environment variable values"""
        invalid_conn_str = "invalid-connection-string"
        
        with patch.dict(os.environ, {'STORAGE_CONNECTION_STRING': invalid_conn_str}):
            # Should still return the value (validation happens in parser)
            result = StorageFactory.get_connection_string()
            assert result == invalid_conn_str
    
    def test_empty_environment_variable_uses_default(self):
        """Test that empty environment variable uses default"""
        with patch.dict(os.environ, {'STORAGE_CONNECTION_STRING': ''}):
            result = StorageFactory.get_connection_string()
            
            # Should use default, not empty string
            assert result.startswith("sqlite:///")
            assert "memory.db" in result


class TestStorageFactoryProviderSpecificConfiguration:
    """Test provider-specific configuration handling"""
    
    @pytest.mark.asyncio
    async def test_sqlite_provider_configuration(self):
        """Test SQLite provider receives correct configuration"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            conn_str = f"sqlite:///{tmp.name}?timeout=60&check_same_thread=true"
            
            provider = await StorageFactory.create_provider(conn_str)
            
            # Verify SQLite-specific configuration
            assert isinstance(provider, SQLiteStorageProvider)
            assert provider.timeout == 60.0
            assert provider.check_same_thread == True
            
            await provider.close()
            os.unlink(tmp.name)
    
    @pytest.mark.asyncio
    async def test_redis_provider_configuration(self):
        """Test Redis provider receives correct configuration"""
        if not REDIS_AVAILABLE:
            pytest.skip("Redis not available")
            
        with patch('extended_memory_mcp.core.storage.providers.redis.services.connection_service.redis') as mock_redis:
            mock_connection = AsyncMock()
            mock_redis.from_url.return_value = mock_connection
            mock_connection.ping.return_value = True
            
            # Test with environment overrides for Redis settings
            with patch.dict(os.environ, {
                'REDIS_KEY_PREFIX': 'test_prefix',
                'REDIS_TTL_HOURS': '24'
            }):
                provider = await StorageFactory.create_provider("redis://localhost:6379/0")
                
                # Verify Redis-specific configuration
                assert isinstance(provider, RedisStorageProvider)
                assert provider.key_prefix == "test_prefix"
                assert provider.ttl_seconds == 24 * 3600
                
                await provider.close()


class TestStorageFactoryErrorMessages:
    """Test quality of error messages from storage factory"""
    
    @pytest.mark.asyncio
    async def test_redis_unavailable_error_message(self):
        """Test helpful error message when Redis is unavailable"""
        # Mock the import to simulate Redis not being available
        with patch.dict('sys.modules', {'redis.asyncio': None}):
            with patch('extended_memory_mcp.core.storage.providers.redis.redis_provider.REDIS_AVAILABLE', False):
                with patch('extended_memory_mcp.core.storage.providers.redis.redis_provider.REDIS_VERSION_ERROR', "ImportError: No module named 'redis'"):
                    try:
                        await StorageFactory.create_provider("redis://localhost:6379/0")
                        assert False, "Should have raised RuntimeError"
                    except RuntimeError as e:
                        error_msg = str(e)
                        assert "Redis storage provider is not available" in error_msg
                        assert "pip install extended-memory-mcp[redis]" in error_msg
    
    @pytest.mark.asyncio
    async def test_connection_failure_error_message(self):
        """Test helpful error message for connection failures"""
        with patch('extended_memory_mcp.core.storage.providers.redis.services.connection_service.redis') as mock_redis:
            mock_connection = AsyncMock()
            mock_redis.from_url.return_value = mock_connection
            mock_connection.ping.side_effect = Exception("Connection timeout")
            
            try:
                await StorageFactory.create_provider("redis://unreachable-host:6379/0")
                assert False, "Should have raised RuntimeError"
            except RuntimeError as e:
                error_msg = str(e)
                assert "Failed to create Redis provider" in error_msg
                assert "Connection timeout" in error_msg
                assert "Please check" in error_msg


class TestStorageFactoryPerformance:
    """Test performance characteristics of storage factory"""
    
    @pytest.mark.asyncio
    async def test_provider_creation_performance(self):
        """Test that provider creation is reasonably fast"""
        import time
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            conn_str = f"sqlite:///{tmp.name}"
            
            start_time = time.time()
            provider = await StorageFactory.create_provider(conn_str)
            creation_time = time.time() - start_time
            
            # Should create provider quickly (< 1 second)
            assert creation_time < 1.0, f"Provider creation took too long: {creation_time}s"
            
            await provider.close()
            os.unlink(tmp.name)
    
    @pytest.mark.asyncio
    async def test_multiple_provider_creation(self):
        """Test creating multiple providers doesn't leak resources"""
        providers = []
        
        try:
            for i in range(5):
                with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
                    conn_str = f"sqlite:///{tmp.name}"
                    provider = await StorageFactory.create_provider(conn_str)
                    providers.append((provider, tmp.name))
            
            # All providers should be successfully created
            assert len(providers) == 5
            
        finally:
            # Cleanup all providers
            for provider, db_path in providers:
                await provider.close()
                try:
                    os.unlink(db_path)
                except:
                    pass


class TestStorageFactoryValidation:
    """Test validation methods in storage factory"""
    
    def test_validate_connection_string_method_exists(self):
        """Test that validate_connection_string method exists"""
        # Check if method exists (may be inherited from ConnectionStringParser)
        assert hasattr(StorageFactory, 'validate_connection_string') or \
               hasattr(StorageFactory, '_validate_connection_string')
    
    def test_connection_string_info_extraction(self):
        """Test connection string info extraction"""
        test_cases = [
            ("sqlite:///test.db", "sqlite"),
            ("redis://localhost:6379/0", "redis"),
        ]
        
        for conn_str, expected_provider in test_cases:
            info = StorageFactory.get_provider_info(conn_str)
            assert info["provider"] == expected_provider
            # Note: connection_string is not returned by get_provider_info()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
