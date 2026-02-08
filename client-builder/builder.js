// import express from "express";
import { rollup } from "rollup";
import path from "path";
import fs from "fs";
import { connect, deferred, nuid } from "@nats-io/transport-node";

//const app = express();
//const PORT = 3000;


const nc = await connect({ servers: "nats:4222" });
console.log(`connected`);

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

nc.subscribe("client.page-build", {
  callback: (err, msg) => {
    buildBundle().then(() => {
      console.log("Bundle built successfully");
      msg.respond(Buffer.from("success"));
    });
  },
});

async function buildBundle() {
  const config = await loadRollupConfig();

  const bundle = await rollup(config);

  const outputOptions = Array.isArray(config.output)
    ? config.output[0]
    : config.output || {
        file: BUNDLE_PATH,
        format: "esm",
      };

  await bundle.write(outputOptions);
  await bundle.close();
}

/*// Endpoint to trigger build
app.post("/build", async (req, res) => {
  try {
    await buildBundle();
    res.json({ success: true, message: "Bundle built successfully using rollup.config.js." });
  } catch (err) {
    console.error(err);
    res.status(500).json({ success: false, error: err.message });
  }
});

// Endpoint to fetch the bundle
app.get("/bundle", async (req, res) => {
  try {
    const config = await loadRollupConfig();

    const outputOptions = Array.isArray(config.output)
      ? config.output[0]
      : config.output;

    const filePath = outputOptions?.file
      ? path.resolve(outputOptions.file)
      : BUNDLE_PATH;

    if (!fs.existsSync(filePath)) {
      return res.status(404).json({ error: "Bundle not found. Run /build first." });
    }

    res.sendFile(filePath);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`Rollup build server running at http://localhost:${PORT}`);
});*/