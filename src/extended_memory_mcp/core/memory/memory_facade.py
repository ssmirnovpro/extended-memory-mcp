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
Memory Facade - Slim coordinator that delegates to domain services.

This is the primary entry point for all memory operations.
Maintains backward compatibility while delegating to specialized domain services.
"""

import logging
from typing import Any, Dict, List, Optional

from .database_manager import DatabaseManager
from .instruction_service import InstructionService

# Personality service removed - functionality deleted
from .services import AnalyticsService, ContextService

logger = logging.getLogger(__name__)


class MemoryFacade:
    """
    Slim memory facade that coordinates domain services.

    Provides the same public API while delegating to specialized domain services.
    This maintains backward compatibility while improving internal architecture.
    """

    def __init__(
        self, db_path: Optional[str] = None, custom_instruction_path: Optional[str] = None
    ):
        """
        Initialize the memory system with all domain services.

        Args:
            db_path: Database path (uses default if None)
            custom_instruction_path: Custom instruction template path
        """
        # Initialize core infrastructure
        self.db_manager = DatabaseManager(db_path)

        # Initialize domain services
        self.context_service = ContextService(self.db_manager)
        self.analytics_service = AnalyticsService(
            self.db_manager,
            self.context_service.context_repo,
            self.context_service.tags_repo,
        )

        # Initialize application services
        self.instruction_service = InstructionService(
            self.context_service.context_repo,
            self.context_service.tags_repo,
            custom_instruction_path,
        )

        # Store paths for compatibility
        self.db_path = self.db_manager.db_path
        self.custom_instruction_path = custom_instruction_path

    # ==========================================
    # Core Memory Operations (Delegate to ContextService)
    # ==========================================

    async def save_context(
        self,
        content: str,
        importance_level: int,
        project_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[int]:
        """Save context to database with normalized tags."""
        return await self.context_service.save_context(content, importance_level, project_id, tags)

    async def load_contexts(
        self,
        project_id: Optional[str] = None,
        importance_min: int = 1,
        limit: int = 50,
        offset: int = 0,
        search_query: Optional[str] = None,
        tags_filter: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Load contexts with filtering."""
        return await self.context_service.load_contexts(
            project_id, importance_min, limit, offset, search_query, tags_filter
        )

    async def delete_context(self, context_id: int) -> bool:
        """Delete context by ID."""
        return await self.context_service.delete_context(context_id)

    async def get_context_by_id(self, context_id: int) -> Optional[Dict[str, Any]]:
        """Get single context by ID with tags."""
        return await self.context_service.get_context_by_id(context_id)

    async def count_contexts(self, project_id: Optional[str] = None) -> int:
        """Count total contexts, optionally filtered by project."""
        return await self.context_service.count_contexts(project_id)

    async def get_contexts_by_importance(
        self, min_importance: int = 7, limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Load high-importance contexts across all projects."""
        return await self.context_service.get_contexts_by_importance(min_importance, limit)

    # ==========================================
    # Analytics and Statistics (Delegate to AnalyticsService)
    # ==========================================

    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics for monitoring."""
        return await self.analytics_service.get_database_stats()

    async def get_memory_stats(
        self, project_id: Optional[str] = None, limit: int = 30
    ) -> Dict[str, Any]:
        """Get memory statistics for a project or globally."""
        return await self.analytics_service.get_memory_stats(project_id, limit)

    async def analyze_tag_patterns(self, limit: int = 50) -> Dict[str, Any]:
        """Analyze tags from recent contexts to show available navigation options."""
        return await self.analytics_service.analyze_tag_patterns(limit)

    async def get_activity_trends(self, days: int = 30) -> Dict[str, Any]:
        """Analyze activity trends over the specified period."""
        return await self.analytics_service.get_activity_trends(days)

    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health metrics."""
        return await self.analytics_service.get_system_health()

    # ==========================================
    # Instruction and Initialization (Delegate to InstructionService)
    # ==========================================

    async def load_init_contexts(
        self, project_id: Optional[str] = None, limit: int = 30
    ) -> Dict[str, Any]:
        """Load contexts for session initialization with instruction and personality."""
        return await self.instruction_service.load_init_contexts(project_id, limit)

    async def load_smart_contexts(
        self, project_id: Optional[str] = None, limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Smart context loading with importance-based prioritization."""
        return await self.instruction_service.load_smart_contexts(project_id, limit)

    async def load_init_contexts_enhanced(
        self, project_id: Optional[str] = None, limit: int = 30
    ) -> Dict[str, Any]:
        """Enhanced version with better instruction templating."""
        return await self.instruction_service.load_init_contexts_enhanced(project_id, limit)

    # ==========================================
    # ==========================================
    # Analysis and Database Utility Methods
    # ==========================================

    async def _analyze_available_tags(self, project_id: Optional[str] = None) -> str:
        """Analyze available tags for navigation and discovery."""
        return await self.analytics_service.analyze_tag_patterns(limit=50)

    async def _ensure_initialized(self) -> bool:
        """Ensure database is initialized and ready for operations."""
        return await self.db_manager.ensure_database()

    async def initialize_database(self) -> bool:
        """Initialize database with schema if not exists."""
        return await self.db_manager.initialize_database()

    async def _load_context_tags(self, db, context_id: int) -> List[str]:
        """Load tags for a specific context by ID."""
        return await self.context_service.tags_repo.load_context_tags(context_id)

    async def cleanup_unused_tags(self) -> int:
        """Remove tags that are not linked to any contexts."""
        return await self.context_service.tags_repo.cleanup_unused_tags()

    # ==========================================
    # Utility Methods
    # ==========================================

    def get_db_path(self) -> str:
        """Get current database path."""
        return self.db_path
