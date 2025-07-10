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
Instruction Manager - Handles init instructions with conditional logic
Provides smart guidance for Claude on memory usage patterns
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, Template


def is_safe_path(file_path: str) -> bool:
    """
    Validate that file path is safe to read.

    Prevents directory traversal attacks and access to system files.

    Args:
        file_path: File path to validate

    Returns:
        True if path is safe (regardless of existence), False if unsafe
    """
    try:
        # Convert to absolute path and resolve any symbolic links
        abs_path = Path(file_path).resolve()

        # Check for dangerous patterns
        path_str = str(abs_path)
        dangerous_patterns = [
            "/etc/",
            "/proc/",
            "/sys/",
            "/dev/",
            "/bin/",
            "/sbin/",
            "/usr/bin/",
            "/usr/sbin/",
            "~/.ssh/",
            "~/.aws/",
        ]

        # Block access to system directories
        for pattern in dangerous_patterns:
            if pattern in path_str:
                return False

        # Additional check: ensure it has allowed extension
        allowed_extensions = {".md", ".txt", ".text", ".markdown"}
        if abs_path.suffix.lower() not in allowed_extensions:
            return False

        return True

    except (OSError, ValueError, RuntimeError) as e:
        # Any filesystem errors = unsafe
        return False


logger = logging.getLogger(__name__)


class InstructionManager:
    """
    Manages init instructions with template rendering and conditional logic
    Supports file-based instructions with parameterization
    """

    def __init__(self, instructions_dir: Optional[str] = None):
        if instructions_dir is None:
            # Default to config/instructions relative to this file
            current_dir = Path(__file__).parent
            instructions_dir = current_dir.parent / "config" / "instructions"

        self.instructions_dir = Path(instructions_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.instructions_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            variable_start_string="{{",
            variable_end_string="}}",
            block_start_string="{%",
            block_end_string="%}",
            comment_start_string="{#",
            comment_end_string="#}",
            # Enable autoescape for security (prevents XSS attacks)
            autoescape=True,
        )

    async def load_init_instruction(
        self,
        project_id: Optional[str] = None,
        memory_state: Optional[Dict[str, Any]] = None,
        custom_instruction_path: Optional[str] = None,
    ) -> str:
        """
        Load custom user instruction if CUSTOM_INSTRUCTION_PATH is set.

        Args:
            project_id: Current project identifier (ignored)
            memory_state: Current memory statistics (ignored)
            custom_instruction_path: Path to custom user instruction (ignored - reads from env)

        Returns:
            Custom instruction content or empty string if no custom instruction
        """
        try:
            # Read custom instruction path from environment
            custom_instruction_path = os.getenv("CUSTOM_INSTRUCTION_PATH")

            if not custom_instruction_path or not custom_instruction_path.strip():
                # No custom instruction specified - return empty
                logger.debug("No CUSTOM_INSTRUCTION_PATH specified")
                return ""

            # Load custom instruction with security validation
            custom_content = await self._load_custom_instructions(custom_instruction_path.strip())

            if custom_content:
                logger.info(f"Loaded custom instruction from: {custom_instruction_path}")
                return custom_content
            else:
                logger.warning(f"Custom instruction file is empty: {custom_instruction_path}")
                return ""

        except Exception as e:
            logger.error(f"Failed to load custom instruction: {e}")
            # Re-raise to fail fast on configuration errors
            raise

    async def _determine_base_instruction_file(self, project_id: Optional[str] = None) -> str:
        """Determine base instruction file (project-specific or default)"""
        # Priority: project-specific > default (custom is handled separately)

        if project_id:
            project_file = f"{project_id}_init.md"
            if (self.instructions_dir / project_file).exists():
                return project_file

        # Default fallback
        return "default_init.md"

    async def _prepare_template_variables(
        self, project_id: Optional[str], memory_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare variables for template rendering"""

        # Calculate derived flags
        now = datetime.now()
        last_activity = memory_state.get("last_activity_date")

        # Load user custom instructions from environment variable
        user_custom_instructions = ""
        custom_instruction_path = os.getenv("CUSTOM_INSTRUCTION_PATH")
        if custom_instruction_path and custom_instruction_path.strip():
            user_custom_instructions = await self._load_custom_instructions(
                custom_instruction_path.strip()
            )

        return {
            # Project info
            "project_name": project_id or "default",
            "project_id": project_id,
            # Memory state flags
            "has_recent_contexts": memory_state.get("has_recent_contexts", False),
            "context_count_high": memory_state.get("total_contexts", 0) > 50,
            # Metrics
            "total_contexts": memory_state.get("total_contexts", 0),
            "last_activity_date": (
                last_activity.strftime("%Y-%m-%d") if last_activity else "unknown"
            ),
            "days_since_activity": (now - last_activity).days if last_activity else 0,
            # Project-specific guidance
            "project_guidance": memory_state.get("project_guidance", ""),
            # User custom instructions
            "user_custom_instructions": user_custom_instructions,
            # Timestamps
            "current_date": now.strftime("%Y-%m-%d"),
            "current_time": now.strftime("%H:%M"),
        }

    def _get_fallback_instruction(self) -> str:
        """Simple fallback if template loading fails"""
        return """# Memory System Active

Use `load_contexts` with specific parameters:
- `context_type` for targeted queries
- `importance_min` for priority filtering
- `init_load=false` for subsequent calls

Load AI personality if mentioned in session."""

    async def _load_custom_instructions(self, custom_path: str) -> str:
        """
        Load custom user instructions from file with security validation.

        Args:
            custom_path: Path to custom instruction file

        Returns:
            Content of custom instruction file

        Raises:
            SecurityError: If file path is unsafe
            FileNotFoundError: If file doesn't exist
            RuntimeError: If file can't be read
        """
        try:
            # Expand user path (handle ~ notation)
            expanded_path = os.path.expanduser(custom_path)

            # Security validation: check if path is safe
            if not is_safe_path(expanded_path):
                logger.error(f"Unsafe custom instruction path detected: {expanded_path}")
                raise RuntimeError(f"Unsafe file path: {expanded_path}")

            # Check file existence
            if not os.path.exists(expanded_path):
                logger.error(f"Custom instruction file not found: {custom_path}")
                raise FileNotFoundError(f"Custom instruction file not found: {custom_path}")

            # Load file content with encoding validation
            with open(expanded_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            if not content:
                logger.warning(f"Custom instruction file is empty: {custom_path}")
                return ""

            logger.info(f"Successfully loaded custom instructions from: {custom_path}")
            return content

        except (FileNotFoundError, RuntimeError):
            # Re-raise expected errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading custom instructions from {custom_path}: {e}")
            raise RuntimeError(f"Failed to load custom instructions: {e}")

    def set_custom_instruction_path(self, path: Optional[str]):
        """Set path to custom user instructions"""
        self.custom_instruction_path = path
