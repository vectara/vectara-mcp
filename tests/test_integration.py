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
from vectara_mcp.agents import (
    list_agents,
    get_agent,
    create_agent,
    update_agent,
    delete_agent,
    create_session,
    list_sessions,
    get_session,
    delete_session,
    chat_with_agent,
    list_events,
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


# Agent integration tests require API key + an agent key
AGENT_KEY = os.getenv("VECTARA_AGENT_KEY", "")

agent_pytestmark = pytest.mark.skipif(
    not API_KEY or not AGENT_KEY,
    reason="Agent integration tests require VECTARA_API_KEY and VECTARA_AGENT_KEY in .env file"
)


@agent_pytestmark
class TestAgentIntegration:
    """Integration tests for Vectara Agent MCP tools using real API endpoints.

    Set VECTARA_API_KEY and VECTARA_AGENT_KEY in .env to run these tests.
    """

    @pytest_asyncio.fixture(autouse=True)
    async def cleanup_connection_manager(self):
        from vectara_mcp.connection_manager import ConnectionManager, connection_manager
        await connection_manager.close()
        ConnectionManager.reset_instance()
        yield
        await connection_manager.close()
        ConnectionManager.reset_instance()

    @pytest.fixture(autouse=True)
    def set_api_key(self):
        import vectara_mcp.server
        vectara_mcp.server._stored_api_key = API_KEY
        yield
        vectara_mcp.server._stored_api_key = None

    @pytest.fixture
    def mock_context(self):
        context = AsyncMock(spec=Context)
        context.info = MagicMock()
        context.report_progress = AsyncMock()
        return context

    @pytest.mark.asyncio
    async def test_list_agents_integration(self, mock_context):
        result = await list_agents(ctx=mock_context, limit=5)

        print(f"\n=== list_agents result ===")
        print(f"Result: {json.dumps(result, indent=2, default=str)}")

        assert isinstance(result, dict)
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_get_agent_integration(self, mock_context):
        result = await get_agent(agent_key=AGENT_KEY, ctx=mock_context)

        print(f"\n=== get_agent result ===")
        print(f"Result keys: {list(result.keys())}")

        assert isinstance(result, dict)
        assert "error" not in result
        assert result.get("key") == AGENT_KEY

    @pytest.mark.asyncio
    async def test_agent_session_chat_lifecycle(self, mock_context):
        """End-to-end: create session -> chat -> list events -> delete session."""
        import time
        session_result = await create_session(
            agent_key=AGENT_KEY,
            ctx=mock_context,
            name=f"mcp-integ-test-{int(time.time())}",
        )

        print(f"\n=== create_session result ===")
        print(f"Result: {json.dumps(session_result, indent=2, default=str)}")

        assert isinstance(session_result, dict)
        assert "error" not in session_result
        session_key = session_result.get("key")
        assert session_key

        try:
            sessions_result = await list_sessions(
                agent_key=AGENT_KEY, ctx=mock_context, limit=5
            )
            assert "error" not in sessions_result

            get_result = await get_session(
                agent_key=AGENT_KEY, session_key=session_key, ctx=mock_context
            )
            assert "error" not in get_result
            assert get_result.get("key") == session_key

            chat_result = await chat_with_agent(
                agent_key=AGENT_KEY,
                session_key=session_key,
                message="Hello, this is an integration test. Please reply briefly.",
                ctx=mock_context,
            )

            print(f"\n=== chat_with_agent result ===")
            print(f"Result: {json.dumps(chat_result, indent=2, default=str)}")

            assert isinstance(chat_result, dict)
            assert "error" not in chat_result
            assert chat_result.get("agent_output")

            events_result = await list_events(
                agent_key=AGENT_KEY, session_key=session_key, ctx=mock_context
            )

            print(f"\n=== list_events result ===")
            print(f"Result: {json.dumps(events_result, indent=2, default=str)}")

            assert "error" not in events_result

        finally:
            delete_result = await delete_session(
                agent_key=AGENT_KEY, session_key=session_key, ctx=mock_context
            )
            print(f"\n=== delete_session result ===")
            print(f"Result: {json.dumps(delete_result, indent=2, default=str)}")

    @pytest.mark.asyncio
    async def test_create_and_delete_agent(self, mock_context):
        """End-to-end: create agent -> verify -> update -> delete."""
        create_result = await create_agent(
            name="MCP Integration Test Agent",
            ctx=mock_context,
            description="Temporary agent created by integration tests",
            model={"name": "gpt-4o", "parameters": {"temperature": 0.5}},
            first_step_name="main",
            steps={
                "main": {
                    "instructions": [
                        {"type": "inline", "name": "system", "template": "You are a helpful assistant."}
                    ],
                    "output_parser": {"type": "default"},
                }
            },
        )

        print(f"\n=== create_agent result ===")
        print(f"Result: {json.dumps(create_result, indent=2, default=str)}")

        assert isinstance(create_result, dict)
        assert "error" not in create_result
        new_agent_key = create_result.get("key")
        assert new_agent_key

        try:
            get_result = await get_agent(agent_key=new_agent_key, ctx=mock_context)
            assert get_result.get("name") == "MCP Integration Test Agent"

            update_result = await update_agent(
                agent_key=new_agent_key,
                ctx=mock_context,
                description="Updated by integration test",
            )
            assert "error" not in update_result

        finally:
            delete_result = await delete_agent(agent_key=new_agent_key, ctx=mock_context)
            print(f"\n=== delete_agent result ===")
            print(f"Result: {json.dumps(delete_result, indent=2, default=str)}")

    @pytest.mark.asyncio
    async def test_list_agents_pagination(self, mock_context):
        """Test that list_agents respects limit and returns page_key."""
        result = await list_agents(ctx=mock_context, limit=1)

        assert "error" not in result
        agents = result.get("agents", [])
        assert len(agents) <= 1

        page_key = result.get("metadata", {}).get("page_key", "")
        if page_key:
            result2 = await list_agents(ctx=mock_context, limit=1, page_key=page_key)
            assert "error" not in result2

    @pytest.mark.asyncio
    async def test_list_agents_filter(self, mock_context):
        """Test filtering agents by name."""
        result = await list_agents(ctx=mock_context, filter_name="SDK")

        assert "error" not in result
        agents = result.get("agents", [])
        for agent in agents:
            assert "SDK" in agent.get("name", "") or "sdk" in agent.get("name", "").lower()

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self, mock_context):
        """Test get_agent with a non-existent key."""
        result = await get_agent(agent_key="nonexistent_agent_key_12345", ctx=mock_context)

        assert "error" in result

    @pytest.mark.asyncio
    async def test_update_agent_integration(self, mock_context):
        """Test updating an existing agent's description."""
        import time
        original = await get_agent(agent_key=AGENT_KEY, ctx=mock_context)
        original_desc = original.get("description", "")

        new_desc = f"Updated at {int(time.time())} by integration test"
        result = await update_agent(
            agent_key=AGENT_KEY, ctx=mock_context, description=new_desc,
        )

        assert "error" not in result

        # Verify the update took effect
        updated = await get_agent(agent_key=AGENT_KEY, ctx=mock_context)
        assert updated.get("description") == new_desc

        # Restore original
        await update_agent(
            agent_key=AGENT_KEY, ctx=mock_context, description=original_desc,
        )

    @pytest.mark.asyncio
    async def test_session_with_metadata(self, mock_context):
        """Test creating a session with metadata and verifying it's stored."""
        import time
        metadata = {"customer_id": "test-123", "source": "integration_test"}
        session_result = await create_session(
            agent_key=AGENT_KEY,
            ctx=mock_context,
            name=f"meta-test-{int(time.time())}",
            metadata=metadata,
        )

        assert "error" not in session_result
        session_key = session_result.get("key")
        assert session_key

        try:
            get_result = await get_session(
                agent_key=AGENT_KEY, session_key=session_key, ctx=mock_context
            )
            assert "error" not in get_result
            assert get_result.get("metadata", {}).get("customer_id") == "test-123"
            assert get_result.get("metadata", {}).get("source") == "integration_test"
        finally:
            await delete_session(
                agent_key=AGENT_KEY, session_key=session_key, ctx=mock_context
            )

    @pytest.mark.asyncio
    async def test_multi_turn_chat(self, mock_context):
        """Test multiple chat turns maintain conversation context."""
        import time
        session_result = await create_session(
            agent_key=AGENT_KEY,
            ctx=mock_context,
            name=f"multi-turn-{int(time.time())}",
        )

        assert "error" not in session_result
        session_key = session_result["key"]

        try:
            # Turn 1
            chat1 = await chat_with_agent(
                agent_key=AGENT_KEY, session_key=session_key,
                message="Remember this number: 42.", ctx=mock_context,
            )
            assert "error" not in chat1
            assert chat1.get("agent_output")

            # Turn 2 — ask about context from turn 1
            chat2 = await chat_with_agent(
                agent_key=AGENT_KEY, session_key=session_key,
                message="What number did I ask you to remember?", ctx=mock_context,
            )
            assert "error" not in chat2
            assert chat2.get("agent_output")
            assert "42" in chat2["agent_output"]

            # Verify events accumulated
            events_result = await list_events(
                agent_key=AGENT_KEY, session_key=session_key, ctx=mock_context
            )
            assert len(events_result.get("events", [])) >= 4
        finally:
            await delete_session(
                agent_key=AGENT_KEY, session_key=session_key, ctx=mock_context
            )

    @pytest.mark.asyncio
    async def test_list_events_pagination(self, mock_context):
        """Test listing events with limit."""
        import time
        session_result = await create_session(
            agent_key=AGENT_KEY, ctx=mock_context,
            name=f"evt-page-{int(time.time())}",
        )
        session_key = session_result["key"]

        try:
            await chat_with_agent(
                agent_key=AGENT_KEY, session_key=session_key,
                message="Hello", ctx=mock_context,
            )

            result = await list_events(
                agent_key=AGENT_KEY, session_key=session_key,
                ctx=mock_context, limit=1,
            )

            assert "error" not in result
            assert len(result.get("events", [])) <= 1
        finally:
            await delete_session(
                agent_key=AGENT_KEY, session_key=session_key, ctx=mock_context
            )
