# Vectara MCP Server

![GitHub Repo stars](https://img.shields.io/github/stars/Vectara/Vectara-mcp?style=social)
![PyPI version](https://img.shields.io/pypi/v/vectara-mcp.svg)
![License](https://img.shields.io/pypi/l/vectara-mcp.svg)

> 🔌 **Compatible with [Claude Desktop](https://claude.ai/desktop), and any other MCP Client!**
>
> Vectara MCP is also compatible with any MCP client
>

The Model Context Protocol (MCP) is an open standard that enables AI systems to interact seamlessly with various data sources and tools, facilitating secure, two-way connections.

Vectara-MCP provides any agentic application with access to fast, reliable RAG with reduced hallucination, powered by Vectara's Trusted RAG platform, through the MCP protocol.

## Installation

You can install the package directly from PyPI:

```bash
pip install vectara-mcp
```

## Available Tools

### API Key Management
- **setup_vectara_api_key:**
  Configure and validate your Vectara API key for the session (one-time setup).

  Args:
  - api_key: str, Your Vectara API key - required.

  Returns:
  - Success confirmation with masked API key or validation error.


- **clear_vectara_api_key:**
  Clear the stored API key from server memory.

  Returns:
  - Confirmation message.

### Query Tools
- **ask_vectara:**
  Run a RAG query using Vectara, returning search results with a generated response.

  Args:
  - query: str, The user query to run - required.
  - corpus_keys: list[str], List of Vectara corpus keys to use for the search - required.
  - n_sentences_before: int, Number of sentences before the answer to include in the context - optional, default is 2.
  - n_sentences_after: int, Number of sentences after the answer to include in the context - optional, default is 2.
  - lexical_interpolation: float, The amount of lexical interpolation to use - optional, default is 0.005.
  - max_used_search_results: int, The maximum number of search results to use - optional, default is 10.
  - generation_preset_name: str, The name of the generation preset to use - optional, default is "vectara-summary-table-md-query-ext-jan-2025-gpt-4o".
  - response_language: str, The language of the response - optional, default is "eng".

  Returns:
  - The response from Vectara, including the generated answer and the search results.

- **search_vectara:**
  Run a semantic search query using Vectara, without generation.

  Args:
  - query: str, The user query to run - required.
  - corpus_keys: list[str], List of Vectara corpus keys to use for the search - required.
  - n_sentences_before: int, Number of sentences before the answer to include in the context - optional, default is 2.
  - n_sentences_after: int, Number of sentences after the answer to include in the context - optional, default is 2.
  - lexical_interpolation: float, The amount of lexical interpolation to use - optional, default is 0.005.

  Returns:
  - The response from Vectara, including the matching search results.

### Analysis Tools
- **correct_hallucinations:**
  Identify and correct hallucinations in generated text using Vectara's VHC (Vectara Hallucination Correction) API.

  Args:
  - generated_text: str, The generated text to analyze for hallucinations - required.
  - documents: list[str], List of source documents to compare against - required.
  - query: str, The original user query that led to the generated text - optional.

  Returns:
  - JSON-formatted string containing corrected text and detailed correction information.

- **eval_factual_consistency:**
  Evaluate the factual consistency of generated text against source documents using Vectara's dedicated factual consistency evaluation API.

  Args:
  - generated_text: str, The generated text to evaluate for factual consistency - required.
  - documents: list[str], List of source documents to compare against - required.
  - query: str, The original user query that led to the generated text - optional.

  Returns:
  - JSON-formatted string containing factual consistency evaluation results and scoring.

**Note:** API key must be configured first using `setup_vectara_api_key` tool or `VECTARA_API_KEY` environment variable.


## Configuration with Claude Desktop

Add to your claude_desktop_config.json:

```json
{
  "mcpServers": {
    "Vectara": {
      "command": "uv",
      "args": [
        "tool",
        "run",
        "vectara-mcp"
      ]
    }
  }
}
```

## Usage in Claude Desktop App

Once the installation is complete, and the Claude desktop app is configured, you must completely close and re-open the Claude desktop app to see the Vectara-mcp server. You should see a hammer icon in the bottom left of the app, indicating available MCP tools, you can click on the hammer icon to see more detial on the Vectara-search and Vectara-extract tools.

Now claude will have complete access to the Vectara-mcp server, including all six Vectara tools.

## Secure Setup Workflow

**First-time setup (one-time per session):**
1. Configure your API key securely:
```
setup-vectara-api-key
API key: [your-vectara-api-key]
```


**After setup, use any tools without exposing your API key:**

### Vectara Tool Examples

1. **RAG Query with Generation**:
```
ask-vectara
Query: Who is Amr Awadallah?
Corpus keys: ["your-corpus-key"]
```

2. **Semantic Search Only**:
```
search-vectara
Query: events in NYC?
Corpus keys: ["your-corpus-key"]
```

3. **Hallucination Correction**:
```
correct-hallucinations
Generated text: "The capital of France is Berlin and it's located in Germany."
Documents: ["Paris is the capital of France.", "Berlin is the capital of Germany."]
```

4. **Factual Consistency Evaluation**:
```
eval-factual-consistency
Generated text: "The Eiffel Tower was built in 1887 in London."
Documents: ["The Eiffel Tower was built in 1889 in Paris, France."]
```

## Alternative: Environment Variable Setup

You can also set the `VECTARA_API_KEY` environment variable instead of using the setup tool:

```bash
export VECTARA_API_KEY=your-vectara-api-key
```

The server will automatically detect and use environment variables, providing the same secure experience.

## Development and Release

### Running Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run integration tests
python -m pytest tests/test_integration.py -v -s

# Run unit tests
python -m pytest tests/test_server.py -v
```

### Releasing New Versions

This project uses GitHub Actions for automated PyPI publishing. To release a new version:

1. **Update version** in `pyproject.toml`
2. **Commit and push** changes to main branch
3. **Create and push a version tag**:
   ```bash
   git tag v<VERSION>
   git push origin v<VERSION>
   ```
4. **GitHub Actions will automatically**:
   - Run tests
   - Build the package
   - Publish to PyPI

The workflow requires **PyPI trusted publishing** to be configured:
- Go to [PyPI trusted publisher management](https://pypi.org/manage/account/publishing/)
- Add this repository with workflow: `publish-to-pypi.yml`

## Acknowledgments ✨

- [Model Context Protocol](https://modelcontextprotocol.io) for the MCP specification
- [Anthropic](https://anthropic.com) for Claude Desktop
