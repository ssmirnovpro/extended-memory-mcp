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
Analytics Service - Handles statistics and memory analysis.

Responsible for:
- Database statistics and monitoring
- Memory usage analytics
- Performance metrics
- Trend analysis
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..context_repository import ContextRepository
from ..database_manager import DatabaseManager
from ..tags_repository import TagsRepository

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Provides analytics and statistics for the memory system.
    Helps monitor usage patterns and system health.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        context_repository: ContextRepository,
        tags_repository: TagsRepository,
    ):
        self.db_manager = db_manager
        self.context_repo = context_repository
        self.tags_repo = tags_repository

    async def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics for monitoring"""
        try:
            async with self.db_manager.get_connection() as db:
                # Basic counts
                cursor = await db.execute("SELECT COUNT(*) FROM contexts WHERE status = 'active'")
                active_contexts = (await cursor.fetchone())[0]
                # Get unique project count from contexts
                cursor = await db.execute(
                    "SELECT COUNT(DISTINCT project_id) FROM contexts WHERE project_id IS NOT NULL"
                )
                active_projects = (await cursor.fetchone())[0]

                cursor = await db.execute("SELECT COUNT(*) FROM tags")
                total_tags = (await cursor.fetchone())[0]

                # Database file size
                db_size = (
                    os.path.getsize(self.db_manager.db_path)
                    if os.path.exists(self.db_manager.db_path)
                    else 0
                )

                # Date range of contexts
                cursor = await db.execute(
                    """
                    SELECT MIN(created_at) as oldest, MAX(created_at) as newest
                    FROM contexts WHERE status = 'active'
                """
                )
                row = await cursor.fetchone()
                oldest_context = row[0] if row[0] else None
                newest_context = row[1] if row[1] else None

                # Context type distribution - using tags instead of context_type
                cursor = await db.execute(
                    """
                    SELECT 'context' as type, COUNT(*) as count
                    FROM contexts WHERE status = 'active'
                """
                )
                row = await cursor.fetchone()
                type_distribution = [{"type": "context", "count": row[1] if row else 0}]

                # Importance distribution
                cursor = await db.execute(
                    """
                    SELECT importance_level, COUNT(*) as count
                    FROM contexts WHERE status = 'active'
                    GROUP BY importance_level
                    ORDER BY importance_level DESC
                """
                )
                importance_distribution = [
                    {"level": row[0], "count": row[1]} for row in await cursor.fetchall()
                ]

                return {
                    "active_contexts": active_contexts,
                    "active_projects": active_projects,
                    "total_tags": total_tags,
                    "database_size_bytes": db_size,
                    "database_size_mb": round(db_size / (1024 * 1024), 2),
                    "oldest_context": oldest_context,
                    "newest_context": newest_context,
                    "database_path": self.db_manager.db_path,
                    "context_types": type_distribution,
                    "importance_levels": importance_distribution,
                }

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}

    async def get_memory_stats(
        self, project_id: Optional[str] = None, limit: int = 30
    ) -> Dict[str, Any]:
        """Get comprehensive memory statistics for a project or globally"""
        try:
            # Basic context stats
            total_contexts = await self.context_repo.count_contexts(project_id)
            contexts = await self.context_repo.load_contexts(project_id=project_id, limit=limit)

            # Calculate averages
            if contexts:
                avg_importance = sum(c["importance_level"] for c in contexts) / len(contexts)
                latest_context = contexts[0]["created_at"]
            else:
                avg_importance = 0
                latest_context = None

            # Context breakdown for this project
            all_contexts = await self.context_repo.load_contexts(project_id=project_id, limit=200)

            # Using tags for categorization instead of context_type
            tag_counts = {}
            importance_counts = {}

            for context in all_contexts:
                # Count by tags
                tags = context.get("tags", [])
                if tags:
                    for tag in tags:
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1
                else:
                    tag_counts["untagged"] = tag_counts.get("untagged", 0) + 1

                # Count by importance
                importance = context.get("importance_level", 0)
                importance_counts[importance] = importance_counts.get(importance, 0) + 1

            # Get popular tags for this project
            popular_tags = await self.tags_repo.get_popular_tags(limit=10)

            # Recent activity (last 7 days)
            recent_cutoff = datetime.now() - timedelta(days=7)
            recent_count = 0

            for context in all_contexts:
                try:
                    created_at = datetime.fromisoformat(context["created_at"])
                    if created_at >= recent_cutoff:
                        recent_count += 1
                except (ValueError, TypeError):
                    continue

            return {
                "project_id": project_id,
                "total_contexts": total_contexts,
                "contexts_loaded": len(contexts),
                "avg_importance": round(avg_importance, 2),
                "latest_context": latest_context,
                "tag_distribution": [{"tag": k, "count": v} for k, v in tag_counts.items()],
                "importance_levels": [
                    {"level": k, "count": v} for k, v in importance_counts.items()
                ],
                "popular_tags": popular_tags,
                "recent_activity_7d": recent_count,
                "memory_stats": {
                    "contexts_analyzed": len(all_contexts),
                    "has_recent_activity": recent_count > 0,
                    "diversity_score": len(tag_counts),  # Number of different tags
                },
            }

        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {"memory_stats": {"error": str(e)}}

    async def analyze_tag_patterns(self, limit: int = 50) -> Dict[str, Any]:
        """
        Analyze tags from recent contexts to show available navigation options.
        Uses normalized tags schema for efficient querying.
        """
        try:
            async with self.db_manager.get_connection() as db:
                # Get tag usage patterns with context information
                cursor = await db.execute(
                    """
                    SELECT
                        t.name,
                        COUNT(ct.context_id) as usage_count,
                        AVG(c.importance_level) as avg_importance,
                        MAX(c.created_at) as latest_usage,
                        COUNT(DISTINCT c.project_id) as project_count
                    FROM tags t
                    JOIN context_tags ct ON t.id = ct.tag_id
                    JOIN contexts c ON ct.context_id = c.id
                    WHERE c.status = 'active'
                    GROUP BY t.id, t.name
                    ORDER BY usage_count DESC, latest_usage DESC
                    LIMIT ?
                """,
                    (limit,),
                )

                tag_rows = await cursor.fetchall()

                # Get project-specific tag distribution
                cursor = await db.execute(
                    """
                    SELECT
                        c.project_id,
                        t.name,
                        COUNT(*) as count
                    FROM contexts c
                    JOIN context_tags ct ON c.id = ct.context_id
                    JOIN tags t ON ct.tag_id = t.id
                    WHERE c.status = 'active' AND c.project_id IS NOT NULL
                    GROUP BY c.project_id, t.name
                    ORDER BY c.project_id, count DESC
                """
                )

                project_tag_rows = await cursor.fetchall()

                # Process results
                tag_analysis = []
                for row in tag_rows:
                    tag_analysis.append(
                        {
                            "tag": row[0],
                            "usage_count": row[1],
                            "avg_importance": round(row[2], 2),
                            "latest_usage": row[3],
                            "project_count": row[4],
                        }
                    )

                # Group project tags
                project_tags = {}
                for row in project_tag_rows:
                    project_id = row[0]
                    if project_id not in project_tags:
                        project_tags[project_id] = []
                    project_tags[project_id].append({"tag": row[1], "count": row[2]})

                return {
                    "tag_analysis": tag_analysis,
                    "project_tags": project_tags,
                    "total_unique_tags": len(tag_analysis),
                    "analysis_timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(f"Failed to analyze tags: {e}")
            return {"error": "Tag analysis unavailable"}

    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health metrics"""
        try:
            # Database stats
            db_stats = await self.get_database_stats()

            # Check for potential issues
            issues = []
            recommendations = []

            # Check database size
            if db_stats.get("database_size_mb", 0) > 100:
                issues.append("Large database size (>100MB)")
                recommendations.append("Consider archiving old contexts")

            # Check for orphaned data
            async with self.db_manager.get_connection() as db:
                # Check for contexts without tags
                cursor = await db.execute(
                    """
                    SELECT COUNT(*) FROM contexts c
                    LEFT JOIN context_tags ct ON c.id = ct.context_id
                    WHERE ct.context_id IS NULL AND c.status = 'active'
                """
                )
                untagged_contexts = (await cursor.fetchone())[0]

                if untagged_contexts > db_stats.get("active_contexts", 0) * 0.3:
                    issues.append(f"Many contexts without tags ({untagged_contexts})")
                    recommendations.append("Consider adding tags to improve searchability")

                # Check for unused tags
                cursor = await db.execute(
                    """
                    SELECT COUNT(*) FROM tags t
                    LEFT JOIN context_tags ct ON t.id = ct.tag_id
                    WHERE ct.tag_id IS NULL
                """
                )
                unused_tags = (await cursor.fetchone())[0]

                if unused_tags > 10:
                    issues.append(f"Unused tags found ({unused_tags})")
                    recommendations.append("Run tag cleanup to optimize storage")

            # Performance scoring
            health_score = 100
            if len(issues) > 0:
                health_score -= len(issues) * 15
            health_score = max(0, health_score)

            status = (
                "excellent"
                if health_score >= 90
                else "good" if health_score >= 70 else "needs_attention"
            )

            return {
                "health_score": health_score,
                "status": status,
                "database_stats": db_stats,
                "issues": issues,
                "recommendations": recommendations,
                "metrics": {"untagged_contexts": untagged_contexts, "unused_tags": unused_tags},
                "last_check": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {"health_score": 0, "status": "error", "error": str(e)}
