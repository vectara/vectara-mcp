import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
import os
import aiohttp
from mcp.server.fastmcp import Context

from vectara_mcp.server import (
    setup_vectara_api_key,
    clear_vectara_api_key
)


class TestApiKeyManagement:
    """Test suite for API key management tools"""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context for testing"""
        context = AsyncMock(spec=Context)
        context.info = MagicMock()
        context.report_progress = AsyncMock()
        return context

    @pytest.fixture(autouse=True)
    def clear_stored_api_key(self):
        """Clear stored API key before each test"""
        import vectara_mcp.server
        vectara_mcp.server._stored_api_key = None
        yield
        vectara_mcp.server._stored_api_key = None

    @pytest.mark.asyncio
    async def test_setup_vectara_api_key_missing_key(self, mock_context):
        """Test setup_vectara_api_key with missing API key"""
        result = await setup_vectara_api_key(
            api_key="",
            ctx=mock_context
        )
        assert result == "API key is required."

    @pytest.mark.asyncio
    @patch('vectara_mcp.server._make_api_request')
    async def test_setup_vectara_api_key_invalid_key(self, mock_api_request, mock_context):
        """Test setup_vectara_api_key with invalid API key (401 response)"""
        mock_api_request.side_effect = Exception("API error 401: API key error")

        result = await setup_vectara_api_key(
            api_key="invalid-key",
            ctx=mock_context
        )

        assert result == "Invalid API key. Please check your Vectara API key and try again."

    @pytest.mark.asyncio
    @patch('vectara_mcp.server._make_api_request')
    async def test_setup_vectara_api_key_success(self, mock_api_request, mock_context):
        """Test successful setup_vectara_api_key call"""
        mock_api_request.side_effect = Exception("Corpus not found")  # Valid API key but corpus doesn't exist

        result = await setup_vectara_api_key(
            api_key="valid-api-key-12345",
            ctx=mock_context
        )

        assert "API key configured successfully: vali***2345" in result
        mock_context.info.assert_called_once()

    @pytest.mark.asyncio
    @patch('vectara_mcp.server._make_api_request')
    async def test_setup_vectara_api_key_network_error(self, mock_api_request, mock_context):
        """Test setup_vectara_api_key with network error"""
        mock_api_request.side_effect = Exception("Network error")

        result = await setup_vectara_api_key(
            api_key="test-key",
            ctx=mock_context
        )

        assert result == "API validation failed: Network error"

    @pytest.mark.asyncio
    async def test_clear_vectara_api_key(self, mock_context):
        """Test clear_vectara_api_key"""
        # First set an API key
        import vectara_mcp.server
        vectara_mcp.server._stored_api_key = "test-key"

        result = await clear_vectara_api_key(ctx=mock_context)

        assert result == "API key cleared from server memory."
        assert vectara_mcp.server._stored_api_key is None
        mock_context.info.assert_called_once_with("Clearing stored Vectara API key")

