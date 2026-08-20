import assert from "node:assert/strict";
import { Client } from "@modelcontextprotocol/client";
import { StdioClientTransport } from "@modelcontextprotocol/client/stdio";

const transport = new StdioClientTransport({
  command: process.execPath,
  args: ["./node_modules/tsx/dist/cli.mjs", "src/server.ts"],
  cwd: process.cwd(),
  stderr: "pipe",
});

const client = new Client({ name: "repoguardian-mcp-smoke", version: "1.0.0" });
await client.connect(transport);

const tools = await client.listTools();
assert.ok(tools.tools.some((tool) => tool.name === "rhd_search_repository"));
assert.ok(tools.tools.some((tool) => tool.name === "rhd_prepare_action"));

const resources = await client.listResources();
assert.ok(resources.resources.some((resource) => resource.uri === "repoguardian://system/status"));

const templates = await client.listResourceTemplates();
assert.ok(templates.resourceTemplates.some((template) => template.uriTemplate === "repo://{owner}/{name}/summary"));

const prompts = await client.listPrompts();
assert.ok(prompts.prompts.some((prompt) => prompt.name === "rhd-security-review"));

const prompt = await client.getPrompt({ name: "rhd-full-review", arguments: { repository: "owner/repo" } });
assert.equal(prompt.messages[0]?.role, "user");

await client.close();
