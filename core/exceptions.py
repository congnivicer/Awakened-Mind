#!/usr/bin/env python3
"""
Custom Exception Hierarchy for Awakened Mind Knowledge Harvesting System

This module defines a comprehensive exception hierarchy that provides:
- Specific error types for different failure modes
- Better error context and debugging information
- Consistent error handling patterns across the system
- Recovery suggestions for common error scenarios
"""

from datetime import datetime
from typing import Optional, Dict, Any, Union
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels for classification and handling"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for grouping and handling"""
    CONNECTION = "connection"
    VALIDATION = "validation"
    STORAGE = "storage"
    API = "api"
    CONFIGURATION = "configuration"
    PROCESSING = "processing"
    SECURITY = "security"


class AwakenedMindError(Exception):
    """
    Base exception for all Awakened Mind system errors

    Provides enhanced error context including:
    - Error classification and severity
    - Timestamp and context information
    - Recovery suggestions
    - Debugging information
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        category: ErrorCategory = ErrorCategory.PROCESSING,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        recovery_suggestion: Optional[str] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.recovery_suggestion = recovery_suggestion
        self.cause = cause
        self.timestamp = datetime.now().isoformat()

    def __str__(self) -> str:
        """Enhanced string representation with full context"""
        parts = [f"[{self.error_code}] {self.message}"]

        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"Context: {context_str}")

        if self.recovery_suggestion:
            parts.append(f"Suggestion: {self.recovery_suggestion}")

        return " | ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/serialization"""
        return {
            'error_code': self.error_code,
            'message': self.message,
            'category': self.category.value,
            'severity': self.severity.value,
            'context': self.context,
            'recovery_suggestion': self.recovery_suggestion,
            'timestamp': self.timestamp,
            'cause': str(self.cause) if self.cause else None
        }


# Connection-related errors
class ChromaConnectionError(AwakenedMindError):
    """Raised when ChromaDB connection fails"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="CHROMA_CONN_FAILED",
            category=ErrorCategory.CONNECTION,
            severity=ErrorSeverity.HIGH,
            recovery_suggestion="Check ChromaDB service status and network connectivity",
            **kwargs
        )


class ChromaOperationError(AwakenedMindError):
    """Raised when ChromaDB operations fail"""

    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="CHROMA_OP_FAILED",
            category=ErrorCategory.STORAGE,
            severity=ErrorSeverity.MEDIUM,
            context={'operation': operation} if operation else {},
            recovery_suggestion="Verify collection exists and document format is correct",
            **kwargs
        )


# Storage and data-related errors
class KnowledgeStorageError(AwakenedMindError):
    """Raised when document storage operations fail"""

    def __init__(self, message: str, collection: Optional[str] = None, document_id: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="STORAGE_FAILED",
            category=ErrorCategory.STORAGE,
            severity=ErrorSeverity.HIGH,
            context={
                'collection': collection,
                'document_id': document_id
            },
            recovery_suggestion="Check document format and collection permissions",
            **kwargs
        )


class MetadataFormatError(AwakenedMindError):
    """Raised when document metadata is invalid for ChromaDB"""

    def __init__(self, message: str, field: Optional[str] = None, value: Any = None, **kwargs):
        super().__init__(
            message=message,
            error_code="METADATA_INVALID",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            context={'field': field, 'value_type': type(value).__name__},
            recovery_suggestion="Ensure metadata values are strings, numbers, booleans, or None",
            **kwargs
        )


# API-related errors
class GitHubAPIError(AwakenedMindError):
    """Raised when GitHub API operations fail"""

    def __init__(self, message: str, status_code: Optional[int] = None, url: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="GITHUB_API_FAILED",
            category=ErrorCategory.API,
            severity=ErrorSeverity.MEDIUM,
            context={
                'status_code': status_code,
                'url': url
            },
            recovery_suggestion="Check GitHub API token and rate limits",
            **kwargs
        )


class GitHubRateLimitError(GitHubAPIError):
    """Raised when GitHub API rate limit is exceeded"""

    def __init__(self, reset_time: Optional[str] = None, **kwargs):
        super().__init__(
            message="GitHub API rate limit exceeded",
            error_code="GITHUB_RATE_LIMIT",
            severity=ErrorSeverity.HIGH,
            context={'reset_time': reset_time},
            recovery_suggestion=f"Wait until {reset_time} before retrying or upgrade API plan",
            **kwargs
        )


class GitHubTokenError(GitHubAPIError):
    """Raised when GitHub token is invalid or missing"""

    def __init__(self, **kwargs):
        super().__init__(
            message="GitHub API token is invalid or missing",
            error_code="GITHUB_TOKEN_INVALID",
            severity=ErrorSeverity.CRITICAL,
            recovery_suggestion="Check GITHUB_TOKEN environment variable or token configuration",
            **kwargs
        )


# Configuration errors
class ConfigurationError(AwakenedMindError):
    """Raised when system configuration is invalid"""

    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="CONFIG_INVALID",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            context={'config_key': config_key},
            recovery_suggestion="Check configuration files and environment variables",
            **kwargs
        )


class PathConfigurationError(ConfigurationError):
    """Raised when path configuration is invalid"""

    def __init__(self, message: str, path: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="PATH_CONFIG_INVALID",
            context={'path': path},
            recovery_suggestion="Verify volume paths are accessible and properly mounted",
            **kwargs
        )


# Processing errors
class DocumentProcessingError(AwakenedMindError):
    """Raised when document processing fails"""

    def __init__(self, message: str, document_id: Optional[str] = None, stage: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="DOC_PROCESS_FAILED",
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.MEDIUM,
            context={
                'document_id': document_id,
                'processing_stage': stage
            },
            recovery_suggestion="Check document format and content validity",
            **kwargs
        )


class PipelineExecutionError(AwakenedMindError):
    """Raised when knowledge pipeline execution fails"""

    def __init__(self, message: str, stage: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="PIPELINE_FAILED",
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.HIGH,
            context={'stage': stage},
            recovery_suggestion="Check component initialization and external service availability",
            **kwargs
        )


# Security-related errors
class SecurityError(AwakenedMindError):
    """Raised for security-related issues"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="SECURITY_ERROR",
            category=ErrorCategory.SECURITY,
            severity=ErrorSeverity.CRITICAL,
            recovery_suggestion="Review security configuration and access controls",
            **kwargs
        )


