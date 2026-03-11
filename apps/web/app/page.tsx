"use client";

import { AppShell } from "./components/shell";
import { Dashboard } from "./components/dashboard";

export default function Home() {
  return (
    <AppShell>
      <Dashboard />
    </AppShell>
  );
}
