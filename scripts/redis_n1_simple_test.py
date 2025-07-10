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
Simple Redis N+1 Performance Test

Quick test to demonstrate N+1 issues in current Redis implementation.
"""

import asyncio
import time
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mcp-server'))

from core.storage.providers.redis.redis_provider import RedisStorageProvider


async def test_redis_n1_issues():
    """Demonstrate Redis N+1 performance issues."""
    print("🚀 Redis N+1 Performance Issues Demonstration")
    print("=" * 50)
    
    try:
        # Initialize Redis provider
        provider = RedisStorageProvider(
            host="localhost",
            port=6379,
            db=1,  # Use test database
            key_prefix="n1_test"
        )
        
        print("✅ Redis provider initialized")
        
        # Clear test data
        redis = await provider.connection_service.get_connection()
        pattern = provider.connection_service.make_key("*")
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
            print(f"🧹 Cleaned up {len(keys)} old test keys")
        
        # Create test data - 10 tags with 5 contexts each
        print("📊 Creating test data...")
        
        for tag_idx in range(10):
            tag_name = f"test_tag_{tag_idx}"
            
            for ctx_idx in range(5):
                context_id = await provider.save_context(
                    project_id="test_project",
                    content=f"Test content for tag {tag_name}, context {ctx_idx}",
                    importance_level=5,
                    tags=[tag_name, "common_tag"]
                )
        
        print("✅ Created 50 test contexts with 10 tags")
        
        # Test 1: get_popular_tags N+1 issue
        print("\n🔍 Testing get_popular_tags() N+1 performance...")
        
        start_time = time.time()
        popular_tags = await provider.tag_service.get_popular_tags(limit=10, min_usage=2)
        execution_time = time.time() - start_time
        
        print(f"⏱️  Execution time: {execution_time * 1000:.2f}ms")
        print(f"📊 Results: {len(popular_tags)} tags")
        print(f"🔢 Estimated Redis operations: ~{10 + 10 * 5} (1 KEYS + 10 LRANGE + 50 GET for project filter)")
        
        # Test 2: find_contexts_by_multiple_tags N+1 issue
        print("\n🔍 Testing find_contexts_by_multiple_tags() N+1 performance...")
        
        start_time = time.time()
        context_ids = await provider.tag_service.find_contexts_by_multiple_tags(
            tags=["test_tag_0", "test_tag_1", "test_tag_2"],
            limit=20,
            project_id="test_project"
        )
        execution_time = time.time() - start_time
        
        print(f"⏱️  Execution time: {execution_time * 1000:.2f}ms")
        print(f"📊 Results: {len(context_ids)} contexts")
        print(f"🔢 Estimated Redis operations: ~{3 + len(context_ids)} (3 LRANGE + {len(context_ids)} GET for project filter)")
        
        # Test 3: load_contexts with tags_filter N+1 issue
        print("\n🔍 Testing load_contexts() with tags_filter N+1 performance...")
        
        start_time = time.time()
        contexts = await provider.load_contexts(
            project_id="test_project",
            limit=15,
            tags_filter=["test_tag_0", "test_tag_1"]
        )
        execution_time = time.time() - start_time
        
        print(f"⏱️  Execution time: {execution_time * 1000:.2f}ms")
        print(f"📊 Results: {len(contexts)} contexts")
        print(f"🔢 Estimated Redis operations: Inherited from find_contexts_by_multiple_tags + 1 MGET")
        
        # Summary
        print("\n" + "=" * 50)
        print("🎯 N+1 ISSUES SUMMARY:")
        print("=" * 50)
        print("❌ get_popular_tags: 1 + N_tags + N_contexts operations")
        print("❌ find_contexts_by_multiple_tags: N_tags + N_contexts operations")
        print("❌ load_contexts with tags_filter: Inherits above N+1 issues")
        print("\n✅ Expected after optimization: 2-3 operations per method")
        print("🚀 Potential speedup: 8-10x (similar to SQLite fixes)")
        
        # Cleanup
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
        print(f"\n🧹 Cleaned up {len(keys)} test keys")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    return True


if __name__ == "__main__":
    result = asyncio.run(test_redis_n1_issues())
    sys.exit(0 if result else 1)
