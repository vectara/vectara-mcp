"""
Health check endpoints for Vectara MCP Server.

Provides liveness, readiness, and detailed health status endpoints
for production deployment with load balancers and orchestration platforms.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from .connection_manager import get_connection_manager
from .retry_logic import retry_metrics

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status values."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result."""
    name: str
    status: HealthStatus
    message: str
    response_time_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


class HealthChecker:
    """Manages health checks for the MCP server."""

    def __init__(self):
        """Initialize health checker."""
        self.server_start_time = time.time()
        self.last_check_cache = {}
        self.cache_ttl = 5  # Cache health checks for 5 seconds

    async def liveness_check(self) -> Dict[str, Any]:
        """Basic liveness check - is the server process running and responding?

        This should be fast and only check if the process is alive.
        Used by load balancers to determine if traffic should be routed here.

        Returns:
            Dict: Liveness status
        """
        return {
            "status": HealthStatus.HEALTHY.value,
            "timestamp": time.time(),
            "uptime_seconds": round(time.time() - self.server_start_time, 2),
            "version": "2.0.0",
            "service": "vectara-mcp-server"
        }

    async def readiness_check(self) -> Dict[str, Any]:
        """Readiness check - can the server handle traffic?

        Checks critical dependencies that must be working for the server
        to properly handle requests. Used by orchestration platforms.

        Returns:
            Dict: Readiness status with dependency checks
        """
        checks = []
        overall_status = HealthStatus.HEALTHY
        start_time = time.time()

        # Check connection manager
        try:
            connection_check = await self._check_connection_manager()
            checks.append(connection_check)
            if connection_check.status != HealthStatus.HEALTHY:
                overall_status = HealthStatus.UNHEALTHY
        except Exception as e:
            checks.append(HealthCheck(
                name="connection_manager",
                status=HealthStatus.UNHEALTHY,
                message=f"Connection manager check failed: {str(e)}"
            ))
            overall_status = HealthStatus.UNHEALTHY

        # Check Vectara API connectivity
        try:
            vectara_check = await self._check_vectara_connectivity()
            checks.append(vectara_check)
            if vectara_check.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif vectara_check.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
        except Exception as e:
            checks.append(HealthCheck(
                name="vectara_api",
                status=HealthStatus.UNHEALTHY,
                message=f"Vectara API check failed: {str(e)}"
            ))
            overall_status = HealthStatus.UNHEALTHY

        total_time = round((time.time() - start_time) * 1000, 2)

        return {
            "status": overall_status.value,
            "timestamp": time.time(),
            "response_time_ms": total_time,
            "checks": [
                {
                    "name": check.name,
                    "status": check.status.value,
                    "message": check.message,
                    "response_time_ms": check.response_time_ms,
                    "details": check.details
                }
                for check in checks
            ]
        }

    async def detailed_health_check(self) -> Dict[str, Any]:
        """Comprehensive health check with all system components.

        Provides detailed information about all system components,
        metrics, and configuration. Used for monitoring and debugging.

        Returns:
            Dict: Detailed health status
        """
        checks = []
        metrics = {}
        overall_status = HealthStatus.HEALTHY
        start_time = time.time()

        # Basic server info
        server_info = {
            "uptime_seconds": round(time.time() - self.server_start_time, 2),
            "version": "2.0.0",
            "service": "vectara-mcp-server",
            "pid": os.getpid() if hasattr(os, 'getpid') else None
        }

        # Connection manager health
        try:
            connection_check = await self._check_connection_manager_detailed()
            checks.append(connection_check)
            if connection_check.status != HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
        except Exception as e:
            checks.append(HealthCheck(
                name="connection_manager_detailed",
                status=HealthStatus.UNHEALTHY,
                message=f"Detailed connection check failed: {str(e)}"
            ))
            overall_status = HealthStatus.UNHEALTHY

        # Vectara API connectivity
        try:
            vectara_check = await self._check_vectara_connectivity()
            checks.append(vectara_check)
            if vectara_check.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif vectara_check.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
        except Exception as e:
            checks.append(HealthCheck(
                name="vectara_api_detailed",
                status=HealthStatus.UNHEALTHY,
                message=f"Vectara API detailed check failed: {str(e)}"
            ))
            overall_status = HealthStatus.UNHEALTHY

        # Retry metrics
        try:
            metrics["retry"] = retry_metrics.get_stats()
        except Exception as e:
            logger.warning(f"Failed to get retry metrics: {e}")

        # Memory usage (if available)
        try:
            import psutil
            process = psutil.Process()
            metrics["memory"] = {
                "rss_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                "vms_mb": round(process.memory_info().vms / 1024 / 1024, 2),
                "percent": round(process.memory_percent(), 2)
            }
        except ImportError:
            metrics["memory"] = {"error": "psutil not available"}
        except Exception as e:
            metrics["memory"] = {"error": str(e)}

        total_time = round((time.time() - start_time) * 1000, 2)

        return {
            "status": overall_status.value,
            "timestamp": time.time(),
            "response_time_ms": total_time,
            "server": server_info,
            "checks": [
                {
                    "name": check.name,
                    "status": check.status.value,
                    "message": check.message,
                    "response_time_ms": check.response_time_ms,
                    "details": check.details
                }
                for check in checks
            ],
            "metrics": metrics
        }

    async def _check_connection_manager(self) -> HealthCheck:
        """Check connection manager basic health."""
        start_time = time.time()

        try:
            manager = await get_connection_manager()
            stats = manager.get_stats()

            response_time = round((time.time() - start_time) * 1000, 2)

            if stats["session_initialized"]:
                return HealthCheck(
                    name="connection_manager",
                    status=HealthStatus.HEALTHY,
                    message="Connection manager initialized and ready",
                    response_time_ms=response_time,
                    details={"circuit_breaker_state": stats["circuit_breaker"]["state"]}
                )
            else:
                return HealthCheck(
                    name="connection_manager",
                    status=HealthStatus.UNHEALTHY,
                    message="Connection manager not initialized",
                    response_time_ms=response_time
                )

        except Exception as e:
            response_time = round((time.time() - start_time) * 1000, 2)
            return HealthCheck(
                name="connection_manager",
                status=HealthStatus.UNHEALTHY,
                message=f"Connection manager error: {str(e)}",
                response_time_ms=response_time
            )

    async def _check_connection_manager_detailed(self) -> HealthCheck:
        """Check connection manager detailed health."""
        start_time = time.time()

        try:
            manager = await get_connection_manager()
            stats = manager.get_stats()

            response_time = round((time.time() - start_time) * 1000, 2)

            circuit_state = stats["circuit_breaker"]["state"]
            failure_count = stats["circuit_breaker"]["failure_count"]

            if stats["session_initialized"]:
                if circuit_state == "open":
                    status = HealthStatus.UNHEALTHY
                    message = f"Circuit breaker OPEN with {failure_count} failures"
                elif circuit_state == "half_open":
                    status = HealthStatus.DEGRADED
                    message = "Circuit breaker testing recovery"
                elif failure_count > 0:
                    status = HealthStatus.DEGRADED
                    message = f"Recent failures: {failure_count}"
                else:
                    status = HealthStatus.HEALTHY
                    message = "Connection manager healthy"

                return HealthCheck(
                    name="connection_manager_detailed",
                    status=status,
                    message=message,
                    response_time_ms=response_time,
                    details=stats
                )
            else:
                return HealthCheck(
                    name="connection_manager_detailed",
                    status=HealthStatus.UNHEALTHY,
                    message="Connection manager not initialized",
                    response_time_ms=response_time
                )

        except Exception as e:
            response_time = round((time.time() - start_time) * 1000, 2)
            return HealthCheck(
                name="connection_manager_detailed",
                status=HealthStatus.UNHEALTHY,
                message=f"Connection manager error: {str(e)}",
                response_time_ms=response_time
            )

    async def _check_vectara_connectivity(self) -> HealthCheck:
        """Check Vectara API connectivity."""
        cache_key = "vectara_connectivity"

        # Check cache first
        if cache_key in self.last_check_cache:
            cached_result, cache_time = self.last_check_cache[cache_key]
            if time.time() - cache_time < self.cache_ttl:
                return cached_result

        start_time = time.time()

        try:
            manager = await get_connection_manager()
            health_result = await manager.health_check("https://api.vectara.io")

            response_time = round((time.time() - start_time) * 1000, 2)

            if health_result["status"] == "healthy":
                status = HealthStatus.HEALTHY
                message = f"Vectara API accessible ({health_result['response_time_ms']}ms)"
            else:
                status = HealthStatus.DEGRADED
                message = f"Vectara API issues: {health_result.get('error', 'Unknown error')}"

            result = HealthCheck(
                name="vectara_api",
                status=status,
                message=message,
                response_time_ms=response_time,
                details={
                    "api_response_time_ms": health_result.get("response_time_ms"),
                    "circuit_breaker_state": health_result.get("circuit_breaker_state")
                }
            )

            # Cache the result
            self.last_check_cache[cache_key] = (result, time.time())
            return result

        except Exception as e:
            response_time = round((time.time() - start_time) * 1000, 2)
            result = HealthCheck(
                name="vectara_api",
                status=HealthStatus.UNHEALTHY,
                message=f"Vectara API connectivity failed: {str(e)}",
                response_time_ms=response_time
            )

            # Cache the result
            self.last_check_cache[cache_key] = (result, time.time())
            return result


# Global health checker instance
health_checker = HealthChecker()


# Convenience functions for FastMCP integration
async def get_liveness() -> Dict[str, Any]:
    """Get liveness status."""
    return await health_checker.liveness_check()


async def get_readiness() -> Dict[str, Any]:
    """Get readiness status."""
    return await health_checker.readiness_check()


async def get_detailed_health() -> Dict[str, Any]:
    """Get detailed health status."""
    return await health_checker.detailed_health_check()


# Import os here to avoid issues if not available
import os