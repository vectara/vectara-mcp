import logging

from mcp.server.fastmcp import FastMCP, Context

from vectara import (
    Vectara, 
    SearchCorporaParameters, GenerationParameters, CitationParameters,
    KeyedSearchCorpus, ContextConfiguration, CustomerSpecificReranker
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vectara-mcp-server")

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

# Query tool
@mcp.tool()
async def ask_vectara(
    query: str,
    ctx: Context,
    corpus_keys: list[str] = [],
    api_key: str = "",
    n_sentences_before: int = 2,
    n_sentences_after: int = 2,
    lexical_interpolation: float = 0.005,
    max_used_search_results: int = 10,
    generation_preset_name: str = "vectara-summary-table-md-query-ext-jan-2025-gpt-4o",
    response_language: str = "eng",
) -> str:
    """
    Run a RAG query using Vectara, returning search results with a generated response.

    Args:
        query: str, The user query to run - required.
        corpus_keys: list[str], List of Vectara corpus keys to use for the search - required. Please ask the user to provide one or more corpus keys. 
        api_key: str, The Vectara API key - required.
        n_sentences_before: int, Number of sentences before the answer to include in the context - optional, default is 2.
        n_sentences_after: int, Number of sentences after the answer to include in the context - optional, default is 2.
        lexical_interpolation: float, The amount of lexical interpolation to use - optional, default is 0.005.
        max_used_search_results: int, The maximum number of search results to use - optional, default is 10.
        generation_preset_name: str, The name of the generation preset to use - optional, default is "vectara-summary-table-md-query-ext-jan-2025-gpt-4o".
        response_language: str, The language of the response - optional, default is "eng".

    Returns:
        The response from Vectara, including the generated answer and the search results.
    """
    if not query:
        return "Query is required."
    if not corpus_keys:
        return "Corpus keys are required. Please ask the user to provide one or more corpus keys."
    if not api_key:
        return "API key is required. Please provide your Vectara API key."

    if ctx:
        ctx.info(f"Running Vectara RAG query: {query}")
    try:
        client = Vectara(api_key=api_key)
        if ctx:
            await ctx.report_progress(0, 1)
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
        if ctx:
            await ctx.report_progress(1, 1)
        return res.summary
    except Exception as e:
        return f"Error with Vectara RAG query: {str(e)}"


# Query tool
@mcp.tool()
async def search_vectara(
    query: str,
    ctx: Context,
    corpus_keys: list[str] = [],
    api_key: str = "",
    n_sentences_before: int = 2,
    n_sentences_after: int = 2,
    lexical_interpolation: float = 0.005
) -> str:
    """
    Run a semantic search query using Vectara, without generation.

    Args:
        query: str, The user query to run - required.
        corpus_keys: list[str], List of Vectara corpus keys to use for the search - required. Please ask the user to provide one or more corpus keys. 
        api_key: str, The Vectara API key - required.
        n_sentences_before: int, Number of sentences before the answer to include in the context - optional, default is 2.
        n_sentences_after: int, Number of sentences after the answer to include in the context - optional, default is 2.
        lexical_interpolation: float, The amount of lexical interpolation to use - optional, default is 0.005.
    
    Returns:
        The response from Vectara, including the matching search results.
    """
    if not query:
        return "Query is required."
    if not corpus_keys:
        return "Corpus keys are required. Please ask the user to provide one or more corpus keys."
    if not api_key:
        return "API key is required. Please provide your Vectara API key."

    if ctx:
        ctx.info(f"Running Vectara semantic search query: {query}")
    try:
        client = Vectara(api_key=api_key)
        if ctx:
            await ctx.report_progress(0, 1)
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
        if ctx:
            await ctx.report_progress(1, 1)
        return res.summary
    except Exception as e:
        return f"Error with Vectara semantic search query: {str(e)}"


def main():
    """Command-line interface for starting the Vectara MCP Server."""
    print("Starting Vectara MCP Server")
    mcp.run()

if __name__ == "__main__":
    main()
