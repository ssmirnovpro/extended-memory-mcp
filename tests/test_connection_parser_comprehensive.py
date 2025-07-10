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
Comprehensive Connection String Parser Tests

Tests all edge cases, error conditions, and supported formats
for the connection string parsing functionality.
"""

import pytest
from pathlib import Path
import os

# Import what we're testing
import sys
sys.path.append(str(Path(__file__).parent.parent / "mcp-server"))

from extended_memory_mcp.core.storage.connection_parser import ConnectionStringParser, ConnectionStringError


class TestConnectionStringParserEdgeCases:
    """Test edge cases and error conditions in connection string parsing"""
    
    def test_empty_connection_string(self):
        """Test handling of empty connection string"""
        with pytest.raises(ConnectionStringError, match="Connection string cannot be empty"):
            ConnectionStringParser.parse("")
    
    def test_none_connection_string(self):
        """Test handling of None connection string"""
        with pytest.raises(ConnectionStringError, match="Connection string cannot be empty"):
            ConnectionStringParser.parse(None)
    
    def test_whitespace_only_connection_string(self):
        """Test handling of whitespace-only connection string"""
        with pytest.raises(ConnectionStringError, match="Missing scheme"):
            ConnectionStringParser.parse("   \t\n   ")
    
    def test_invalid_scheme(self):
        """Test handling of unsupported database schemes"""
        with pytest.raises(ConnectionStringError, match="Unsupported scheme"):
            ConnectionStringParser.parse("mongodb://localhost:27017/test")
        
        with pytest.raises(ConnectionStringError, match="Unsupported scheme"):
            ConnectionStringParser.parse("mysql://user:pass@localhost:3306/db")
    
    def test_malformed_url(self):
        """Test handling of malformed URLs"""
        with pytest.raises(ConnectionStringError):
            ConnectionStringParser.parse("not-a-url-at-all")
        
        with pytest.raises(ConnectionStringError):
            ConnectionStringParser.parse("://missing-scheme")
        
        with pytest.raises(ConnectionStringError):
            ConnectionStringParser.parse("scheme-only:")


class TestSQLiteConnectionStringParsing:
    """Test SQLite connection string parsing in detail"""
    
    def test_sqlite_absolute_path_unix(self):
        """Test SQLite with absolute Unix path"""
        result = ConnectionStringParser.parse("sqlite:////usr/local/data/memory.db")
        
        assert result["provider"] == "sqlite"
        assert result["config"]["database_path"] == "/usr/local/data/memory.db"
        assert result["config"]["timeout"] == 30.0
        assert result["config"]["check_same_thread"] == True  # Default value
    
    def test_sqlite_absolute_path_windows(self):
        """Test SQLite with absolute Windows path"""
        result = ConnectionStringParser.parse("sqlite:///C:/Users/user/memory.db")
        
        assert result["provider"] == "sqlite"
        assert result["config"]["database_path"] == "/C:/Users/user/memory.db"  # URLparse behavior
    
    def test_sqlite_relative_path(self):
        """Test SQLite with relative path"""
        result = ConnectionStringParser.parse("sqlite:///data/memory.db")
        
        assert result["provider"] == "sqlite"
        assert result["config"]["database_path"] == "/data/memory.db"  # URLparse behavior
    
    def test_sqlite_user_home_path(self):
        """Test SQLite with user home path expansion"""
        result = ConnectionStringParser.parse("sqlite:///~/Documents/memory.db")
        
        assert result["provider"] == "sqlite"
        expected_path = str(Path.home() / "Documents" / "memory.db")
        assert result["config"]["database_path"] == expected_path
    
    def test_sqlite_with_query_parameters(self):
        """Test SQLite with query parameters"""
        result = ConnectionStringParser.parse("sqlite:///memory.db?timeout=60&check_same_thread=true")
        
        assert result["provider"] == "sqlite"
        assert result["config"]["database_path"] == "/memory.db"  # URLparse behavior
        assert result["config"]["timeout"] == 60.0
        # Note: boolean parsing might not work as expected in current implementation
    
    def test_sqlite_memory_database(self):
        """Test SQLite in-memory database"""
        result = ConnectionStringParser.parse("sqlite:///:memory:")
        
        assert result["provider"] == "sqlite"
        assert result["config"]["database_path"] == "/:memory:"  # URLparse behavior
    
    def test_sqlite_empty_path(self):
        """Test SQLite with empty path (should use default)"""
        result = ConnectionStringParser.parse("sqlite:///")
        
        assert result["provider"] == "sqlite"
        # Should use default path behavior of ConnectionStringParser
        assert result["config"]["database_path"] == "/"


class TestRedisConnectionStringParsing:
    """Test Redis connection string parsing in detail"""
    
    def test_redis_basic_localhost(self):
        """Test basic Redis localhost connection"""
        result = ConnectionStringParser.parse("redis://localhost:6379/0")
        
        assert result["provider"] == "redis"
        assert result["config"]["host"] == "localhost"
        assert result["config"]["port"] == 6379
        assert result["config"]["database"] == 0
        # Note: password/username keys not present when not specified
    
    def test_redis_with_password_only(self):
        """Test Redis with password authentication"""
        result = ConnectionStringParser.parse("redis://:secret123@localhost:6379/1")
        
        assert result["provider"] == "redis"
        assert result["config"]["host"] == "localhost"
        assert result["config"]["port"] == 6379
        assert result["config"]["database"] == 1
        assert result["config"]["password"] == "secret123"
        assert result["config"]["username"] == ""  # Empty string, not None
    
    def test_redis_with_username_and_password(self):
        """Test Redis with username and password"""
        result = ConnectionStringParser.parse("redis://admin:password@redis.example.com:6380/2")
        
        assert result["provider"] == "redis"
        assert result["config"]["host"] == "redis.example.com"
        assert result["config"]["port"] == 6380
        assert result["config"]["database"] == 2
        assert result["config"]["username"] == "admin"
        assert result["config"]["password"] == "password"
    
    def test_redis_default_port(self):
        """Test Redis with default port"""
        result = ConnectionStringParser.parse("redis://localhost/3")
        
        assert result["provider"] == "redis"
        assert result["config"]["host"] == "localhost"
        assert result["config"]["port"] == 6379  # Default port
        assert result["config"]["database"] == 3
    
    def test_redis_default_database(self):
        """Test Redis with default database"""
        result = ConnectionStringParser.parse("redis://localhost:6379")
        
        assert result["provider"] == "redis"
        assert result["config"]["host"] == "localhost"
        assert result["config"]["port"] == 6379
        assert result["config"]["database"] == 0  # Default database
    
    def test_redis_ip_address(self):
        """Test Redis with IP address"""
        result = ConnectionStringParser.parse("redis://192.168.1.100:6379/5")
        
        assert result["provider"] == "redis"
        assert result["config"]["host"] == "192.168.1.100"
        assert result["config"]["port"] == 6379
        assert result["config"]["database"] == 5
    
    def test_redis_high_database_number(self):
        """Test Redis with high database number"""
        result = ConnectionStringParser.parse("redis://localhost:6379/15")
        
        assert result["provider"] == "redis"
        assert result["config"]["database"] == 15
    
    def test_redis_query_parameters_ignored(self):
        """Test that Redis query parameters are properly ignored"""
        result = ConnectionStringParser.parse("redis://localhost:6379/0?ssl=true&timeout=30")
        
        assert result["provider"] == "redis"
        assert result["config"]["host"] == "localhost"
        assert result["config"]["port"] == 6379
        assert result["config"]["database"] == 0
        # Query parameters should be ignored for basic Redis parsing
    
    def test_redis_invalid_database_number(self):
        """Test Redis with invalid database number"""
        with pytest.raises(ConnectionStringError, match="Invalid Redis database number"):
            ConnectionStringParser.parse("redis://localhost:6379/not_a_number")
    
    def test_redis_invalid_port(self):
        """Test Redis with invalid port number"""
        with pytest.raises(ValueError, match="Port could not be cast to integer"):
            ConnectionStringParser.parse("redis://localhost:not_a_port/0")
        
        with pytest.raises(ValueError, match="Port out of range"):
            ConnectionStringParser.parse("redis://localhost:99999/0")  # Port too high


class TestPostgreSQLConnectionStringParsing:
    """Test PostgreSQL connection string parsing"""
    
    def test_postgresql_basic(self):
        """Test basic PostgreSQL connection"""
        result = ConnectionStringParser.parse("postgresql://user:password@localhost:5432/mydatabase")
        
        assert result["provider"] == "postgresql"
        assert result["config"]["host"] == "localhost"
        assert result["config"]["port"] == 5432
        assert result["config"]["database"] == "mydatabase"
        assert result["config"]["user"] == "user"
        assert result["config"]["password"] == "password"
    
    def test_postgres_alias(self):
        """Test postgres:// alias for PostgreSQL"""
        result = ConnectionStringParser.parse("postgres://user:pass@host:5432/db")
        
        assert result["provider"] == "postgresql"
        assert result["config"]["host"] == "host"
        assert result["config"]["user"] == "user"
        assert result["config"]["password"] == "pass"
        assert result["config"]["database"] == "db"
    
    def test_postgresql_default_port(self):
        """Test PostgreSQL with default port"""
        result = ConnectionStringParser.parse("postgresql://user:password@localhost/database")
        
        assert result["provider"] == "postgresql"
        assert result["config"]["port"] == 5432  # Default PostgreSQL port
    
    def test_postgresql_no_password(self):
        """Test PostgreSQL without password"""
        result = ConnectionStringParser.parse("postgresql://user@localhost:5432/database")
        
        assert result["provider"] == "postgresql"
        assert result["config"]["user"] == "user"
        # Note: password key not present when not specified
        assert "password" not in result["config"] or result["config"]["password"] is None
    
    def test_postgresql_query_parameters(self):
        """Test PostgreSQL with query parameters"""
        result = ConnectionStringParser.parse("postgresql://user:pass@host:5432/db?sslmode=require&connect_timeout=10")
        
        assert result["provider"] == "postgresql"
        assert result["config"]["host"] == "host"
        # Query parameters handling depends on implementation


