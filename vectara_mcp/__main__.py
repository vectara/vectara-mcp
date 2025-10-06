# __main__.py
"""
Vectara MCP Server entry point.

Supports multiple transports:
- HTTP (default, secure)
- SSE (Server-Sent Events)
- STDIO (for local development)
"""

from vectara_mcp.server import main

if __name__ == "__main__":
    main()