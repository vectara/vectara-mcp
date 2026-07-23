import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from mcp.server.fastmcp import Context

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
    _extract_chat_response,
)


class TestAgentManagement:

    @pytest.fixture
    def mock_context(self):
        context = AsyncMock(spec=Context)
        context.info = MagicMock()
        context.report_progress = AsyncMock()
        return context

    @pytest.fixture(autouse=True)
    def clear_stored_api_key(self):
        import vectara_mcp.server
        vectara_mcp.server._stored_api_key = None
        yield
        vectara_mcp.server._stored_api_key = None

    @pytest.fixture
    def mock_api_key(self):
        import vectara_mcp.server
        vectara_mcp.server._stored_api_key = "test-api-key"
        return "test-api-key"

    # --- list_agents ---

    @pytest.mark.asyncio
    @patch.dict('os.environ', {}, clear=True)
    async def test_list_agents_missing_api_key(self, mock_context):
        result = await list_agents(ctx=mock_context)
        assert "error" in result
        assert "API key not configured" in result["error"]

    @pytest.mark.asyncio
    @patch('vectara_mcp.agents._make_api_request')
    async def test_list_agents_success(self, mock_request, mock_context, mock_api_key):
        mock_request.return_value = {
            "agents": [{"key": "agent1", "name": "Test Agent"}],
            "metadata": {"page_key": "next123"}
        }

        result = await list_agents(ctx=mock_context)

        assert "agents" in result
        assert len(result["agents"]) == 1
        assert result["agents"][0]["key"] == "agent1"
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "GET"

    @pytest.mark.asyncio
    @patch('vectara_mcp.agents._make_api_request')
    async def test_list_agents_with_filters(self, mock_request, mock_context, mock_api_key):
        mock_request.return_value = {"agents": []}

        await list_agents(ctx=mock_context, filter_name="support", enabled=True, limit=5)

        call_kwargs = mock_request.call_args
        params = call_kwargs.kwargs["params"]
        assert params["filter"] == "support"
        assert params["enabled"] == "true"
        assert params["limit"] == 5

    @pytest.mark.asyncio
    @patch('vectara_mcp.agents._make_api_request')
    async def test_list_agents_with_pagination(self, mock_request, mock_context, mock_api_key):
        mock_request.return_value = {"agents": []}

        await list_agents(ctx=mock_context, page_key="abc123")

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["params"]["page_key"] == "abc123"

    @pytest.mark.asyncio
    @patch('vectara_mcp.agents._make_api_request')
    async def test_list_agents_exception(self, mock_request, mock_context, mock_api_key):
        mock_request.side_effect = Exception("Network error")

        result = await list_agents(ctx=mock_context)

        assert result == {"error": "Error with list agents: Network error"}

    # --- get_agent ---

    @pytest.mark.asyncio
    async def test_get_agent_missing_key(self, mock_context, mock_api_key):
        result = await get_agent(agent_key="", ctx=mock_context)
        assert result == {"error": "agent_key is required."}

    @pytest.mark.asyncio
    @patch.dict('os.environ', {}, clear=True)
    async def test_get_agent_missing_api_key(self, mock_context):
        result = await get_agent(agent_key="agent1", ctx=mock_context)
        assert "API key not configured" in result["error"]

    @pytest.mark.asyncio
    @patch('vectara_mcp.agents._make_api_request')
    async def test_get_agent_success(self, mock_request, mock_context, mock_api_key):
        mock_request.return_value = {
            "key": "agent1",
            "name": "Support Agent",
            "tool_configurations": {"search": {"type": "corpora_search"}},
        }

        result = await get_agent(agent_key="agent1", ctx=mock_context)

        assert result["key"] == "agent1"
        assert result["name"] == "Support Agent"
        mock_request.assert_called_once()
        assert "agents/agent1" in mock_request.call_args.kwargs.get("url", mock_request.call_args[0][0])

    @pytest.mark.asyncio
    @patch('vectara_mcp.agents._make_api_request')
    async def test_get_agent_exception(self, mock_request, mock_context, mock_api_key):
        mock_request.side_effect = Exception("Not found")

        result = await get_agent(agent_key="agent1", ctx=mock_context)

        assert result == {"error": "Error with get agent: Not found"}

    # --- create_agent ---

    @pytest.mark.asyncio
    async def test_create_agent_missing_name(self, mock_context, mock_api_key):
        result = await create_agent(name="", ctx=mock_context)
        assert result == {"error": "name is required."}

    @pytest.mark.asyncio
    @patch.dict('os.environ', {}, clear=True)
    async def test_create_agent_missing_api_key(self, mock_context):
        result = await create_agent(name="My Agent", ctx=mock_context)
        assert "API key not configured" in result["error"]

    @pytest.mark.asyncio
    @patch('vectara_mcp.agents._make_api_request')
    async def test_create_agent_minimal(self, mock_request, mock_context, mock_api_key):
        mock_request.return_value = {"key": "my_agent", "name": "My Agent"}

        result = await create_agent(name="My Agent", ctx=mock_context)

        assert result["name"] == "My Agent"
        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "POST"
        payload = call_kwargs.kwargs["payload"]
        assert payload == {"name": "My Agent"}

    @pytest.mark.asyncio
    @patch('vectara_mcp.agents._make_api_request')
    async def test_create_agent_full_config(self, mock_request, mock_context, mock_api_key):
        mock_request.return_value = {"key": "support", "name": "Support Agent"}

        tool_configs = {"search": {"type": "corpora_search"}}
        model = {"name": "gpt-4o", "parameters": {"temperature": 0.7}}
        steps = {"main": {"instructions": [{"type": "inline", "template": "Help the user"}]}}

        result = await create_agent(
            name="Support Agent",
            ctx=mock_context,
            key="support",
            description="Handles support",
            tool_configurations=tool_configs,
            model=model,
            first_step_name="main",
            steps=steps,
            metadata={"team": "support"},
        )

        payload = mock_request.call_args.kwargs["payload"]
        assert payload["key"] == "support"
        assert payload["name"] == "Support Agent"
        assert payload["description"] == "Handles support"
        assert payload["tool_configurations"] == tool_configs
        assert payload["model"] == model
        assert payload["first_step_name"] == "main"
        assert payload["steps"] == steps
        assert payload["metadata"] == {"team": "support"}

    @pytest.mark.asyncio
    @patch('vectara_mcp.agents._make_api_request')
    async def test_create_agent_exception(self, mock_request, mock_context, mock_api_key):
        mock_request.side_effect = Exception("Bad request")

        result = await create_agent(name="Agent", ctx=mock_context)

        assert result == {"error": "Error with create agent: Bad request"}

    # --- update_agent ---

    @pytest.mark.asyncio
    async def test_update_agent_missing_key(self, mock_context, mock_api_key):
        result = await update_agent(agent_key="", ctx=mock_context, name="New Name")
        assert result == {"error": "agent_key is required."}

    @pytest.mark.asyncio
    async def test_update_agent_no_fields(self, mock_context, mock_api_key):
        result = await update_agent(agent_key="agent1", ctx=mock_context)
        assert result == {"error": "At least one field to update is required."}

    @pytest.mark.asyncio
    @patch('vectara_mcp.agents._make_api_request')
    async def test_update_agent_success(self, mock_request, mock_context, mock_api_key):
        mock_request.return_value = {"key": "agent1", "name": "Updated Name"}

        result = await update_agent(
            agent_key="agent1", ctx=mock_context, name="Updated Name", enabled=False
        )

        assert result["name"] == "Updated Name"
        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs["method"] == "PATCH"
        payload = call_kwargs.kwargs["payload"]
        assert payload["name"] == "Updated Name"
        assert payload["enabled"] is False

    # --- delete_agent ---

    @pytest.mark.asyncio
    async def test_delete_agent_missing_key(self, mock_context, mock_api_key):
        result = await delete_agent(agent_key="", ctx=mock_context)
        assert result == {"error": "agent_key is required."}

    @pytest.mark.asyncio
    @patch('vectara_mcp.agents._make_api_request')
    async def test_delete_agent_success(self, mock_request, mock_context, mock_api_key):
        mock_request.return_value = {"status": "deleted"}

        result = await delete_agent(agent_key="agent1", ctx=mock_context)

        assert result == {"status": "deleted"}
        assert mock_request.call_args.kwargs["method"] == "DELETE"


