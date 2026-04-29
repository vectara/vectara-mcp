"""Vectara Agents tools for the MCP server.

Provides tools for managing agents, sessions, and chat interactions
via the Vectara v2 API.
"""

import json

from mcp.server.fastmcp import Context

import vectara_mcp.server as _server
from vectara_mcp.server import (
    mcp, _make_api_request, _get_api_key, _format_error, API_KEY_ERROR_MESSAGE
)


def _validate_api_key_available() -> str | None:
    """Return error message if no API key is available, None otherwise."""
    if not _get_api_key():
        return API_KEY_ERROR_MESSAGE
    return None


# ---------------------------------------------------------------------------
# Agent Management Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_agents(
    ctx: Context,
    filter_name: str = "",
    enabled: bool | None = None,
    limit: int = 10,
    page_key: str = "",
) -> dict:
    """List agents in the Vectara account.

    Args:
        filter_name: str, Filter agents by name (substring match). Optional.
        enabled: bool, Filter by enabled status. Optional.
        limit: int, Max agents to return per page. Default 10.
        page_key: str, Pagination key from a previous response. Optional.

    Returns:
        dict: List of agents and pagination metadata.
    """
    error = _validate_api_key_available()
    if error:
        return {"error": error}

    if ctx:
        ctx.info("Listing agents")

    try:
        params = {"limit": limit}
        if filter_name:
            params["filter"] = filter_name
        if enabled is not None:
            params["enabled"] = str(enabled).lower()
        if page_key:
            params["page_key"] = page_key

        return await _make_api_request(
            f"{_server.VECTARA_BASE_URL}/agents",
            ctx=ctx,
            error_context="list agents",
            method="GET",
            params=params,
        )
    except Exception as e:
        return {"error": _format_error("list agents", e)}


@mcp.tool()
async def get_agent(
    agent_key: str,
    ctx: Context,
) -> dict:
    """Get full details of a Vectara agent.

    Args:
        agent_key: str, The unique key of the agent. Required.

    Returns:
        dict: Agent configuration including tools, steps, model, and metadata.
    """
    error = _validate_api_key_available()
    if error:
        return {"error": error}

    if not agent_key:
        return {"error": "agent_key is required."}

    if ctx:
        ctx.info(f"Getting agent: {agent_key}")

    try:
        return await _make_api_request(
            f"{_server.VECTARA_BASE_URL}/agents/{agent_key}",
            ctx=ctx,
            error_context="get agent",
            method="GET",
        )
    except Exception as e:
        return {"error": _format_error("get agent", e)}


@mcp.tool()
async def create_agent(
    name: str,
    ctx: Context,
    key: str = "",
    description: str = "",
    tool_configurations: dict = None,
    model: dict = None,
    first_step_name: str = "",
    steps: dict = None,
    skills: dict = None,
    metadata: dict = None,
    guardrails: dict = None,
) -> dict:
    """Create a new Vectara agent.

    Args:
        name: str, Human-readable agent name. Required.
        key: str, Unique agent key (alphanumeric, max 50 chars). Optional, auto-generated if empty.
        description: str, Description of the agent's purpose. Optional.
        tool_configurations: dict, Map of tool name to tool config. Each config needs a "type"
            field. Common types: "corpora_search", "web_search", "sub_agent", "lambda".
            Example: {"search": {"type": "corpora_search", "query_configuration": {"search": {"corpora": [{"corpus_key": "my_corpus"}]}}}}
        model: dict, LLM configuration. Example: {"name": "gpt-4o", "parameters": {"temperature": 0.7}}
        first_step_name: str, Entry point step name. Optional.
        steps: dict, Map of step name to step config with instructions, output_parser, etc. Optional.
        skills: dict, Map of skill name to skill config with description and content. Optional.
        metadata: dict, Arbitrary key-value pairs. Optional.
        guardrails: dict, Safety check configurations. Optional.

    Returns:
        dict: The created agent object.
    """
    error = _validate_api_key_available()
    if error:
        return {"error": error}

    if not name:
        return {"error": "name is required."}

    if ctx:
        ctx.info(f"Creating agent: {name}")

    try:
        payload = {"name": name}
        if key:
            payload["key"] = key
        if description:
            payload["description"] = description
        if tool_configurations:
            payload["tool_configurations"] = tool_configurations
        if model:
            payload["model"] = model
        if first_step_name:
            payload["first_step_name"] = first_step_name
        if steps:
            payload["steps"] = steps
        if skills:
            payload["skills"] = skills
        if metadata:
            payload["metadata"] = metadata
        if guardrails:
            payload["guardrails"] = guardrails

        return await _make_api_request(
            f"{_server.VECTARA_BASE_URL}/agents",
            payload=payload,
            ctx=ctx,
            error_context="create agent",
            method="POST",
        )
    except Exception as e:
        return {"error": _format_error("create agent", e)}


