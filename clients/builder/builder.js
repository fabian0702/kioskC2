// import express from "express";
import { rollup } from "rollup";
import path from "path";
import fs from "fs";

const SRC_DIR = path.resolve("src");
const PLUGIN_DIR = path.resolve("plugins")
const FLATTENED_DIR = path.resolve("flattened");

const DIST_DIR = path.resolve("dist");
const BUNDLE_PATH = path.join(DIST_DIR, "bundle.js");

// Ensure dist directory exists
if (!fs.existsSync(DIST_DIR)) {
  fs.mkdirSync(DIST_DIR);
}

async function loadRollupConfig() {
  const configPath = path.resolve("rollup.config.js");

  if (!fs.existsSync(configPath)) {
    throw new Error("rollup.config.js not found in current directory");
  }

  // Dynamic import so ESM/CJS both work in Node
  const imported = await import(configPath);
  const config = imported.default || imported;

  return Array.isArray(config) ? config[0] : config;
}

const config = await loadRollupConfig();

// async function buildBundle() {
fs.cpSync(PLUGIN_DIR, FLATTENED_DIR, { recursive: true });
fs.cpSync(SRC_DIR, FLATTENED_DIR, { recursive: true });

const bundle = await rollup(config);

const outputOptions = Array.isArray(config.output)
  ? config.output[0]
  : config.output || {
    file: BUNDLE_PATH,
    format: "esm",
  };

await bundle.write(outputOptions);
await bundle.close();

console.log("Bundle rebuilt successfully");
// }

/*fs.watch(PLUGIN_DIR, async function (eventType, filename) {
  console.log(`Plugin directory changed: ${eventType} on ${filename}`);

  try {
    await buildBundle();
  } catch (err) {
    console.error("Error rebuilding bundle:", err);
  }
});*/