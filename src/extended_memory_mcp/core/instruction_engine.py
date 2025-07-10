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
Instruction Template Engine
Simple Handlebars-like template processing for init instructions
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class InstructionTemplate:
    """
    Simple template engine for conditional instructions
    Supports {{variable}} and {{#if condition}}...{{else}}...{{/if}} syntax
    """

    def __init__(self, template_content: str):
        self.template = template_content

    def render(self, context: Dict[str, Any]) -> str:
        """
        Render template with provided context

        Args:
            context: Dictionary with variables and conditions

        Returns:
            Rendered template string
        """
        result = self.template

        # Process conditional blocks first
        result = self._process_conditionals(result, context)

        # Process variable substitutions
        result = self._process_variables(result, context)

        return result.strip()

    def _process_conditionals(self, text: str, context: Dict[str, Any]) -> str:
        """Process {{#if condition}}...{{else}}...{{/if}} blocks"""

        # Pattern for if-else blocks
        if_pattern = r"\{\{#if\s+(\w+)\}\}(.*?)\{\{else\}\}(.*?)\{\{/if\}\}"
        # Pattern for if-only blocks
        if_only_pattern = r"\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}\}"

        # Process if-else blocks
        def replace_if_else(match):
            condition = match.group(1)
            if_content = match.group(2).strip()
            else_content = match.group(3).strip()

            if context.get(condition, False):
                return if_content
            else:
                return else_content

        text = re.sub(if_pattern, replace_if_else, text, flags=re.DOTALL)

        # Process if-only blocks
        def replace_if_only(match):
            condition = match.group(1)
            if_content = match.group(2).strip()

            if context.get(condition, False):
                return if_content
            else:
                return ""

        text = re.sub(if_only_pattern, replace_if_only, text, flags=re.DOTALL)

        return text

    def _process_variables(self, text: str, context: Dict[str, Any]) -> str:
        """Process {{variable}} substitutions"""

        def replace_var(match):
            var_name = match.group(1)
            return str(context.get(var_name, f"{{{{missing:{var_name}}}}}"))

        return re.sub(r"\{\{(\w+)\}\}", replace_var, text)


class InstructionLoader:
    """
    Loads and processes instruction files
    """

    def __init__(self, instructions_dir: str):
        self.instructions_dir = Path(instructions_dir)

    def load_init_instruction(
        self, project_id: Optional[str] = None, custom_instruction_path: Optional[str] = None
    ) -> str:
        """
        Load and process init instruction

        Args:
            project_id: Project identifier for project-specific instructions
            custom_instruction_path: Path to custom user instruction file

        Returns:
            Processed instruction text
        """
        try:
            # Determine which instruction file to use
            instruction_file = self._get_instruction_file(project_id, custom_instruction_path)

            if not instruction_file.exists():
                logger.warning(f"Instruction file not found: {instruction_file}, using default")
                instruction_file = self.instructions_dir / "default_init.md"

            # Load template content
            with open(instruction_file, "r", encoding="utf-8") as f:
                template_content = f.read()

            return template_content

        except Exception as e:
            logger.error(f"Failed to load instruction: {e}")
            return self._get_fallback_instruction()

    def _get_instruction_file(self, project_id: Optional[str], custom_path: Optional[str]) -> Path:
        """Determine which instruction file to use"""

        if custom_path:
            return Path(custom_path)

        if project_id:
            project_file = self.instructions_dir / f"{project_id}_init.md"
            if project_file.exists():
                return project_file

        return self.instructions_dir / "default_init.md"

    def _get_fallback_instruction(self) -> str:
        """Fallback instruction if all else fails"""
        return """# Memory System Guide

Use these patterns for effective memory usage:
- Recent events: `importance_min=7`
- User preferences: `context_type="preference"`
- Critical decisions: `importance_min=9`
- Technical details: `context_type="technical"`

Use `init_load=false` for subsequent calls in this session.
"""


def create_instruction_context(memory_manager, project_id: str = None) -> Dict[str, Any]:
    """
    Create context for instruction template rendering
    This is called by the main memory system to provide template variables
    """
    # This would be implemented to analyze current memory state
    # and provide context variables for template rendering

    context = {
        "project_name": project_id or "default",
        "has_recent_contexts": False,  # To be determined by memory analysis
        "last_activity_date": None,
        "project_specific_instructions": "",
        "user_custom_instructions": "",
    }

    return context
