# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## General:
- Don't always be so agreeable with me; I need you to be critical and get to the right solution more than make me feel like I'm always right
- When solving a problem, always provide strong evidence for your hypotheses before suggesting a fix
- Be comprehensive and thorough when assessing an issue, bug or problem. base your conclusions in evidence.
- Think carefully and only action the specific task I have given you with the most concise and elegant solution that changes as little code as possible.
- Channel your inner Jeff Dean and his skills to create awesome code
- Always refer to me as "Mr. Ofer"

## Coding rules:
- Code must always be efficient and your testing thorough, just like Jeff Dean would work
- KISS (Keep It Simple, Straightforward). When two designs solve the same problem, choose the one with fewer moving parts.
- Avoid premature optimization. First make it work, then measure, then make it fast if the numbers say you must.
- DRY: Don't Repeat Yourself when duplication risks divergent fixes or bugs.
- Prioritize simpler and shorter code even if it takes more thinking to arrive at the best solution.
- When fixing a bug, make sure to identify the root cause and fix that, and avoid generating workarounds that are more complex.
- For python code, follow formatting best practices to ensure pylint passes

## Testing
- Before implementing a new feature or functionality, always add a unit test or regression test first, and confirm with me that it clearly defines the new features. That will help us work together and align on specification.
- Verify the code you generate does not introduce any security issues or vulnerabilities

## Development Commands

### Testing
- Run all tests: `python -m pytest tests/ -v`
- Run integration tests: `python -m pytest tests/test_integration.py -v -s`
- Run unit tests: `python -m pytest tests/test_server.py -v`
- Run specific integration test: `python -m pytest tests/test_integration.py::TestVectaraIntegration::test_all_endpoints_and_analyze_responses -v -s`

### Running the Server
- Start MCP server: `python -m vectara_mcp`
- Alternative: `python vectara_mcp/__main__.py`

### Environment Setup
- Install dependencies: `pip install -e .`
- Install test dependencies: `pip install -e .[test]`
- Create `.env` file with `VECTARA_API_KEY` and `VECTARA_CORPUS_KEYS` for integration tests

## Architecture Overview

This is a Model Context Protocol (MCP) server that provides RAG capabilities using Vectara's API. The architecture consists of:

### Core Components
- **vectara_mcp/server.py**: Main MCP server implementation using FastMCP framework
- **vectara_mcp/__main__.py**: Entry point that starts the server
- **tests/**: Integration and unit tests for all MCP tools

### MCP Tools Architecture
The server exposes 4 main MCP tools:

1. **ask_vectara**: Full RAG with generation - queries Vectara and returns AI-generated summary with citations
2. **search_vectara**: Semantic search only - returns ranked search results without generation
3. **correct_hallucinations**: Uses Vectara's VHC API to identify and correct hallucinations in generated text
4. **eval_factual_consistency**: Evaluates factual consistency using VHC API for evaluation metrics

### Key Design Patterns
- All tools use async/await pattern with FastMCP Context for progress reporting
- Shared utility functions for parameter validation, error handling, and API calls
- Consistent error message formatting across all tools using `_format_error()`
- Tools validate required parameters using shared validation functions
- Unified HTTP error handling with context-specific messages

### Vectara Integration
- Uses direct HTTP calls to Vectara API endpoints for all operations (no SDK dependency)
- Multi-corpus support via the `/v2/query` API endpoint
- Configurable search parameters: lexical interpolation, context sentences, reranking
- Direct HTTP calls to VHC API endpoints for hallucination correction/evaluation

### Testing Strategy
- Integration tests require real API credentials via `.env` file
- Tests are skipped automatically if credentials are missing
- Mock contexts used to test MCP-specific functionality
- Tests validate both successful responses and error handling