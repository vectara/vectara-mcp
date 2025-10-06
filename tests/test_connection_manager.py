"""
Tests for connection manager and circuit breaker functionality.
"""

import pytest
import asyncio
import aiohttp
from unittest.mock import AsyncMock, MagicMock, patch
from vectara_mcp.connection_manager import (
    ConnectionManager,
    CircuitBreaker,
    CircuitState,
    get_connection_manager,
    cleanup_connections
)
from vectara_mcp.retry_logic import (
    RetryConfig,
    retry_async,
    is_retryable_http_error,
    is_retryable_exception,
    RetryableError,
    NonRetryableError
)


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_success(self):
        """Test circuit breaker with successful calls."""
        circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=1)

        async def successful_func():
            return "success"

        result = await circuit.call(successful_func)
        assert result == "success"
        assert circuit.state == CircuitState.CLOSED
        assert circuit.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_threshold(self):
        """Test circuit breaker opening after failure threshold."""
        circuit = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        async def failing_func():
            raise aiohttp.ClientError("Test error")

        # First failure
        with pytest.raises(aiohttp.ClientError):
            await circuit.call(failing_func)
        assert circuit.state == CircuitState.CLOSED
        assert circuit.failure_count == 1

        # Second failure - should open circuit
        with pytest.raises(aiohttp.ClientError):
            await circuit.call(failing_func)
        assert circuit.state == CircuitState.OPEN
        assert circuit.failure_count == 2

        # Third call should fail fast
        with pytest.raises(Exception, match="Circuit breaker OPEN"):
            await circuit.call(failing_func)

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout."""
        circuit = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

        async def failing_func():
            raise aiohttp.ClientError("Test error")

        async def successful_func():
            return "success"

        # Trigger circuit opening
        with pytest.raises(aiohttp.ClientError):
            await circuit.call(failing_func)
        assert circuit.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.2)

        # Should transition to half-open and then closed on success
        result = await circuit.call(successful_func)
        assert result == "success"
        assert circuit.state == CircuitState.CLOSED
        assert circuit.failure_count == 0

    def test_circuit_breaker_state_info(self):
        """Test circuit breaker state information."""
        circuit = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

        state = circuit.get_state()
        assert state["state"] == "closed"
        assert state["failure_count"] == 0
        assert state["failure_threshold"] == 5
        assert state["recovery_timeout"] == 60
        assert state["last_failure_time"] is None


class TestRetryLogic:
    """Test retry logic functionality."""

    @pytest.mark.asyncio
    async def test_successful_first_attempt(self):
        """Test function succeeding on first attempt."""
        call_count = 0

        async def test_func():
            nonlocal call_count
            call_count += 1
            return "success"

        config = RetryConfig(max_attempts=3)
        result = await retry_async(test_func, config=config)

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test retry logic with eventual success."""
        call_count = 0

        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise aiohttp.ServerTimeoutError("Timeout")
            return "success"

        config = RetryConfig(max_attempts=3, initial_delay=0.01)
        result = await retry_async(test_func, config=config)

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self):
        """Test failure after max attempts."""
        call_count = 0

        async def test_func():
            nonlocal call_count
            call_count += 1
            raise aiohttp.ServerTimeoutError("Always fails")

        config = RetryConfig(max_attempts=2, initial_delay=0.01)

        with pytest.raises(aiohttp.ServerTimeoutError):
            await retry_async(test_func, config=config)

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_non_retryable_exception(self):
        """Test that non-retryable exceptions are not retried."""
        call_count = 0

        async def test_func():
            nonlocal call_count
            call_count += 1
            raise NonRetryableError("Should not retry")

        config = RetryConfig(max_attempts=3)

        with pytest.raises(NonRetryableError):
            await retry_async(test_func, config=config)

        assert call_count == 1

    def test_retryable_http_errors(self):
        """Test retryable HTTP status code detection."""
        assert is_retryable_http_error(500) is True
        assert is_retryable_http_error(502) is True
        assert is_retryable_http_error(503) is True
        assert is_retryable_http_error(504) is True
        assert is_retryable_http_error(429) is True
        assert is_retryable_http_error(408) is True

        assert is_retryable_http_error(400) is False
        assert is_retryable_http_error(401) is False
        assert is_retryable_http_error(404) is False
        assert is_retryable_http_error(200) is False

    def test_retryable_exceptions(self):
        """Test retryable exception detection."""
        assert is_retryable_exception(asyncio.TimeoutError()) is True
        assert is_retryable_exception(aiohttp.ServerTimeoutError()) is True
        assert is_retryable_exception(aiohttp.ClientConnectionError()) is True
        assert is_retryable_exception(RetryableError()) is True

        assert is_retryable_exception(NonRetryableError()) is False
        assert is_retryable_exception(ValueError()) is False
        assert is_retryable_exception(KeyError()) is False

    def test_retry_config_delay_calculation(self):
        """Test retry delay calculations."""
        config = RetryConfig(
            initial_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0,
            jitter=False
        )

        assert config.calculate_delay(0) == 0  # First attempt
        assert config.calculate_delay(1) == 1.0  # 1.0 * 2^0
        assert config.calculate_delay(2) == 2.0  # 1.0 * 2^1
        assert config.calculate_delay(3) == 4.0  # 1.0 * 2^2
        assert config.calculate_delay(4) == 8.0  # 1.0 * 2^3
        assert config.calculate_delay(5) == 10.0  # Max delay cap