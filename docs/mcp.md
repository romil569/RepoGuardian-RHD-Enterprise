# MCP Server

Status: `IMPLEMENTED` for stdio, `ROADMAP` for authenticated remote Streamable HTTP.

The MCP server lives in `mcp-server/` and uses the official TypeScript v2 split SDK packages:

- `@modelcontextprotocol/server`
- `@modelcontextprotocol/client`

## stdio

```powershell
cd C:\Users\HP\Desktop\RepoGuardian\mcp-server
npm install
$env:REPOGUARDIAN_API_URL="http://127.0.0.1:8000"
npm start
```

## Tools

- `rhd_search_repository`
- `rhd_full_review`
- `rhd_health_review`
- `rhd_daily_priorities`
- `rhd_generate_report`
- `rhd_get_review_queue`
- `rhd_prepare_action`

Write-gated tools are annotated as destructive and require human approval. The MCP server does not execute external GitHub writes.

## Resources

- `repoguardian://system/status`
- `repo://{owner}/{name}/summary`
- `repo://{owner}/{name}/health`

## Prompts

- `rhd-full-review`
- `rhd-security-review`
- `rhd-release-readiness`
- `rhd-engineering-manager-report`

## Tests

```powershell
cd mcp-server
npm run typecheck
npm test
```

Remote MCP over Streamable HTTP is a deployment roadmap item until authentication, rate limiting, and repository membership checks are wired for a public endpoint.
