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
Storage abstraction layer for Extended Memory MCP.

Provides abstract storage interface with multiple provider implementations:
- SQLite (default)
- Redis (key-value) - coming soon
- PostgreSQL (future)
- MongoDB (future)
"""

from .interfaces.storage_provider import IStorageProvider
from .providers.sqlite.sqlite_provider import SQLiteStorageProvider
from .storage_factory import StorageFactory, get_storage_provider

# from .providers.redis.redis_provider import RedisStorageProvider  # Temporarily disabled

__all__ = [
    "IStorageProvider",
    "StorageFactory",
    "get_storage_provider",
    "SQLiteStorageProvider",
    # 'RedisStorageProvider'
]
