"""
Retry logic with exponential backoff for Vectara MCP Server.

Provides robust retry mechanisms for handling transient failures
when communicating with external APIs.
"""

import asyncio
import logging
import random
import time
from typing import Optional, Callable, Any, TypeVar, Union
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: tuple = (Exception,)
    ):
        """Initialize retry configuration.

        Args:
            max_attempts: Maximum number of retry attempts (including initial)
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff calculation
            jitter: Whether to add random jitter to delays
            retryable_exceptions: Tuple of exception types that trigger retries
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number.

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            float: Delay in seconds
        """
        if attempt == 0:
            return 0  # No delay for first attempt

        # Calculate exponential delay
        delay = min(
            self.initial_delay * (self.exponential_base ** (attempt - 1)),
            self.max_delay
        )

        # Add jitter to prevent thundering herd
        if self.jitter:
            delay *= (0.5 + random.random() * 0.5)  # ±25% jitter

        return delay


class RetryableError(Exception):
    """Exception that indicates an operation should be retried."""
    pass


class NonRetryableError(Exception):
    """Exception that indicates an operation should NOT be retried."""
    pass


def is_retryable_http_error(status_code: int) -> bool:
    """Determine if an HTTP status code indicates a retryable error.

    Args:
        status_code: HTTP status code

    Returns:
        bool: True if the error is retryable
    """
    # Retryable: 5xx server errors, 429 rate limiting, 408 timeout
    retryable_codes = {408, 429, 500, 502, 503, 504}
    return status_code in retryable_codes


def is_retryable_exception(exception: Exception) -> bool:
    """Determine if an exception indicates a retryable error.

    Args:
        exception: Exception to check

    Returns:
        bool: True if the error is retryable
    """
    import aiohttp

    # Always retry these
    if isinstance(exception, (asyncio.TimeoutError, aiohttp.ServerTimeoutError)):
        return True

    # Check if it's an HTTP error with retryable status
    if hasattr(exception, 'status') and hasattr(exception, 'status_code'):
        status = getattr(exception, 'status', None) or getattr(exception, 'status_code', None)
        if status and is_retryable_http_error(status):
            return True

    # Check for connection errors
    connection_errors = (
        aiohttp.ClientConnectionError,
        aiohttp.ServerConnectionError,
        aiohttp.ClientConnectorError,
        ConnectionError,
        OSError
    )
    if isinstance(exception, connection_errors):
        return True

    # Check for explicit retry markers
    if isinstance(exception, RetryableError):
        return True

    if isinstance(exception, NonRetryableError):
        return False

    # Default to non-retryable for safety
    return False


async def retry_async(
    func: Callable[..., T],
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> T:
    """Retry an async function with exponential backoff.

    Args:
        func: Async function to retry
        *args: Function arguments
        config: Retry configuration (uses default if None)
        **kwargs: Function keyword arguments

    Returns:
        Function result

    Raises:
        Exception: Last exception if all retries fail
    """
    if config is None:
        config = RetryConfig()

    last_exception = None

    for attempt in range(config.max_attempts):
        try:
            if attempt > 0:
                delay = config.calculate_delay(attempt)
                logger.debug(f"Retrying after {delay:.2f}s (attempt {attempt + 1}/{config.max_attempts})")
                await asyncio.sleep(delay)

            result = await func(*args, **kwargs)

            if attempt > 0:
                logger.info(f"Operation succeeded on attempt {attempt + 1}/{config.max_attempts}")

            return result

        except Exception as e:
            last_exception = e

            # Check if we should retry this exception
            if not is_retryable_exception(e):
                logger.debug(f"Non-retryable exception: {type(e).__name__}: {e}")
                raise

            # Check if we have more attempts
            if attempt + 1 >= config.max_attempts:
                logger.warning(f"All {config.max_attempts} attempts failed. Last error: {type(e).__name__}: {e}")
                raise

            logger.warning(f"Attempt {attempt + 1}/{config.max_attempts} failed: {type(e).__name__}: {e}")

    # This should never be reached, but just in case
    if last_exception:
        raise last_exception
    else:
        raise RuntimeError("Retry logic failed without exception")


def with_retry(config: Optional[RetryConfig] = None):
    """Decorator to add retry logic to async functions.

    Args:
        config: Retry configuration (uses default if None)

    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_async(func, *args, config=config, **kwargs)
        return wrapper
    return decorator


# Predefined retry configurations for common scenarios

# Conservative retry for critical operations
CONSERVATIVE_RETRY = RetryConfig(
    max_attempts=2,
    initial_delay=0.5,
    max_delay=5.0,
    exponential_base=2.0,
    jitter=True
)

# Standard retry for most API calls
STANDARD_RETRY = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=10.0,
    exponential_base=2.0,
    jitter=True
)

# Aggressive retry for non-critical operations
AGGRESSIVE_RETRY = RetryConfig(
    max_attempts=5,
    initial_delay=0.5,
    max_delay=30.0,
    exponential_base=1.5,
    jitter=True
)

# Network-specific retry (longer delays for network issues)
NETWORK_RETRY = RetryConfig(
    max_attempts=4,
    initial_delay=2.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True
)


class RetryMetrics:
    """Tracks retry metrics for monitoring."""

    def __init__(self):
        """Initialize retry metrics."""
        self.total_attempts = 0
        self.total_successes = 0
        self.total_failures = 0
        self.retry_counts = {}  # attempt_number -> count
        self.failure_types = {}  # exception_type -> count

    def record_attempt(self, attempt_number: int, success: bool, exception_type: Optional[str] = None):
        """Record a retry attempt.

        Args:
            attempt_number: Which attempt this was (1-indexed)
            success: Whether the attempt succeeded
            exception_type: Type of exception if failed
        """
        self.total_attempts += 1

        if success:
            self.total_successes += 1
        else:
            self.total_failures += 1
            if exception_type:
                self.failure_types[exception_type] = self.failure_types.get(exception_type, 0) + 1

        self.retry_counts[attempt_number] = self.retry_counts.get(attempt_number, 0) + 1

    def get_stats(self) -> dict:
        """Get retry statistics.

        Returns:
            dict: Statistics about retry behavior
        """
        success_rate = self.total_successes / max(self.total_attempts, 1)

        return {
            "total_attempts": self.total_attempts,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "success_rate": round(success_rate, 3),
            "retry_distribution": dict(self.retry_counts),
            "failure_types": dict(self.failure_types)
        }


# Global retry metrics instance
retry_metrics = RetryMetrics()