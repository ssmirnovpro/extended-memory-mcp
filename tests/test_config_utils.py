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
Tests for config_utils module
Tests configuration loading and path handling
"""

import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

# Add mcp-server to path for imports
project_root = Path(__file__).parent.parent / "mcp-server"
sys.path.append(str(project_root))

from extended_memory_mcp.core.config_utils import (
    load_memory_config,
    MEMORY_CONFIG_PATH
)


class TestConfigUtils:
    """Test configuration utilities"""

    def test_memory_config_path_exists(self):
        """Test that MEMORY_CONFIG_PATH is properly defined"""
        assert MEMORY_CONFIG_PATH is not None
        assert isinstance(MEMORY_CONFIG_PATH, Path)
        assert str(MEMORY_CONFIG_PATH).endswith("config/memory_config.yaml")

    @patch("extended_memory_mcp.core.config_utils.MEMORY_CONFIG_PATH")
    @patch("builtins.open", new_callable=mock_open, read_data="key: value\nnested:\n  item: 123")
    def test_load_memory_config_success(self, mock_file, mock_path):
        """Test successful config loading"""
        mock_path.exists.return_value = True
        
        result = load_memory_config()
        
        assert result == {"key": "value", "nested": {"item": 123}}
        mock_path.exists.assert_called_once()
        mock_file.assert_called_once_with(mock_path, "r", encoding="utf-8")

    @patch("extended_memory_mcp.core.config_utils.MEMORY_CONFIG_PATH")
    def test_load_memory_config_file_not_exists(self, mock_path):
        """Test config loading when file doesn't exist"""
        mock_path.exists.return_value = False
        
        result = load_memory_config()
        
        assert result == {}
        mock_path.exists.assert_called_once()

    @patch("builtins.open", side_effect=FileNotFoundError("File not found"))
    @patch("extended_memory_mcp.core.config_utils.MEMORY_CONFIG_PATH")
    def test_load_memory_config_file_error(self, mock_path, mock_file):
        """Test config loading with file access error"""
        mock_path.exists.return_value = True
        
        result = load_memory_config()
        
        assert result == {}

    @patch("builtins.open", new_callable=mock_open, read_data="invalid: yaml: content:")
    @patch("extended_memory_mcp.core.config_utils.MEMORY_CONFIG_PATH")
    def test_load_memory_config_invalid_yaml(self, mock_path, mock_file):
        """Test config loading with invalid YAML"""
        mock_path.exists.return_value = True
        
        result = load_memory_config()
        
        # Should return empty dict on YAML parse error
        assert result == {}

    @patch("builtins.open", new_callable=mock_open, read_data="")
    @patch("extended_memory_mcp.core.config_utils.MEMORY_CONFIG_PATH")
    def test_load_memory_config_empty_file(self, mock_path, mock_file):
        """Test config loading with empty file"""
        mock_path.exists.return_value = True
        
        result = load_memory_config()
        
        assert result == {}

    @patch("builtins.open", new_callable=mock_open, read_data="null")
    @patch("extended_memory_mcp.core.config_utils.MEMORY_CONFIG_PATH")
    def test_load_memory_config_null_content(self, mock_path, mock_file):
        """Test config loading with null YAML content"""
        mock_path.exists.return_value = True
        
        result = load_memory_config()
        
        assert result == {}

    def test_integration_with_real_temp_file(self):
        """Integration test with real temporary file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("test_key: test_value\ntest_list:\n  - item1\n  - item2")
            temp_path = Path(f.name)
        
        try:
            with patch("extended_memory_mcp.core.config_utils.MEMORY_CONFIG_PATH", temp_path):
                result = load_memory_config()
                
                assert result == {
                    "test_key": "test_value",
                    "test_list": ["item1", "item2"]
                }
        finally:
            temp_path.unlink()  # Clean up temp file

    @patch("extended_memory_mcp.core.config_utils.Path")
    def test_memory_config_path_exception_fallback(self, mock_path_class):
        """Test fallback when Path construction fails"""
        mock_path_class.side_effect = Exception("Path error")
        
        # Re-import to trigger the exception handling
        import importlib
        import extended_memory_mcp.core.config_utils
        importlib.reload(extended_memory_mcp.core.config_utils)
        
        # Should not raise exception and should have fallback path
        from extended_memory_mcp.core.config_utils import MEMORY_CONFIG_PATH
        assert MEMORY_CONFIG_PATH is not None
