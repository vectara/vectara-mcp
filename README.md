[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/vectara-vectara-mcp-badge.png)](https://mseep.ai/app/vectara-vectara-mcp)

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

- **ask_vectara:**
  Run a RAG query using Vectara, returning search results with a generated response.

  Args:

  - query: str, The user query to run - required.
  - corpus_keys: list[str], List of Vectara corpus keys to use for the search - required. Please ask the user to provide one or more corpus keys. 
  - api_key: str, The Vectara API key - required.
  - n_sentences_before: int, Number of sentences before the answer to include in the context - optional, default is 2.
  - n_sentences_after: int, Number of sentences after the answer to include in the context - optional, default is 2.
  - lexical_interpolation: float, The amount of lexical interpolation to use - optional, default is 0.005.
  - max_used_search_results: int, The maximum number of search results to use - optional, default is 10.
  - generation_preset_name: str, The name of the generation preset to use - optional, default is "vectara-summary-table-md-query-ext-jan-2025-gpt-4o".
  - response_language: str, The language of the response - optional, default is "eng".

  Returns:

    - The response from Vectara, including the generated answer and the search results.
<br><br>

- **search_vectara:**
    Run a semantic search query using Vectara, without generation.

  Args:

  - query: str, The user query to run - required.
  - corpus_keys: list[str], List of Vectara corpus keys to use for the search - required. Please ask the user to provide one or more corpus keys. 
  - api_key: str, The Vectara API key - required.
  - n_sentences_before: int, Number of sentences before the answer to include in the context - optional, default is 2.
  - n_sentences_after: int, Number of sentences after the answer to include in the context - optional, default is 2.
  - lexical_interpolation: float, The amount of lexical interpolation to use - optional, default is 0.005.
    
  Returns:
  - The response from Vectara, including the matching search results.


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

Now claude will have complete access to the Vectara-mcp server, including the ask-vectara and search-vectara tools. 
When you issue the tools for the first time, Claude will ask you for your Vectara api key and corpus key (or keys if you want to use multiple corpora). After you set those, you will be ready to go. Here are some examples you can try (with the Vectara corpus that includes information from our [website](https://vectara.com):

### Vectara RAG Examples

1. **Querying Vectara corpus**:
```
ask-vectara Who is Amr Awadallah?
```

2. **Searching Vectara corpus**:
```
search-vectara events in NYC?
```

## Acknowledgments ✨

- [Model Context Protocol](https://modelcontextprotocol.io) for the MCP specification
- [Anthropic](https://anthropic.com) for Claude Desktop
