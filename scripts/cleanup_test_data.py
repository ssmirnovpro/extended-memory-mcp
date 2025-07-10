#!/usr/bin/env python3

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


# Extended Memory MCP Server
# Copyright (C) 2025 Sergey Smirnov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.


"""
Test data cleanup script
Removes temporary database files and logs
"""

import os
import sys
from pathlib import Path

def cleanup_test_data():
    """Clean up test data"""
    
    project_root = Path(__file__).parent.parent
    
    # Files to remove
    files_to_remove = [
        project_root / "mcp-server" / "storage" / "test_memory.db",
        project_root / "mcp-server" / "storage" / "test_memory.db-wal",
        project_root / "mcp-server" / "storage" / "test_memory.db-shm",
        project_root / "mcp-server" / "storage" / "memory.db",
        project_root / "mcp-server" / "storage" / "memory.db-wal", 
        project_root / "mcp-server" / "storage" / "memory.db-shm"
    ]
    
    # Directories with temporary files
    temp_dirs = [
        project_root / "__pycache__",
        project_root / "mcp-server" / "__pycache__",
        project_root / "mcp-server" / "core" / "__pycache__",
        project_root / "mcp-server" / "tools" / "__pycache__",
        project_root / "tests" / "__pycache__",
        project_root / ".pytest_cache"
    ]
    
    removed_count = 0
    
    print("🧹 Cleaning up test data...")
    
    # Remove files
    for file_path in files_to_remove:
        if file_path.exists():
            try:
                file_path.unlink()
                print(f"  ✅ Removed file: {file_path.name}")
                removed_count += 1
            except Exception as e:
                print(f"  ❌ Error removing {file_path.name}: {e}")
    
    # Remove directories
    for dir_path in temp_dirs:
        if dir_path.exists():
            try:
                import shutil
                shutil.rmtree(dir_path)
                print(f"  ✅ Removed directory: {dir_path.name}")
                removed_count += 1
            except Exception as e:
                print(f"  ❌ Error removing {dir_path.name}: {e}")
    
    if removed_count == 0:
        print("  📭 No files to remove")
    else:
        print(f"\n🎉 Cleanup completed! Removed {removed_count} items")

if __name__ == "__main__":
    cleanup_test_data()
