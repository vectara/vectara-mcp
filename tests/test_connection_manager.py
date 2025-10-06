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