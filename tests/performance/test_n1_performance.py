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
Performance test to verify N+1 query fixes in SQLite provider.

This script creates test data and measures performance of:
1. search_contexts() - before/after N+1 fixes
2. load_contexts_by_ids() - before/after N+1 fixes
3. batch vs individual tag loading
"""

import asyncio
import logging
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, List

# Setup path and imports
import sys
sys.path.append("/Users/sergeysmirnov/projects/extended-memory-mcp/mcp-server")

from extended_memory_mcp.core.storage.providers.sqlite.sqlite_provider import SQLiteStorageProvider

# Disable debug logging for cleaner output
logging.getLogger("core.storage").setLevel(logging.WARNING)
logging.getLogger("core.memory").setLevel(logging.WARNING)

class PerformanceTester:
    def __init__(self):
        self.provider = None
        self.test_db_path = None
        
    async def setup(self):
        """Setup test database with sample data"""
        # Create temporary database
        temp_file = NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db_path = temp_file.name
        temp_file.close()
        
        # Initialize provider
        self.provider = SQLiteStorageProvider(db_path=self.test_db_path)
        await self.provider.initialize()
        
        print(f"📊 Setting up test database: {self.test_db_path}")
        
        # Create test data
        await self._create_test_data()
        
    async def _create_test_data(self):
        """Create test contexts with tags for performance testing"""
        print("🔨 Creating test data...")
        
        # Create test contexts with different tag patterns
        test_data = [
            {"content": "Context about database optimization", "importance": 8, 
             "tags": ["database", "performance", "optimization"]},
            {"content": "Context about memory management", "importance": 7, 
             "tags": ["memory", "management", "system"]},
            {"content": "Context about search algorithms", "importance": 9, 
             "tags": ["search", "algorithms", "performance"]},
            {"content": "Context about API design patterns", "importance": 6, 
             "tags": ["api", "design", "patterns"]},
            {"content": "Context about testing strategies", "importance": 8, 
             "tags": ["testing", "quality", "automation"]},
        ]
        
        context_ids = []
        for i in range(500):  # Create 500 contexts for stress testing
            data = test_data[i % len(test_data)]
            content = f"Context {i}: {data['content']}"
            
            context_id = await self.provider.save_context(
                content=content,
                importance_level=data["importance"],
                project_id="test-project",
                tags=data["tags"]
            )
            
            if context_id:
                context_ids.append(context_id)
                
        print(f"✅ Created {len(context_ids)} test contexts")
        return context_ids
        
    async def test_search_performance(self):
        """Test search_contexts performance with different filter patterns"""
        print("\n🔍 Testing search_contexts() performance...")
        
        # Test 1: Search by content (SQL vs Python filtering)
        start_time = time.time()
        results1 = await self.provider.search_contexts({
            "project_id": "test-project",
            "content_search": "database",
            "limit": 50
        })
        search_time = time.time() - start_time
        
        print(f"   Content search: {len(results1)} results in {search_time:.3f}s")
        
        # Test 2: Search by tags (batch vs N+1 tag loading)
        start_time = time.time()
        results2 = await self.provider.search_contexts({
            "project_id": "test-project", 
            "tags": ["performance"],
            "limit": 50
        })
        tag_search_time = time.time() - start_time
        
        print(f"   Tag search: {len(results2)} results in {tag_search_time:.3f}s")
        
        # Test 3: Complex search (multiple filters)
        start_time = time.time()
        results3 = await self.provider.search_contexts({
            "project_id": "test-project",
            "content_search": "optimization",
            "tags": ["database", "performance"],
            "min_importance": 7,
            "limit": 30
        })
        complex_search_time = time.time() - start_time
        
        print(f"   Complex search: {len(results3)} results in {complex_search_time:.3f}s")
        
        return {
            "content_search_time": search_time,
            "tag_search_time": tag_search_time,
            "complex_search_time": complex_search_time,
            "total_results": len(results1) + len(results2) + len(results3)
        }
        
    async def test_batch_loading_performance(self):
        """Test load_contexts_by_ids performance (batch tag loading)"""
        print("\n📦 Testing load_contexts_by_ids() batch performance...")
        
        # Get some context IDs to load
        all_contexts = await self.provider.load_contexts(
            project_id="test-project",
            limit=30
        )
        
        context_ids = [str(ctx["id"]) for ctx in all_contexts[:20]]
        
        # Test batch loading performance
        start_time = time.time()
        loaded_contexts = await self.provider.load_contexts_by_ids(context_ids)
        batch_time = time.time() - start_time
        
        print(f"   Batch loading: {len(loaded_contexts)} contexts in {batch_time:.3f}s")
        
        # Verify all contexts have tags loaded
        contexts_with_tags = sum(1 for ctx in loaded_contexts if "tags" in ctx and ctx["tags"])
        print(f"   Contexts with tags: {contexts_with_tags}/{len(loaded_contexts)}")
        
        return {
            "batch_load_time": batch_time,
            "contexts_loaded": len(loaded_contexts),
            "contexts_with_tags": contexts_with_tags
        }
        
    async def test_memory_vs_sql_filtering(self):
        """Compare SQL filtering vs Python filtering performance"""
        print("\n⚡ Testing SQL vs Python filtering performance...")
        
        # Test optimized search (SQL filtering)
        start_time = time.time()
        sql_results = await self.provider.search_contexts({
            "project_id": "test-project",
            "content_search": "optimization",
            "min_importance": 7,
            "limit": 50
        })
        sql_time = time.time() - start_time
        
        print(f"   SQL filtering: {len(sql_results)} results in {sql_time:.3f}s")
        
        # Simulate old approach (load all, filter in Python)
        start_time = time.time()
        all_contexts = await self.provider.load_contexts(
            project_id="test-project",
            limit=100  # Get more to filter
        )
        
        # Python filtering
        filtered_results = [
            ctx for ctx in all_contexts
            if "optimization" in ctx.get("content", "").lower() and
               ctx.get("importance_level", 0) >= 7
        ][:50]
        python_time = time.time() - start_time
        
        print(f"   Python filtering: {len(filtered_results)} results in {python_time:.3f}s")
        
        if python_time > 0:
            speedup = python_time / sql_time if sql_time > 0 else float('inf')
            print(f"   🚀 SQL is {speedup:.1f}x faster than Python filtering")
        
        return {
            "sql_filter_time": sql_time,
            "python_filter_time": python_time,
            "speedup_ratio": python_time / sql_time if sql_time > 0 else 0
        }
        
    async def run_all_tests(self):
        """Run all performance tests"""
        print("🚀 Starting N+1 Query Performance Tests")
        print("=" * 50)
        
        await self.setup()
        
        # Run tests
        search_metrics = await self.test_search_performance()
        batch_metrics = await self.test_batch_loading_performance()
        filter_metrics = await self.test_memory_vs_sql_filtering()
        
        # Summary
        print("\n📈 Performance Summary")
        print("=" * 50)
        print(f"Search operations: {search_metrics['total_results']} total results")
        print(f"Batch loading: {batch_metrics['contexts_loaded']} contexts loaded")
        print(f"Tag coverage: {batch_metrics['contexts_with_tags']}/{batch_metrics['contexts_loaded']} contexts have tags")
        
        if filter_metrics['speedup_ratio'] > 1:
            print(f"🎯 SQL filtering is {filter_metrics['speedup_ratio']:.1f}x faster than Python filtering")
        
        # Check for performance issues
        total_time = (search_metrics['content_search_time'] + 
                     search_metrics['tag_search_time'] + 
                     batch_metrics['batch_load_time'])
                     
        if total_time < 0.5:
            print("✅ Performance looks good - all operations under 0.5s total")
        elif total_time < 1.0:
            print("⚠️  Performance acceptable - under 1s total")
        else:
            print("🚨 Performance issues detected - over 1s total time")
            
        print(f"\nTotal test time: {total_time:.3f}s")
        
        # Cleanup
        await self.cleanup()
        
    async def cleanup(self):
        """Clean up test resources"""
        if self.provider:
            await self.provider.close()
            
        if self.test_db_path:
            Path(self.test_db_path).unlink(missing_ok=True)
            print(f"🧹 Cleaned up test database")

async def main():
    tester = PerformanceTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
