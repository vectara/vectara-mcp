"""
Tests for health check functionality.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

from vectara_mcp.health_checks import (
    HealthChecker,
    HealthStatus,
    HealthCheck,
    get_liveness,
    get_readiness,
    get_detailed_health
)


class TestHealthChecker:
    """Test health checker functionality."""

    @pytest.fixture
    def health_checker(self):
        """Create a health checker instance for testing."""
        return HealthChecker()

    @pytest.mark.asyncio
    async def test_liveness_check(self, health_checker):
        """Test basic liveness check."""
        result = await health_checker.liveness_check()

        assert result["status"] == HealthStatus.HEALTHY.value
        assert "timestamp" in result
        assert "uptime_seconds" in result
        assert result["version"] == "2.0.0"
        assert result["service"] == "vectara-mcp-server"
        assert result["uptime_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_readiness_check_healthy(self, health_checker):
        """Test readiness check with healthy dependencies."""
        with patch.object(health_checker, '_check_connection_manager') as mock_conn:
            with patch.object(health_checker, '_check_vectara_connectivity') as mock_vectara:
                # Mock healthy responses
                mock_conn.return_value = HealthCheck(
                    name="connection_manager",
                    status=HealthStatus.HEALTHY,
                    message="Connection manager healthy",
                    response_time_ms=10.0
                )
                mock_vectara.return_value = HealthCheck(
                    name="vectara_api",
                    status=HealthStatus.HEALTHY,
                    message="Vectara API accessible",
                    response_time_ms=20.0
                )

                result = await health_checker.readiness_check()

                assert result["status"] == HealthStatus.HEALTHY.value
                assert "timestamp" in result
                assert "response_time_ms" in result
                assert len(result["checks"]) == 2

                # Check individual components
                check_names = [check["name"] for check in result["checks"]]
                assert "connection_manager" in check_names
                assert "vectara_api" in check_names

    @pytest.mark.asyncio
    async def test_readiness_check_unhealthy(self, health_checker):
        """Test readiness check with unhealthy dependencies."""
        with patch.object(health_checker, '_check_connection_manager') as mock_conn:
            with patch.object(health_checker, '_check_vectara_connectivity') as mock_vectara:
                # Mock unhealthy connection manager
                mock_conn.return_value = HealthCheck(
                    name="connection_manager",
                    status=HealthStatus.UNHEALTHY,
                    message="Connection manager error",
                    response_time_ms=5.0
                )
                mock_vectara.return_value = HealthCheck(
                    name="vectara_api",
                    status=HealthStatus.HEALTHY,
                    message="Vectara API accessible",
                    response_time_ms=20.0
                )

                result = await health_checker.readiness_check()

                assert result["status"] == HealthStatus.UNHEALTHY.value
                assert len(result["checks"]) == 2

    @pytest.mark.asyncio
    async def test_readiness_check_degraded(self, health_checker):
        """Test readiness check with degraded dependencies."""
        with patch.object(health_checker, '_check_connection_manager') as mock_conn:
            with patch.object(health_checker, '_check_vectara_connectivity') as mock_vectara:
                # Mock healthy connection but degraded API
                mock_conn.return_value = HealthCheck(
                    name="connection_manager",
                    status=HealthStatus.HEALTHY,
                    message="Connection manager healthy",
                    response_time_ms=10.0
                )
                mock_vectara.return_value = HealthCheck(
                    name="vectara_api",
                    status=HealthStatus.DEGRADED,
                    message="Vectara API slow response",
                    response_time_ms=5000.0
                )

                result = await health_checker.readiness_check()

                assert result["status"] == HealthStatus.DEGRADED.value

    @pytest.mark.asyncio
    async def test_detailed_health_check(self, health_checker):
        """Test detailed health check."""
        with patch.object(health_checker, '_check_connection_manager_detailed') as mock_conn:
            with patch.object(health_checker, '_check_vectara_connectivity') as mock_vectara:
                # Mock detailed responses
                mock_conn.return_value = HealthCheck(
                    name="connection_manager_detailed",
                    status=HealthStatus.HEALTHY,
                    message="Connection manager healthy",
                    response_time_ms=15.0,
                    details={"circuit_breaker_state": "closed"}
                )
                mock_vectara.return_value = HealthCheck(
                    name="vectara_api",
                    status=HealthStatus.HEALTHY,
                    message="Vectara API accessible",
                    response_time_ms=25.0
                )

                result = await health_checker.detailed_health_check()

                assert result["status"] == HealthStatus.HEALTHY.value
                assert "server" in result
                assert "metrics" in result
                assert "checks" in result
                assert result["server"]["service"] == "vectara-mcp-server"

    @pytest.mark.asyncio
    async def test_connection_manager_check_healthy(self, health_checker):
        """Test connection manager health check when healthy."""
        with patch('vectara_mcp.health_checks.get_connection_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_stats.return_value = {
                "session_initialized": True,
                "circuit_breaker": {"state": "closed"}
            }
            mock_get_manager.return_value = mock_manager

            result = await health_checker._check_connection_manager()

            assert result.name == "connection_manager"
            assert result.status == HealthStatus.HEALTHY
            assert "initialized and ready" in result.message
            assert result.response_time_ms is not None

    @pytest.mark.asyncio
    async def test_connection_manager_check_unhealthy(self, health_checker):
        """Test connection manager health check when unhealthy."""
        with patch('vectara_mcp.health_checks.get_connection_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_stats.return_value = {
                "session_initialized": False,
                "circuit_breaker": {"state": "closed"}
            }
            mock_get_manager.return_value = mock_manager

            result = await health_checker._check_connection_manager()

            assert result.name == "connection_manager"
            assert result.status == HealthStatus.UNHEALTHY
            assert "not initialized" in result.message

    @pytest.mark.asyncio
    async def test_connection_manager_check_exception(self, health_checker):
        """Test connection manager health check with exception."""
        with patch('vectara_mcp.health_checks.get_connection_manager') as mock_get_manager:
            mock_get_manager.side_effect = Exception("Connection failed")

            result = await health_checker._check_connection_manager()

            assert result.name == "connection_manager"
            assert result.status == HealthStatus.UNHEALTHY
            assert "Connection failed" in result.message

    @pytest.mark.asyncio
    async def test_vectara_connectivity_check_healthy(self, health_checker):
        """Test Vectara API connectivity check when healthy."""
        with patch('vectara_mcp.health_checks.get_connection_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_manager.health_check.return_value = {
                "status": "healthy",
                "response_time_ms": 150.0,
                "circuit_breaker_state": "closed"
            }
            mock_get_manager.return_value = mock_manager

            result = await health_checker._check_vectara_connectivity()

            assert result.name == "vectara_api"
            assert result.status == HealthStatus.HEALTHY
            assert "accessible" in result.message

    @pytest.mark.asyncio
    async def test_vectara_connectivity_check_degraded(self, health_checker):
        """Test Vectara API connectivity check when degraded."""
        with patch('vectara_mcp.health_checks.get_connection_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_manager.health_check.return_value = {
                "status": "unhealthy",
                "error": "Timeout",
                "circuit_breaker_state": "open"
            }
            mock_get_manager.return_value = mock_manager

            result = await health_checker._check_vectara_connectivity()

            assert result.name == "vectara_api"
            assert result.status == HealthStatus.DEGRADED
            assert "issues" in result.message

    @pytest.mark.asyncio
    async def test_vectara_connectivity_check_exception(self, health_checker):
        """Test Vectara API connectivity check with exception."""
        with patch('vectara_mcp.health_checks.get_connection_manager') as mock_get_manager:
            mock_get_manager.side_effect = Exception("Network error")

            result = await health_checker._check_vectara_connectivity()

            assert result.name == "vectara_api"
            assert result.status == HealthStatus.UNHEALTHY
            assert "Network error" in result.message

    @pytest.mark.asyncio
    async def test_detailed_connection_manager_check_circuit_open(self, health_checker):
        """Test detailed connection manager check with open circuit."""
        with patch('vectara_mcp.health_checks.get_connection_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_stats.return_value = {
                "session_initialized": True,
                "circuit_breaker": {
                    "state": "open",
                    "failure_count": 5
                }
            }
            mock_get_manager.return_value = mock_manager

            result = await health_checker._check_connection_manager_detailed()

            assert result.name == "connection_manager_detailed"
            assert result.status == HealthStatus.UNHEALTHY
            assert "OPEN" in result.message

    @pytest.mark.asyncio
    async def test_detailed_connection_manager_check_circuit_half_open(self, health_checker):
        """Test detailed connection manager check with half-open circuit."""
        with patch('vectara_mcp.health_checks.get_connection_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_stats.return_value = {
                "session_initialized": True,
                "circuit_breaker": {
                    "state": "half_open",
                    "failure_count": 3
                }
            }
            mock_get_manager.return_value = mock_manager

            result = await health_checker._check_connection_manager_detailed()

            assert result.name == "connection_manager_detailed"
            assert result.status == HealthStatus.DEGRADED
            assert "testing recovery" in result.message

    @pytest.mark.asyncio
    async def test_cache_functionality(self, health_checker):
        """Test that connectivity check results are cached."""
        with patch('vectara_mcp.health_checks.get_connection_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_manager.health_check.return_value = {
                "status": "healthy",
                "response_time_ms": 100.0,
                "circuit_breaker_state": "closed"
            }
            mock_get_manager.return_value = mock_manager

            # First call
            result1 = await health_checker._check_vectara_connectivity()

            # Second call (should use cache)
            result2 = await health_checker._check_vectara_connectivity()

            # Should only call the manager once due to caching
            assert mock_manager.health_check.call_count == 1
            assert result1.status == result2.status

    def test_health_status_enum(self):
        """Test HealthStatus enum values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNKNOWN.value == "unknown"

    def test_health_check_dataclass(self):
        """Test HealthCheck dataclass."""
        check = HealthCheck(
            name="test_check",
            status=HealthStatus.HEALTHY,
            message="Test message",
            response_time_ms=100.0,
            details={"key": "value"}
        )

        assert check.name == "test_check"
        assert check.status == HealthStatus.HEALTHY
        assert check.message == "Test message"
        assert check.response_time_ms == 100.0
        assert check.details == {"key": "value"}


