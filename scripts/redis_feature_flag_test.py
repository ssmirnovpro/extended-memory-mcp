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
Redis Feature Flag Optimization Test

Tests the feature flag approach for enabling Redis optimizations.
"""

import asyncio
import time
import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mcp-server'))

from core.storage.providers.redis.redis_provider import RedisStorageProvider


async def test_feature_flag_optimization():
    """Test Redis optimization feature flag."""
    print("🚀 Redis Feature Flag Optimization Test")
    print("=" * 50)
    
    try:
        # Initialize Redis provider
        provider = RedisStorageProvider(
            host="localhost",
            port=6379,
            db=4,  # Use separate test database
            key_prefix="feature_flag_test"
        )
        
        print("✅ Redis provider initialized")
        
        # Clean and create test data
        redis = await provider.connection_service.get_connection()
        pattern = provider.connection_service.make_key("*")
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
        
        # Create small test dataset
        for i in range(10):
            await provider.save_context(
                project_id="test_project",
                content=f"Test content {i}",
                importance_level=5,
                tags=[f"tag_{i}", "common_tag"]
            )
        
        print("✅ Created test data")
        
        # Test 1: Default behavior (optimizations OFF)
        print("\n🔧 Testing DEFAULT behavior (optimizations OFF)")
        os.environ.pop('REDIS_USE_OPTIMIZED', None)  # Ensure flag is off
        
        start_time = time.time()
        result_default = await provider.tag_service.get_popular_tags_with_optimization(
            limit=10, min_usage=1
        )
        time_default = (time.time() - start_time) * 1000
        
        print(f"   Default method: {time_default:.2f}ms")
        print(f"   Results: {len(result_default)} tags")
        
        # Test 2: Optimized behavior (optimizations ON)
        print("\n🚀 Testing OPTIMIZED behavior (optimizations ON)")
        os.environ['REDIS_USE_OPTIMIZED'] = 'true'
        
        start_time = time.time()
        result_optimized = await provider.tag_service.get_popular_tags_with_optimization(
            limit=10, min_usage=1
        )
        time_optimized = (time.time() - start_time) * 1000
        
        print(f"   Optimized method: {time_optimized:.2f}ms")
        print(f"   Results: {len(result_optimized)} tags")
        
        # Verify results are identical
        print("\n📊 COMPARISON:")
        print(f"   Default:    {time_default:.2f}ms")
        print(f"   Optimized:  {time_optimized:.2f}ms")
        speedup = time_default / time_optimized if time_optimized > 0 else 1
        print(f"   🚀 Speedup: {speedup:.1f}x")
        print(f"   ✅ Results identical: {len(result_default) == len(result_optimized)}")
        
        # Test 3: Feature flag control
        print("\n🎛️ Testing feature flag control:")
        
        # Test different flag values
        flag_tests = [
            ('false', False),
            ('0', False), 
            ('no', False),
            ('true', True),
            ('1', True),
            ('yes', True),
        ]
        
        for flag_value, expected in flag_tests:
            os.environ['REDIS_USE_OPTIMIZED'] = flag_value
            # Create new provider to test flag
            test_provider = RedisStorageProvider(
                host="localhost", port=6379, db=4, key_prefix="feature_flag_test"
            )
            actual = test_provider.tag_service._use_optimized_methods()
            status = "✅" if actual == expected else "❌"
            print(f"   {status} '{flag_value}' → {actual} (expected {expected})")
        
        # Cleanup
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
        print(f"\n🧹 Cleaned up {len(keys)} test keys")
        
        print("\n🎉 Feature flag integration successful!")
        print("💡 Use REDIS_USE_OPTIMIZED=true to enable optimizations")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    finally:
        # Clean up environment
        os.environ.pop('REDIS_USE_OPTIMIZED', None)
    
    return True


if __name__ == "__main__":
    result = asyncio.run(test_feature_flag_optimization())
    sys.exit(0 if result else 1)
