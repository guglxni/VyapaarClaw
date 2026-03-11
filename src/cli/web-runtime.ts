import { spawn, type ChildProcess } from "node:child_process";
import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { homedir } from "node:os";
import { join, resolve } from "node:path";

export const DEFAULT_WEB_PORT = 3100;
const PROCESS_FILE = "web-process.json";

type WebProcessInfo = {
  pid: number;
  port: number;
  startedAt: string;
};

function getProcessFilePath(): string {
  const dir = join(homedir(), ".openclaw", "profiles", "vyapaar");
  mkdirSync(dir, { recursive: true });
  return join(dir, PROCESS_FILE);
}

function getWebAppDir(): string {
  const standaloneDir = resolve(
    import.meta.dirname ?? ".",
    "..",
    "apps",
    "web",
    ".next",
    "standalone",
    "apps",
    "web",
  );
  if (existsSync(standaloneDir)) return standaloneDir;

  return resolve(import.meta.dirname ?? ".", "..", "apps", "web");
}

export function isWebRunning(): WebProcessInfo | null {
  const path = getProcessFilePath();
  if (!existsSync(path)) return null;

  try {
    const info: WebProcessInfo = JSON.parse(readFileSync(path, "utf-8"));
    process.kill(info.pid, 0);
    return info;
  } catch {
    return null;
  }
}

export function startWebServer(port: number = DEFAULT_WEB_PORT): {
  started: boolean;
  pid?: number;
  port?: number;
  reason?: string;
} {
  const existing = isWebRunning();
  if (existing) {
    return {
      started: false,
      pid: existing.pid,
      port: existing.port,
      reason: "already-running",
    };
  }

  const appDir = getWebAppDir();
  const serverPath = join(appDir, "server.js");
  const useNextCli = !existsSync(serverPath);

  let child: ChildProcess;

  if (useNextCli) {
    child = spawn("npx", ["next", "start", "--port", String(port)], {
      cwd: appDir,
      stdio: "ignore",
      detached: true,
      env: {
        ...process.env,
        PORT: String(port),
        NODE_ENV: "production",
      },
    });
  } else {
    child = spawn("node", [serverPath], {
      cwd: appDir,
      stdio: "ignore",
      detached: true,
      env: {
        ...process.env,
        PORT: String(port),
        HOSTNAME: "0.0.0.0",
        NODE_ENV: "production",
      },
    });
  }

  child.unref();

  if (child.pid) {
    const info: WebProcessInfo = {
      pid: child.pid,
      port,
      startedAt: new Date().toISOString(),
    };
    writeFileSync(getProcessFilePath(), JSON.stringify(info, null, 2));
    return { started: true, pid: child.pid, port };
  }

  return { started: false, reason: "spawn-failed" };
}

export function stopWebServer(): { stopped: boolean; pid?: number } {
  const info = isWebRunning();
  if (!info) return { stopped: false };

  try {
    process.kill(info.pid, "SIGTERM");
    try {
      const path = getProcessFilePath();
      if (existsSync(path)) {
        const { unlinkSync } = require("node:fs");
        unlinkSync(path);
      }
    } catch {}
    return { stopped: true, pid: info.pid };
  } catch {
    return { stopped: false, pid: info.pid };
  }
}
