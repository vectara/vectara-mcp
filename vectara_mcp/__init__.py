"""
Vectara MCP Server

A Model Context Protocol server for Vectara Trusted Generative AI.
"""

from ._version import __version__

# Import main function for compatibility
from .server import main, mcp

# Define what gets imported with "from vectara-mcp import *"
__all__ = ["mcp", "main", "__version__"]
