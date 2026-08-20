import { McpServer, ResourceTemplate } from "@modelcontextprotocol/server";
import { StdioServerTransport } from "@modelcontextprotocol/server/stdio";
import { z } from "zod";
import { callRepoGuardian, executeRhdTool, repositoryByName } from "./backend.js";
import { promptCatalog, toolCatalog } from "./catalog.js";

function textContent(value: unknown) {
  return { content: [{ type: "text" as const, text: JSON.stringify(value, null, 2) }] };
}

export function createServer() {
  const server = new McpServer(
    { name: "repoguardian-rhd", version: "1.0.0" },
    {
      capabilities: {
        tools: {},
        resources: {},
        prompts: {},
      },
      instructions: "RepoGuardian RHD exposes repository-scoped, evidence-grounded tools. Write-gated actions require human approval outside MCP.",
    },
  );

  for (const item of toolCatalog) {
    server.registerTool(
      item.name,
      ({
        title: item.title,
        description: item.description,
        inputSchema: item.inputSchema,
        annotations: {
          readOnlyHint: item.safety === "read",
          destructiveHint: item.safety === "write_gated",
          idempotentHint: item.safety !== "write_gated",
          openWorldHint: false,
        },
        _meta: {
          "repoguardian/safety": item.safety,
          "repoguardian/requiresApproval": Boolean(item.requiresApproval),
        },
      }) as never,
      async (args: Record<string, unknown>) => {
        const result = await executeRhdTool(item.name, args as Record<string, unknown>);
        return textContent(result);
      },
    );
  }

  server.registerResource(
    "rhd-system-status",
    "repoguardian://system/status",
    { title: "RepoGuardian System Status", description: "Read-only backend and platform health status." },
    async (uri) => ({
      contents: [{ uri: uri.href, mimeType: "application/json", text: JSON.stringify(await callRepoGuardian("/api/system/status"), null, 2) }],
    }),
  );

  server.registerResource(
    "repo-summary",
    new ResourceTemplate("repo://{owner}/{name}/summary", { list: undefined }),
    { title: "Repository Summary", description: "Read-only synchronized repository summary." },
    async (uri, variables) => {
      const fullName = `${variables.owner}/${variables.name}`;
      const repo = await repositoryByName(fullName);
      if (!repo) throw new Error(`Repository is not synchronized in RepoGuardian: ${fullName}`);
      return { contents: [{ uri: uri.href, mimeType: "application/json", text: JSON.stringify(repo, null, 2) }] };
    },
  );

  server.registerResource(
    "repo-health",
    new ResourceTemplate("repo://{owner}/{name}/health", { list: undefined }),
    { title: "Repository Health", description: "Read-only RHD health review resource." },
    async (uri, variables) => {
      const fullName = `${variables.owner}/${variables.name}`;
      const repo = await repositoryByName(fullName);
      if (!repo) throw new Error(`Repository is not synchronized in RepoGuardian: ${fullName}`);
      const result = await executeRhdTool("rhd_health_review", { repository_id: repo.id });
      return { contents: [{ uri: uri.href, mimeType: "application/json", text: JSON.stringify(result, null, 2) }] };
    },
  );

  for (const prompt of promptCatalog) {
    server.registerPrompt(
      prompt.name,
      {
        title: prompt.title,
        description: prompt.description,
        argsSchema: { repository: z.string().describe("Repository full name, for example owner/repo") },
      },
      ({ repository }) => ({
        messages: [
          {
            role: "user" as const,
            content: {
              type: "text" as const,
              text: `${prompt.text}\n\nRepository: ${repository}\nUse MCP tools/resources for facts. Human approval is required for external write actions.`,
            },
          },
        ],
      }),
    );
  }

  return server;
}

if (!process.env.REPOGUARDIAN_MCP_NO_START) {
  const server = createServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
}
