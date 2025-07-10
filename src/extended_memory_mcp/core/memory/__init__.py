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
Memory module - Clean Architecture implementation.

This module provides a refactored version of the monolithic memory_manager.py
split into focused components following Single Responsibility Principle.

Main entry point: MemoryFacade (replaces MemoryManager)
"""

from .context_repository import ContextRepository
from .database_manager import DatabaseManager
from .instruction_service import InstructionService
from .memory_facade import MemoryFacade

# Personality service removed - functionality deleted
from .services.analytics_service import AnalyticsService
from .tags_repository import TagsRepository

# Export facade as manager alias
MemoryManager = MemoryFacade

__all__ = [
    "MemoryFacade",
    "MemoryManager",  # Backward compatibility alias
    "DatabaseManager",
    "ContextRepository",
    "TagsRepository",
    "InstructionService",
    "AnalyticsService",
]
