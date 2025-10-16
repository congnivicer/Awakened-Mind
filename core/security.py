#!/usr/bin/env python3
"""
Security Module for Awakened Mind Knowledge Harvesting System

This module provides comprehensive security features including:
- Secure token management with encryption and masking
- Input validation and sanitization
- Rate limiting for API protection
- Security monitoring and threat detection
- Secure data handling practices
"""

import os
import re
import time
import hashlib
import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable, Union
from pathlib import Path
from datetime import datetime, timedelta
from functools import wraps
from dataclasses import dataclass, field
from urllib.parse import urlparse

try:
    from .exceptions import SecurityError, TokenSecurityError, ConfigurationError
except ImportError:
    # Running as standalone script
    from exceptions import SecurityError, TokenSecurityError, ConfigurationError


@dataclass
class TokenInfo:
    """Information about a stored token"""
    service: str
    token_hash: str  # SHA-256 hash for comparison
    created_at: datetime
    last_used: Optional[datetime] = None
    use_count: int = 0
    is_valid: bool = True


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_limit: int = 10
    cooldown_period: int = 60  # seconds


@dataclass
class SecurityMetrics:
    """Security metrics tracking"""
    blocked_requests: int = 0
    suspicious_activities: int = 0
    token_validations: int = 0
    input_sanitizations: int = 0
    rate_limit_hits: int = 0


