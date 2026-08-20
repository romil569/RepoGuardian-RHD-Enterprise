import { expect, test } from "@playwright/test";

const routes = [
  { path: "/", marker: /RHD Autonomous Repository Intelligence/i },
  { path: "/repositories", marker: /romil569\/RepoGuardian-Demo|No repository connected/i },
  { path: "/investigations", marker: /Issues/i },
  { path: "/review-queue", heading: /Review Queue/i },
  { path: "/audit-log", heading: /Audit Log/i },
  { path: "/mcp", heading: /RHD MCP Tool Matrix/i },
  { path: "/models", heading: /RHD Model Intelligence/i },
  { path: "/automation", heading: /RHD Automation Center/i },
  { path: "/system", heading: /RHD System/i },
  { path: "/architecture", heading: /RHD Production Architecture/i }
];

test.describe("RepoGuardian responsive routes", () => {
  for (const route of routes) {
    test(`${route.path} renders without horizontal overflow`, async ({ page }) => {
      const consoleErrors: string[] = [];
      page.on("console", (message) => {
        if (message.type() === "error") consoleErrors.push(message.text());
      });
      await page.goto(route.path);
      const expectedHeading = route.heading ?? route.marker;
      expect(expectedHeading).toBeDefined();
      await expect(page.locator("h1").first()).toContainText(expectedHeading!);
      await expect(page.getByText("Application error", { exact: false })).toHaveCount(0);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow).toBeLessThanOrEqual(2);
      expect(consoleErrors.filter((message) => !message.includes("Failed to fetch"))).toEqual([]);
    });
  }
});
