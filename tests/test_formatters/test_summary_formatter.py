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

"""Test Summary Formatter"""

import pytest
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add project path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "mcp-server"))

from extended_memory_mcp.formatters.summary_formatter import ContextSummaryFormatter, create_summary_formatter


class TestContextSummaryFormatter:
    """Test context summary formatting"""

    def test_create_summary_formatter(self):
        """Test factory function"""
        formatter = create_summary_formatter()
        assert isinstance(formatter, ContextSummaryFormatter)

    def test_empty_contexts(self):
        """Test handling of empty contexts"""
        formatter = ContextSummaryFormatter()
        result = formatter.generate_summary([], "test_project")
        assert "No saved context found for project test_project" in result

    def test_single_context(self):
        """Test formatting single context"""
        formatter = ContextSummaryFormatter()
        contexts = [
            {
                "content": "Test content",
                "importance_level": 5,
                "created_at": "2025-07-04T10:00:00"
            }
        ]
        
        result = formatter.generate_summary(contexts, "test_project")
        
        assert "Found 1 saved contexts" in result
        assert "test_project" in result
        # Summary now only contains header, not content or formatting

    def test_high_importance_context(self):
        """Test high importance context detection"""
        formatter = ContextSummaryFormatter()
        contexts = [
            {
                "content": "Important decision",
                "context_type": "decision", 
                "importance_level": 9,
                "created_at": "2025-07-04T10:00:00"
            }
        ]
        
        result = formatter.generate_summary(contexts, "test_project")
        
        assert "1 high-importance" in result
        # Summary now only contains header, not content

    def test_recent_context(self):
        """Test recent context detection"""
        formatter = ContextSummaryFormatter()
        recent_time = datetime.now().isoformat()
        
        contexts = [
            {
                "content": "Recent update",
                "context_type": "status",
                "importance_level": 6,
                "created_at": recent_time
            }
        ]
        
        result = formatter.generate_summary(contexts, "test_project")
        
        assert "1 from last 24h" in result

    def test_content_truncation(self):
        """Test content truncation for long content"""
        formatter = ContextSummaryFormatter()
        long_content = "A" * 300  # Longer than normal limit (200)
        
        contexts = [
            {
                "content": long_content,
                "context_type": "general",
                "importance_level": 5,
                "created_at": "2025-07-04T10:00:00"
            }
        ]
        
        result = formatter.generate_summary(contexts, "test_project")
        
        assert "Found 1 saved contexts" in result
        # Summary now only contains header, not truncated content

    def test_critical_type_no_truncation(self):
        """Test that content under truncation limit is not truncated"""
        formatter = ContextSummaryFormatter()
        short_content = "B" * 180  # Under truncation limit (200 chars)
        
        contexts = [
            {
                "content": short_content,
                "importance_level": 8,
                "created_at": "2025-07-04T10:00:00"
            }
        ]
        
        result = formatter.generate_summary(contexts, "test_project")
        
        assert "1 high-importance" in result
        # Summary now only contains header, not content

    def test_multiple_contexts_sorting(self):
        """Test multiple contexts are sorted by importance"""
        formatter = ContextSummaryFormatter()
        contexts = [
            {
                "content": "Low importance",
                "importance_level": 3,
                "created_at": "2025-07-04T10:00:00"
            },
            {
                "content": "High importance", 
                "importance_level": 9,
                "created_at": "2025-07-04T09:00:00"
            }
        ]
        
        result = formatter.generate_summary(contexts, "test_project")
        
        assert "1 high-importance" in result  
        # Summary now only contains header, not content or sorting details

    def test_context_type_grouping(self):
        """Test context type grouping in summary (all contexts are now 'general')"""
        formatter = ContextSummaryFormatter()
        contexts = [
            {"content": "Status 1", "importance_level": 5, "created_at": "2025-07-04T10:00:00"},
            {"content": "Status 2", "importance_level": 5, "created_at": "2025-07-04T11:00:00"},
            {"content": "Decision 1", "importance_level": 8, "created_at": "2025-07-04T12:00:00"}
        ]
        
        result = formatter.generate_summary(contexts, "test_project")
        
        assert "Found 3 saved contexts" in result
        # No type grouping anymore since context_type was removed

    def test_found_vs_loaded_logic(self):
        """Test Found vs Loaded logic based on limit"""
        formatter = ContextSummaryFormatter()
        contexts = [
            {"content": "Context 1", "importance_level": 5, "created_at": "2025-07-04T10:00:00"},
            {"content": "Context 2", "importance_level": 5, "created_at": "2025-07-04T11:00:00"}
        ]
        
        # Case 1: No limit provided - should say "Found"
        result = formatter.generate_summary(contexts, "test_project")
        assert "Found 2 saved contexts" in result
        
        # Case 2: Limit = number of contexts - should say "Loaded only" (hit the limit)
        result = formatter.generate_summary(contexts, "test_project", limit=2)
        assert "Loaded only 2 saved contexts" in result
        
        # Case 3: Limit > number of contexts - should say "Found" (didn't hit limit)
        result = formatter.generate_summary(contexts, "test_project", limit=5)
        assert "Found 2 saved contexts" in result