class TokenSecurityError(SecurityError):
    """Raised when token handling violates security policies"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="TOKEN_SECURITY_ERROR",
            recovery_suggestion="Ensure tokens are properly encrypted and not logged",
            **kwargs
        )


# Resource and system errors
class ResourceExhaustionError(AwakenedMindError):
    """Raised when system resources are exhausted"""

    def __init__(self, message: str, resource_type: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="RESOURCE_EXHAUSTED",
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.HIGH,
            context={'resource_type': resource_type},
            recovery_suggestion="Check system resources and consider scaling up",
            **kwargs
        )


class InitializationError(AwakenedMindError):
    """Raised when system or component initialization fails"""

    def __init__(self, message: str, component: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="INIT_FAILED",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.CRITICAL,
            context={'component': component},
            recovery_suggestion="Check component dependencies and configuration",
            **kwargs
        )


# Utility functions for error handling
def handle_chroma_errors(operation_name: str):
    """
    Decorator for handling ChromaDB-specific errors

    Args:
        operation_name: Name of the operation for context

    Usage:
        @handle_chroma_errors("document_storage")
        def add_documents(self, ...):
            # Implementation
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ValueError as e:
                if "metadata" in str(e).lower():
                    raise MetadataFormatError(
                        f"Invalid metadata in {operation_name}: {e}",
                        context={'operation': operation_name}
                    )
                else:
                    raise ChromaOperationError(
                        f"ChromaDB operation failed in {operation_name}: {e}",
                        operation=operation_name
                    )
            except Exception as e:
                raise ChromaConnectionError(
                    f"Unexpected error in {operation_name}: {e}",
                    context={'operation': operation_name}
                )
        return wrapper
    return decorator


def handle_github_api_errors(operation_name: str):
    """
    Decorator for handling GitHub API errors with rate limit detection

    Args:
        operation_name: Name of the API operation for context
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Check for rate limit errors (HTTP 403)
                if hasattr(e, 'status') and getattr(e, 'status', None) == 403:
                    raise GitHubRateLimitError(
                        f"Rate limit exceeded in {operation_name}",
                        context={'operation': operation_name}
                    )
                # Check for authentication errors
                elif any(term in str(e).lower() for term in ["token", "unauthorized", "authentication"]):
                    raise GitHubTokenError(
                        message=f"Authentication failed in {operation_name}",
                        context={'operation': operation_name}
                    )
                # Generic GitHub API error
                else:
                    raise GitHubAPIError(
                        f"GitHub API error in {operation_name}: {e}",
                        context={'operation': operation_name}
                    )
        return wrapper
    return decorator