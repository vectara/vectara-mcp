import argparse
import atexit
import asyncio
import json
import logging
import os
import signal
import sys

import aiohttp
from mcp.server.fastmcp import FastMCP, Context
from starlette.requests import Request
from starlette.responses import JSONResponse

from vectara_mcp._version import __version__
from vectara_mcp.auth import AuthMiddleware
from vectara_mcp.connection_manager import (
    get_connection_manager, cleanup_connections, connection_manager
)
from vectara_mcp.health_checks import get_liveness, get_readiness, get_detailed_health

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
VECTARA_BASE_URL = "https://api.vectara.io/v2"
VHC_MODEL_NAME = "vhc-large-1.0"
DEFAULT_LANGUAGE = "en"
API_KEY_ERROR_MESSAGE = (
    "API key not configured. Please use 'setup_vectara_api_key' tool first "
    "or set VECTARA_API_KEY environment variable."
)

# Create the Vectara MCP server with default settings
# These will be overridden in main() by updating the settings
mcp = FastMCP("vectara")

# Initialize authentication component
_auth_middleware = None  # pylint: disable=invalid-name

# Global API key storage (session-scoped)
_stored_api_key: str | None = None
# Global authentication requirement flag
_auth_required: bool = True

def initialize_auth(auth_required: bool):
    """Initialize authentication middleware.

    Args:
        auth_required: Whether authentication is required
    """
    global _auth_middleware  # pylint: disable=global-statement
    _auth_middleware = AuthMiddleware(auth_required=auth_required)

def _mask_api_key(api_key: str) -> str:
    """Mask API key for safe logging/display.

    Args:
        api_key: The API key to mask

    Returns:
        str: Masked API key showing only first 4 and last 4 characters
    """
    if not api_key or len(api_key) < 8:
        return "***"
    return f"{api_key[:4]}***{api_key[-4:]}"

def _get_api_key() -> str | None:
    """Get API key with fallback priority: stored > environment > None.

    Returns:
        str: API key if available, None otherwise
    """
    # Priority 1: Stored API key
    if _stored_api_key:
        return _stored_api_key

    # Priority 2: Environment variable; good for local deployments
    env_key = os.getenv("VECTARA_API_KEY")
    if env_key:
        return env_key

    # Priority 3: None (will trigger error in validation)
    return None

def _validate_common_parameters(query: str = "", corpus_keys: list[str] = None) -> str | None:
    """Validate common parameters used across Vectara tools.

    Returns:
        str: Error message if validation fails, None if valid
    """
    if not query:
        return "Query is required."
    if not corpus_keys:
        return "Corpus keys are required. Please ask the user to provide one or more corpus keys."

    # Check API key availability
    api_key = _get_api_key()
    if not api_key:
        return API_KEY_ERROR_MESSAGE

    return None


def _validate_api_key(api_key_override: str = None) -> str:
    """Validate and return API key, raise exception if not found.

    Args:
        api_key_override: Optional API key override for testing

    Returns:
        str: Valid API key

    Raises:
        ValueError: If no API key is configured
    """
    api_key = api_key_override or _get_api_key()
    if not api_key:
        raise ValueError(
            "API key not configured. Please use 'setup_vectara_api_key' tool first."
        )
    return api_key

