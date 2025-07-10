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
Test license headers compliance

Ensures all Python files have proper MIT license headers
"""

import os
import pytest
from pathlib import Path


class TestLicenseCompliance:
    """Test that all Python files have proper license headers"""

    @staticmethod
    def get_python_files():
        """Get all Python files in the project"""
        project_root = Path(__file__).parent.parent
        python_files = []
        
        # Find all Python files
        for root, dirs, files in os.walk(project_root):
            # Skip .git, __pycache__, .pytest_cache, venv and other hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv']]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    # Convert to relative path for cleaner error messages
                    relative_path = file_path.relative_to(project_root)
                    python_files.append(str(relative_path))
        
        return sorted(python_files)

    @staticmethod
    def has_license_header(file_path):
        """Check if file has proper MIT license header"""
        project_root = Path(__file__).parent.parent
        full_path = project_root / file_path
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read(2000)  # Read first 2000 chars
                
                # Check for required license components
                required_components = [
                    "Extended Memory MCP Server",
                    "Copyright (c) 2024 Sergey Smirnov",
                    "Permission is hereby granted, free of charge",
                    "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND"
                ]
                
                for component in required_components:
                    if component not in content:
                        return False, f"Missing: {component}"
                
                return True, "License header found"
                
        except Exception as e:
            return False, f"Error reading file: {e}"

    def test_all_python_files_have_license_headers(self):
        """Test that all Python files have proper MIT license headers"""
        python_files = self.get_python_files()
        files_without_license = []
        
        for file_path in python_files:
            has_license, reason = self.has_license_header(file_path)
            if not has_license:
                files_without_license.append(f"{file_path}: {reason}")
        
        if files_without_license:
            error_message = (
                f"Found {len(files_without_license)} Python files without proper MIT license headers:\n"
                + "\n".join(f"  - {file}" for file in files_without_license)
            )
            pytest.fail(error_message)

    def test_license_header_format_consistency(self):
        """Test that license headers follow consistent format"""
        python_files = self.get_python_files()
        inconsistent_files = []
        
        expected_start = "# Extended Memory MCP Server"
        expected_copyright = "# Copyright (c) 2024 Sergey Smirnov"
        
        for file_path in python_files:
            project_root = Path(__file__).parent.parent
            full_path = project_root / file_path
            
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Find first license line (skip shebang)
                license_start_line = None
                for i, line in enumerate(lines):
                    if expected_start in line:
                        license_start_line = i
                        break
                
                if license_start_line is None:
                    continue  # Will be caught by previous test
                
                # Check format consistency
                if license_start_line < len(lines) - 1:
                    copyright_line = lines[license_start_line + 1]
                    if expected_copyright not in copyright_line:
                        inconsistent_files.append(f"{file_path}: Incorrect copyright line format")
                
            except Exception as e:
                inconsistent_files.append(f"{file_path}: Error reading file: {e}")
        
        if inconsistent_files:
            error_message = (
                f"Found {len(inconsistent_files)} Python files with inconsistent license header format:\n"
                + "\n".join(f"  - {file}" for file in inconsistent_files)
            )
            pytest.fail(error_message)

    def test_project_file_count_sanity_check(self):
        """Sanity check that we're finding a reasonable number of Python files"""
        python_files = self.get_python_files()
        
        # We should have a reasonable number of Python files (at least 50)
        assert len(python_files) >= 50, (
            f"Expected at least 50 Python files, found {len(python_files)}. "
            "This might indicate an issue with file discovery."
        )
        
        # Should include key files
        expected_files = [
            "src/extended_memory_mcp/server.py",
            "src/extended_memory_mcp/core/memory/memory_facade.py",
            "src/extended_memory_mcp/core/storage/storage_factory.py"
        ]
        
        for expected_file in expected_files:
            assert expected_file in python_files, f"Expected file not found: {expected_file}"
