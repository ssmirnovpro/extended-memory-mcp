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
Summary Formatter
Handles generation of human-readable context summaries
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


class ContextSummaryFormatter:
    """Formats context data into human-readable summaries"""

    def __init__(self):
        # Configuration for summary generation
        self.critical_types = ["preference", "decision"]
        self.high_importance_threshold = 8
        self.recent_hours_threshold = 24
        self.max_length_critical = 500
        self.max_length_normal = 200

    def generate_summary(
        self, contexts: List[Dict[str, Any]], project_id: Optional[str], limit: Optional[int] = None
    ) -> str:
        """Generate human-readable summary of loaded contexts with smart loading stats"""
        if not contexts:
            return f"No saved context found for project {project_id or 'global'}."

        # Analyze contexts
        analysis = self._analyze_contexts(contexts)

        # Build summary header
        header = self._build_summary_header(contexts, project_id, analysis, limit)

        return header

    def _analyze_contexts(self, contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze contexts for grouping and statistics"""
        high_importance = 0
        recent_items = 0

        # Calculate 24h threshold
        recent_threshold = datetime.now() - timedelta(hours=self.recent_hours_threshold)

        for ctx in contexts:
            importance = ctx.get("importance_level", 0)
            created_at = ctx.get("created_at", "")

            # Count high importance
            if importance >= self.high_importance_threshold:
                high_importance += 1

            # Check if item is from last 24h
            if created_at:
                try:
                    item_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    if item_time.replace(tzinfo=None) > recent_threshold:
                        recent_items += 1
                except Exception:
                    logger.warning(
                        f"Could not parse created_at timestamp for context {context.get('id')}: {e}"
                    )

        return {
            "high_importance": high_importance,
            "recent_items": recent_items,
        }

    def _build_summary_header(
        self,
        contexts: List[Dict[str, Any]],
        project_id: Optional[str],
        analysis: Dict[str, Any],
        limit: Optional[int] = None,
    ) -> str:
        """Build summary header with statistics"""
        # Determine if we hit the limit or found all available contexts
        if limit and len(contexts) == limit:
            verb = "Loaded only"  # Hit the limit, might be more contexts available
        else:
            verb = "Found"  # Got all available contexts (less than limit or no limit)

        summary_parts = [f"{verb} {len(contexts)} saved contexts"]

        if project_id:
            summary_parts.append(f"for project '{project_id}'")

        # Add smart details
        smart_details = []
        if analysis["recent_items"] > 0:
            smart_details.append(
                f"{analysis['recent_items']} from last {self.recent_hours_threshold}h"
            )
        if analysis["high_importance"] > 0:
            smart_details.append(f"{analysis['high_importance']} high-importance")

        if smart_details:
            summary_parts.append(f"including {', '.join(smart_details)}")

        header = " ".join(summary_parts) + "."
        return header

    def _format_context_items(self, contexts: List[Dict[str, Any]]) -> List[str]:
        """Format individual context items for display in chronological order"""
        # Sort contexts chronologically (oldest first, like a chat log)
        sorted_contexts = sorted(
            contexts,
            key=lambda x: x.get("created_at", ""),
            reverse=False,  # Chronological order: oldest first
        )

        content_parts = []
        for ctx in sorted_contexts:  # Remove enumeration completely
            content = ctx.get("content", "").strip()
            created_at = ctx.get("created_at", "")

            # Format creation date
            date_str = self._format_creation_date(created_at)

            # Standard truncation
            content = self._truncate_content(content, "general")

            content_parts.append(f"**•** {content}{date_str}")

        return content_parts

    def _format_creation_date(self, created_at: str) -> str:
        """Format creation date for display"""
        if not created_at:
            return ""

        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            return f" ({dt.strftime('%m-%d %H:%M')})"
        except Exception:
            return ""

    def _truncate_content(self, content: str, ctx_type: str) -> str:
        """Truncate content based on context type importance"""
        max_length = (
            self.max_length_critical if ctx_type in self.critical_types else self.max_length_normal
        )

        if len(content) > max_length:
            return content[:max_length] + "..."

        return content


# Factory function for easy import
def create_summary_formatter() -> ContextSummaryFormatter:
    """Create a new context summary formatter instance"""
    return ContextSummaryFormatter()
