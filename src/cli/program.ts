import { Command } from "commander";
import chalk from "chalk";
import { spawn, execSync, type ChildProcess } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { join, resolve } from "node:path";

const PROFILE = "vyapaar";
const WORKSPACE_ROOT = join(homedir(), ".openclaw", "profiles", PROFILE);
const ENV_PATH = join(WORKSPACE_ROOT, ".env");

function getProjectRoot(): string {
  return resolve(import.meta.dirname ?? ".", "..");
}

function startMcpServer(): ChildProcess {
  const projectRoot = getProjectRoot();
  const envFile = existsSync(ENV_PATH) ? ENV_PATH : join(projectRoot, ".env");

  console.log(chalk.yellow("Starting VyapaarClaw MCP server (SSE)..."));

  const child = spawn("uv", ["run", "vyapaarclaw"], {
    cwd: projectRoot,
    stdio: "inherit",
    env: {
      ...process.env,
      VYAPAAR_TRANSPORT: "sse",
      ...(existsSync(envFile) ? { ENV_FILE: envFile } : {}),
    },
    detached: false,
  });

  child.on("error", (err) => {
    console.error(chalk.red(`MCP server failed to start: ${err.message}`));
  });

  return child;
}

export function buildProgram(): Command {
  const program = new Command();

  program
    .name("vyapaarclaw")
    .description(
      "VyapaarClaw — Fully Managed OpenClaw Framework for AI Financial Governance"
    )
    .version("0.1.0");

  program
    .command("bootstrap")
    .description("Set up VyapaarClaw: credentials, workspace, and OpenClaw profile")
    .action(async () => {
      const { runBootstrap } = await import("./bootstrap.js");
      await runBootstrap();
    });

  program
    .command("start")
    .description("Start the VyapaarClaw MCP server and Agent")
    .option("--mcp-only", "Start only the MCP server (no agent)")
    .action(async (opts) => {
      const mcpChild = startMcpServer();

      if (!opts.mcpOnly) {
        await new Promise<void>((r) => setTimeout(r, 2000));

        console.log(
          chalk.cyan(`\nStarting VyapaarClaw Agent (Profile: ${PROFILE})...`)
        );

        try {
          // Use npx to ensure it resolves the local openclaw dependency
          const oc = spawn(
            "npx",
            ["openclaw", "--profile", PROFILE, "gateway"],
            { stdio: "inherit", env: process.env }
          );

          oc.on("error", (err) => {
            console.log(
              chalk.red(
                `Failed to start VyapaarClaw Agent: ${err.message}`
              )
            );
          const shutdown = () => {
            mcpChild.kill();
            oc.kill();
            process.exit(0);
          };
          process.on("SIGINT", shutdown);
          process.on("SIGTERM", shutdown);

          await new Promise<void>((resolve) => {
            oc.once("exit", () => {
              mcpChild.kill();
              resolve();
            });
          });
        } catch {
          console.log(
            chalk.dim(
              "VyapaarClaw Agent failed to start."
            )
          );
          await new Promise<void>((resolve) => {
            mcpChild.once("exit", resolve);
          });
        }
      } else {
        console.log(
          chalk.green(
            "MCP server running at http://localhost:8000/sse"
          )
        );
        await new Promise<void>((resolve) => {
          mcpChild.once("exit", resolve);
        });
      }
    });

  program
    .command("stop")
    .description("Stop the VyapaarClaw MCP server, web UI, and OpenClaw gateway")
    .action(() => {
      console.log(chalk.yellow("Stopping VyapaarClaw..."));

      try {
        execSync("pkill -f 'vyapaarclaw'", { stdio: "ignore" });
        console.log(chalk.green("  MCP server stopped."));
      } catch {
        console.log(chalk.dim("  MCP server was not running."));
      }

      const webResult = stopWebServer();
      if (webResult.stopped) {
        console.log(chalk.green(`  Web UI stopped (pid ${webResult.pid}).`));
      } else {
        console.log(chalk.dim("  Web UI was not running."));
      }

      try {
        execSync(`openclaw --profile ${PROFILE} gateway stop`, {
          stdio: "inherit",
        });
      } catch {
        console.log(chalk.dim("  OpenClaw gateway was not running."));
      }
    });

  program
    .command("restart")
    .description("Restart the VyapaarClaw MCP server")
    .action(async () => {
      console.log(chalk.yellow("Restarting VyapaarClaw..."));
      try {
        execSync("pkill -f 'vyapaarclaw'", { stdio: "ignore" });
      } catch {
        // Not running
      }
      await new Promise<void>((r) => setTimeout(r, 1000));
      startMcpServer();
      console.log(chalk.green("MCP server restarted."));
    });

  program
    .command("mcp")
    .description("Start only the MCP server (SSE mode)")
    .action(async () => {
      const child = startMcpServer();
      await new Promise<void>((resolve) => {
        child.once("exit", resolve);
      });
    });

  program
    .command("status")
    .description("Check VyapaarClaw service status")
    .action(async () => {
      console.log(chalk.bold("VyapaarClaw Status\n"));

      // Check MCP server
      try {
        const resp = await fetch("http://localhost:8000/health");
        if (resp.ok) {
          const data = await resp.json();
          console.log(chalk.green("  MCP Server:  running"));
          console.log(
            chalk.dim(`    Redis:     ${data.redis ?? "unknown"}`)
          );
          console.log(
            chalk.dim(`    Postgres:  ${data.postgres ?? "unknown"}`)
          );
          console.log(
            chalk.dim(`    Uptime:    ${data.uptime_seconds ?? 0}s`)
          );
        } else {
          console.log(chalk.red("  MCP Server:  error"));
        }
      } catch {
        console.log(chalk.red("  MCP Server:  not running"));
      }

      // Check web UI
      const webInfo = isWebRunning();
      if (webInfo) {
        console.log(
          chalk.green(`  Web UI:      http://localhost:${webInfo.port} (pid ${webInfo.pid})`)
        );
      } else {
        console.log(chalk.dim("  Web UI:      not running"));
      }

      // Check workspace
      console.log(
        existsSync(WORKSPACE_ROOT)
          ? chalk.green(`  Workspace:   ${WORKSPACE_ROOT}`)
          : chalk.yellow("  Workspace:   not set up (run vyapaarclaw bootstrap)")
      );
    });

  program
    .command("tui")
    .description("Launch the terminal UI dashboard (Python Textual)")
    .action(() => {
      console.log(chalk.yellow("Launching VyapaarClaw TUI..."));
      const projectRoot = getProjectRoot();
      const tui = spawn("uv", ["run", "vyapaarclaw-tui"], {
        cwd: projectRoot,
        stdio: "inherit",
      });
      tui.on("error", (err) => {
        if ((err as NodeJS.ErrnoException).code === "ENOENT") {
          console.log(
            chalk.red("uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh")
          );
        }
      });
    });

  // Default command: bootstrap
  program.action(async () => {
    const { runBootstrap } = await import("./bootstrap.js");
    await runBootstrap();
  });

  return program;
}
