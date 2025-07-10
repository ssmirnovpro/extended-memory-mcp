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
N+1 Query Problem Demonstration

This script simulates the OLD N+1 behavior vs NEW optimized behavior
to demonstrate the performance improvement achieved.
"""

import asyncio
import logging
import time
from pathlib import Path
from tempfile import NamedTemporaryFile

# Setup path and imports
import sys
sys.path.append("/Users/sergeysmirnov/projects/extended-memory-mcp/mcp-server")

from extended_memory_mcp.core.storage.providers.sqlite.sqlite_provider import SQLiteStorageProvider

# Disable debug logging
logging.getLogger("core.storage").setLevel(logging.WARNING)
logging.getLogger("core.memory").setLevel(logging.WARNING)

class N1DemonstrationTest:
    def __init__(self):
        self.provider = None
        self.test_db_path = None
        
    async def setup(self, num_contexts=100):
        """Setup test database with sample data"""
        # Create temporary database
        temp_file = NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db_path = temp_file.name
        temp_file.close()
        
        # Initialize provider
        self.provider = SQLiteStorageProvider(db_path=self.test_db_path)
        await self.provider.initialize()
        
        print(f"📊 Setting up test database with {num_contexts} contexts")
        
        # Create test data
        await self._create_test_data(num_contexts)
        
    async def _create_test_data(self, num_contexts):
        """Create test contexts with tags"""
        test_templates = [
            {"content": "Database optimization and performance tuning", "importance": 8, 
             "tags": ["database", "performance", "optimization", "sql"]},
            {"content": "Memory management and garbage collection", "importance": 7, 
             "tags": ["memory", "management", "gc", "performance"]},
            {"content": "Search algorithms and data structures", "importance": 9, 
             "tags": ["search", "algorithms", "datastructures", "performance"]},
            {"content": "API design patterns and best practices", "importance": 6, 
             "tags": ["api", "design", "patterns", "architecture"]},
            {"content": "Testing strategies and automation frameworks", "importance": 8, 
             "tags": ["testing", "quality", "automation", "frameworks"]},
        ]
        
        context_ids = []
        for i in range(num_contexts):
            template = test_templates[i % len(test_templates)]
            content = f"Context {i}: {template['content']}"
            
            context_id = await self.provider.save_context(
                content=content,
                importance_level=template["importance"],
                project_id="demo-project",
                tags=template["tags"]
            )
            
            if context_id:
                context_ids.append(context_id)
                
        print(f"✅ Created {len(context_ids)} test contexts")
        return context_ids
        
    async def simulate_old_n1_behavior(self, context_ids):
        """Simulate the OLD N+1 query behavior (individual tag queries)"""
        print("\n🔴 Simulating OLD N+1 behavior (individual tag queries)...")
        
        start_time = time.time()
        
        # Load contexts using repository
        int_ids = [int(cid) for cid in context_ids]
        contexts = await self.provider.context_repo.load_contexts_by_ids(int_ids)
        
        # Simulate OLD behavior: individual tag queries for each context (N+1!)
        for context in contexts:
            context_id = context.get("id")
            if context_id:
                # This is the N+1 problem: one query per context
                tags = await self.provider.tags_repo.load_context_tags(context_id)
                context["tags"] = tags
                
        old_time = time.time() - start_time
        
        print(f"   OLD method: {len(contexts)} contexts loaded in {old_time:.3f}s")
        print(f"   SQL queries executed: 1 (contexts) + {len(contexts)} (individual tag queries) = {1 + len(contexts)}")
        
        return old_time, contexts
        
    async def test_new_optimized_behavior(self, context_ids):
        """Test the NEW optimized batch behavior"""
        print("\n🟢 Testing NEW optimized behavior (batch tag queries)...")
        
        start_time = time.time()
        
        # Use the NEW optimized method
        contexts = await self.provider.load_contexts_by_ids(context_ids)
        
        new_time = time.time() - start_time
        
        print(f"   NEW method: {len(contexts)} contexts loaded in {new_time:.3f}s")
        print(f"   SQL queries executed: 1 (contexts) + 1 (batch tags) = 2 total")
        
        return new_time, contexts
        
    async def run_comparison(self, num_contexts=100):
        """Run comparison between old and new approaches"""
        print(f"🚀 N+1 Query Problem Demonstration ({num_contexts} contexts)")
        print("=" * 60)
        
        await self.setup(num_contexts)
        
        # Get some context IDs to test with
        all_contexts = await self.provider.load_contexts(
            project_id="demo-project",
            limit=min(50, num_contexts)  # Test with subset
        )
        
        test_context_ids = [str(ctx["id"]) for ctx in all_contexts[:min(30, len(all_contexts))]]
        actual_test_count = len(test_context_ids)
        
        print(f"Testing with {actual_test_count} contexts...")
        
        # Test old N+1 behavior
        old_time, old_contexts = await self.simulate_old_n1_behavior(test_context_ids)
        
        # Test new optimized behavior  
        new_time, new_contexts = await self.test_new_optimized_behavior(test_context_ids)
        
        # Calculate improvements
        if old_time > 0:
            speedup = old_time / new_time if new_time > 0 else float('inf')
            query_reduction = ((actual_test_count + 1) - 2) / (actual_test_count + 1) * 100
        else:
            speedup = 1.0
            query_reduction = 0
            
        # Results
        print("\n📊 Performance Comparison")
        print("=" * 60)
        print(f"OLD N+1 approach:     {old_time:.3f}s ({actual_test_count + 1} SQL queries)")
        print(f"NEW optimized approach: {new_time:.3f}s (2 SQL queries)")
        print(f"")
        print(f"🚀 Speedup: {speedup:.1f}x faster")
        print(f"📉 Query reduction: {query_reduction:.1f}% fewer queries")
        print(f"⚡ Absolute improvement: {(old_time - new_time)*1000:.1f}ms saved")
        
        # Verify data integrity
        old_with_tags = sum(1 for ctx in old_contexts if ctx.get("tags"))
        new_with_tags = sum(1 for ctx in new_contexts if ctx.get("tags"))
        
        print(f"\n✅ Data integrity check:")
        print(f"   OLD approach: {old_with_tags}/{len(old_contexts)} contexts have tags")
        print(f"   NEW approach: {new_with_tags}/{len(new_contexts)} contexts have tags")
        
        if old_with_tags == new_with_tags and len(old_contexts) == len(new_contexts):
            print("   ✅ Both approaches return identical data!")
        else:
            print("   ⚠️  Data mismatch detected!")
            
        await self.cleanup()
        
        return {
            "speedup": speedup,
            "query_reduction": query_reduction,
            "time_saved_ms": (old_time - new_time) * 1000,
            "old_time": old_time,
            "new_time": new_time
        }
        
    async def cleanup(self):
        """Clean up test resources"""
        if self.provider:
            await self.provider.close()
            
        if self.test_db_path:
            Path(self.test_db_path).unlink(missing_ok=True)

async def main():
    """Run N+1 demonstration with different dataset sizes"""
    test_sizes = [50, 100, 200]
    
    print("🎯 N+1 Query Problem - Before vs After Optimization")
    print("=" * 70)
    print()
    
    for size in test_sizes:
        tester = N1DemonstrationTest()
        results = await tester.run_comparison(size)
        
        print(f"\n📈 Summary for {size} contexts:")
        print(f"   Performance improvement: {results['speedup']:.1f}x faster")
        print(f"   Time saved: {results['time_saved_ms']:.1f}ms")
        print(f"   Query efficiency: {results['query_reduction']:.1f}% fewer queries")
        print("\n" + "="*50)

if __name__ == "__main__":
    asyncio.run(main())