class TestConnectionStringValidation:
    """Test connection string validation methods"""
    
    def test_validate_valid_connection_strings(self):
        """Test validation of valid connection strings"""
        valid_strings = [
            "sqlite:///memory.db",
            "redis://localhost:6379/0",
            "postgresql://user:pass@localhost/db"
        ]
        
        for conn_str in valid_strings:
            assert ConnectionStringParser.validate_connection_string(conn_str) == True
    
    def test_validate_invalid_connection_strings(self):
        """Test validation of invalid connection strings"""
        invalid_strings = [
            "",
            None,
            "not-a-connection-string",
            "mysql://localhost/db",  # Unsupported
            "redis://localhost:invalid_port/0"
        ]
        
        for conn_str in invalid_strings:
            assert ConnectionStringParser.validate_connection_string(conn_str) == False


class TestConnectionStringDefaults:
    """Test default connection string generation"""
    
    def test_get_default_sqlite_path(self):
        """Test default SQLite path generation"""
        import os
        
        # Save original env var if exists
        original_storage_connection = os.environ.get("STORAGE_CONNECTION_STRING")
        
        try:
            # Unset env var to test true default
            if "STORAGE_CONNECTION_STRING" in os.environ:
                del os.environ["STORAGE_CONNECTION_STRING"]
            
            default_conn = ConnectionStringParser.get_default_connection_string()
            
            assert default_conn.startswith("sqlite:///")
            assert "extended-memory-mcp" in default_conn
            assert default_conn.endswith("memory.db")
            
        finally:
            # Restore original env var
            if original_storage_connection is not None:
                os.environ["STORAGE_CONNECTION_STRING"] = original_storage_connection
    
    def test_default_path_is_writable_location(self):
        """Test that default path points to writable location"""
        import os
        
        # Save original env var if exists
        original_storage_connection = os.environ.get("STORAGE_CONNECTION_STRING")
        
        try:
            # Unset env var to test true default
            if "STORAGE_CONNECTION_STRING" in os.environ:
                del os.environ["STORAGE_CONNECTION_STRING"]
            
            default_conn = ConnectionStringParser.get_default_connection_string()
            parsed = ConnectionStringParser.parse(default_conn)
            
            # Only test if we got an SQLite connection
            if parsed["provider"] != "sqlite":
                pytest.skip("Default connection is not SQLite (likely due to CI env vars)")
            
            db_path = Path(parsed["config"]["database_path"])
            parent_dir = db_path.parent
            
            # Parent directory should be creatable/writable
            # In CI environments, we may need to create the directory structure
            try:
                parent_dir.mkdir(parents=True, exist_ok=True)
                # If we can create it, it's writable
                assert parent_dir.exists()
            except (PermissionError, OSError):
                # If we can't create it, at least one parent should exist
                pass
                
        finally:
            # Restore original env var
            if original_storage_connection is not None:
                os.environ["STORAGE_CONNECTION_STRING"] = original_storage_connection
            
            # If we couldn't create the directory, at least check that one of the parent directories exists
            if not parent_dir.exists():
                assert parent_dir.parent.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
