import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { CommandPalette } from "@/components/ui/command-palette";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "RepoGuardian",
  description: "Agentic Repository Intelligence & Maintenance"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${inter.className} rg-page`}>
        {children}
        <CommandPalette />
      </body>
    </html>
  );
}