@mcp.tool()
async def update_agent(
    agent_key: str,
    ctx: Context,
    name: str | None = None,
    description: str | None = None,
    enabled: bool | None = None,
    tool_configurations: dict = None,
    model: dict = None,
    steps: dict = None,
    skills: dict = None,
    metadata: dict = None,
) -> dict:
    """Update an existing Vectara agent (partial update).

    Args:
        agent_key: str, The unique key of the agent to update. Required.
        name: str, New agent name. Optional.
        description: str, New description (pass empty string to clear). Optional.
        enabled: bool, Enable or disable the agent. Optional.
        tool_configurations: dict, Updated tool configurations. Optional.
        model: dict, Updated LLM configuration. Optional.
        steps: dict, Updated step configurations. Optional.
        skills: dict, Updated skills. Optional.
        metadata: dict, Updated metadata. Optional.

    Returns:
        dict: The updated agent object.
    """
    error = _validate_api_key_available()
    if error:
        return {"error": error}

    if not agent_key:
        return {"error": "agent_key is required."}

    if ctx:
        ctx.info(f"Updating agent: {agent_key}")

    try:
        payload = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if enabled is not None:
            payload["enabled"] = enabled
        if tool_configurations is not None:
            payload["tool_configurations"] = tool_configurations
        if model is not None:
            payload["model"] = model
        if steps is not None:
            payload["steps"] = steps
        if skills is not None:
            payload["skills"] = skills
        if metadata is not None:
            payload["metadata"] = metadata

        if not payload:
            return {"error": "At least one field to update is required."}

        return await _make_api_request(
            f"{_server.VECTARA_BASE_URL}/agents/{agent_key}",
            payload=payload,
            ctx=ctx,
            error_context="update agent",
            method="PATCH",
        )
    except Exception as e:
        return {"error": _format_error("update agent", e)}


@mcp.tool()
async def delete_agent(
    agent_key: str,
    ctx: Context,
) -> dict:
    """Delete a Vectara agent.

    Args:
        agent_key: str, The unique key of the agent to delete. Required.

    Returns:
        dict: Confirmation of deletion.
    """
    error = _validate_api_key_available()
    if error:
        return {"error": error}

    if not agent_key:
        return {"error": "agent_key is required."}

    if ctx:
        ctx.info(f"Deleting agent: {agent_key}")

    try:
        return await _make_api_request(
            f"{_server.VECTARA_BASE_URL}/agents/{agent_key}",
            ctx=ctx,
            error_context="delete agent",
            method="DELETE",
        )
    except Exception as e:
        return {"error": _format_error("delete agent", e)}


# ---------------------------------------------------------------------------
# Session Management Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def create_session(
    agent_key: str,
    ctx: Context,
    session_key: str = "",
    name: str = "",
    description: str = "",
    metadata: dict = None,
    tti_minutes: int = 0,
) -> dict:
    """Create a new chat session for a Vectara agent.

    Args:
        agent_key: str, The agent to create a session for. Required.
        session_key: str, Custom session key. Optional, auto-generated if empty.
        name: str, Session name. Optional.
        description: str, Session description. Optional.
        metadata: dict, Session metadata accessible to the agent. Optional.
        tti_minutes: int, Time-to-idle in minutes before auto-delete (0 = never). Default 0.

    Returns:
        dict: The created session object with key and details.
    """
    error = _validate_api_key_available()
    if error:
        return {"error": error}

    if not agent_key:
        return {"error": "agent_key is required."}

    if ctx:
        ctx.info(f"Creating session for agent: {agent_key}")

    try:
        payload = {}
        if session_key:
            payload["key"] = session_key
        if name:
            payload["name"] = name
        if description:
            payload["description"] = description
        if metadata:
            payload["metadata"] = metadata
        if tti_minutes:
            payload["tti_minutes"] = tti_minutes

        return await _make_api_request(
            f"{_server.VECTARA_BASE_URL}/agents/{agent_key}/sessions",
            payload=payload,
            ctx=ctx,
            error_context="create session",
            method="POST",
        )
    except Exception as e:
        return {"error": _format_error("create session", e)}


@mcp.tool()
async def list_sessions(
    agent_key: str,
    ctx: Context,
    limit: int = 10,
    page_key: str = "",
) -> dict:
    """List sessions for a Vectara agent.

    Args:
        agent_key: str, The agent to list sessions for. Required.
        limit: int, Max sessions to return per page. Default 10.
        page_key: str, Pagination key from a previous response. Optional.

    Returns:
        dict: List of sessions and pagination metadata.
    """
    error = _validate_api_key_available()
    if error:
        return {"error": error}

    if not agent_key:
        return {"error": "agent_key is required."}

    if ctx:
        ctx.info(f"Listing sessions for agent: {agent_key}")

    try:
        params = {"limit": limit}
        if page_key:
            params["page_key"] = page_key

        return await _make_api_request(
            f"{_server.VECTARA_BASE_URL}/agents/{agent_key}/sessions",
            ctx=ctx,
            error_context="list sessions",
            method="GET",
            params=params,
        )
    except Exception as e:
        return {"error": _format_error("list sessions", e)}