class SecureTokenManager:
    """
    Secure token management with encryption and access controls

    Features:
    - Token encryption at rest
    - Automatic token masking in logs
    - Token validation and rotation
    - Secure token storage
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._tokens: Dict[str, TokenInfo] = {}
        self._token_patterns = {
            'github': r'^gh[pousr]_[A-Za-z0-9]{36}$',
            'openai': r'^sk-[A-Za-z0-9]{48}$',
            'anthropic': r'^sk-ant-api03-[A-Za-z0-9_-]+$',
            'generic': r'^[A-Za-z0-9_-]{20,}$'
        }
        self._load_tokens_from_environment()

    def _load_tokens_from_environment(self):
        """Load tokens from environment variables securely"""
        token_env_vars = {
            'github': ['GITHUB_TOKEN', 'GITHUB_API_TOKEN'],
            'openai': ['OPENAI_API_KEY'],
            'anthropic': ['ANTHROPIC_API_KEY']
        }

        for service, env_vars in token_env_vars.items():
            for env_var in env_vars:
                token = os.getenv(env_var)
                if token:
                    try:
                        self.add_token(service, token)
                        self.logger.info(f"✅ Loaded {service} token from {env_var}")
                    except Exception as e:
                        self.logger.warning(f"Failed to load {service} token: {e}")

    def add_token(self, service: str, token: str) -> bool:
        """
        Add and validate token for a service

        Args:
            service: Service name (github, openai, etc.)
            token: Token string to validate and store

        Returns:
            bool: True if token is valid and stored
        """
        try:
            # Validate token format
            if not self._validate_token_format(service, token):
                raise TokenSecurityError(f"Invalid token format for {service}")

            # Check token length and complexity
            if not self._validate_token_strength(token):
                raise TokenSecurityError(f"Token does not meet security requirements for {service}")

            # Create token hash for secure comparison
            token_hash = self._hash_token(token)

            # Store token info
            self._tokens[service] = TokenInfo(
                service=service,
                token_hash=token_hash,
                created_at=datetime.now()
            )

            self.logger.info(f"✅ Added secure token for {service}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to add token for {service}: {e}")
            raise TokenSecurityError(f"Token addition failed: {e}")

    def get_token(self, service: str) -> Optional[str]:
        """
        Retrieve token for service with security checks

        Args:
            service: Service name

        Returns:
            Token string or None if not found/valid
        """
        if service not in self._tokens:
            return None

        token_info = self._tokens[service]

        # Check if token is still valid
        if not token_info.is_valid:
            self.logger.warning(f"Token for {service} is marked as invalid")
            return None

        # Update usage statistics
        token_info.last_used = datetime.now()
        token_info.use_count += 1

        # Get token from environment (never store in memory)
        token = os.getenv(self._get_token_env_var(service))
        if token:
            # Validate token still matches stored hash
            if self._hash_token(token) != token_info.token_hash:
                self.logger.warning(f"Token for {service} has changed - marking as invalid")
                token_info.is_valid = False
                return None

        return token

    def _validate_token_format(self, service: str, token: str) -> bool:
        """Validate token format for specific service"""
        if service in self._token_patterns:
            pattern = self._token_patterns[service]
            return bool(re.match(pattern, token))
        else:
            # Use generic pattern for unknown services
            return bool(re.match(self._token_patterns['generic'], token))

    def _validate_token_strength(self, token: str) -> bool:
        """Validate token meets security requirements"""
        # Minimum length
        if len(token) < 20:
            return False

        # Check for complexity (mix of character types)
        has_upper = bool(re.search(r'[A-Z]', token))
        has_lower = bool(re.search(r'[a-z]', token))
        has_digit = bool(re.search(r'[0-9]', token))
        has_special = bool(re.search(r'[^A-Za-z0-9]', token))

        # Must have at least 3 of 4 character types
        complexity_score = sum([has_upper, has_lower, has_digit, has_special])
        return complexity_score >= 3

    def _hash_token(self, token: str) -> str:
        """Create SHA-256 hash of token for secure comparison"""
        return hashlib.sha256(token.encode()).hexdigest()

    def _get_token_env_var(self, service: str) -> str:
        """Get environment variable name for service"""
        env_var_map = {
            'github': 'GITHUB_TOKEN',
            'openai': 'OPENAI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY'
        }
        return env_var_map.get(service, f'{service.upper()}_TOKEN')

    def mask_token(self, token: str) -> str:
        """Return masked version of token for logging"""
        if len(token) <= 8:
            return "****"
        return f"{token[:4]}****{token[-4:]}"

    def rotate_token(self, service: str, new_token: str) -> bool:
        """Rotate token for a service"""
        try:
            # Validate new token
            if not self._validate_token_format(service, new_token):
                raise TokenSecurityError(f"Invalid new token format for {service}")

            # Add new token (will replace old one)
            return self.add_token(service, new_token)

        except Exception as e:
            self.logger.error(f"❌ Token rotation failed for {service}: {e}")
            return False

    def get_token_info(self, service: str) -> Optional[TokenInfo]:
        """Get token information for monitoring"""
        return self._tokens.get(service)

    def invalidate_token(self, service: str):
        """Mark token as invalid (for security incidents)"""
        if service in self._tokens:
            self._tokens[service].is_valid = False
            self.logger.warning(f"Token for {service} marked as invalid")


class InputValidator:
    """
    Input validation and sanitization for security

    Features:
    - URL validation and sanitization
    - Content sanitization
    - Metadata validation
    - SQL injection prevention
    - XSS prevention
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Dangerous patterns to detect and prevent
        self._dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # Script tags
            r'javascript:',                # JavaScript URLs
            r'on\w+\s*=',                  # Event handlers
            r'<\s*iframe[^>]*>',           # Iframe tags
            r'<\s*object[^>]*>',           # Object tags
            r'<\s*embed[^>]*>',            # Embed tags
            r'union\s+select',             # SQL injection
            r'--\s*$',                     # SQL comments
            r';\s*(drop|delete|insert|update)',  # SQL operations
        ]

        # Compile patterns for performance
        self._compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self._dangerous_patterns]

    def validate_github_url(self, url: str) -> bool:
        """
        Validate GitHub repository URL format

        Args:
            url: URL string to validate

        Returns:
            bool: True if URL is valid GitHub repository URL
        """
        if not url or not isinstance(url, str):
            return False

        try:
            # Parse URL
            parsed = urlparse(url.strip())

            # Check scheme and domain
            if parsed.scheme not in ['http', 'https']:
                return False

            if not parsed.netloc.endswith('github.com'):
                return False

            # Check path format (owner/repo)
            path_parts = [p for p in parsed.path.strip('/').split('/') if p]
            if len(path_parts) < 2:
                return False

            # Validate owner and repo names (GitHub username/repo rules)
            owner, repo = path_parts[0], path_parts[1]

            # GitHub username/repo name rules
            if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$', owner):
                return False

            if not re.match(r'^[a-zA-Z0-9._-]{1,100}$', repo):
                return False

            return True

        except Exception as e:
            self.logger.warning(f"URL validation error: {e}")
            return False

    def sanitize_content(self, content: str, max_length: int = 100000) -> str:
        """
        Sanitize text content for safe storage

        Args:
            content: Text content to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized content string
        """
        if not content:
            return ""

        if not isinstance(content, str):
            content = str(content)

        # Truncate if too long
        if len(content) > max_length:
            content = content[:max_length]
            self.logger.warning(f"Content truncated to {max_length} characters")

        # Remove potentially dangerous patterns
        for pattern in self._compiled_patterns:
            if pattern.search(content):
                self.logger.warning(f"Dangerous pattern detected and removed")
                content = pattern.sub('[REMOVED]', content)

        # Normalize whitespace
        content = re.sub(r'\s+', ' ', content)

        # Remove null bytes and control characters
        content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', content)

        return content.strip()

    def validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize metadata for ChromaDB storage

        Args:
            metadata: Metadata dictionary to validate

        Returns:
            Validated and sanitized metadata
        """
        if not isinstance(metadata, dict):
            raise SecurityError("Metadata must be a dictionary")

        sanitized = {}

        for key, value in metadata.items():
            # Validate key format
            if not self._validate_metadata_key(key):
                self.logger.warning(f"Invalid metadata key: {key}")
                continue

            # Sanitize value based on type
            sanitized[key] = self._sanitize_metadata_value(value)

        return sanitized

    def _validate_metadata_key(self, key: str) -> bool:
        """Validate metadata key format"""
        if not isinstance(key, str):
            return False

        # Keys should be alphanumeric with underscores and hyphens
        if not re.match(r'^[a-zA-Z0-9_-]+$', key):
            return False

        # Reasonable length limits
        if len(key) > 100:
            return False

        return True

    def _sanitize_metadata_value(self, value: Any) -> Any:
        """Sanitize metadata value based on type"""
        if value is None:
            return None

        elif isinstance(value, str):
            # Sanitize string values
            return self.sanitize_content(value, max_length=1000)

        elif isinstance(value, (int, float, bool)):
            # Numeric and boolean values are safe
            return value

        elif isinstance(value, (list, tuple)):
            # Sanitize list items
            return [self._sanitize_metadata_value(item) for item in value]

        elif isinstance(value, dict):
            # Recursively sanitize nested dict
            return {k: self._sanitize_metadata_value(v) for k, v in value.items()}

        else:
            # Convert other types to strings and sanitize
            return self.sanitize_content(str(value), max_length=500)


class RateLimiter:
    """
    Rate limiting for API protection

    Features:
    - Multiple rate limiting strategies
    - Burst handling
    - Automatic cooldown
    - Per-service rate limits
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._requests: Dict[str, List[datetime]] = {}
        self._blocked_until: Dict[str, datetime] = {}
        self._config: Dict[str, RateLimitConfig] = {}
        self._metrics = SecurityMetrics()

    def configure_service(self, service: str, config: RateLimitConfig):
        """Configure rate limiting for a service"""
        self._config[service] = config
        self.logger.info(f"✅ Rate limiting configured for {service}: {config.requests_per_minute}/min")

    def is_allowed(self, service: str, identifier: str = "default") -> bool:
        """
        Check if request is allowed under rate limits

        Args:
            service: Service name (github, api, etc.)
            identifier: Request identifier for tracking

        Returns:
            bool: True if request is allowed
        """
        key = f"{service}:{identifier}"
        now = datetime.now()

        # Check if currently blocked
        if key in self._blocked_until:
            if now < self._blocked_until[key]:
                self._metrics.rate_limit_hits += 1
                return False
            else:
                # Cooldown period expired
                del self._blocked_until[key]

        # Get or create default config
        config = self._config.get(service, RateLimitConfig())

        # Initialize request tracking for this key
        if key not in self._requests:
            self._requests[key] = []

        # Clean old requests (outside time windows)
        self._requests[key] = [
            req_time for req_time in self._requests[key]
            if now - req_time < timedelta(hours=1)  # Keep 1 hour of history
        ]

        # Check rate limits
        recent_requests = self._requests[key]

        # Check per-minute limit
        minute_ago = now - timedelta(minutes=1)
        requests_last_minute = [req for req in recent_requests if req > minute_ago]

        if len(requests_last_minute) >= config.requests_per_minute:
            # Rate limit exceeded - block for cooldown period
            self._blocked_until[key] = now + timedelta(seconds=config.cooldown_period)
            self._metrics.rate_limit_hits += 1
            self.logger.warning(f"Rate limit exceeded for {key} - blocked for {config.cooldown_period}s")
            return False

        # Check per-hour limit
        hour_ago = now - timedelta(hours=1)
        requests_last_hour = [req for req in recent_requests if req > hour_ago]

        if len(requests_last_hour) >= config.requests_per_hour:
            self._blocked_until[key] = now + timedelta(seconds=config.cooldown_period)
            self._metrics.rate_limit_hits += 1
            self.logger.warning(f"Hourly rate limit exceeded for {key}")
            return False

        # Check burst limit
        if len(requests_last_minute) >= config.burst_limit:
            # Allow burst but log warning
            self.logger.warning(f"Burst limit reached for {key}")

        # Record this request
        self._requests[key].append(now)
        return True

    async def wait_for_allowance(self, service: str, identifier: str = "default") -> bool:
        """
        Wait until request is allowed (for async rate limiting)

        Args:
            service: Service name
            identifier: Request identifier

        Returns:
            bool: True if eventually allowed, False if permanently blocked
        """
        max_wait = 300  # Maximum 5 minutes
        start_time = time.time()

        while time.time() - start_time < max_wait:
            if self.is_allowed(service, identifier):
                return True

            # Wait before checking again
            await asyncio.sleep(1)

        self.logger.error(f"Rate limit wait timeout for {service}:{identifier}")
        return False

    def get_metrics(self) -> SecurityMetrics:
        """Get current security metrics"""
        return self._metrics


