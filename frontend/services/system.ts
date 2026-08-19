import { API_BASE_URL } from "@/lib/api";
import type { SystemStatus } from "@/types/system";

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const response = await fetch(`${API_BASE_URL}/api/system/status`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Unable to load system status");
  }
  return response.json() as Promise<SystemStatus>;
}
