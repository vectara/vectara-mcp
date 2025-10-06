"""
Vectara MCP Server

A Model Context Protocol server for Vectara Trusted Generative AI.
"""

__version__ = "0.2.0"

# Import main function for compatibility
from .server import main, mcp

# Define what gets imported with "from vectara-mcp import *"
__all__ = ["mcp", "main"]
