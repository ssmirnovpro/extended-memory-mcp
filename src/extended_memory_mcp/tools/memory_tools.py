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
Memory Tools Handler
Handles execution of MCP memory-related tools
"""

import logging
from typing import Any, Dict, List, Optional

from extended_memory_mcp.core.errors import (
    MemoryMCPError,
    StorageError,
    ValidationError,
    error_handler,
)
from extended_memory_mcp.core.project_utils import normalize_project_id
from extended_memory_mcp.formatters.summary_formatter import ContextSummaryFormatter


# Default tags configuration
def get_default_tags_config():
    return {
        "popular_tags_limit": 10,
        "popular_tags_min_usage": 2,
        "show_in_responses": True,
        "recent_tags_hours": 24,
        "smart_grouping_popular_threshold": 3,
        "smart_grouping_recent_threshold": 1,
    }


class MemoryToolsHandler:
    """Handles memory-related MCP tools execution"""

    def __init__(
        self, storage_provider, summary_formatter: ContextSummaryFormatter, logger: logging.Logger
    ):
        self.storage_provider = storage_provider
        self.summary_formatter = summary_formatter
        self.logger = logger

        # Current active project (can be switched by Claude)
        self.current_project = None

    async def execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a memory tool and return the result"""

        if tool_name == "save_context":
            return await self.save_context(**tool_args)
        elif tool_name == "load_contexts":
            return await self.load_contexts(**tool_args)
        elif tool_name == "forget_context":
            return await self.forget_context(**tool_args)
        elif tool_name == "list_all_projects":
            return await self.list_all_projects_global()
        elif tool_name == "get_popular_tags":
            return await self.get_popular_tags_tool(**tool_args)
        else:
            raise Exception(f"Unknown tool: {tool_name}")

    # Tool methods will be extracted from server.py in next step
    async def save_context(
        self,
        content: str,
        importance_level: int = 5,
        tags: Optional[List[str]] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        MCP Tool: save_context
        Claude decides all parameters - this is "dumb storage"
        """
        try:
            # Use current_project if no project_id specified
            if project_id is None and hasattr(self, "current_project") and self.current_project:
                project_id = self.current_project

            # Normalize project_id (replace None/empty with "general")
            original_project_id = project_id
            project_id = normalize_project_id(project_id)
            self.logger.info(f"NORMALIZE DEBUG: {original_project_id} → {project_id}")

            # Save to database using storage_provider
            context_id = await self.storage_provider.save_context(
                project_id=project_id,
                content=content,
                importance_level=importance_level,
                tags=tags,
            )

            # Get timestamp for logging
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            self.logger.debug(f"Saved context {context_id} for project {project_id} at {timestamp}")

            # Return text content for Claude Desktop UI
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"✅ Context saved successfully!\n\n📝 **Details:**\n- Context ID: {context_id}\n- Project: {project_id}\n- Importance: {importance_level}/10\n- Saved at: {timestamp} \n- Content: {content[:100]}{'...' if len(content) > 100 else ''}",
                    }
                ]
            }

        except Exception as e:
            # Structured error handling for save_context
            memory_error = error_handler.handle_error(
                e,
                context={
                    "content_length": len(content),
                    "importance_level": importance_level,
                    "project_id": project_id,
                    "tags_count": len(tags) if tags else 0,
                },
                operation="save_context_tool",
            )

            # Return structured error response
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"❌ Error saving context: {memory_error.message}\n\n🔍 **Error Details:**\n- Category: {memory_error.category.value}\n- Severity: {memory_error.severity.value}",
                    }
                ]
            }

    async def load_contexts(
        self,
        project_id: Optional[str] = None,
        importance_level: Optional[int] = None,
        init_load: bool = True,
        limit: int = 30,
        tags_filter: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        MCP Tool: load_contexts
        Load relevant contexts for Claude to use

        Args:
            project_id: Project to load contexts for
            importance_level: Minimum importance level (default: 7)
            init_load: True for session initialization (includes instruction + contexts)
            limit: Maximum number of contexts
            tags_filter: Filter by specific tags using OR logic (list of strings, max 10 tags)
                        Note: When tags_filter is used, init_load is automatically set to false
        """
        try:
            # Normalize project_id (replace None/empty with "general")
            project_id = normalize_project_id(project_id)

            # Set default importance level
            if importance_level is None:
                importance_level = 7

            # Validate and normalize tags_filter
            if tags_filter is not None:
                if not isinstance(tags_filter, list):
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": "❌ Error: tags_filter must be a list of strings",
                            }
                        ]
                    }

                # Normalize tags: remove empty/whitespace, convert to lowercase, limit count
                normalized_tags = []
                for tag in tags_filter:
                    if isinstance(tag, str) and tag.strip():
                        normalized_tags.append(tag.strip().lower())

                # Limit number of tags to prevent performance issues
                if len(normalized_tags) > 10:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": "❌ Error: Maximum 10 tags allowed in tags_filter",
                            }
                        ]
                    }

                tags_filter = normalized_tags if normalized_tags else None

            # Handle string boolean values for init_load
            if isinstance(init_load, str):
                init_load = init_load.lower() not in ("false", "0", "no", "off")

            self.logger.info(f"DEBUG: init_load parameter = {init_load} (type: {type(init_load)})")

            # If tags_filter is provided, override init_load behavior
            if tags_filter:
                self.logger.info(
                    f"DEBUG: tags_filter provided {tags_filter}, using regular load_contexts instead of init_load"
                )

            # Regular context loading (subsequent calls)
            contexts = await self.storage_provider.load_contexts(
                project_id=project_id,
                limit=limit,
                importance_threshold=importance_level,
                tags_filter=tags_filter,
            )

            # Load popular tags for suggestions
            # Load popular tags (optimized with Redis caching)
            popular_tags = []
            try:
                if hasattr(self.storage_provider, "tags_repo"):
                    popular_tags = await self.storage_provider.tags_repo.get_popular_tags()
            except Exception as e:
                self.logger.debug(f"Could not load popular tags: {e}")

            # Generate human-readable summary
            summary = self.summary_formatter.generate_summary(contexts, project_id, limit)

            self.logger.info(f"Loaded {len(contexts)} contexts for project {project_id}")

            # Get timestamp for response
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")

            # Format for Claude Desktop UI
            if not contexts:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"🔍 No saved contexts found for project '{project_id or 'current project'}'.\n\nMemory is currently empty.\n\n🕐 Checked at: {timestamp}",
                        }
                    ]
                }

            # Build detailed text response
            text_content = ""

            # Add custom instructions if init_load=true
            if init_load:
                self.logger.info(f"DEBUG: init_load=true, trying to load custom instructions")
                try:
                    from extended_memory_mcp.core.instruction_manager import InstructionManager

                    instruction_manager = InstructionManager()
                    custom_instruction = await instruction_manager.load_init_instruction()
                    self.logger.info(
                        f"DEBUG: custom_instruction loaded: {bool(custom_instruction)}"
                    )
                    if custom_instruction:
                        text_content += f"## Custom Instructions\n\n{custom_instruction}\n\n"
                        self.logger.info(f"DEBUG: Added custom instructions to text_content")
                except Exception as e:
                    self.logger.error(f"Could not load custom instructions: {e}")
            else:
                self.logger.info(f"DEBUG: init_load=false, skipping custom instructions")

            text_content += f"🧠 **Memory Loaded Successfully**\n\n"
            text_content += f"📊 **Summary:** {summary}\n\n"

            # Add popular tags section
            if popular_tags:
                try:
                    tags_config = get_default_tags_config()
                    show_tags = tags_config.get("show_in_responses", True)

                    if show_tags:
                        tags_text = ", ".join(
                            [f"{tag['tag']} ({tag['count']} uses)" for tag in popular_tags]
                        )
                        text_content += f"🏷️ **Popular Tags:** {tags_text}\n\n"
                except Exception as e:
                    self.logger.debug(f"Could not load config for tags display: {e}")

            text_content += f"Memory contexts in chronological order (showing last {len(contexts)} entries):\n\n"

            # Sort contexts chronologically (oldest first)
            sorted_contexts = sorted(
                contexts[:10], key=lambda x: x.get("created_at", ""), reverse=False
            )

            # Load tags for all contexts in one batch query (avoid N+1)
            context_ids = [ctx.get("id") for ctx in sorted_contexts if ctx.get("id")]
            tags_batch = {}
            if context_ids and hasattr(self.storage_provider, "tags_repo"):
                try:
                    tags_batch = await self.storage_provider.tags_repo.load_context_tags_batch(
                        context_ids
                    )
                except Exception as e:
                    self.logger.debug(f"Could not load tags batch: {e}")

            for ctx in sorted_contexts:
                created_at = ctx.get("created_at", "")
                date_str = ""
                if created_at:
                    try:
                        from datetime import datetime

                        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        date_str = f" ({dt.strftime('%m-%d %H:%M')})"
                    except:
                        date_str = ""

                text_content += f"(ID: {ctx.get('id')}, Importance: {ctx.get('importance_level', 0)}/10{date_str})\n"

                # Add tags for this context
                ctx_tags = tags_batch.get(ctx.get("id"), [])
                if ctx_tags and isinstance(ctx_tags, list):
                    text_content += f"🏷️ Tags: {', '.join(ctx_tags)}\n"

                full_content = ctx.get("content", "")
                text_content += f"📝 {full_content}\n\n"

            if len(contexts) > 10:
                text_content += f"... and {len(contexts) - 10} more contexts\n"

            return {"content": [{"type": "text", "text": text_content}]}

        except Exception as e:
            # Structured error handling for load_contexts
            memory_error = error_handler.handle_error(
                e,
                context={
                    "project_id": project_id,
                    "importance_level": importance_level,
                    "init_load": init_load,
                    "limit": limit,
                    "tags_filter": tags_filter,
                },
                operation="load_contexts_tool",
            )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"❌ Error loading contexts: {memory_error.message}\n\n🔍 **Error Details:**\n- Category: {memory_error.category.value}\n- Severity: {memory_error.severity.value}",
                    }
                ]
            }

    async def forget_context(self, context_id: int) -> Dict[str, Any]:
        """
        MCP Tool: forget_context
        Claude decides what to delete
        """
        try:
            success = await self.storage_provider.forget_context(context_id)

            if success:
                self.logger.info(f"Deleted context {context_id}")
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"✅ Context deleted successfully!\n\n📝 **Details:**\n- Context ID: {context_id}\n- Status: Permanently removed from memory",
                        }
                    ]
                }
            else:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"❌ Context not found!\n\n📝 **Details:**\n- Context ID: {context_id}\n- Status: Not found or already deleted",
                        }
                    ]
                }

        except Exception as e:
            self.logger.error(f"Error in forget_context: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"❌ Error deleting context!\n\n📝 **Details:**\n- Context ID: {context_id}\n- Error: {str(e)}",
                    }
                ]
            }

    async def list_all_projects_global(self) -> Dict[str, Any]:
        """
        MCP Tool: list_all_projects
        Show ALL available projects (ignores project isolation)

        This tool bypasses project isolation to show all projects across
        the entire memory system. Useful for discovering what projects exist
        and then switching context to specific projects.

        Returns:
            Dict with success status, all projects list, and total count
        """
        try:
            projects = await self.storage_provider.list_all_projects_global()

            # Format for MCP protocol - same as other tools
            project_list = "\n".join(
                [f"- {p.get('id', 'Unknown')} ({p.get('name', 'No name')})" for p in projects]
            )

            response_text = f"🗂️ **All Projects** (ignores isolation)\n\n"
            if projects:
                response_text += f"**Found {len(projects)} projects:**\n{project_list}\n\n"
                response_text += '💡 Use `load_contexts(project_id="project_name")` to load specific project context'
            else:
                response_text += "No projects found in memory system."

            return {"content": [{"type": "text", "text": response_text}]}

        except Exception as e:
            self.logger.error(f"Error in list_all_projects_global: {e}")
            return {"success": False, "error": str(e)}

    async def get_popular_tags_tool(
        self, limit: int = 20, min_usage: int = 1, project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        MCP Tool: get_popular_tags
        Get popular tags with flexible filtering by usage count and project

        Args:
            limit: Maximum number of tags to return (default: 20)
            min_usage: Minimum usage count to include (default: 1)
            project_id: Project ID to filter tags (optional, uses current project if not specified)

        Returns:
            Dict with success status, tags list, and formatted content for Claude Desktop

        Note:
            - If project_id is None, uses self.current_project or "default"
            - Provides flexible filtering with customizable min_usage threshold
            - Ensures project isolation - only shows tags from specified project
        """
        try:
            # Use current_project if no project_id specified
            if project_id is None and hasattr(self, "current_project") and self.current_project:
                project_id = self.current_project

            # Normalize project_id (replace None/empty with "general")
            project_id = normalize_project_id(project_id)

            if hasattr(self.storage_provider, "tags_repo"):
                tags = await self.storage_provider.tags_repo.get_popular_tags(
                    limit=limit, min_usage=min_usage, project_id=project_id
                )
            else:
                tags = []

            if not tags:
                return {
                    "success": True,
                    "tags": [],
                    "message": f"No tags found with min_usage >= {min_usage}",
                    "total": 0,
                }

            from datetime import datetime

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            response_text = f"🏷️ **Popular Tags** (min {min_usage} uses, {len(tags)} found)\n\n"

            for tag in tags:
                response_text += f"• `{tag['tag']}` ({tag['count']} uses)\n"

            response_text += f"\n🕐 **Generated at:** {timestamp}"

            self.logger.info(f"Retrieved {len(tags)} popular tags with min_usage >= {min_usage}")

            return {
                "success": True,
                "tags": tags,
                "total": len(tags),
                "min_usage": min_usage,
                "content": [{"type": "text", "text": response_text}],
            }

        except Exception as e:
            self.logger.error(f"Error in get_popular_tags_tool: {e}")
            return {"success": False, "error": str(e)}

    def _load_tags_config(self) -> Dict[str, Any]:
        """
        Load tags configuration using centralized config utils
        """
        return get_default_tags_config()


# Factory function for easy import
def create_memory_tools_handler(
    storage_provider, summary_formatter: ContextSummaryFormatter, logger: logging.Logger
) -> MemoryToolsHandler:
    """Create a new memory tools handler instance"""
    return MemoryToolsHandler(storage_provider, summary_formatter, logger)
