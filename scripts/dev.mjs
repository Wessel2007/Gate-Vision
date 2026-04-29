import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, "..");
const backendDir = path.join(rootDir, "backend");
const frontendPort = 4173;
const frontendUrl = `http://127.0.0.1:${frontendPort}`;
const shouldOpenBrowser = !process.argv.includes("--no-open");

let backendProcess = null;
let frontendProcess = null;
let shuttingDown = false;

function log(msg) {
  console.log(`[dev] ${msg}`);
}

function openBrowser(url) {
  spawn("cmd", ["/c", "start", "", url], {
    detached: true,
    stdio: "ignore"
  }).unref();
}

function killProcessTree(processRef) {
  return new Promise((resolve) => {
    if (!processRef?.pid) {
      resolve();
      return;
    }

    const killer = spawn("taskkill", ["/pid", String(processRef.pid), "/t", "/f"], {
      stdio: "ignore"
    });

    killer.on("exit", () => resolve());
    killer.on("error", () => resolve());
  });
}

function startBackend() {
  if (!fs.existsSync(path.join(backendDir, "start.bat"))) {
    throw new Error("Arquivo backend/start.bat nao encontrado.");
  }

  backendProcess = spawn("cmd", ["/c", "start.bat"], {
    cwd: backendDir,
    stdio: "inherit"
  });
}

function startFrontend() {
  frontendProcess = spawn("cmd", ["/c", "npm", "run", "dev:front", "--", "--host", "127.0.0.1", "--port", String(frontendPort)], {
    cwd: rootDir,
    stdio: "inherit"
  });
}

async function shutdown(signal = "encerramento") {
  if (shuttingDown) return;
  shuttingDown = true;
  log(`recebido ${signal}, finalizando processos...`);

  await Promise.all([
    killProcessTree(frontendProcess),
    killProcessTree(backendProcess)
  ]);

  process.exit(0);
}

process.on("SIGINT", () => { void shutdown("SIGINT"); });
process.on("SIGTERM", () => { void shutdown("SIGTERM"); });

log("iniciando backend/start.bat...");
startBackend();
log(`iniciando frontend React em ${frontendUrl}...`);
startFrontend();

if (shouldOpenBrowser) {
  setTimeout(() => {
    log("abrindo navegador...");
    openBrowser(frontendUrl);
  }, 2500);
}
