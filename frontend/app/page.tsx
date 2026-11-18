"use client";

import { AppShell } from "@/components/layout/AppShell";
import { WorkspaceProvider } from "@/hooks/useWorkspace";

export default function HomePage() {
  return (
    <WorkspaceProvider>
      <AppShell />
    </WorkspaceProvider>
  );
}
