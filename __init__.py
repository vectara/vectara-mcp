"""
Vectara MCP Server

A Model Context Protocol server for Vectara Trusted Generative AI.
"""

__version__ = "0.1.0"

# Import the functions we want to expose
from .server import mcp, cli

# Define what gets imported with "from vectara-mcp import *"
__all__ = ["mcp", "cli"]
