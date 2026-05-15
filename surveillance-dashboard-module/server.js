const http = require("http");
const fs = require("fs");
const path = require("path");

const ROOT = __dirname;
const PROJECT_ROOT = path.resolve(__dirname, "..");
const PORT = 4173;

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
};

function safeResolve(urlPath) {
  const target = urlPath === "/" ? "/index.html" : urlPath;
  const normalized = path.normalize(target).replace(/^(\.\.[/\\])+/, "");
  const candidate = path.resolve(ROOT, `.${normalized}`);
  if (candidate.startsWith(ROOT)) {
    return candidate;
  }
  const artifactCandidate = path.resolve(PROJECT_ROOT, `.${normalized}`);
  if (artifactCandidate.startsWith(PROJECT_ROOT)) {
    return artifactCandidate;
  }
  return null;
}

http.createServer((req, res) => {
  const filePath = safeResolve((req.url || "/").split("?")[0]);
  if (!filePath) {
    res.writeHead(403);
    res.end("Forbidden");
    return;
  }

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404);
      res.end("Not found");
      return;
    }

    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, { "Content-Type": MIME[ext] || "text/plain; charset=utf-8" });
    res.end(data);
  });
}).listen(PORT, () => {
  console.log(`Sentinel dashboard running at http://localhost:${PORT}`);
});