class TestSessionManagement:

    @pytest.fixture
    def mock_context(self):
        context = AsyncMock(spec=Context)
        context.info = MagicMock()
        context.report_progress = AsyncMock()
        return context

    @pytest.fixture(autouse=True)
    def clear_stored_api_key(self):
        import vectara_mcp.server
        vectara_mcp.server._stored_api_key = None
        yield
        vectara_mcp.server._stored_api_key = None

    @pytest.fixture
    def mock_api_key(self):
        import vectara_mcp.server
        vectara_mcp.server._stored_api_key = "test-api-key"
        return "test-api-key"

    # --- create_session ---

    @pytest.mark.asyncio
    async def test_create_session_missing_agent_key(self, mock_context, mock_api_key):
        result = await create_session(agent_key="", ctx=mock_context)
        assert result == {"error": "agent_key is required."}

    @pytest.mark.asyncio
    @patch.dict('os.environ', {}, clear=True)
    async def test_create_session_missing_api_key(self, mock_context):
        result = await create_session(agent_key="agent1", ctx=mock_context)
        assert "API key not configured" in result["error"]

    @pytest.mark.asyncio
    @patch('vectara_mcp.agents._make_api_request')
    async def test_create_session_minimal(self, mock_request, mock_context, mock_api_key):
        mock_request.return_value = {"key": "sess_abc", "agent_key": "agent1"}

        result = await create_session(agent_key="agent1", ctx=mock_context)

        assert result["key"] == "sess_abc"
        payload = mock_request.call_args.kwargs["payload"]
        assert payload == {}

    @pytest.mark.asyncio
    @patch('vectara_mcp.agents._make_api_request')
    async def test_create_session_with_metadata(self, mock_request, mock_context, mock_api_key):
        mock_request.return_value = {"key": "my_session", "agent_key": "agent1"}

        await create_session(
            agent_key="agent1",
            ctx=mock_context,
            session_key="my_session",
            name="Support Session",
            metadata={"customer_id": "123"},
            tti_minutes=60,
        )

        payload = mock_request.call_args.kwargs["payload"]
        assert payload["key"] == "my_session"
        assert payload["name"] == "Support Session"
        assert payload["metadata"] == {"customer_id": "123"}
        assert payload["tti_minutes"] == 60

    # --- list_sessions ---

    @pytest.mark.asyncio
    async def test_list_sessions_missing_agent_key(self, mock_context, mock_api_key):
        result = await list_sessions(agent_key="", ctx=mock_context)
        assert result == {"error": "agent_key is required."}

    @pytest.mark.asyncio
    @patch('vectara_mcp.agents._make_api_request')
    async def test_list_sessions_success(self, mock_request, mock_context, mock_api_key):
        mock_request.return_value = {
            "sessions": [{"key": "sess1"}, {"key": "sess2"}]
        }

        result = await list_sessions(agent_key="agent1", ctx=mock_context)

        assert len(result["sessions"]) == 2
        assert mock_request.call_args.kwargs["method"] == "GET"

    # --- get_session ---

    @pytest.mark.asyncio
    async def test_get_session_missing_keys(self, mock_context, mock_api_key):
        result = await get_session(agent_key="", session_key="sess1", ctx=mock_context)
        assert result == {"error": "agent_key and session_key are required."}

        result = await get_session(agent_key="agent1", session_key="", ctx=mock_context)
        assert result == {"error": "agent_key and session_key are required."}

    @pytest.mark.asyncio
    @patch('vectara_mcp.agents._make_api_request')
    async def test_get_session_success(self, mock_request, mock_context, mock_api_key):
        mock_request.return_value = {
            "key": "sess1",
            "agent_key": "agent1",
            "session_context_usage": {"total_tokens": 150},
        }

        result = await get_session(agent_key="agent1", session_key="sess1", ctx=mock_context)

        assert result["key"] == "sess1"
        assert result["session_context_usage"]["total_tokens"] == 150

    # --- delete_session ---

    @pytest.mark.asyncio
    async def test_delete_session_missing_keys(self, mock_context, mock_api_key):
        result = await delete_session(agent_key="agent1", session_key="", ctx=mock_context)
        assert result == {"error": "agent_key and session_key are required."}

    @pytest.mark.asyncio
    @patch('vectara_mcp.agents._make_api_request')
    async def test_delete_session_success(self, mock_request, mock_context, mock_api_key):
        mock_request.return_value = {"status": "deleted"}

        result = await delete_session(agent_key="agent1", session_key="sess1", ctx=mock_context)

        assert result == {"status": "deleted"}
        assert mock_request.call_args.kwargs["method"] == "DELETE"


