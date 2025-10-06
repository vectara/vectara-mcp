from setuptools import setup, find_packages

setup(
    name="vectara-mcp",
    version="0.2.0",
    description="Open source MCP server for Vectara",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Ofer Mendelevitch",
    author_email="ofer@vectara.com",
    url="https://github.com/vectara/vectara-mcp",
    packages=find_packages(),  # Automatically find all packages
    install_requires=[
        "mcp>=1.6.0",
        "fastmcp>=0.4.1",
        "fastapi>=0.95.0",
        "uvicorn>=0.34.0",
        "aiohttp>=3.8.0",
        "tenacity>=8.0.0",
        "python-dotenv>=1.0.0",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: Linguistic",
    ],
    python_requires=">=3.11",  # Specify the minimum Python version
    entry_points={
        "console_scripts": [
            "vectara-mcp=vectara_mcp.server:main",
        ],
    },
    keywords="vectara, mcp, rag, ai, search, semantic-search",
    project_urls={
        "Bug Reports": "https://github.com/vectara/vectara-mcp/issues",
        "Source": "https://github.com/vectara/vectara-mcp",
    },
)