def _build_headers(api_key: str) -> dict:
    """Build standard HTTP headers for Vectara API calls.

    Args:
        api_key: The API key to include in headers

    Returns:
        dict: Standard headers for Vectara API requests
    """
    return {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

async def _handle_http_response(
    response: aiohttp.ClientResponse, error_context: str = "API"
) -> dict:
    """Handle HTTP response with unified error handling.

    Args:
        response: The aiohttp response object
        error_context: Context string for error messages

    Returns:
        dict: Response JSON data

    Raises:
        RuntimeError: With descriptive error message based on status code
    """
    if response.status == 200:
        return await response.json()
    if response.status == 400:
        error_text = await response.text()
        raise RuntimeError(f"Bad request: {error_text}")
    if response.status == 403:
        if "hallucination" in error_context.lower():
            raise PermissionError(f"Permissions do not allow {error_context}.")
        raise PermissionError("Permission denied. Check your API key and corpus access.")
    if response.status == 404:
        raise LookupError("Corpus not found. Check your corpus keys.")
    if response.status == 422:
        raise ValueError("Language not supported by service.")
    error_text = await response.text()
    raise RuntimeError(f"API error {response.status}: {error_text}")

async def _make_api_request(
    url: str,
    payload: dict,
    ctx: Context = None,
    api_key_override: str = None,
    error_context: str = "API"
) -> dict:
    """Generic HTTP POST request with progress reporting and error handling.

    Uses persistent connection pooling and circuit breaker pattern.

    Args:
        url: The API endpoint URL
        payload: Request payload
        ctx: MCP context for progress reporting
        api_key_override: Optional API key override for testing
        error_context: Context for error messages

    Returns:
        dict: API response data

    Raises:
        Exception: With descriptive error message
    """
    api_key = _validate_api_key(api_key_override)
    headers = _build_headers(api_key)

    # Get connection manager with persistent session
    conn_manager = await get_connection_manager()

    if ctx:
        await ctx.report_progress(0, 1)

    try:
        # Use persistent session with circuit breaker protection
        response = await conn_manager.request(
            method='POST',
            url=url,
            headers=headers,
            json_data=payload
        )

        if ctx:
            await ctx.report_progress(1, 1)

        # Handle response using existing logic
        async with response:
            return await _handle_http_response(response, error_context)

    except Exception as e:  # pylint: disable=broad-exception-caught
        # Log the error with context
        logger.error("API request failed: %s - %s", error_context, str(e))
        raise


# pylint: disable=too-many-arguments,too-many-positional-arguments
def _build_query_payload(
    query: str,
    corpus_keys: list[str],
    n_sentences_before: int = 2,
    n_sentences_after: int = 2,
    lexical_interpolation: float = 0.005,
    max_used_search_results: int = 10,
    generation_preset_name: str = "vectara-summary-table-md-query-ext-jan-2025-gpt-4o",
    response_language: str = "eng",
    enable_generation: bool = True
) -> dict:
    """Build the query payload for Vectara API"""
    payload = {
        "query": query,
        "search": {
            "limit": 100,
            "corpora": [
                {
                    "corpus_key": corpus_key,
                    "lexical_interpolation": lexical_interpolation
                } for corpus_key in corpus_keys
            ],
            "context_configuration": {
                "sentences_before": n_sentences_before,
                "sentences_after": n_sentences_after
            },
            "reranker": {
                "type": "customer_reranker",
                "reranker_name": "Rerank_Multilingual_v1",
                "limit": 100,
                "cutoff": 0.2
            }
        },
        "save_history": True,
    }

    if enable_generation:
        payload["generation"] = {
            "generation_preset_name": generation_preset_name,
            "max_used_search_results": max_used_search_results,
            "response_language": response_language,
            "citations": {
                "style": "markdown",
                "url_pattern": "{doc.url}",
                "text_pattern": "{doc.title}"
            },
            "enable_factual_consistency_score": True
        }

    return payload

async def _call_vectara_query(
    payload: dict,
    ctx: Context = None,
    api_key_override: str = None
) -> dict:
    """Make API call to Vectara query endpoint"""
    return await _make_api_request(
        f"{VECTARA_BASE_URL}/query",
        payload,
        ctx,
        api_key_override,
        "query"
    )


def _format_error(tool_name: str, error: Exception) -> str:
    """Format error messages consistently across tools.

    Args:
        tool_name: Name of the tool (e.g., "Vectara RAG query")
        error: The exception that occurred

    Returns:
        str: Formatted error message
    """
    return f"Error with {tool_name}: {str(error)}"

# API Key Management Tools
@mcp.tool()
async def setup_vectara_api_key(
    api_key: str,
    ctx: Context
) -> str:
    """
    Configure and validate the Vectara API key for the session.

    Args:
        api_key: str, The Vectara API key to configure - required.

    Returns:
        str: Success message with masked API key or error message.
    """
    global _stored_api_key  # pylint: disable=global-statement

    if not api_key:
        return "API key is required."

    if ctx:
        ctx.info(f"Setting up Vectara API key: {_mask_api_key(api_key)}")

    try:
        # Test the API key with a minimal query to validate it
        test_payload = _build_query_payload(
            query="test",
            corpus_keys=["test"],  # Will likely fail but tests API key auth
            enable_generation=False
        )

        # Use our existing query function with the test API key
        await _call_vectara_query(test_payload, ctx, api_key_override=api_key)

        # If we get here without exception, API key is valid
        _stored_api_key = api_key
        masked_key = _mask_api_key(api_key)
        return f"API key configured successfully: {masked_key}"

    except Exception as e:  # pylint: disable=broad-exception-caught
        error_msg = str(e)
        auth_errors = ["403", "401", "Permission denied", "API key error"]
        if any(err in error_msg for err in auth_errors):
            return "Invalid API key. Please check your Vectara API key and try again."
        request_errors = ["400", "404", "Bad request", "Corpus not found"]
        if any(status in error_msg for status in request_errors):
            # These errors indicate API key is valid but request failed for other reasons
            _stored_api_key = api_key
            masked_key = _mask_api_key(api_key)
            return f"API key configured successfully: {masked_key}"
        return f"API validation failed: {error_msg}"

@mcp.tool()
async def clear_vectara_api_key(ctx: Context) -> str:
    """
    Clear the stored Vectara API key from server memory.

    Returns:
        str: Confirmation message.
    """
    global _stored_api_key  # pylint: disable=global-statement

    if ctx:
        ctx.info("Clearing stored Vectara API key")

    _stored_api_key = None
    return "API key cleared from server memory."


# HTTP Health Check Endpoints (for Kubernetes/load balancers)
# These are exposed as HTTP routes, not MCP tools


@mcp.custom_route("/health", methods=["GET"])
async def http_health_check(request: Request) -> JSONResponse:  # pylint: disable=unused-argument
    """Liveness probe - is the server running?"""
    try:
        result = await get_liveness()
        return JSONResponse(result)
    except Exception as e:  # pylint: disable=broad-exception-caught
        return JSONResponse({"error": str(e)}, status_code=500)


@mcp.custom_route("/ready", methods=["GET"])
async def http_readiness_check(request: Request) -> JSONResponse:  # pylint: disable=unused-argument
    """Readiness probe - can the server handle traffic?"""
    try:
        result = await get_readiness()
        status_code = 200 if result.get("status") == "healthy" else 503
        return JSONResponse(result, status_code=status_code)
    except Exception as e:  # pylint: disable=broad-exception-caught
        return JSONResponse({"error": str(e)}, status_code=500)


@mcp.custom_route("/health/detailed", methods=["GET"])
async def http_detailed_health_check(request: Request) -> JSONResponse:  # pylint: disable=unused-argument
    """Detailed health with metrics - for monitoring dashboards."""
    try:
        result = await get_detailed_health()
        status_code = 200 if result.get("status") == "healthy" else 503
        return JSONResponse(result, status_code=status_code)
    except Exception as e:  # pylint: disable=broad-exception-caught
        return JSONResponse({"error": str(e)}, status_code=500)


@mcp.custom_route("/stats", methods=["GET"])
async def http_server_stats(request: Request) -> JSONResponse:  # pylint: disable=unused-argument
    """Server statistics for monitoring."""
    try:
        stats = {
            "connection_manager": connection_manager.get_stats(),
            "server_info": {
                "version": __version__,
                "auth_enabled": bool(_auth_required)
            }
        }
        return JSONResponse(stats)
    except Exception as e:  # pylint: disable=broad-exception-caught
        return JSONResponse({"error": str(e)}, status_code=500)


# Query tool
# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
@mcp.tool()
async def ask_vectara(
    query: str,
    ctx: Context,
    corpus_keys: list[str],
    n_sentences_before: int = 2,
    n_sentences_after: int = 2,
    lexical_interpolation: float = 0.005,
    max_used_search_results: int = 10,
    generation_preset_name: str = "vectara-summary-table-md-query-ext-jan-2025-gpt-4o",
    response_language: str = "eng",
) -> dict:
    """
    Run a RAG query using Vectara, returning search results with generated response.

    Args:
        query: str, The user query to run - required.
        corpus_keys: list[str], List of Vectara corpus keys to use. Required.
        n_sentences_before: int, Sentences before answer for context. Default 2.
        n_sentences_after: int, Sentences after answer for context. Default 2.
        lexical_interpolation: float, Lexical interpolation amount. Default 0.005.
        max_used_search_results: int, Max search results to use. Default 10.
        generation_preset_name: str, Generation preset name.
        response_language: str, Response language. Default "eng".

    Note: API key must be configured first using 'setup_vectara_api_key' tool

    Returns:
        dict: Structured response containing:
            - "summary": Generated AI summary with markdown citations
            - "citations": List of citation objects with score, text, metadata
            - "factual_consistency_score": Score if available
        On error, returns dict with "error" key.
    """
    # Validate parameters
    validation_error = _validate_common_parameters(query, corpus_keys)
    if validation_error:
        return {"error": validation_error}

    if ctx:
        ctx.info(f"Running Vectara RAG query: {query}")

    try:
        payload = _build_query_payload(
            query=query,
            corpus_keys=corpus_keys,
            n_sentences_before=n_sentences_before,
            n_sentences_after=n_sentences_after,
            lexical_interpolation=lexical_interpolation,
            max_used_search_results=max_used_search_results,
            generation_preset_name=generation_preset_name,
            response_language=response_language,
            enable_generation=True
        )

        result = await _call_vectara_query(payload, ctx)

        # Extract the generated summary from the response
        summary_text = ""
        if "summary" in result:
            summary_text = result["summary"]
        elif "answer" in result:
            summary_text = result["answer"]
        else:
            return {"error": f"Unexpected response format: {json.dumps(result, indent=2)}"}

        # Build citations list
        citations = []
        if "search_results" in result and result["search_results"]:
            for i, search_result in enumerate(result["search_results"], 1):
                citation = {
                    "id": i,
                    "score": search_result.get("score", 0.0),
                    "text": search_result.get("text", ""),
                    "document_metadata": search_result.get("document_metadata", {})
                }
                citations.append(citation)

        # Build response dict
        response = {
            "summary": summary_text,
            "citations": citations
        }

        # Add factual consistency score if available
        if "factual_consistency_score" in result:
            response["factual_consistency_score"] = result["factual_consistency_score"]

        return response

    except Exception as e:  # pylint: disable=broad-exception-caught
        return {"error": _format_error("Vectara RAG query", e)}


# Query tool
# pylint: disable=too-many-arguments,too-many-positional-arguments
@mcp.tool()
async def search_vectara(
    query: str,
    ctx: Context,
    corpus_keys: list[str],
    n_sentences_before: int = 2,
    n_sentences_after: int = 2,
    lexical_interpolation: float = 0.005
) -> dict:
    """
    Run a semantic search query using Vectara, without generation.

    Args:
        query: str, The user query to run - required.
        corpus_keys: list[str], List of Vectara corpus keys to use. Required.
        n_sentences_before: int, Sentences before answer for context. Default 2.
        n_sentences_after: int, Sentences after answer for context. Default 2.
        lexical_interpolation: float, Lexical interpolation amount. Default 0.005.

    Note: API key must be configured first using 'setup_vectara_api_key' tool

    Returns:
        dict: Raw search results from Vectara API containing:
            - "search_results": List of result objects with scores, text, metadata
            - Additional response metadata from the API
        On error, returns dict with "error" key.
    """
    # Validate parameters
    validation_error = _validate_common_parameters(query, corpus_keys)
    if validation_error:
        return {"error": validation_error}

    if ctx:
        ctx.info(f"Running Vectara semantic search query: {query}")

    try:
        payload = _build_query_payload(
            query=query,
            corpus_keys=corpus_keys,
            n_sentences_before=n_sentences_before,
            n_sentences_after=n_sentences_after,
            lexical_interpolation=lexical_interpolation,
            enable_generation=False
        )

        result = await _call_vectara_query(payload, ctx)
        return result

    except Exception as e:  # pylint: disable=broad-exception-caught
        return {"error": _format_error("Vectara semantic search query", e)}


@mcp.tool()
async def correct_hallucinations(
    generated_text: str,
    documents: list[str],
    ctx: Context,
    query: str = "",
) -> dict:
    """
    Identify and correct hallucinations in generated text using Vectara API.

    Args:
        generated_text: str, The text to analyze for hallucinations - required.
        documents: list[str], Source documents to compare against - required.
        query: str, The original user query - optional.

    Note: API key must be configured first using 'setup_vectara_api_key' tool

    Returns:
        dict: Structured response containing:
            - "corrected_text": Text with hallucinations corrected
            - "corrections": Array of correction objects with:
                * "original_text": The hallucinated content
                * "corrected_text": The factually accurate replacement
                * "explanation": Detailed reason for the correction
        On error, returns dict with "error" key.
    """
    # Validate parameters
    if not generated_text:
        return {"error": "Generated text is required."}
    if not documents:
        return {"error": "Documents are required."}

    # Validate API key early
    api_key = _get_api_key()
    if not api_key:
        return {"error": API_KEY_ERROR_MESSAGE}

    if ctx:
        ctx.info(f"Analyzing text for hallucinations: {generated_text[:100]}...")

    try:
        # Build payload for VHC hallucination correction endpoint
        payload = {
            "generated_text": generated_text,
            "documents": [{"text": doc} for doc in documents],
            "model_name": VHC_MODEL_NAME
        }
        if query:
            payload["query"] = query

        return await _make_api_request(
            f"{VECTARA_BASE_URL}/hallucination_correctors/correct_hallucinations",
            payload,
            ctx,
            None,
            "hallucination correction"
        )

    except Exception as e:  # pylint: disable=broad-exception-caught
        return {"error": _format_error("hallucination correction", e)}


@mcp.tool()
async def eval_factual_consistency(
    generated_text: str,
    documents: list[str],
    ctx: Context,
) -> dict:
    """
    Evaluate factual consistency of text against source documents using Vectara.

    Args:
        generated_text: str, The text to evaluate for factual consistency.
        documents: list[str], Source documents to compare against - required.

    Note: API key must be configured first using 'setup_vectara_api_key' tool

    Returns:
        dict: Response containing factual consistency evaluation score.
        On error, returns dict with "error" key.
    """
    # Validate parameters
    if not generated_text:
        return {"error": "Generated text is required."}
    if not documents:
        return {"error": "Documents are required."}

    # Validate API key early
    api_key = _get_api_key()
    if not api_key:
        return {"error": API_KEY_ERROR_MESSAGE}

    if ctx:
        ctx.info(f"Evaluating factual consistency for text: {generated_text[:100]}...")

    try:
        # Build payload for dedicated factual consistency evaluation endpoint
        payload = {
            "generated_text": generated_text,
            "source_texts": documents,
        }

        return await _make_api_request(
            f"{VECTARA_BASE_URL}/evaluate_factual_consistency",
            payload,
            ctx,
            None,
            "factual consistency evaluation"
        )

    except Exception as e:  # pylint: disable=broad-exception-caught
        return {"error": _format_error("factual consistency evaluation", e)}


def _setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, _frame):
        logger.info("Received signal %s, initiating graceful shutdown...", signum)
        # Schedule cleanup in the event loop
        if hasattr(asyncio, 'get_running_loop'):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(cleanup_connections())
            except RuntimeError:
                # No running loop, cleanup will happen at exit
                pass
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def _setup_cleanup():
    """Setup cleanup for process exit."""
    atexit.register(lambda: asyncio.run(cleanup_connections()))


def main():
    """Command-line interface for starting the Vectara MCP Server."""
    parser = argparse.ArgumentParser(description="Vectara MCP Server")
    parser.add_argument(
        '--transport',
        default='sse',
        choices=['stdio', 'sse', 'streamable-http'],
        help='Transport protocol: stdio, sse (default), or streamable-http'
    )
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='Host address for network transports (default: 127.0.0.1)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Port for network transports (default: 8000)'
    )
    parser.add_argument(
        '--no-auth',
        action='store_true',
        help='Disable authentication (DANGEROUS: development only)'
    )
    parser.add_argument(
        '--path',
        default='/sse/messages',
        help='Path for SSE endpoint (default: /sse/messages)'
    )

    args = parser.parse_args()

    # Configure authentication based on transport and flags
    auth_enabled = args.transport != 'stdio' and not args.no_auth

    # Update MCP server settings with runtime configuration
    if args.transport != 'stdio':
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.settings.sse_path = args.path

    # Display startup information
    if args.transport == 'stdio':
        logger.warning("STDIO transport is less secure. Use only for local dev.")
        logger.info("Starting Vectara MCP Server (STDIO mode)...")
        mcp.run()
        sys.exit(0)
    else:
        if args.no_auth:
            logger.warning("Authentication disabled. NEVER use in production!")

        transport_name = "Streamable HTTP" if args.transport == 'streamable-http' else "SSE"
        auth_status = "enabled" if auth_enabled else "DISABLED"
        path_suffix = args.path if args.transport == 'sse' else '/mcp'

        logger.info("Starting Vectara MCP Server (%s mode)", transport_name)
        logger.info("Server: http://%s:%s%s", args.host, args.port, path_suffix)
        logger.info("Authentication: %s", auth_status)

        # Initialize authentication middleware
        initialize_auth(auth_enabled)

        # Setup signal handlers and cleanup
        _setup_signal_handlers()
        _setup_cleanup()

        if args.transport == 'sse':
            mcp.run(transport='sse', mount_path=args.path)
        else:  # streamable-http
            mcp.run(transport='streamable-http')

        sys.exit(0)

if __name__ == "__main__":
    main()
