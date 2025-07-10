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
Tests for Instruction Template Engine

Tests template processing and variable substitution
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

import sys
sys.path.append(str(Path(__file__).parent.parent / "mcp-server"))

from extended_memory_mcp.core.instruction_engine import InstructionTemplate, InstructionLoader, create_instruction_context


class TestInstructionTemplate:
    """Test instruction template functionality"""

    def test_simple_variable_substitution(self):
        """Test basic variable substitution"""
        template = InstructionTemplate("Hello {{name}}, welcome to {{project}}!")
        variables = {"name": "Alice", "project": "Memory MCP"}
        
        result = template.render(variables)
        
        assert result == "Hello Alice, welcome to Memory MCP!"

    def test_multiple_same_variable(self):
        """Test multiple occurrences of same variable"""
        template = InstructionTemplate("{{name}} is working on {{name}}'s project")
        variables = {"name": "Bob"}
        
        result = template.render(variables)
        
        assert result == "Bob is working on Bob's project"

    def test_missing_variable_replacement(self):
        """Test handling of missing variables"""
        template = InstructionTemplate("Hello {{name}}, your score is {{score}}")
        variables = {"name": "Charlie"}  # score is missing
        
        result = template.render(variables)
        
        # Missing variables should show missing indicator
        assert "Charlie" in result
        assert "missing:score" in result

    def test_conditional_if_true(self):
        """Test conditional block when condition is true"""
        template = InstructionTemplate("{{#if has_memory}}You have memory!{{/if}}")
        variables = {"has_memory": True}
        
        result = template.render(variables)
        
        assert result == "You have memory!"

    def test_conditional_if_false(self):
        """Test conditional block when condition is false"""
        template = InstructionTemplate("{{#if has_memory}}You have memory!{{/if}}")
        variables = {"has_memory": False}
        
        result = template.render(variables)
        
        assert result == ""

    def test_conditional_if_else_true(self):
        """Test if-else block when condition is true"""
        template = InstructionTemplate("{{#if has_data}}Data found{{else}}No data{{/if}}")
        variables = {"has_data": True}
        
        result = template.render(variables)
        
        assert result == "Data found"

    def test_conditional_if_else_false(self):
        """Test if-else block when condition is false"""
        template = InstructionTemplate("{{#if has_data}}Data found{{else}}No data{{/if}}")
        variables = {"has_data": False}
        
        result = template.render(variables)
        
        assert result == "No data"

    def test_complex_template_with_conditions_and_variables(self):
        """Test complex template with both conditionals and variables"""
        template_content = """
Hello {{user_name}}!

{{#if has_memory}}
You have {{memory_count}} memories stored.
{{else}}
No memories found. Start creating some!
{{/if}}

{{#if is_admin}}
Admin panel available.
{{/if}}
        """.strip()
        
        template = InstructionTemplate(template_content)
        variables = {
            "user_name": "Developer",
            "has_memory": True,
            "memory_count": "42",
            "is_admin": False
        }
        
        result = template.render(variables)
        
        assert "Hello Developer!" in result
        assert "You have 42 memories stored." in result
        assert "Admin panel" not in result

    def test_empty_template(self):
        """Test processing empty template"""
        template = InstructionTemplate("")
        result = template.render({"var": "value"})
        assert result == ""

    def test_template_with_no_variables(self):
        """Test template without any variables"""
        template = InstructionTemplate("This is a plain text template")
        result = template.render({"unused": "value"})
        assert result == "This is a plain text template"

    def test_nested_conditions_not_supported(self):
        """Test that nested conditions don't break the engine"""
        template = InstructionTemplate("{{#if outer}}{{#if inner}}nested{{/if}}{{/if}}")
        variables = {"outer": True, "inner": True}
        
        # Should not crash, behavior may vary
        result = template.render(variables)
        assert isinstance(result, str)

    def test_special_characters_in_variables(self):
        """Test variables with special characters"""
        template = InstructionTemplate("Path: {{file_path}}, Size: {{file_size}}")
        variables = {
            "file_path": "/path/to/file.txt",
            "file_size": "1.5 MB"
        }
        
        result = template.render(variables)
        
        assert result == "Path: /path/to/file.txt, Size: 1.5 MB"


class TestInstructionLoader:
    """Test instruction loader functionality"""

    def test_fallback_instruction(self):
        """Test fallback instruction when files not found"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            loader = InstructionLoader(tmp_dir)
            
            # Try to load instruction for non-existent project
            result = loader.load_init_instruction("nonexistent_project")
            
            # Should return fallback instruction
            assert "Memory System Guide" in result
            assert "init_load=false" in result

    def test_load_default_instruction_file(self):
        """Test loading default instruction file"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create a default instruction file
            default_file = Path(tmp_dir) / "default_init.md" 
            default_file.write_text("Default instruction for {{project_name}}")
            
            loader = InstructionLoader(tmp_dir)
            result = loader.load_init_instruction()
            
            # Should load and process the default file
            assert "Default instruction" in result

    def test_load_project_specific_instruction(self):
        """Test loading project-specific instruction file"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create project-specific instruction file
            project_file = Path(tmp_dir) / "test_project_init.md"
            project_file.write_text("Project {{project_name}} instructions")
            
            loader = InstructionLoader(tmp_dir)
            result = loader.load_init_instruction("test_project")
            
            assert "Project" in result
            assert "instructions" in result

    def test_load_custom_instruction_path(self):
        """Test loading instruction from custom path"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create custom instruction file
            custom_file = Path(tmp_dir) / "custom.md"
            custom_file.write_text("Custom instruction content")
            
            loader = InstructionLoader(tmp_dir)
            result = loader.load_init_instruction(
                project_id="any_project",
                custom_instruction_path=str(custom_file)
            )
            
            assert "Custom instruction content" in result

    def test_instruction_file_not_found_uses_fallback(self):
        """Test that missing instruction files fall back gracefully"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            loader = InstructionLoader(tmp_dir)
            
            # Try to load custom file that doesn't exist
            result = loader.load_init_instruction(
                custom_instruction_path="/nonexistent/path.md"
            )
            
            # Should fall back to default instruction
            assert "Memory System Guide" in result

    def test_instruction_file_read_error_uses_fallback(self):
        """Test that file read errors fall back gracefully"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            loader = InstructionLoader(tmp_dir)
            
            # Mock file read to raise exception
            with patch("builtins.open", side_effect=IOError("Read error")):
                result = loader.load_init_instruction()
            
            # Should fall back to default instruction
            assert "Memory System Guide" in result


class TestCreateInstructionContext:
    """Test instruction context creation"""

    def test_create_default_context(self):
        """Test creating default instruction context"""
        # Mock memory manager
        mock_memory_manager = None
        
        context = create_instruction_context(mock_memory_manager)
        
        # Should have expected default values
        assert "project_name" in context
        assert "has_recent_contexts" in context
        assert context["project_name"] == "default"
        assert context["has_recent_contexts"] is False

    def test_create_context_with_project_id(self):
        """Test creating context with specific project ID"""
        mock_memory_manager = None
        
        context = create_instruction_context(mock_memory_manager, "test_project")
        
        # Should include project ID in context
        assert "project_name" in context
        # Additional context logic would be tested when implemented

    def test_context_has_required_fields(self):
        """Test that context contains all required template fields"""
        mock_memory_manager = None
        
        context = create_instruction_context(mock_memory_manager)
        
        # Check for required context fields
        required_fields = [
            "project_name", 
            "has_recent_contexts",
            "last_activity_date",
            "project_specific_instructions",
            "user_custom_instructions"
        ]
        
        for field in required_fields:
            assert field in context, f"Required field '{field}' missing from context"
