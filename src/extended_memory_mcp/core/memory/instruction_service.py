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
Instruction Service - Handles instruction building and context analysis.

Responsible for:
- Loading initialization contexts
- Building instruction templates
- Memory state analysis
- Smart context loading
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..instruction_manager import InstructionManager
from .context_repository import ContextRepository

# Personality service removed - functionality deleted
from .tags_repository import TagsRepository

logger = logging.getLogger(__name__)


class InstructionService:
    """
    Handles instruction building and smart context loading.
    Orchestrates memory components for session initialization.
    """

    def __init__(
        self,
        context_repository: ContextRepository,
        tags_repository: TagsRepository,
        custom_instruction_path: Optional[str] = None,
    ):
        self.context_repo = context_repository
        self.tags_repo = tags_repository

        # Initialize instruction manager
        instructions_dir = Path(__file__).parent.parent.parent / "config" / "instructions"
        self.instruction_manager = InstructionManager(str(instructions_dir))

        # Set custom instruction path if provided
        if custom_instruction_path:
            self.instruction_manager.set_custom_instruction_path(custom_instruction_path)

    async def load_init_contexts(
        self, project_id: Optional[str] = None, limit: int = 30
    ) -> Dict[str, Any]:
        """
        Load contexts for session initialization with instruction and personality.

        Returns:
            Dictionary with init_instruction and contexts
        """
        try:
            # Load regular contexts using smart loading
            contexts = await self.load_smart_contexts(project_id, limit)

            # Generate instruction context for templating
            await self._create_instruction_context(project_id, contexts)

            # Load and render instruction template
            template_content = await self.instruction_manager.load_init_instruction(
                project_id=project_id
            )

            return {
                "init_instruction": template_content,
                "contexts": contexts,
                "metadata": {
                    "total_contexts": len(contexts),
                    "project_id": project_id,
                },
            }

        except Exception as e:
            logger.error(f"Failed to load init contexts: {e}")
            # Fallback to just contexts
            contexts = await self.load_smart_contexts(project_id, limit)
            return {
                "init_instruction": "# Memory System Active\nUse init_load=false for subsequent calls.",
                "contexts": contexts,
                "metadata": {"error": str(e)},
            }

    async def load_smart_contexts(
        self, project_id: Optional[str] = None, limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Smart context loading with importance-based prioritization.

        Returns contexts optimized for session initialization:
        - High importance contexts first
        - Recent activity
        - Diverse context types
        """
        try:
            all_contexts = []

            # 1. High importance contexts (7+) - always include
            high_importance = await self.context_repo.load_contexts(
                project_id=project_id, importance_min=7, limit=15
            )
            all_contexts.extend(high_importance)

            # 2. Recent contexts (last 7 days) with medium importance (4+)
            recent_contexts = await self.context_repo.load_contexts(
                project_id=project_id, importance_min=4, limit=20
            )

            # Filter for recent contexts not already included
            recent_cutoff = datetime.now() - timedelta(days=7)
            for context in recent_contexts:
                if context not in all_contexts:
                    try:
                        created_at = datetime.fromisoformat(context["created_at"])
                        if created_at >= recent_cutoff:
                            all_contexts.append(context)
                    except (ValueError, TypeError):
                        # Skip contexts with invalid dates
                        continue

            # 3. Load tags for all contexts
            for context in all_contexts:
                context["tags"] = await self.tags_repo.load_context_tags(context["id"])

            # 4. Sort by recency only (newest first), limit to requested amount
            all_contexts.sort(key=lambda x: x["created_at"], reverse=True)

            final_contexts = all_contexts[:limit]

            logger.info(f"Smart loaded {len(final_contexts)} contexts for project {project_id}")
            return final_contexts

        except Exception as e:
            logger.error(f"Failed to smart load contexts: {e}")
            return []

    async def _create_instruction_context(
        self,
        project_id: Optional[str],
        contexts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate instruction context for templating"""
        try:
            # Analyze available tags from contexts
            all_tags = set()
            for context in contexts:
                if "tags" in context and context["tags"]:
                    all_tags.update(context["tags"])

            # Get popular tags for navigation suggestions
            popular_tags = await self.tags_repo.get_popular_tags(limit=15)

            return {
                "available_tags": list(all_tags),
                "popular_tags": popular_tags,
                "total_contexts": len(contexts),
            }

        except Exception as e:
            logger.error(f"Failed to create instruction context: {e}")
            return {}

    async def analyze_memory_state(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Analyze current memory state for instruction templating"""
        try:
            # Get basic stats
            total_contexts = await self.context_repo.count_contexts(project_id)

            # Check for recent activity (last 24 hours)
            recent_contexts = await self.context_repo.load_contexts(project_id=project_id, limit=5)

            has_recent = False
            last_activity = None

            if recent_contexts:
                latest_context = recent_contexts[0]
                last_activity = latest_context.get("created_at")

                try:
                    latest_time = datetime.fromisoformat(last_activity)
                    cutoff_time = datetime.now() - timedelta(hours=24)
                    has_recent = latest_time >= cutoff_time
                except (ValueError, TypeError):
                    has_recent = False

            return {
                "has_contexts": total_contexts > 0,
                "total_contexts": total_contexts,
                "has_recent_contexts": has_recent,
                "last_activity_date": (
                    datetime.fromisoformat(last_activity) if last_activity else None
                ),
                "project_guidance": "",  # Could be loaded from project-specific config
            }

        except Exception as e:
            logger.error(f"Failed to analyze memory state: {e}")
            return {}

    async def load_init_contexts_enhanced(
        self, project_id: Optional[str] = None, limit: int = 30
    ) -> Dict[str, Any]:
        """
        Enhanced version that uses instruction_manager for better templating.
        Returns complete init package: instruction + contexts
        """
        try:
            # Load regular contexts
            contexts = await self.load_smart_contexts(project_id, limit)

            # Analyze memory state for instruction templating
            memory_state = await self.analyze_memory_state(project_id)

            # Load and render instruction using the manager
            init_instruction = await self.instruction_manager.load_init_instruction(
                project_id=project_id, memory_state=memory_state
            )

            result = {
                "init_instruction": init_instruction,
                "contexts": contexts,
                "memory_state": memory_state,
                "metadata": {
                    "total_contexts": len(contexts),
                    "project_id": project_id,
                    "memory_analysis": memory_state,
                },
            }

            logger.info(
                f"Enhanced init contexts loaded for project {project_id}: {len(contexts)} contexts"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to load enhanced init contexts: {e}")
            # Fallback to basic loading
            return await self.load_init_contexts(project_id, limit)
