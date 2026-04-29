import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, "..");
const backendDir = path.join(rootDir, "backend");
const frontendDir = path.join(rootDir, "front", "Projeto-GateVision-main");
const frontendPort = 4173;
const frontendUrl = `http://127.0.0.1:${frontendPort}`;
const shouldOpenBrowser = !process.argv.includes("--no-open");

const mimeTypes = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".ico": "image/x-icon",
  ".webp": "image/webp"
};

let backendProcess = null;
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

function killBackendTree() {
  return new Promise((resolve) => {
    if (!backendProcess?.pid) {
      resolve();
      return;
    }

    const killer = spawn("taskkill", ["/pid", String(backendProcess.pid), "/t", "/f"], {
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

  backendProcess.on("exit", (code) => {
    if (!shuttingDown) {
      log(`backend finalizado com codigo ${code ?? "desconhecido"}`);
    }
  });

  backendProcess.on("error", (error) => {
    console.error("[dev] erro ao iniciar backend:", error);
  });
}

function resolveFileFromUrl(urlPath) {
  const cleanPath = decodeURIComponent(urlPath.split("?")[0]);
  const requestedPath = cleanPath === "/" ? "/index.html" : cleanPath;
  const normalized = path.normalize(requestedPath).replace(/^(\.\.[/\\])+/, "");
  const absolute = path.join(frontendDir, normalized);

  if (!absolute.startsWith(frontendDir)) return null;
  return absolute;
}

function createFrontendServer() {
  return http.createServer((req, res) => {
    const absolute = resolveFileFromUrl(req.url || "/");
    if (!absolute) {
      res.writeHead(403);
      res.end("Forbidden");
      return;
    }

    fs.readFile(absolute, (error, content) => {
      if (error) {
        if (error.code === "ENOENT") {
          res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
          res.end("Not found");
          return;
        }

        res.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" });
        res.end("Internal server error");
        return;
      }

      const ext = path.extname(absolute).toLowerCase();
      const contentType = mimeTypes[ext] || "application/octet-stream";
      res.writeHead(200, { "Content-Type": contentType });
      res.end(content);
    });
  });
}

const server = createFrontendServer();

async function shutdown(signal = "encerramento") {
  if (shuttingDown) return;
  shuttingDown = true;
  log(`recebido ${signal}, finalizando processos...`);

  await new Promise((resolve) => server.close(() => resolve()));
  await killBackendTree();
  process.exit(0);
}

process.on("SIGINT", () => { void shutdown("SIGINT"); });
process.on("SIGTERM", () => { void shutdown("SIGTERM"); });

server.listen(frontendPort, "127.0.0.1", () => {
  log(`frontend disponivel em ${frontendUrl}`);
  log("iniciando backend/start.bat...");
  startBackend();

  if (shouldOpenBrowser) {
    log("abrindo navegador...");
    openBrowser(frontendUrl);
  }
});
