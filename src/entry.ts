#!/usr/bin/env node
import { spawn } from "node:child_process";
import process from "node:process";

process.title = "vyapaarclaw";

const PROFILE = "vyapaar";

function shouldDelegateToOpenClaw(argv: string[]): boolean {
  const primary = argv[2];
  if (!primary) return false;
  if (primary.startsWith("-")) return false;
  const ownCommands = new Set([
    "bootstrap",
    "update",
    "start",
    "stop",
    "restart",
    "mcp",
    "status",
  ]);
  return !ownCommands.has(primary);
}

async function delegateToOpenClaw(argv: string[]): Promise<number> {
  const delegatedArgv = ["--profile", PROFILE, ...argv.slice(2)];
  return await new Promise<number>((resolve, reject) => {
    const child = spawn("openclaw", delegatedArgv, {
      stdio: "inherit",
      env: process.env,
    });

    child.once("error", (error) => {
      const err = error as NodeJS.ErrnoException;
      if (err?.code === "ENOENT") {
        reject(
          new Error(
            [
              "Global `openclaw` CLI was not found on PATH.",
              "Install it first: npm install -g openclaw@latest",
            ].join("\n")
          )
        );
        return;
      }
      reject(error);
    });

    child.once("exit", (code, signal) => {
      resolve(signal ? 1 : code ?? 1);
    });
  });
}

async function main() {
  const { emitBanner } = await import("./cli/banner.js");
  const { buildProgram } = await import("./cli/program.js");

  if (!process.argv.includes("--json") && process.stdout.isTTY) {
    await emitBanner();
  }

  if (shouldDelegateToOpenClaw(process.argv)) {
    try {
      const exitCode = await delegateToOpenClaw(process.argv);
      process.exitCode = exitCode;
    } catch (error) {
      console.error(
        `[vyapaarclaw] ${error instanceof Error ? error.message : error}`
      );
      process.exitCode = 1;
    }
    return;
  }

  const program = buildProgram();
  await program.parseAsync(process.argv);
}

main().catch((error) => {
  console.error(
    "[vyapaarclaw] Fatal:",
    error instanceof Error ? error.stack ?? error.message : error
  );
  process.exitCode = 1;
});
