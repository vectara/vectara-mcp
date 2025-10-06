import pytest
import pytest_asyncio
import os
import json
from dotenv import load_dotenv
from mcp.server.fastmcp import Context
from unittest.mock import AsyncMock, MagicMock

from vectara_mcp.server import (
    ask_vectara,
    search_vectara,
    correct_hallucinations,
    eval_factual_consistency
)

# Load environment variables
load_dotenv()

# Test configuration
API_KEY = os.getenv("VECTARA_API_KEY")
CORPUS_KEYS = os.getenv("VECTARA_CORPUS_KEYS", "").split(",") if os.getenv("VECTARA_CORPUS_KEYS") else []
TEST_TEXT = os.getenv("TEST_TEXT", "The capital of France is Berlin. The Eiffel Tower is located in London.")
TEST_SOURCE_DOCS = os.getenv("TEST_SOURCE_DOCS", "Paris is the capital of France. The Eiffel Tower is located in Paris, France.|London is the capital of the United Kingdom.").split("|")

# Skip integration tests if no API key provided
pytestmark = pytest.mark.skipif(
    not API_KEY or not CORPUS_KEYS or CORPUS_KEYS == [""],
    reason="Integration tests require VECTARA_API_KEY and VECTARA_CORPUS_KEYS in .env file"
)


class TestVectaraIntegration:
    """Integration tests for Vectara MCP tools using real API endpoints"""

    @pytest_asyncio.fixture(autouse=True)
    async def cleanup_connection_manager(self):
        """Cleanup connection manager before and after each test"""
        from vectara_mcp.connection_manager import ConnectionManager, connection_manager
        # Clean up before test
        await connection_manager.close()
        ConnectionManager.reset_instance()
        yield
        # Clean up after test
        await connection_manager.close()
        ConnectionManager.reset_instance()

    @pytest.fixture
    def mock_context(self):
        """Create a mock context for testing"""
        context = AsyncMock(spec=Context)
        context.info = MagicMock()  # Non-async mock to avoid coroutine warnings
        context.report_progress = AsyncMock()  # Keep async since this is actually async
        return context

    @pytest.mark.asyncio
    async def test_ask_vectara_integration(self, mock_context):
        """Test ask_vectara with real API to determine response format"""
        if not API_KEY or not CORPUS_KEYS:
            pytest.skip("Missing API credentials")

        query = "What is the main topic of this corpus?"

        # Set API key in environment since integration tests need it
        import vectara_mcp.server
        vectara_mcp.server._stored_api_key = API_KEY

        result = await ask_vectara(
            query=query,
            ctx=mock_context,
            corpus_keys=CORPUS_KEYS,
            max_used_search_results=5
        )

        # Print result for analysis
        print(f"\n=== ask_vectara result type: {type(result)} ===")
        print(f"Result: {result}")
        print("=" * 50)

        # Basic validation
        assert isinstance(result, dict)
        assert "summary" in result
        assert "citations" in result
        assert "error" not in result

        return result

    @pytest.mark.asyncio
    async def test_search_vectara_integration(self, mock_context):
        """Test search_vectara with real API to determine response format"""
        if not API_KEY or not CORPUS_KEYS:
            pytest.skip("Missing API credentials")

        query = "main topics"

        # Set API key in environment since integration tests need it
        import vectara_mcp.server
        vectara_mcp.server._stored_api_key = API_KEY

        result = await search_vectara(
            query=query,
            ctx=mock_context,
            corpus_keys=CORPUS_KEYS
        )

        # Print result for analysis
        print(f"\n=== search_vectara result type: {type(result)} ===")
        print(f"Result: {result}")
        print("=" * 50)

        # Basic validation
        assert isinstance(result, dict)
        assert "search_results" in result
        assert "error" not in result

        return result

    @pytest.mark.asyncio
    async def test_correct_hallucinations_integration(self, mock_context):
        """Test correct_hallucinations with real API to determine response format"""
        if not API_KEY:
            pytest.skip("Missing API key")

        # Set API key in environment since integration tests need it
        import vectara_mcp.server
        vectara_mcp.server._stored_api_key = API_KEY

        result = await correct_hallucinations(
            generated_text=TEST_TEXT,
            documents=TEST_SOURCE_DOCS,
            ctx=mock_context
        )

        # Print result for analysis
        print(f"\n=== correct_hallucinations result type: {type(result)} ===")
        print(f"Result: {result}")
        print("=" * 50)

        # Basic validation - VHC functions now return dict
        assert isinstance(result, dict)
        assert "error" not in result

        print(f"Result structure: {json.dumps(result, indent=2)}")

        return result

    @pytest.mark.asyncio
    async def test_eval_factual_consistency_integration(self, mock_context):
        """Test eval_factual_consistency with real API to determine response format"""
        if not API_KEY:
            pytest.skip("Missing API key")

        # Set API key in environment since integration tests need it
        import vectara_mcp.server
        vectara_mcp.server._stored_api_key = API_KEY

        result = await eval_factual_consistency(
            generated_text=TEST_TEXT,
            documents=TEST_SOURCE_DOCS,
            ctx=mock_context
        )

        # Print result for analysis
        print(f"\n=== eval_factual_consistency result type: {type(result)} ===")
        print(f"Result: {result}")
        print("=" * 50)

        # Basic validation - VHC functions now return dict
        assert isinstance(result, dict)
        assert "error" not in result

        print(f"Result structure: {json.dumps(result, indent=2)}")

        return result

    @pytest.mark.asyncio
    async def test_all_endpoints_and_analyze_responses(self, mock_context):
        """Run all endpoints and analyze response formats for docstring updates"""
        if not API_KEY:
            pytest.skip("Missing API key")

        print("\n" + "="*80)
        print("COMPREHENSIVE RESPONSE FORMAT ANALYSIS")
        print("="*80)

        # Test all endpoints
        results = {}

        if CORPUS_KEYS and CORPUS_KEYS != [""]:
            print("\n--- Testing ask_vectara ---")
            results['ask_vectara'] = await self.test_ask_vectara_integration(mock_context)

            print("\n--- Testing search_vectara ---")
            results['search_vectara'] = await self.test_search_vectara_integration(mock_context)
        else:
            print("\nSkipping corpus-based tests (no corpus keys)")

        print("\n--- Testing correct_hallucinations ---")
        results['correct_hallucinations'] = await self.test_correct_hallucinations_integration(mock_context)

        print("\n--- Testing eval_factual_consistency ---")
        results['eval_factual_consistency'] = await self.test_eval_factual_consistency_integration(mock_context)

        # Generate docstring recommendations
        print("\n" + "="*80)
        print("DOCSTRING UPDATE RECOMMENDATIONS")
        print("="*80)

        for tool_name, result in results.items():
            print(f"\n--- {tool_name} ---")
            if isinstance(result, dict):
                if "error" in result:
                    print(f"❌ API Error: {result['error']}")
                else:
                    print(f"✅ Returns dict with structure:")
                    print(f"   Keys: {list(result.keys())}")
                    for key, value in result.items():
                        print(f"   - {key}: {type(value).__name__}")
            else:
                print(f"⚠️  Unexpected return type: {type(result).__name__}")
                print(f"   Value: {result}")

        print("\n" + "="*80)