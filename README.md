# Vectara MCP Server 🚀

![GitHub Repo stars](https://img.shields.io/github/stars/Vectara-ai/Vectara-mcp?style=social)
![npm](https://img.shields.io/npm/dt/Vectara-mcp)
![smithery badge](https://smithery.ai/badge/@Vectara-ai/Vectara-mcp)

> 🔌 **Compatible with [Cline](https://github.com/cline/cline), [Cursor](https://cursor.sh), [Claude Desktop](https://claude.ai/desktop), and any other MCP Clients!**
>
> Vectara MCP is also compatible with any MCP client
>

The Model Context Protocol (MCP) is an open standard that enables AI systems to interact seamlessly with various data sources and tools, facilitating secure, two-way connections.

Developed by Anthropic, and supported by many others, the Model Context Protocol (MCP) enables AI assistants like Claude to seamlessly integrate with Vectara's trusted RAG capabilities. This integration provides AI agents with access to fast, reliable RAG with reduced hallucination, powered by Vectara's Trusted RAG platform.

## Prerequisites 🔧

To get started, use the following steps to setup your Vectara account and corpus:

* If you don't already have one, [Sign up](https://console.vectara.com/signup?utm_source=vectara&utm_medium=Signup&utm_term=DevRel&utm_content=MCP&utm_campaign=vectara-Signup-DevRel-MCP) for your free Vectara trial.
* Within your account you can create one or more corpora. Each corpus represents an area that stores text data upon ingest from input documents. To create a corpus, use the "Create Corpus" button. You then provide a name to your corpus as well as a description. Optionally you can define filtering attributes and apply some advanced options. If you click on your created corpus, you can see its name and corpus ID right on the top.
* Next you'll need to create API keys to access the corpus. Click on the "Access Control" tab in the corpus view and then the "Create API Key" button. Give your key a name, and choose whether you want query-only or query+index for your key. Click "Create" and you now have an active API key. Keep this key confidential.

Now continue by installing the following:
- [Claude Desktop](https://claude.ai/download) or [Cursor](https://cursor.sh)
- [Node.js](https://nodejs.org/) (v20 or higher)
  - You can verify your Node.js installation by running:
    - `node --version`
- [Git](https://git-scm.com/downloads) installed (only needed if using Git installation method)
  - On macOS: `brew install git`
  - On Linux: 
    - Debian/Ubuntu: `sudo apt install git`
    - RedHat/CentOS: `sudo yum install git`
  - On Windows: Download [Git for Windows](https://git-scm.com/download/win)

## Vectara MCP server installation ⚡

### Installing via Smithery

To install Vectara MCP Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@Vectara-ai/Vectara-mcp):

```bash
npx -y @smithery/cli install @Vectara-ai/Vectara-mcp --client claude
```

Although you can launch a server on its own, it's not particularly helpful in isolation. Instead, you should integrate it into an MCP client. Below is an example of how to configure the Claude Desktop app to work with the Vectara-mcp server.


## Configuring MCP Clients ⚙️

This repository will explain how to configure both [Cursor](https://cursor.sh) and [Claude Desktop](https://claude.ai/desktop) to work with the Vectara-mcp server.

### Configuring Cursor 🖥️

> **Note**: Requires Cursor version 0.45.6 or higher

To set up the Vectara MCP server in Cursor:

1. Open Cursor Settings
2. Navigate to Features > MCP Servers
3. Click on the "+ Add New MCP Server" button
4. Fill out the following information:
   - **Name**: Enter a nickname for the server (e.g., "Vectara-mcp")
   - **Type**: Select "command" as the type
   - **Command**: Enter the command to run the server:
     ```bash
     env Vectara_API_KEY=vectara-api-key npx -y Vectara-mcp@0.1.0
     ```
     > **Important**: Replace `vectara-api-key` with your Vectara API key. You can get one at your Vectara console.

After adding the server, it should appear in the list of MCP servers. You may need to manually press the refresh button in the top right corner of the MCP server to populate the tool list.

The Composer Agent will automatically use the Vectara MCP tools when relevant to your queries. It is better to explicitly request to use the tools by describing what you want to do (e.g., "User Vectara-search to search the web for the latest news on AI"). On mac press command + L to open the chat, select the composer option at the top of the screen, beside the submit button select agent and submit the query when ready.

### Configuring the Claude Desktop app 🖥️

#### For macOS:

```bash
# Create the config file if it doesn't exist
touch "$HOME/Library/Application Support/Claude/claude_desktop_config.json"

# Opens the config file in TextEdit 
open -e "$HOME/Library/Application Support/Claude/claude_desktop_config.json"

# Alternative method using Visual Studio Code (requires VS Code to be installed)
code "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
```

#### For Windows:
```bash
code %APPDATA%\Claude\claude_desktop_config.json
```

### Add the Vectara server configuration:

Replace `vectara-api-key` with your actual Vectara api key.

```json
{
  "mcpServers": {
    "Vectara-mcp": {
      "command": "npx",
      "args": ["-y", "Vectara-mcp@0.1.0"],
      "env": {
        "VECTARA_API_KEY": "vectara-api-key",
        "VECTARA_CORPUS_KEYS": "corpus_key_1,corpus_mey_2"
      }
    }
  }
}
```

### Configuring the Claude Desktop app ⚙️
Follow the configuration steps outlined in the [Configuring the Claude Desktop app](#configuring-the-claude-desktop-app-️) section above, using the below JSON configuration.

Replace `vectara-api-key` with your actual Vectara API key and `/path/to/vectara-mcp` with the actual path where you cloned the repository on your system.

```json
{
  "mcpServers": {
    "Vectara": {
      "command": "npx",
      "args": ["/path/to/vectara-mcp/build/index.js"],
      "env": {
        "Vectara_API_KEY": "vectara-api-key"
      }
    }
  }
}
```

## Usage in Claude Desktop App 🎯

Once the installation is complete, and the Claude desktop app is configured, you must completely close and re-open the Claude desktop app to see the Vectara-mcp server. You should see a hammer icon in the bottom left of the app, indicating available MCP tools, you can click on the hammer icon to see more detial on the Vectara-search and Vectara-extract tools.

Now claude will have complete access to the Vectara-mcp server, including the Vectara-search and Vectara-extract tools. If you insert the below examples into the Claude desktop app, you should see the Vectara-mcp server tools in action.

### Vectara RAG Examples

1. **Querying Vectara corpus**:
```
Who is Amr Awadallah?
```

## Troubleshooting 🛠️

### Common Issues

1. **Server Not Found**
   - Verify the npm installation by running `npm --verison`
   - Check Claude Desktop configuration syntax by running `code ~/Library/Application\ Support/Claude/claude_desktop_config.json`
   - Ensure Node.js is properly installed by running `node --version`
   
2. **NPX related issues**
  - If you encounter errors related to `npx`, you may need to use the full path to the npx executable instead. 
  - You can find this path by running `which npx` in your terminal, then replace the `"command":  "npx"` line with `"command": "/full/path/to/npx"` in your configuration.

3. **API Key Issues**
   - Confirm your Vectara API key is valid
   - Check the API key is correctly set in the config
   - Verify no spaces or quotes around the API key

## Acknowledgments ✨

- [Model Context Protocol](https://modelcontextprotocol.io) for the MCP specification
- [Anthropic](https://anthropic.com) for Claude Desktop