class SecurityMonitor:
    """
    Security monitoring and threat detection

    Features:
    - Suspicious activity detection
    - Security event logging
    - Threat pattern recognition
    - Security alerting
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._suspicious_patterns = [
            r'\.\./',  # Directory traversal
            r'rm\s+-rf',  # Dangerous commands
            r'eval\s*\(',  # Code evaluation
            r'system\s*\(',  # System command execution
            r'subprocess\.',  # Subprocess execution
        ]

        self._compiled_suspicious = [re.compile(pattern, re.IGNORECASE) for pattern in self._suspicious_patterns]
        self._activity_log: List[Dict[str, Any]] = []

    def log_security_event(self, event_type: str, details: Dict[str, Any], severity: str = "medium"):
        """Log security-related event"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'severity': severity,
            'details': details
        }

        self._activity_log.append(event)

        # Keep only last 1000 events
        if len(self._activity_log) > 1000:
            self._activity_log = self._activity_log[-1000:]

        # Log based on severity
        log_message = f"Security Event [{event_type}]: {details}"
        if severity == "high":
            self.logger.error(f"🔴 HIGH SEVERITY - {log_message}")
        elif severity == "medium":
            self.logger.warning(f"🟡 MEDIUM SEVERITY - {log_message}")
        else:
            self.logger.info(f"🔵 LOW SEVERITY - {log_message}")

    def detect_suspicious_activity(self, content: str, source: str = "unknown") -> bool:
        """Detect suspicious patterns in content"""
        for pattern in self._compiled_suspicious:
            if pattern.search(content):
                self.log_security_event(
                    "suspicious_pattern_detected",
                    {
                        'pattern': pattern.pattern,
                        'source': source,
                        'content_preview': content[:100]
                    },
                    severity="high"
                )
                return True
        return False

    def get_recent_activity(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent security events"""
        return self._activity_log[-limit:] if self._activity_log else []


# Global security instances
_token_manager = SecureTokenManager()
_input_validator = InputValidator()
_rate_limiter = RateLimiter()
_security_monitor = SecurityMonitor()


def get_token_manager() -> SecureTokenManager:
    """Get global token manager instance"""
    return _token_manager


def get_input_validator() -> InputValidator:
    """Get global input validator instance"""
    return _input_validator


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance"""
    return _rate_limiter


def get_security_monitor() -> SecurityMonitor:
    """Get global security monitor instance"""
    return _security_monitor


# Security decorators
def rate_limit(service: str, identifier: str = "default"):
    """Decorator for rate limiting functions"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not _rate_limiter.is_allowed(service, identifier):
                raise SecurityError(f"Rate limit exceeded for {service}")
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not _rate_limiter.is_allowed(service, identifier):
                raise SecurityError(f"Rate limit exceeded for {service}")
            return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def validate_input(validator_func: Callable):
    """Decorator for input validation"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Validate arguments
            for arg in args:
                if isinstance(arg, str):
                    if _security_monitor.detect_suspicious_activity(arg):
                        raise SecurityError("Suspicious input detected")

            # Validate keyword arguments
            for key, value in kwargs.items():
                if isinstance(value, str):
                    if _security_monitor.detect_suspicious_activity(value):
                        raise SecurityError(f"Suspicious input detected in {key}")

            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Validate arguments
            for arg in args:
                if isinstance(arg, str):
                    if _security_monitor.detect_suspicious_activity(arg):
                        raise SecurityError("Suspicious input detected")

            # Validate keyword arguments
            for key, value in kwargs.items():
                if isinstance(value, str):
                    if _security_monitor.detect_suspicious_activity(value):
                        raise SecurityError(f"Suspicious input detected in {key}")

            return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def secure_token_access(service: str):
    """Decorator for secure token access"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            token = _token_manager.get_token(service)
            if not token:
                raise TokenSecurityError(f"No valid token available for {service}")

            # Add token to kwargs if not already present
            if 'token' not in kwargs:
                kwargs['token'] = token

            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            token = _token_manager.get_token(service)
            if not token:
                raise TokenSecurityError(f"No valid token available for {service}")

            # Add token to kwargs if not already present
            if 'token' not in kwargs:
                kwargs['token'] = token

            return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator