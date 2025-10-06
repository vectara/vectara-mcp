import logging
import json
import aiohttp
import os

from mcp.server.fastmcp import FastMCP, Context

logging.basicConfig(level=logging.INFO)

# Constants
VECTARA_BASE_URL = "https://api.vectara.io/v2"
VHC_MODEL_NAME = "vhc-large-1.0"
DEFAULT_LANGUAGE = "en"

# Create the Vectara MCP server
mcp = FastMCP("vectara")

# Global API key storage (session-scoped)
_stored_api_key: str | None = None

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
    global _stored_api_key

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
        return "API key not configured. Please use 'setup_vectara_api_key' tool first or set VECTARA_API_KEY environment variable."

    return None

def _validate_vhc_parameters(generated_text: str = "", documents: list[str] = None) -> str | None:
    """Validate parameters for VHC (hallucination correction) tools.

    Returns:
        str: Error message if validation fails, None if valid
    """
    if not generated_text:
        return "Generated text is required."
    if not documents:
        return "Documents are required."

    # Check API key availability
    api_key = _get_api_key()
    if not api_key:
        return "API key not configured. Please use 'setup_vectara_api_key' tool first or set VECTARA_API_KEY environment variable."

    return None

def _validate_api_key(api_key_override: str = None) -> str:
    """Validate and return API key, raise exception if not found.

    Args:
        api_key_override: Optional API key override for testing

    Returns:
        str: Valid API key

    Raises:
        Exception: If no API key is configured
    """
    api_key = api_key_override or _get_api_key()
    if not api_key:
        raise Exception("API key not configured. Please use 'setup_vectara_api_key' tool first.")
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

async def _handle_http_response(response: aiohttp.ClientResponse, error_context: str = "API") -> dict:
    """Handle HTTP response with unified error handling.

    Args:
        response: The aiohttp response object
        error_context: Context string for error messages (e.g., "query", "hallucination correction")

    Returns:
        dict: Response JSON data

    Raises:
        Exception: With descriptive error message based on status code
    """
    if response.status == 200:
        return await response.json()
    elif response.status == 400:
        error_text = await response.text()
        raise Exception(f"Bad request: {error_text}")
    elif response.status == 403:
        if "hallucination" in error_context.lower():
            raise Exception(f"Permissions do not allow {error_context}.")
        else:
            raise Exception("Permission denied. Check your API key and corpus access.")
    elif response.status == 404:
        raise Exception("Corpus not found. Check your corpus keys.")
    elif response.status == 422:
        raise Exception("Language not supported by service.")
    else:
        error_text = await response.text()
        raise Exception(f"API error {response.status}: {error_text}")

