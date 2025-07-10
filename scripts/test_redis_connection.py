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
Quick Redis Connection Test

Tests if Redis is available and working for benchmarks.
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mcp-server'))

from core.storage.providers.redis.redis_provider import RedisStorageProvider


async def test_redis_connection():
    """Test Redis connection and basic operations."""
    try:
        print("🔍 Testing Redis connection...")
        
        # Initialize Redis provider
        provider = RedisStorageProvider(
            host="localhost",
            port=6379,
            db=1,  # Use test database
            key_prefix="connection_test"
        )
        
        print("✅ Redis provider initialized")
        
        # Test basic operations
        redis = await provider.connection_service.get_connection()
        
        # Test ping
        result = await redis.ping()
        print(f"✅ Redis ping successful: {result}")
        
        # Test basic set/get
        test_key = provider.connection_service.make_key("test", "connection")
        await redis.set(test_key, "test_value")
        value = await redis.get(test_key)
        await redis.delete(test_key)
        
        print(f"✅ Redis set/get/delete successful: {value}")
        
        print("🎉 Redis is ready for benchmarking!")
        return True
        
    except ImportError as e:
        print(f"❌ Redis library not available: {e}")
        print("💡 Install with: pip install 'redis[hiredis]>=4.5.0'")
        return False
        
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("💡 Make sure Redis is running on localhost:6379")
        print("💡 You can start Redis with: redis-server")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_redis_connection())
    sys.exit(0 if result else 1)