class TestHealthCheckEndpoints:
    """Test health check endpoint functions."""

    @pytest.mark.asyncio
    async def test_get_liveness(self):
        """Test get_liveness function."""
        result = await get_liveness()

        assert result["status"] == HealthStatus.HEALTHY.value
        assert "uptime_seconds" in result
        assert result["service"] == "vectara-mcp-server"

    @pytest.mark.asyncio
    async def test_get_readiness(self):
        """Test get_readiness function."""
        with patch('vectara_mcp.health_checks.health_checker') as mock_checker:
            async def mock_readiness():
                return {
                    "status": HealthStatus.HEALTHY.value,
                    "checks": []
                }
            mock_checker.readiness_check = mock_readiness

            result = await get_readiness()

            assert result["status"] == HealthStatus.HEALTHY.value

    @pytest.mark.asyncio
    async def test_get_detailed_health(self):
        """Test get_detailed_health function."""
        with patch('vectara_mcp.health_checks.health_checker') as mock_checker:
            async def mock_detailed():
                return {
                    "status": HealthStatus.HEALTHY.value,
                    "checks": [],
                    "metrics": {}
                }
            mock_checker.detailed_health_check = mock_detailed

            result = await get_detailed_health()

            assert result["status"] == HealthStatus.HEALTHY.value