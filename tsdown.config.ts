import { defineConfig } from "tsdown";

export default defineConfig({
  entry: ["src/entry.ts"],
  format: "esm",
  target: "node22",
  clean: true,
  dts: true,
});