async def _make_api_request(
    url: str,
    payload: dict,
    ctx: Context = None,
    api_key_override: str = None,
    error_context: str = "API"
) -> dict:
    """Generic HTTP POST request with progress reporting and error handling.

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

    async with aiohttp.ClientSession() as session:
        if ctx:
            await ctx.report_progress(0, 1)

        async with session.post(url, headers=headers, json=payload) as response:
            if ctx:
                await ctx.report_progress(1, 1)

            return await _handle_http_response(response, error_context)

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
    global _stored_api_key

    if not api_key:
        return "API key is required."

    if ctx:
        ctx.info(f"Setting up Vectara API key: {_mask_api_key(api_key)}")

    try:
        # Test the API key with a minimal query to validate it
        test_payload = _build_query_payload(
            query="test",
            corpus_keys=["test"],  # This will likely fail but we just want to test API key auth
            enable_generation=False
        )

        # Use our existing query function with the test API key
        await _call_vectara_query(test_payload, ctx, api_key_override=api_key)

        # If we get here without exception, API key is valid
        _stored_api_key = api_key
        masked_key = _mask_api_key(api_key)
        return f"API key configured successfully: {masked_key}"

    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg or "Permission denied" in error_msg:
            return "Invalid API key. Please check your Vectara API key and try again."
        elif any(status in error_msg for status in ["400", "404", "Bad request", "Corpus not found"]):
            # These errors indicate API key is valid but request failed for other reasons
            _stored_api_key = api_key
            masked_key = _mask_api_key(api_key)
            return f"API key configured successfully: {masked_key}"
        else:
            return f"API validation failed: {error_msg}"

@mcp.tool()
async def clear_vectara_api_key(ctx: Context) -> str:
    """
    Clear the stored Vectara API key from server memory.

    Returns:
        str: Confirmation message.
    """
    global _stored_api_key

    if ctx:
        ctx.info("Clearing stored Vectara API key")

    _stored_api_key = None
    return "API key cleared from server memory."


# Query tool
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
    Run a RAG query using Vectara, returning search results with a generated response.

    Args:
        query: str, The user query to run - required.
        corpus_keys: list[str], List of Vectara corpus keys to use for the search - required. Please ask the user to provide one or more corpus keys.
        n_sentences_before: int, Number of sentences before the answer to include in the context - optional, default is 2.
        n_sentences_after: int, Number of sentences after the answer to include in the context - optional, default is 2.
        lexical_interpolation: float, The amount of lexical interpolation to use - optional, default is 0.005.
        max_used_search_results: int, The maximum number of search results to use - optional, default is 10.
        generation_preset_name: str, The name of the generation preset to use - optional, default is "vectara-summary-table-md-query-ext-jan-2025-gpt-4o".
        response_language: str, The language of the response - optional, default is "eng".

    Note: API key must be configured first using 'setup_vectara_api_key' tool

    Returns:
        dict: Structured response containing:
            - "summary": Generated AI summary with markdown citations
            - "citations": List of citation objects with score, text, and metadata
            - "factual_consistency_score": Score indicating factual consistency (if available)
        On error, returns dict with "error" key containing error message.
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

    except Exception as e:
        return {"error": _format_error("Vectara RAG query", e)}


# Query tool
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
        corpus_keys: list[str], List of Vectara corpus keys to use for the search - required. Please ask the user to provide one or more corpus keys.
        n_sentences_before: int, Number of sentences before the answer to include in the context - optional, default is 2.
        n_sentences_after: int, Number of sentences after the answer to include in the context - optional, default is 2.
        lexical_interpolation: float, The amount of lexical interpolation to use - optional, default is 0.005.

    Note: API key must be configured first using 'setup_vectara_api_key' tool

    Returns:
        dict: Raw search results from Vectara API containing:
            - "search_results": List of search result objects with scores, text, and metadata
            - Additional response metadata from the API
        On error, returns dict with "error" key containing error message.
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

    except Exception as e:
        return {"error": _format_error("Vectara semantic search query", e)}


@mcp.tool()
async def correct_hallucinations(
    generated_text: str,
    documents: list[str],
    ctx: Context,
    query: str = "",
) -> dict:
    """
    Identify and correct hallucinations in generated text using Vectara's hallucination correction API.

    Args:
        generated_text: str, The generated text to analyze for hallucinations - required.
        documents: list[str], List of source documents to compare against - required.
        query: str, The original user query that led to the generated text - optional.

    Note: API key must be configured first using 'setup_vectara_api_key' tool

    Returns:
        dict: Structured response containing:
            - "corrected_text": Text with hallucinations corrected
            - "corrections": Array of correction objects with:
                * "original_text": The hallucinated content
                * "corrected_text": The factually accurate replacement
                * "explanation": Detailed reason for the correction
        On error, returns dict with "error" key containing error message.
    """
    # Validate parameters
    validation_error = _validate_vhc_parameters(generated_text, documents)
    if validation_error:
        return {"error": validation_error}

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

    except Exception as e:
        return {"error": _format_error("hallucination correction", e)}


@mcp.tool()
async def eval_factual_consistency(
    generated_text: str,
    documents: list[str],
    ctx: Context,
) -> dict:
    """
    Evaluate the factual consistency of generated text against source documents using Vectara's dedicated factual consistency API.

    Args:
        generated_text: str, The generated text to evaluate for factual consistency - required.
        documents: list[str], List of source documents to compare against - required.

    Note: API key must be configured first using 'setup_vectara_api_key' tool

    Returns:
        dict: Structured response containing factual consistency evaluation score.
        On error, returns dict with "error" key containing error message.
    """
    # Validate parameters
    validation_error = _validate_vhc_parameters(generated_text, documents)
    if validation_error:
        return {"error": validation_error}

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

    except Exception as e:
        return {"error": _format_error("factual consistency evaluation", e)}


def main():
    """Command-line interface for starting the Vectara MCP Server."""
    print("Starting Vectara MCP Server")
    mcp.run()

if __name__ == "__main__":
    main()