class TestChatAndEvents:

    @pytest.fixture
    def mock_context(self):
        context = AsyncMock(spec=Context)
        context.info = MagicMock()
        context.report_progress = AsyncMock()
        return context

    @pytest.fixture(autouse=True)
    def clear_stored_api_key(self):
        import vectara_mcp.server
        vectara_mcp.server._stored_api_key = None
        yield
        vectara_mcp.server._stored_api_key = None

    @pytest.fixture
    def mock_api_key(self):
        import vectara_mcp.server
        vectara_mcp.server._stored_api_key = "test-api-key"
        return "test-api-key"

    # --- chat_with_agent ---

    @pytest.mark.asyncio
    async def test_chat_missing_keys(self, mock_context, mock_api_key):
        result = await chat_with_agent(
            agent_key="", session_key="sess1", message="hi", ctx=mock_context
        )
        assert result == {"error": "agent_key and session_key are required."}

    @pytest.mark.asyncio
    async def test_chat_missing_message(self, mock_context, mock_api_key):
        result = await chat_with_agent(
            agent_key="agent1", session_key="sess1", message="", ctx=mock_context
        )
        assert result == {"error": "message is required."}

    @pytest.mark.asyncio
    @patch.dict('os.environ', {}, clear=True)
    async def test_chat_missing_api_key(self, mock_context):
        result = await chat_with_agent(
            agent_key="agent1", session_key="sess1", message="hi", ctx=mock_context
        )
        assert "API key not configured" in result["error"]

    @pytest.mark.asyncio
    @patch('vectara_mcp.agents._make_api_request')
    async def test_chat_success_simple(self, mock_request, mock_context, mock_api_key):
        mock_request.return_value = {
            "events": [
                {"type": "agent_output", "id": "evt1", "content": "Hello! How can I help?"}
            ]
        }

        result = await chat_with_agent(
            agent_key="agent1", session_key="sess1", message="hi", ctx=mock_context
        )

        assert result["agent_output"] == "Hello! How can I help?"
        assert "tool_calls" not in result
        assert len(result["events_summary"]) == 1

        payload = mock_request.call_args.kwargs["payload"]
        assert payload["type"] == "input_message"
        assert payload["messages"][0]["content"] == "hi"
        assert payload["stream_response"] is False

    @pytest.mark.asyncio
    @patch('vectara_mcp.agents._make_api_request')
    async def test_chat_success_with_tool_calls(self, mock_request, mock_context, mock_api_key):
        mock_request.return_value = {
            "events": [
                {
                    "type": "tool_input",
                    "id": "evt1",
                    "tool_config_name": "search",
                    "arguments": {"query": "vectara pricing"},
                },
                {
                    "type": "tool_output",
                    "id": "evt2",
                    "output": "Vectara offers free and paid plans.",
                },
                {
                    "type": "agent_output",
                    "id": "evt3",
                    "content": "Based on my search, Vectara offers free and paid plans.",
                },
            ]
        }

        result = await chat_with_agent(
            agent_key="agent1", session_key="sess1", message="pricing?", ctx=mock_context
        )

        assert "Based on my search" in result["agent_output"]
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["tool"] == "search"
        assert result["tool_calls"][0]["arguments"] == {"query": "vectara pricing"}
        assert result["tool_calls"][0]["output"] == "Vectara offers free and paid plans."
        assert len(result["events_summary"]) == 3

    @pytest.mark.asyncio
    @patch('vectara_mcp.agents._make_api_request')
    async def test_chat_exception(self, mock_request, mock_context, mock_api_key):
        mock_request.side_effect = Exception("Timeout")

        result = await chat_with_agent(
            agent_key="agent1", session_key="sess1", message="hi", ctx=mock_context
        )

        assert result == {"error": "Error with chat with agent: Timeout"}

    # --- _extract_chat_response ---

    def test_extract_empty_events(self):
        result = _extract_chat_response({"events": []})
        assert result == {"events": []}

    def test_extract_no_events_key(self):
        raw = {"some_other_field": "value"}
        result = _extract_chat_response(raw)
        assert result == raw

    def test_extract_structured_output(self):
        result = _extract_chat_response({
            "events": [
                {"type": "structured_output", "id": "evt1", "fields": {"intent": "billing"}}
            ]
        })
        assert '"intent"' in result["agent_output"]
        assert '"billing"' in result["agent_output"]

    # --- list_events ---

    @pytest.mark.asyncio
    async def test_list_events_missing_keys(self, mock_context, mock_api_key):
        result = await list_events(agent_key="", session_key="sess1", ctx=mock_context)
        assert result == {"error": "agent_key and session_key are required."}

    @pytest.mark.asyncio
    @patch('vectara_mcp.agents._make_api_request')
    async def test_list_events_success(self, mock_request, mock_context, mock_api_key):
        mock_request.return_value = {
            "events": [
                {"type": "input_message", "id": "evt1"},
                {"type": "agent_output", "id": "evt2"},
            ]
        }

        result = await list_events(
            agent_key="agent1", session_key="sess1", ctx=mock_context
        )

        assert len(result["events"]) == 2
        assert mock_request.call_args.kwargs["method"] == "GET"
        assert mock_request.call_args.kwargs["params"]["limit"] == 20

    @pytest.mark.asyncio
    @patch('vectara_mcp.agents._make_api_request')
    async def test_list_events_with_pagination(self, mock_request, mock_context, mock_api_key):
        mock_request.return_value = {"events": []}

        await list_events(
            agent_key="agent1", session_key="sess1", ctx=mock_context,
            limit=5, page_key="page2"
        )

        params = mock_request.call_args.kwargs["params"]
        assert params["limit"] == 5
        assert params["page_key"] == "page2"

    @pytest.mark.asyncio
    @patch('vectara_mcp.agents._make_api_request')
    async def test_list_events_exception(self, mock_request, mock_context, mock_api_key):
        mock_request.side_effect = Exception("Server error")

        result = await list_events(
            agent_key="agent1", session_key="sess1", ctx=mock_context
        )

        assert result == {"error": "Error with list events: Server error"}
