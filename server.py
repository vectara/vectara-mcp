import os
import logging
import uvicorn
from typing import Dict, Optional

from mcp.server.fastmcp import FastMCP, Context
from vectara import (
    Vectara, 
    SearchCorporaParameters, GenerationParameters, CitationParameters,
    KeyedSearchCorpus, ContextConfiguration, CustomerSpecificReranker
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vectara-mcp-server")

# Store API keys per client
client_api_keys: Dict[str, str] = {}

def get_api_key(ctx: Context = None, api_key: str = None) -> str:
    """
    Convenience function to get the API key with priority:
    1. API key passed directly as parameter
    2. API key stored for this client
    3. API key from environment variable
    
    Raises an error if no API key is available.
    """
    vectara_api_key = api_key
    
    # Check client-specific storage if context is provided
    if not vectara_api_key and ctx:
        client_id = ctx.client_id
        if client_id and client_id in client_api_keys:
            vectara_api_key = client_api_keys.get(client_id)
    
    # Fallback to environment variable
    if not vectara_api_key:
        vectara_api_key = os.environ.get("VECTARA_API_KEY")
    
    # Error if no API key is available
    if not vectara_api_key:
        raise ValueError(
            "No Vectara API key available. Please set the API key using the set_vectara_api_key tool "
            "or set the VECTARA_API_KEY environment variable."
        )
        
    return vectara_api_key

def get_vectara_config(client_id: Optional[str] = None):
    vectara_api_key = None
    
    # Try to get API key from client storage first
    if client_id and client_id in client_api_keys:
        vectara_api_key = client_api_keys.get(client_id)
        
    # Fallback to environment variable if no client key
    if not vectara_api_key:
        vectara_api_key = os.environ.get("VECTARA_API_KEY")
        
    return {
        "api_key": vectara_api_key,
    }

# Create the Vectara MCP server
mcp = FastMCP("vectara")

def get_search_config(
    corpus_keys: list[str],
    n_sentences_before: int,
    n_sentences_after: int,
    lexical_interpolation: float,
):
    search_params = SearchCorporaParameters(
        corpora=[
            KeyedSearchCorpus(
                corpus_key=corpus_key,
                lexical_interpolation=lexical_interpolation
            ) for corpus_key in corpus_keys
        ],
        context_configuration=ContextConfiguration(
            sentences_before=n_sentences_before,
            sentences_after=n_sentences_after,
        ),
        reranker=CustomerSpecificReranker(
            reranker_id="rnk_272725719",
            limit=100,
            cutoff=0.1,
        ),
    )
    return search_params

def get_generation_config(
    generation_preset_name: str,
    max_used_search_results: int,
    response_language: str,
) -> GenerationParameters:
    generation_params = GenerationParameters(
        response_language=response_language,
        max_used_search_results=max_used_search_results,
        generation_preset_name=generation_preset_name,
        citations=CitationParameters(style="markdown", url_pattern="{doc.url}"),
        enable_factual_consistency_score=True,
    )
    return generation_params

# Set API Key tool
@mcp.tool()
async def set_vectara_api_key(
    api_key: str,
    ctx: Context
) -> str:
    """
    Set the Vectara API key for the current client session.

    Args:
        api_key: str, The Vectara API key to use for this client session.
        ctx: Context, The FastMCP context object.

    Returns:
        Confirmation message that the API key has been set.
    """
    client_id = ctx.client_id
    client_api_keys[client_id] = api_key
    
    # Log and inform the user
    logger.info(f"API key set for client: {client_id}")
    ctx.info("API key configured for this session")
    
    # Test the API key to verify it works
    try:
        # Create a test client to verify the API key
        client = Vectara(api_key=api_key)
        return "✅ Vectara API key has been set and verified for this session."
    except Exception as e:
        # Remove the invalid API key
        del client_api_keys[client_id]
        error_message = f"❌ Invalid API key: {str(e)}"
        ctx.error(error_message)
        raise ValueError(error_message)

# Query tool
@mcp.tool()
async def ask_vectara(
    query: str,
    corpus_keys: list[str] = [],
    n_sentences_before: int = 2,
    n_sentences_after: int = 2,
    lexical_interpolation: float = 0.005,
    max_used_search_results: int = 10,
    generation_preset_name: str = "vectara-summary-table-md-query-ext-jan-2025-gpt-4o",
    response_language: str = "eng",
    api_key: str = None,
    ctx: Context = None,
) -> str:
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
        api_key: str, Optional Vectara API key to use for this specific request.
        ctx: Context, The FastMCP context object.

    Returns:
        The response from Vectara, including the generated answer and the search results.
    """
    if not query:
        return "Query is required."
    if not corpus_keys:
        return "Corpus keys are required. Please ask the user to provide one or more corpus keys."

    # Report initial progress
    if ctx:
        ctx.info("Processing RAG query with Vectara")
    
    try:
        # Use the convenience function to get API key with error handling
        vectara_api_key = get_api_key(ctx, api_key)
        
        # Report progress
        if ctx:
            ctx.info("Executing search...")
            await ctx.report_progress(0, 2)
        
        # Create client and run query
        client = Vectara(api_key=vectara_api_key)
        res = client.query(
            query=query,
            search=get_search_config(
                corpus_keys=corpus_keys,
                n_sentences_before=n_sentences_before,
                n_sentences_after=n_sentences_after,
                lexical_interpolation=lexical_interpolation,
            ),
            generation=get_generation_config(
                generation_preset_name=generation_preset_name,
                max_used_search_results=max_used_search_results,
                response_language=response_language,
            ),
            save_history=True,
        )
        
        # Report completion
        if ctx:
            ctx.info("RAG query completed successfully")
            await ctx.report_progress(2, 2)
            
        return res.summary
    except Exception as e:
        # Report error
        error_message = f"Error with Vectara RAG query: {str(e)}"
        if ctx:
            ctx.error(error_message)
        return error_message


# Query tool
@mcp.tool()
async def search_vectara(
    query: str,
    corpus_keys: list[str] = [],
    n_sentences_before: int = 2,
    n_sentences_after: int = 2,
    lexical_interpolation: float = 0.005,
    api_key: str = None,
    ctx: Context = None
) -> str:
    """
    Run a semantic search query using Vectara, without generation.

    Args:
        query: str, The user query to run - required.
        corpus_keys: list[str], List of Vectara corpus keys to use for the search - required. Please ask the user to provide one or more corpus keys. 
        n_sentences_before: int, Number of sentences before the answer to include in the context - optional, default is 2.
        n_sentences_after: int, Number of sentences after the answer to include in the context - optional, default is 2.
        lexical_interpolation: float, The amount of lexical interpolation to use - optional, default is 0.005.
        api_key: str, Optional Vectara API key to use for this specific request.
        ctx: Context, The FastMCP context object.
    
    Returns:
        The response from Vectara, including the matching search results.
    """
    if not query:
        return "Query is required."
    if not corpus_keys:
        return "Corpus keys are required. Please ask the user to provide one or more corpus keys."

    # Report initial progress
    if ctx:
        ctx.info("Processing semantic search with Vectara")
    
    try:
        # Use the convenience function to get API key with error handling
        vectara_api_key = get_api_key(ctx, api_key)
        
        # Report progress
        if ctx:
            ctx.info("Executing search...")
            await ctx.report_progress(0, 1)
        
        # Create client and run query
        client = Vectara(api_key=vectara_api_key)
        res = client.query(
            query=query,
            search=get_search_config(
                corpus_keys=corpus_keys,
                n_sentences_before=n_sentences_before,
                n_sentences_after=n_sentences_after,
                lexical_interpolation=lexical_interpolation,
            ),
            save_history=True,
        )
        
        # Report completion
        if ctx:
            ctx.info("Semantic search completed successfully")
            await ctx.report_progress(1, 1)
            
        return res.summary
    except Exception as e:
        # Report error
        error_message = f"Error with Vectara semantic search query: {str(e)}"
        if ctx:
            ctx.error(error_message)
        return error_message


def cli():
    """Command-line interface for starting the Vectara MCP Server."""
    vectara_config = get_vectara_config()
    vectara_api_key = vectara_config.get("api_key")
    print("Starting Vectara MCP Server")
    logger.info(
        f"Default API Key configured: {'Yes' if vectara_api_key else 'No'}"
    )
    logger.info("Client-specific API keys can be set using the set_vectara_api_key tool")

    # Run the server with stdio transport
    mcp.run(transport="stdio")
    

if __name__ == "__main__":
    cli()
#    uvicorn.run(mcp.sse_app(), host="0.0.0.0", port=8000)
