import { apiBaseUrl, mcpToken } from "./catalog.js";

export async function callRepoGuardian(path: string, init?: RequestInit): Promise<unknown> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  if (mcpToken) headers.set("Authorization", `Bearer ${mcpToken}`);
  const response = await fetch(`${apiBaseUrl}${path}`, { ...init, headers });
  const text = await response.text();
  const payload = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(`RepoGuardian API ${response.status}: ${JSON.stringify(payload).slice(0, 500)}`);
  }
  return payload;
}

export async function executeRhdTool(tool: string, payload: Record<string, unknown>): Promise<unknown> {
  return callRepoGuardian("/api/platform/tools/execute", {
    method: "POST",
    body: JSON.stringify({ tool, payload, approved: false }),
  });
}

export async function repositoryByName(fullName: string): Promise<Record<string, unknown> | undefined> {
  const repositories = (await callRepoGuardian("/api/repositories")) as Record<string, unknown>[];
  return repositories.find((repo) => repo.full_name === fullName);
}
