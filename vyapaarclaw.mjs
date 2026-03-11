#!/usr/bin/env node

import module from "node:module";

if (module.enableCompileCache && !process.env.NODE_DISABLE_COMPILE_CACHE) {
  try {
    module.enableCompileCache();
  } catch {
    // Ignore errors
  }
}

const isModuleNotFoundError = (err) =>
  err &&
  typeof err === "object" &&
  "code" in err &&
  err.code === "ERR_MODULE_NOT_FOUND";

const tryImport = async (specifier) => {
  try {
    await import(specifier);
    return true;
  } catch (err) {
    if (isModuleNotFoundError(err)) {
      return false;
    }
    throw err;
  }
};

if (await tryImport("./dist/entry.js")) {
  // Built output found
} else if (await tryImport("./dist/entry.mjs")) {
  // Alternative extension
} else {
  // Fallback: run from source via tsx if available, otherwise error
  console.error(
    "[vyapaarclaw] dist/ not found. Run `pnpm build` first, or use `npx tsx src/entry.ts`."
  );
  process.exit(1);
}
