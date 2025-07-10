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
Unit tests for ConnectionStringParser.

Tests parsing of various connection string formats and error handling.
"""

import pytest
import os
from unittest.mock import patch

from extended_memory_mcp.core.storage.connection_parser import ConnectionStringParser, ConnectionStringError


class TestConnectionStringParser:
    """Test ConnectionStringParser functionality"""
    
    def test_parse_sqlite_absolute_path(self):
        """Test SQLite with absolute path"""
        result = ConnectionStringParser.parse("sqlite:///home/user/data.db")
        
        assert result["provider"] == "sqlite"
        # Path is resolved to absolute, may differ on macOS
        assert result["config"]["database_path"].endswith("/home/user/data.db")
        assert result["config"]["timeout"] == 30.0
        assert result["config"]["check_same_thread"] is True
        assert result["config"]["journal_mode"] == "WAL"
    
    def test_parse_sqlite_with_user_path(self):
        """Test SQLite with ~ expansion"""
        result = ConnectionStringParser.parse("sqlite:///~/data.db")
        
        expected_path = os.path.expanduser("~/data.db")
        assert result["config"]["database_path"] == expected_path
    
    def test_parse_sqlite_with_query_params(self):
        """Test SQLite with custom query parameters"""
        conn_str = "sqlite:///data.db?timeout=60&journal_mode=DELETE&check_same_thread=false"
        result = ConnectionStringParser.parse(conn_str)
        
        assert result["config"]["timeout"] == 60.0
        assert result["config"]["journal_mode"] == "DELETE"
        assert result["config"]["check_same_thread"] is False
    
    def test_parse_redis_basic(self):
        """Test basic Redis connection string"""
        result = ConnectionStringParser.parse("redis://localhost:6379/0")
        
        assert result["provider"] == "redis"
        config = result["config"]
        assert config["host"] == "localhost"
        assert config["port"] == 6379
        assert config["database"] == 0
        assert "password" not in config  # None values removed
    
    def test_parse_redis_with_auth(self):
        """Test Redis with authentication"""
        result = ConnectionStringParser.parse("redis://user:pass123@redis.example.com:6380/2")
        
        config = result["config"]
        assert config["host"] == "redis.example.com"
        assert config["port"] == 6380
        assert config["database"] == 2
        assert config["username"] == "user"
        assert config["password"] == "pass123"
    
    def test_parse_redis_defaults(self):
        """Test Redis with default values"""
        result = ConnectionStringParser.parse("redis://")
        
        config = result["config"]
        assert config["host"] == "localhost"
        assert config["port"] == 6379
        assert config["database"] == 0
    
    def test_parse_redis_with_query_params(self):
        """Test Redis with query parameters"""
        conn_str = "redis://localhost/1?socket_timeout=60&max_connections=20"
        result = ConnectionStringParser.parse(conn_str)
        
        config = result["config"]
        assert config["socket_timeout"] == 60.0
        assert config["max_connections"] == 20
    
    def test_parse_postgresql_basic(self):
        """Test PostgreSQL connection string"""
        result = ConnectionStringParser.parse("postgresql://user:pass@localhost:5432/testdb")
        
        assert result["provider"] == "postgresql"
        config = result["config"]
        assert config["host"] == "localhost"
        assert config["port"] == 5432
        assert config["database"] == "testdb"
        assert config["user"] == "user"
        assert config["password"] == "pass"
    
    def test_parse_postgresql_with_defaults(self):
        """Test PostgreSQL with default port"""
        result = ConnectionStringParser.parse("postgresql://user@localhost/mydb")
        
        config = result["config"]
        assert config["port"] == 5432  # Default port
        assert config["sslmode"] == "prefer"  # Default SSL mode
    
    def test_parse_postgres_alias(self):
        """Test postgres:// alias works"""
        result = ConnectionStringParser.parse("postgres://user@localhost/db")
        
        assert result["provider"] == "postgresql"
        assert result["config"]["database"] == "db"
    
    def test_parse_postgresql_query_params(self):
        """Test PostgreSQL with query parameters"""
        conn_str = "postgresql://user@host/db?sslmode=require&connect_timeout=10"
        result = ConnectionStringParser.parse(conn_str)
        
        config = result["config"]
        assert config["sslmode"] == "require"
        assert config["connect_timeout"] == 10
    
    def test_empty_connection_string(self):
        """Test error on empty connection string"""
        with pytest.raises(ConnectionStringError, match="cannot be empty"):
            ConnectionStringParser.parse("")
    
    def test_none_connection_string(self):
        """Test error on None connection string"""
        with pytest.raises(ConnectionStringError, match="cannot be empty"):
            ConnectionStringParser.parse(None)
    
    def test_missing_scheme(self):
        """Test error on missing scheme"""
        with pytest.raises(ConnectionStringError, match="Unsupported scheme 'localhost'"):
            ConnectionStringParser.parse("localhost:5432/db")
    
    def test_unsupported_scheme(self):
        """Test error on unsupported scheme"""
        with pytest.raises(ConnectionStringError, match="Unsupported scheme 'mongodb'"):
            ConnectionStringParser.parse("mongodb://localhost/db")
    
    def test_sqlite_with_netloc_error(self):
        """Test SQLite error when host/port specified"""
        with pytest.raises(ConnectionStringError, match="should not have host/port"):
            ConnectionStringParser.parse("sqlite://localhost:1234/data.db")
    
    def test_sqlite_missing_path(self):
        """Test SQLite error when path missing"""
        with pytest.raises(ConnectionStringError, match="missing database path"):
            ConnectionStringParser.parse("sqlite://")
    
    def test_redis_invalid_database_number(self):
        """Test Redis error on invalid database number"""
        with pytest.raises(ConnectionStringError, match="Invalid Redis database number"):
            ConnectionStringParser.parse("redis://localhost/not_a_number")
    
    def test_postgresql_missing_hostname(self):
        """Test PostgreSQL error when hostname missing"""
        with pytest.raises(ConnectionStringError, match="missing hostname"):
            ConnectionStringParser.parse("postgresql:///database")
    
    def test_postgresql_missing_database(self):
        """Test PostgreSQL error when database missing"""
        with pytest.raises(ConnectionStringError, match="missing database name"):
            ConnectionStringParser.parse("postgresql://user@localhost/")
    
    def test_invalid_url_format(self):
        """Test error on malformed URL"""
        with pytest.raises(ConnectionStringError, match="Invalid URL format"):
            ConnectionStringParser.parse("not://a[valid{url")
    
    def test_get_default_connection_string(self):
        """Test default connection string generation"""
        import os
        
        # Save original env var if exists
        original_storage_connection = os.environ.get("STORAGE_CONNECTION_STRING")
        
        try:
            # Unset env var to test true default
            if "STORAGE_CONNECTION_STRING" in os.environ:
                del os.environ["STORAGE_CONNECTION_STRING"]
            
            default = ConnectionStringParser.get_default_connection_string()
            
            assert default.startswith("sqlite:///")
            assert "/.local/share/extended-memory-mcp/memory.db" in default
            
            # Should be parseable
            result = ConnectionStringParser.parse(default)
            assert result["provider"] == "sqlite"
            
        finally:
            # Restore original env var
            if original_storage_connection is not None:
                os.environ["STORAGE_CONNECTION_STRING"] = original_storage_connection
    
    def test_validate_connection_string_valid(self):
        """Test validation of valid connection strings"""
        valid_strings = [
            "sqlite:///data.db",
            "redis://localhost:6379/0",
            "postgresql://user@localhost/db"
        ]
        
        for conn_str in valid_strings:
            assert ConnectionStringParser.validate_connection_string(conn_str) is True
    
    def test_validate_connection_string_invalid(self):
        """Test validation of invalid connection strings"""
        invalid_strings = [
            "",
            "invalid",
            "sqlite://host/path",  # SQLite shouldn't have host
            "redis://localhost/abc",  # Invalid database number
            "mongodb://localhost/db"  # Unsupported scheme
        ]
        
        for conn_str in invalid_strings:
            assert ConnectionStringParser.validate_connection_string(conn_str) is False
    
    def test_query_param_boolean_parsing(self):
        """Test boolean query parameter parsing"""
        test_cases = [
            ("true", True),
            ("True", True), 
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
            ("off", False),
            ("invalid", True)  # Default value used when parsing fails
        ]
        
        for bool_str, expected in test_cases:
            conn_str = f"sqlite:///data.db?check_same_thread={bool_str}"
            result = ConnectionStringParser.parse(conn_str)
            # For invalid values, the default (True) should be used
            if bool_str == "invalid":
                assert result["config"]["check_same_thread"] == True  # Default value
            else:
                assert result["config"]["check_same_thread"] == expected
    
    @patch.dict(os.environ, {"TEST_VAR": "expanded_value"})
    def test_sqlite_environment_variable_expansion(self):
        """Test environment variable expansion in SQLite paths"""
        result = ConnectionStringParser.parse("sqlite:///$TEST_VAR/data.db")
        
        assert "expanded_value" in result["config"]["database_path"]
