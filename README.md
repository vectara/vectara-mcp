[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/vectara-vectara-mcp-badge.png)](https://mseep.ai/app/vectara-vectara-mcp)

# Vectara MCP Server

![GitHub Repo stars](https://img.shields.io/github/stars/Vectara/Vectara-mcp?style=social)
![PyPI version](https://img.shields.io/pypi/v/vectara-mcp.svg)
![License](https://img.shields.io/pypi/l/vectara-mcp.svg)
![Security](https://img.shields.io/badge/security-first-brightgreen)

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

## Quick Start

### Secure by Default (HTTP/SSE with Authentication)

```bash
# Start server with secure HTTP transport (DEFAULT)
python -m vectara_mcp
# Server running at http://127.0.0.1:8000 with authentication enabled
```

### Local Development Mode (STDIO)

```bash
# For Claude Desktop or local development (less secure)
python -m vectara_mcp --stdio
# ⚠️ Warning: STDIO transport is less secure. Use only for local development.
```

### Configuration Options

```bash
# Custom host and port
python -m vectara_mcp --host 0.0.0.0 --port 8080

# SSE transport mode
python -m vectara_mcp --transport sse --path /sse

# Disable authentication (DANGEROUS - dev only)
python -m vectara_mcp --no-auth
```

## Transport Modes

### HTTP Transport (Default - Recommended)
- **Security:** Built-in authentication via bearer tokens
- **Encryption:** HTTPS ready
- **Rate Limiting:** 100 requests/minute by default
- **CORS Protection:** Configurable origin validation
- **Use Case:** Production deployments, cloud environments

### SSE Transport
- **Streaming:** Server-Sent Events for real-time updates
- **Authentication:** Bearer token support
- **Compatibility:** Works with legacy MCP clients
- **Use Case:** Real-time streaming applications

### STDIO Transport
- **⚠️ Security Warning:** No transport-layer security
- **Performance:** Low latency for local communication
- **Use Case:** Local development, Claude Desktop
- **Requirement:** Must be explicitly enabled with `--stdio` flag

## Environment Variables

```bash
# Required
export VECTARA_API_KEY="your-api-key"

# Optional
export VECTARA_AUTHORIZED_TOKENS="token1,token2"  # Additional auth tokens
export VECTARA_ALLOWED_ORIGINS="http://localhost:*,https://app.example.com"
export VECTARA_TRANSPORT="http"  # Default transport mode
export VECTARA_AUTH_REQUIRED="true"  # Enforce authentication
```

## Authentication

### HTTP/SSE Transport
When using HTTP or SSE transport, authentication is required by default:

```bash
# Using curl with bearer token
curl -H "Authorization: Bearer $VECTARA_API_KEY" \
     -H "Content-Type: application/json" \
     -X POST http://localhost:8000/call/ask_vectara \
     -d '{"query": "What is Vectara?", "corpus_keys": ["my-corpus"]}'

# Using X-API-Key header (alternative)
curl -H "X-API-Key: $VECTARA_API_KEY" \
     http://localhost:8000/sse
```

### Disabling Authentication (Development Only)
```bash
# ⚠️ NEVER use in production
python -m vectara_mcp --no-auth
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

To use with Claude Desktop, update your configuration to use STDIO transport:

```json
{
  "mcpServers": {
    "Vectara": {
      "command": "python",
      "args": ["-m", "vectara_mcp", "--stdio"],
      "env": {
        "VECTARA_API_KEY": "your-api-key"
      }
    }
  }
}
```

Or using uv:

```json
{
  "mcpServers": {
    "Vectara": {
      "command": "uv",
      "args": ["tool", "run", "vectara-mcp", "--stdio"]
    }
  }
}
```

**Note:** Claude Desktop requires STDIO transport. While less secure than HTTP, it's acceptable for local desktop use.

## Usage in Claude Desktop App

Once the installation is complete, and the Claude desktop app is configured, you must completely close and re-open the Claude desktop app to see the Vectara-mcp server. You should see a hammer icon in the bottom left of the app, indicating available MCP tools, you can click on the hammer icon to see more detail on the Vectara-search and Vectara-extract tools.

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

3. **Hallucination Detection & Correction**:
```
correct-hallucinations
Generated text: [text to check]
Documents: ["source1", "source2"]
```

4. **Factual Consistency Evaluation**:
```
eval-factual-consistency
Generated text: [text to evaluate]
Documents: ["reference1", "reference2"]
```

## Security Best Practices

1. **Always use HTTP transport for production** - Never expose STDIO transport to the network
2. **Keep authentication enabled** - Only disable with `--no-auth` for local testing
3. **Use HTTPS in production** - Deploy behind a reverse proxy with TLS termination
4. **Configure CORS properly** - Set `VECTARA_ALLOWED_ORIGINS` to restrict access
5. **Rotate API keys regularly** - Update `VECTARA_API_KEY` and `VECTARA_AUTHORIZED_TOKENS`
6. **Monitor rate limits** - Default 100 req/min, adjust based on your needs

See [SECURITY.md](SECURITY.md) for detailed security guidelines.

## Support

For issues, questions, or contributions, please visit:
https://github.com/vectara/vectara-mcp