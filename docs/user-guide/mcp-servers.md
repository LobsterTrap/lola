# MCP Servers

AI Context Modules can include MCP (Model Context Protocol) server configurations in `module/mcps.json`. This allows modules to bundle tool access alongside skills and commands.

## Configuration

Lola supports both local and remote MCP servers:

**Local (stdio):**

```json
{
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
  }
}
```

**Remote (http/sse):**

```json
{
  "my-remote-server": {
    "type": "http",
    "url": "https://mcp.example.com/sse"
  }
}
```

MCP configurations are translated to each assistant's native format during installation.
