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
Quick SQLite Provider API Test

Test to understand SQLite provider API for benchmarking.
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mcp-server'))

from core.storage.providers.sqlite.sqlite_provider import SQLiteStorageProvider


async def test_sqlite_api():
    """Test SQLite provider API to understand available methods."""
    try:
        print("🔍 Testing SQLite provider API...")
        
        # Initialize SQLite provider
        provider = SQLiteStorageProvider(db_path=":memory:")
        await provider.initialize()
        
        print("✅ SQLite provider initialized")
        
        # Test save_context
        context_id = await provider.save_context(
            content="Test content",
            importance_level=5,
            project_id="test_project",
            tags=["tag1", "tag2"]
        )
        
        print(f"✅ Context saved: {context_id}")
        
        # Check available methods
        print("\n🔍 Available methods on SQLite provider:")
        methods = [attr for attr in dir(provider) if not attr.startswith('_') and callable(getattr(provider, attr))]
        for method in sorted(methods):
            print(f"  - {method}")
        
        # Check tags_repo methods
        print("\n🔍 Available methods on tags_repo:")
        tags_methods = [attr for attr in dir(provider.tags_repo) if not attr.startswith('_') and callable(getattr(provider.tags_repo, attr))]
        for method in sorted(tags_methods):
            print(f"  - {method}")
        
        # Try to find popular tags method
        try:
            if hasattr(provider.tags_repo, 'get_popular_tags'):
                popular_tags = await provider.tags_repo.get_popular_tags(limit=10, min_usage=1)
                print(f"✅ get_popular_tags found: {popular_tags}")
            else:
                print("❌ get_popular_tags not found in tags_repo")
        except Exception as e:
            print(f"❌ Error calling get_popular_tags: {e}")
        
        # Try find_contexts_by_multiple_tags
        try:
            if hasattr(provider, 'find_contexts_by_multiple_tags'):
                contexts = await provider.find_contexts_by_multiple_tags(tags=["tag1"], limit=10)
                print(f"✅ find_contexts_by_multiple_tags found: {len(contexts)} results")
            else:
                print("❌ find_contexts_by_multiple_tags not found")
        except Exception as e:
            print(f"❌ Error calling find_contexts_by_multiple_tags: {e}")
        
        # Try load_contexts
        try:
            contexts = await provider.load_contexts(project_id="test_project", limit=10)
            print(f"✅ load_contexts found: {len(contexts)} results")
        except Exception as e:
            print(f"❌ Error calling load_contexts: {e}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    return True


if __name__ == "__main__":
    result = asyncio.run(test_sqlite_api())
    sys.exit(0 if result else 1)
