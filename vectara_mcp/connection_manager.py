"""
Connection management and resilience patterns for Vectara MCP Server.

Provides persistent connection pooling and circuit breaker pattern
for reliable communication with Vectara API.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Optional, Dict, Any
import aiohttp
import ssl
from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

# Connection timeout constants
DEFAULT_TOTAL_TIMEOUT = 30  # Total request timeout
DEFAULT_CONNECT_TIMEOUT = 10  # Connection timeout
DEFAULT_SOCK_READ_TIMEOUT = 20  # Socket read timeout
DEFAULT_HEALTH_CHECK_TIMEOUT = 5  # Health check timeout

# Circuit breaker constants
DEFAULT_CIRCUIT_FAILURE_THRESHOLD = 5
DEFAULT_CIRCUIT_RECOVERY_TIMEOUT = 60


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """Circuit breaker pattern implementation for API resilience."""

    def __init__(
        self,
        failure_threshold: int = DEFAULT_CIRCUIT_FAILURE_THRESHOLD,
        recovery_timeout: int = DEFAULT_CIRCUIT_RECOVERY_TIMEOUT,
        expected_exception: tuple = (aiohttp.ClientError, asyncio.TimeoutError)
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception types that trigger circuit opening
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self._lock = asyncio.Lock()

    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails
        """
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
                else:
                    raise Exception(f"Circuit breaker OPEN. Last failure: {self.last_failure_time}")

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except self.expected_exception as e:
            await self._on_failure()
            raise
        except Exception as e:
            # Unexpected exceptions don't trigger circuit breaker
            logger.warning(f"Unexpected exception in circuit breaker: {e}")
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout

    async def _on_success(self):
        """Handle successful execution."""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                logger.info("Circuit breaker reset to CLOSED")
            self.failure_count = 0

    async def _on_failure(self):
        """Handle failed execution."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker OPEN after {self.failure_count} failures")

    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state for monitoring."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout
        }


class ConnectionManager:
    """Manages persistent HTTP connections for Vectara API."""

    _instance: Optional['ConnectionManager'] = None
    _lock = asyncio.Lock()

    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize connection manager."""
        if hasattr(self, '_initialized'):
            return

        self._session: Optional[aiohttp.ClientSession] = None
        self._circuit_breaker = CircuitBreaker()
        self._initialized = True

        # Connection pool configuration
        self._connector_config = {
            'limit': 100,  # Total connection limit
            'limit_per_host': 30,  # Connections per host
            'ttl_dns_cache': 300,  # DNS cache TTL
            'use_dns_cache': True,
            'keepalive_timeout': 30,
            'enable_cleanup_closed': True
        }

        # Request timeout configuration
        self._timeout_config = aiohttp.ClientTimeout(
            total=DEFAULT_TOTAL_TIMEOUT,
            connect=DEFAULT_CONNECT_TIMEOUT,
            sock_read=DEFAULT_SOCK_READ_TIMEOUT,
        )

    async def initialize(self):
        """Initialize the HTTP session."""
        if self._session is not None:
            return

        async with self._lock:
            if self._session is not None:
                return

            # Create SSL context with verification
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = True
            ssl_context.verify_mode = ssl.CERT_REQUIRED

            # Create TCP connector with configuration
            connector = aiohttp.TCPConnector(
                ssl=ssl_context,
                **self._connector_config
            )

            # Create session with connector and timeout
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=self._timeout_config,
                headers={
                    'User-Agent': 'Vectara-MCP-Server/2.0',
                    'Accept': 'application/json',
                    'Accept-Encoding': 'gzip, deflate'
                }
            )

            logger.info("Connection manager initialized with persistent session")

    async def close(self):
        """Close the HTTP session and cleanup resources."""
        if self._session is not None:
            await self._session.close()
            self._session = None
            logger.info("Connection manager closed")

    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """Make HTTP request with circuit breaker protection and retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            headers: Request headers
            json_data: JSON payload
            **kwargs: Additional aiohttp parameters

        Returns:
            aiohttp.ClientResponse: HTTP response

        Raises:
            Exception: If circuit is open or request fails after retries
        """
        await self.initialize()

        if self._session is None:
            raise RuntimeError("Session not initialized")

        async def _make_request_with_circuit_breaker():
            """Make request through circuit breaker."""
            async def _make_request():
                response = await self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json_data,
                    **kwargs
                )

                # Check for HTTP errors that should trigger circuit breaker
                if response.status >= 500:
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"HTTP {response.status}"
                    )

                return response

            return await self._circuit_breaker.call(_make_request)

        # Apply retry logic with circuit breaker using tenacity
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
        ):
            with attempt:
                return await _make_request_with_circuit_breaker()

    def get_stats(self) -> Dict[str, Any]:
        """Get connection and circuit breaker statistics."""
        stats = {
            "session_initialized": self._session is not None,
            "circuit_breaker": self._circuit_breaker.get_state(),
            "connector_config": self._connector_config,
        }

        if self._session and hasattr(self._session.connector, '_conns'):
            # Get connection pool stats if available
            try:
                connector = self._session.connector
                stats["connection_pool"] = {
                    "total_connections": len(connector._conns),
                    "available_connections": sum(
                        len(conns) for conns in connector._conns.values()
                    )
                }
            except (AttributeError, TypeError):
                # Connector stats not available in this aiohttp version
                pass

        return stats

    async def health_check(self, url: str = "https://api.vectara.io/v2") -> Dict[str, Any]:
        """Perform health check on Vectara API.

        Args:
            url: Base URL to check

        Returns:
            Dict with health check results
        """
        start_time = time.time()

        try:
            response = await self.request('GET', f"{url}/health", timeout=DEFAULT_HEALTH_CHECK_TIMEOUT)
            duration = time.time() - start_time

            return {
                "status": "healthy",
                "response_time_ms": round(duration * 1000, 2),
                "status_code": response.status,
                "circuit_breaker_state": self._circuit_breaker.state.value
            }
        except Exception as e:
            duration = time.time() - start_time
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": round(duration * 1000, 2),
                "circuit_breaker_state": self._circuit_breaker.state.value
            }


# Global connection manager instance
connection_manager = ConnectionManager()


async def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance.

    Returns:
        ConnectionManager: Singleton instance
    """
    await connection_manager.initialize()
    return connection_manager


async def cleanup_connections():
    """Cleanup function for graceful shutdown."""
    await connection_manager.close()