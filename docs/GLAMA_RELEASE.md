# Glama release — YodMCP

Keep the Glama CMD on **stdio** (`yodmcp`), not `yodmcp-api`.

| Field | Value |
| --- | --- |
| CMD | `yodmcp` |
| Transport | MCP stdio |
| Data | `/data` sqlite (created in image) |

HTTP (`yodmcp --http`) is a separate product surface and will not score tools
unless Glama is configured for streamable HTTP.
