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
Tests for project utilities
"""

import pytest
from pathlib import Path

# Add project to path
import sys
project_root = Path(__file__).parent.parent / "mcp-server"
sys.path.append(str(project_root))

from extended_memory_mcp.core.project_utils import normalize_project_id, is_default_project


class TestProjectUtils:
    """Test project utility functions"""

    def test_normalize_project_id_none_and_empty(self):
        """Test normalize_project_id with None and empty values"""
        assert normalize_project_id(None) == "general"
        assert normalize_project_id("") == "general"
        assert normalize_project_id("  ") == "general"
        assert normalize_project_id("\t\n") == "general"

    def test_normalize_project_id_case_conversion(self):
        """Test normalize_project_id converts to lowercase"""
        assert normalize_project_id("MyProject") == "myproject"
        assert normalize_project_id("EXTENDED-MEMORY") == "extended memory"
        assert normalize_project_id("Test_Project") == "test project"

    def test_normalize_project_id_underscore_hyphen_replacement(self):
        """Test normalize_project_id replaces underscores and hyphens with spaces"""
        assert normalize_project_id("extended-memory") == "extended memory"
        assert normalize_project_id("my_project") == "my project"
        assert normalize_project_id("test-project_name") == "test project name"
        assert normalize_project_id("a_b-c_d-e") == "a b c d e"

    def test_normalize_project_id_whitespace_handling(self):
        """Test normalize_project_id handles whitespace properly"""
        assert normalize_project_id("  my_project  ") == "my project"
        assert normalize_project_id("extended-memory\t") == "extended memory"
        assert normalize_project_id("\n  test_project  \n") == "test project"

    def test_normalize_project_id_multiple_spaces(self):
        """Test normalize_project_id removes multiple spaces"""
        assert normalize_project_id("my  project") == "my project"
        assert normalize_project_id("test___project") == "test project"
        assert normalize_project_id("a---b___c") == "a b c"

    def test_normalize_project_id_internationalization(self):
        """Test normalize_project_id with international characters"""
        assert normalize_project_id("Проект_Память") == "проект память"
        assert normalize_project_id("プロジェクト-メモリ") == "プロジェクト メモリ"
        assert normalize_project_id("Projet_Mémoire") == "projet mémoire"
        assert normalize_project_id("مشروع-الذاكرة") == "مشروع الذاكرة"

    def test_normalize_project_id_edge_cases(self):
        """Test normalize_project_id with edge cases"""
        assert normalize_project_id("_") == ""  # Only underscore becomes empty
        assert normalize_project_id("-") == ""  # Only hyphen becomes empty
        assert normalize_project_id("_-_-_") == ""  # Only separators become empty
        assert normalize_project_id("a") == "a"  # Single character
        assert normalize_project_id("123") == "123"  # Numbers
        assert normalize_project_id("123_abc-def") == "123 abc def"  # Mixed

    def test_is_default_project(self):
        """Test is_default_project function"""
        assert is_default_project("general") == True
        assert is_default_project("General") == False  # Case sensitive
        assert is_default_project("extended memory") == False
        assert is_default_project("") == False
        assert is_default_project(None) == False  # This will fail if called with None
