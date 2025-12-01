"""
Authentication middleware for Vectara MCP Server.

Provides bearer token validation for HTTP/SSE transports.
"""

import os
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """Authentication middleware for HTTP transport."""

    def __init__(self, auth_required: bool = True):
        """Initialize authentication middleware.

        Args:
            auth_required: Whether authentication is required (default: True)
        """
        self.auth_required = auth_required
        self.valid_tokens = self._load_valid_tokens()

    def _load_valid_tokens(self) -> set:
        """Load valid API tokens from environment.

        Returns:
            Set of valid bearer tokens
        """
        tokens = set()

        # Add main API key if configured
        api_key = os.getenv("VECTARA_API_KEY")
        if api_key:
            tokens.add(api_key)

        # Add additional authorized tokens (comma-separated)
        additional_tokens = os.getenv("VECTARA_AUTHORIZED_TOKENS", "")
        if additional_tokens:
            tokens.update(token.strip() for token in additional_tokens.split(",") if token.strip())

        return tokens

    def validate_token(self, token: Optional[str]) -> bool:
        """Validate a bearer token.

        Args:
            token: Bearer token to validate

        Returns:
            True if token is valid, False otherwise
        """
        if not self.auth_required:
            return True

        if not token:
            logger.warning("No authentication token provided")
            return False

        # Remove "Bearer " prefix if present
        if token.startswith("Bearer "):
            token = token[7:]

        if token in self.valid_tokens:
            return True

        logger.warning("Invalid authentication token")
        return False

    def extract_token_from_headers(self, headers: dict) -> Optional[str]:
        """Extract bearer token from request headers.

        Args:
            headers: Request headers dictionary

        Returns:
            Bearer token if found, None otherwise
        """
        # Check Authorization header
        auth_header = headers.get("Authorization") or headers.get("authorization")
        if auth_header:
            return auth_header

        # Check X-API-Key header (alternative)
        api_key_header = headers.get("X-API-Key") or headers.get("x-api-key")
        if api_key_header:
            return f"Bearer {api_key_header}"

        return None


class RateLimiter:  # pylint: disable=too-few-public-methods
    """Simple in-memory rate limiter for API endpoints."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """Initialize rate limiter.

        Args:
            max_requests: Maximum requests per window (default: 100)
            window_seconds: Time window in seconds (default: 60)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}

    def is_allowed(self, client_id: str) -> bool:
        """Check if client is allowed to make a request.

        Args:
            client_id: Client identifier (IP address or token)

        Returns:
            True if request is allowed, False if rate limited
        """
        current_time = time.time()

        if client_id not in self.requests:
            self.requests[client_id] = []

        # Remove old requests outside the window
        self.requests[client_id] = [
            timestamp for timestamp in self.requests[client_id]
            if current_time - timestamp < self.window_seconds
        ]

        # Check if limit exceeded
        if len(self.requests[client_id]) >= self.max_requests:
            logger.warning("Rate limit exceeded for client: %s", client_id)
            return False

        # Add current request
        self.requests[client_id].append(current_time)
        return True
