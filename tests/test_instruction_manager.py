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
Tests for InstructionManager

Tests custom instruction loading and tilde path expansion
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open

import sys
sys.path.append(str(Path(__file__).parent.parent / "mcp-server"))

from extended_memory_mcp.core.instruction_manager import InstructionManager


class TestInstructionManager:
    """Test InstructionManager functionality"""

    @pytest.fixture
    def instruction_manager(self):
        """Create InstructionManager instance for testing"""
        return InstructionManager()

    @pytest.mark.asyncio
    async def test_load_custom_instruction_with_tilde_path(self, instruction_manager):
        """Test that tilde paths are properly expanded when loading custom instructions"""
        test_content = "Test custom instruction content"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as temp_file:
            temp_file.write(test_content)
            temp_file.flush()
            
            # Create a tilde path that should expand to the temp file location
            tilde_path = f"~/{os.path.relpath(temp_file.name, os.path.expanduser('~'))}"
            
            try:
                # Load instruction using tilde path
                result = await instruction_manager._load_custom_instructions(tilde_path)
                
                # Verify content was loaded correctly
                assert result == test_content
                
            finally:
                # Clean up temp file
                os.unlink(temp_file.name)

    @pytest.mark.asyncio
    async def test_load_custom_instruction_file_not_found_with_tilde(self, instruction_manager):
        """Test proper error handling for non-existent files with tilde paths"""
        non_existent_tilde_path = "~/non_existent_custom_instruction.md"
        
        with pytest.raises(FileNotFoundError, match="Custom instruction file not found"):
            await instruction_manager._load_custom_instructions(non_existent_tilde_path)

    @pytest.mark.asyncio
    async def test_load_custom_instruction_empty_file_with_tilde(self, instruction_manager):
        """Test handling of empty custom instruction files with tilde paths"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as temp_file:
            # Create empty file
            temp_file.flush()
            
            # Create a tilde path
            tilde_path = f"~/{os.path.relpath(temp_file.name, os.path.expanduser('~'))}"
            
            try:
                # Load instruction using tilde path
                result = await instruction_manager._load_custom_instructions(tilde_path)
                
                # Should return empty string for empty file
                assert result == ""
                
            finally:
                # Clean up temp file
                os.unlink(temp_file.name)

    @pytest.mark.asyncio
    async def test_load_custom_instruction_absolute_path(self, instruction_manager):
        """Test that absolute paths still work correctly"""
        test_content = "Test absolute path content"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as temp_file:
            temp_file.write(test_content)
            temp_file.flush()
            
            try:
                # Load instruction using absolute path
                result = await instruction_manager._load_custom_instructions(temp_file.name)
                
                # Verify content was loaded correctly
                assert result == test_content
                
            finally:
                # Clean up temp file
                os.unlink(temp_file.name)

    @pytest.mark.asyncio 
    async def test_load_init_instruction_with_env_var(self, instruction_manager):
        """Test loading custom instruction via environment variable"""
        test_content = "Test env var content"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as temp_file:
            temp_file.write(test_content)
            temp_file.flush()
            
            # Create a tilde path
            tilde_path = f"~/{os.path.relpath(temp_file.name, os.path.expanduser('~'))}"
            
            try:
                # Mock environment variable
                with patch.dict(os.environ, {'CUSTOM_INSTRUCTION_PATH': tilde_path}):
                    result = await instruction_manager.load_init_instruction()
                    
                    # Verify content was loaded correctly
                    assert test_content in result
                    
            finally:
                # Clean up temp file
                os.unlink(temp_file.name)

    @pytest.mark.asyncio
    async def test_load_init_instruction_no_env_var(self, instruction_manager):
        """Test behavior when no CUSTOM_INSTRUCTION_PATH is set"""
        with patch.dict(os.environ, {}, clear=True):
            # Clear the env var if it exists
            if 'CUSTOM_INSTRUCTION_PATH' in os.environ:
                del os.environ['CUSTOM_INSTRUCTION_PATH']
                
            result = await instruction_manager.load_init_instruction()
            
            # Should return empty string when no custom instruction is available
            assert result == ""

    @pytest.mark.asyncio
    async def test_load_init_instruction_empty_env_var(self, instruction_manager):
        """Test behavior when CUSTOM_INSTRUCTION_PATH is empty"""
        with patch.dict(os.environ, {'CUSTOM_INSTRUCTION_PATH': ''}):
            result = await instruction_manager.load_init_instruction()
            
            # Should return empty string when env var is empty
            assert result == ""
