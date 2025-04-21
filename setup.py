from setuptools import setup, find_packages

setup(
    name="vectara-mcp",  # Replace with your package name
    version="0.1.3",     # Start with an initial version
    description="Open source MCP server for Vectara",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Ofer Mendelevitch",
    author_email="ofer@vectara.com",
    url="https://github.com/vectara/vectara-mcp",
    packages=find_packages(),  # Automatically find all packages
    install_requires=[
        "mcp>=1.6.0",
        "uvicorn>=0.34.0",
        "vectara>=0.2.44",
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