@mcp.tool()
async def get_session(
    agent_key: str,
    session_key: str,
    ctx: Context,
) -> dict:
    """Get details of a specific agent session.

    Args:
        agent_key: str, The agent key. Required.
        session_key: str, The session key. Required.

    Returns:
        dict: Session details including metadata and context usage.
    """
    error = _validate_api_key_available()
    if error:
        return {"error": error}

    if not agent_key or not session_key:
        return {"error": "agent_key and session_key are required."}

    if ctx:
        ctx.info(f"Getting session {session_key} for agent {agent_key}")

    try:
        return await _make_api_request(
            f"{_server.VECTARA_BASE_URL}/agents/{agent_key}/sessions/{session_key}",
            ctx=ctx,
            error_context="get session",
            method="GET",
        )
    except Exception as e:
        return {"error": _format_error("get session", e)}


@mcp.tool()
async def delete_session(
    agent_key: str,
    session_key: str,
    ctx: Context,
) -> dict:
    """Delete a specific agent session.

    Args:
        agent_key: str, The agent key. Required.
        session_key: str, The session key. Required.

    Returns:
        dict: Confirmation of deletion.
    """
    error = _validate_api_key_available()
    if error:
        return {"error": error}

    if not agent_key or not session_key:
        return {"error": "agent_key and session_key are required."}

    if ctx:
        ctx.info(f"Deleting session {session_key} for agent {agent_key}")

    try:
        return await _make_api_request(
            f"{_server.VECTARA_BASE_URL}/agents/{agent_key}/sessions/{session_key}",
            ctx=ctx,
            error_context="delete session",
            method="DELETE",
        )
    except Exception as e:
        return {"error": _format_error("delete session", e)}


# ---------------------------------------------------------------------------
# Chat / Interaction Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def chat_with_agent(
    agent_key: str,
    session_key: str,
    message: str,
    ctx: Context,
) -> dict:
    """Send a message to a Vectara agent and get a response.

    This sends a text message to an existing agent session and returns
    the agent's response. The agent may use its configured tools (search,
    web, etc.) to answer.

    Args:
        agent_key: str, The agent key. Required.
        session_key: str, The session key. Required.
        message: str, The message to send. Required.

    Returns:
        dict: Agent response including output text, tool calls, and events.
    """
    error = _validate_api_key_available()
    if error:
        return {"error": error}

    if not agent_key or not session_key:
        return {"error": "agent_key and session_key are required."}
    if not message:
        return {"error": "message is required."}

    if ctx:
        ctx.info(f"Chatting with agent {agent_key}: {message[:100]}")

    try:
        payload = {
            "type": "input_message",
            "messages": [
                {"type": "text", "content": message}
            ],
            "stream_response": False,
        }

        result = await _make_api_request(
            f"{_server.VECTARA_BASE_URL}/agents/{agent_key}/sessions/{session_key}/events",
            payload=payload,
            ctx=ctx,
            error_context="chat with agent",
            method="POST",
        )

        return _extract_chat_response(result)
    except Exception as e:
        return {"error": _format_error("chat with agent", e)}


def _extract_chat_response(result: dict) -> dict:
    """Extract a clean response from the agent events payload."""
    events = result.get("events", [])
    if not events:
        return result

    response = {
        "agent_output": "",
        "tool_calls": [],
        "events_summary": [],
    }

    for event in events:
        event_type = event.get("type", "")
        if event_type == "agent_output":
            response["agent_output"] = event.get("content", "") or event.get("text", "")
        elif event_type == "structured_output":
            response["agent_output"] = json.dumps(event.get("fields", {}))
        elif event_type == "tool_input":
            response["tool_calls"].append({
                "tool": event.get("tool_config_name", ""),
                "arguments": event.get("arguments", {}),
            })
        elif event_type == "tool_output":
            last_tool = response["tool_calls"][-1] if response["tool_calls"] else None
            if last_tool:
                last_tool["output"] = event.get("output", "")
        response["events_summary"].append({
            "type": event_type,
            "id": event.get("id", ""),
        })

    if not response["tool_calls"]:
        del response["tool_calls"]

    return response


@mcp.tool()
async def list_events(
    agent_key: str,
    session_key: str,
    ctx: Context,
    limit: int = 20,
    page_key: str = "",
) -> dict:
    """List conversation events (messages, tool calls, outputs) in a session.

    Args:
        agent_key: str, The agent key. Required.
        session_key: str, The session key. Required.
        limit: int, Max events to return per page. Default 20.
        page_key: str, Pagination key from a previous response. Optional.

    Returns:
        dict: List of events and pagination metadata.
    """
    error = _validate_api_key_available()
    if error:
        return {"error": error}

    if not agent_key or not session_key:
        return {"error": "agent_key and session_key are required."}

    if ctx:
        ctx.info(f"Listing events for session {session_key}")

    try:
        params = {"limit": limit}
        if page_key:
            params["page_key"] = page_key

        return await _make_api_request(
            f"{_server.VECTARA_BASE_URL}/agents/{agent_key}/sessions/{session_key}/events",
            ctx=ctx,
            error_context="list events",
            method="GET",
            params=params,
        )
    except Exception as e:
        return {"error": _format_error("list events", e)}
