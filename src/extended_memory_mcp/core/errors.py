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
Centralized error handling and exception framework.
Provides structured error types and logging for production stability.
"""

import logging
import traceback
from enum import Enum
from typing import Any, Dict, Optional, Union


class ErrorCategory(Enum):
    """Error categories for better error classification and handling"""

    STORAGE = "storage"
    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    NETWORK = "network"
    PERMISSION = "permission"
    INTERNAL = "internal"
    USER_INPUT = "user_input"


class ErrorSeverity(Enum):
    """Error severity levels for proper alerting and response"""

    CRITICAL = "critical"  # Service unavailable
    HIGH = "high"  # Feature broken
    MEDIUM = "medium"  # Degraded performance
    LOW = "low"  # Minor issue


class MemoryMCPError(Exception):
    """Base exception class for all Memory MCP errors"""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.INTERNAL,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.original_error = original_error

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging and API responses"""
        error_dict = {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "context": self.context,
        }

        if self.original_error:
            error_dict["original_error"] = {
                "type": type(self.original_error).__name__,
                "message": str(self.original_error),
            }

        return error_dict


class StorageError(MemoryMCPError):
    """Database and storage related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, category=ErrorCategory.STORAGE, severity=ErrorSeverity.HIGH, **kwargs
        )


class ConfigurationError(MemoryMCPError):
    """Configuration and setup related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, category=ErrorCategory.CONFIGURATION, severity=ErrorSeverity.CRITICAL, **kwargs
        )


class ValidationError(MemoryMCPError):
    """Input validation and data format errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, category=ErrorCategory.VALIDATION, severity=ErrorSeverity.LOW, **kwargs
        )


class NetworkError(MemoryMCPError):
    """Network and connection related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, category=ErrorCategory.NETWORK, severity=ErrorSeverity.MEDIUM, **kwargs
        )


class PermissionError(MemoryMCPError):
    """Access control and permission errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, category=ErrorCategory.PERMISSION, severity=ErrorSeverity.HIGH, **kwargs
        )


class ErrorHandler:
    """Centralized error handling and logging utility"""

    def __init__(self, logger_name: str = "MemoryMCP"):
        self.logger = logging.getLogger(logger_name)

    def handle_error(
        self,
        error: Union[Exception, MemoryMCPError],
        context: Optional[Dict[str, Any]] = None,
        operation: Optional[str] = None,
    ) -> MemoryMCPError:
        """
        Handle any error with structured logging and conversion to MemoryMCPError

        Args:
            error: Original exception
            context: Additional context for debugging
            operation: Name of operation that failed

        Returns:
            MemoryMCPError instance for consistent error handling
        """

        # Convert to MemoryMCPError if needed
        if isinstance(error, MemoryMCPError):
            memory_error = error
        else:
            memory_error = MemoryMCPError(message=str(error), original_error=error, context=context)

        # Add operation context if provided
        if operation:
            memory_error.context["operation"] = operation

        # Add stack trace for debugging
        memory_error.context["stack_trace"] = traceback.format_exc()

        # Log with appropriate level based on severity
        log_level = {
            ErrorSeverity.CRITICAL: logging.CRITICAL,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.LOW: logging.INFO,
        }.get(memory_error.severity, logging.ERROR)

        self.logger.log(
            log_level,
            f"[{memory_error.category.value.upper()}] {memory_error.message}",
            extra={"error_details": memory_error.to_dict(), "operation": operation},
        )

        return memory_error

    def safe_execute(self, operation_name: str, func, *args, default_return=None, **kwargs):
        """
        Safely execute function with automatic error handling

        Args:
            operation_name: Name of operation for logging
            func: Function to execute
            default_return: Value to return on error
            *args, **kwargs: Arguments for function

        Returns:
            Function result or default_return on error
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.handle_error(e, operation=operation_name)
            return default_return


# Global error handler instance
error_handler = ErrorHandler()
