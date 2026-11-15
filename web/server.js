"use strict";

const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");

const WEB_ROOT = __dirname;
const PORT = Number(process.env.PORT || 4173);
const HOST = process.env.HOST || "0.0.0.0";
const API_BASE_URL = (process.env.API_BASE_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");
const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".svg": "image/svg+xml",
};

let apiOrigin;
try {
  const apiUrl = new URL(API_BASE_URL);
  if (!["http:", "https:"].includes(apiUrl.protocol)) throw new Error("Unsupported API URL scheme");
  apiOrigin = apiUrl.origin;
} catch {
  throw new Error("API_BASE_URL must be a valid HTTP or HTTPS URL.");
}

function send(res, status, contentType, body, extraHeaders = {}) {
  res.writeHead(status, {
    "Content-Type": contentType,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": `default-src 'self'; script-src 'self'; style-src 'self'; style-src-attr 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ${apiOrigin}; object-src 'none'; base-uri 'self'; frame-ancestors 'none'`,
    ...extraHeaders,
  });
  res.end(body);
}

const server = http.createServer((req, res) => {
  if (!["GET", "HEAD"].includes(req.method || "")) {
    send(res, 405, "text/plain; charset=utf-8", "Method not allowed.", { Allow: "GET, HEAD" });
    return;
  }

  let pathname;
  try {
    pathname = decodeURIComponent(new URL(req.url || "/", "http://localhost").pathname);
  } catch {
    send(res, 400, "text/plain; charset=utf-8", "Invalid request path.");
    return;
  }

  if (pathname === "/runtime-config.js") {
    const config = JSON.stringify({ apiBaseUrl: API_BASE_URL }).replace(/</g, "\\u003c");
    const body = `window.A11YLENS_CONFIG = ${config};`;
    send(res, 200, "text/javascript; charset=utf-8", req.method === "HEAD" ? "" : body, {
      "Cache-Control": "no-store",
    });
    return;
  }

  const isReportRoute = /^\/r\/[A-Za-z0-9_-]{30,40}\/?$/.test(pathname);
  const requestedPath = pathname === "/" || isReportRoute ? "/index.html" : pathname;
  const absolutePath = path.resolve(WEB_ROOT, `.${requestedPath}`);
  if (!absolutePath.startsWith(`${WEB_ROOT}${path.sep}`)) {
    send(res, 404, "text/plain; charset=utf-8", "Not found.");
    return;
  }

  fs.readFile(absolutePath, (error, body) => {
    if (error) {
      send(res, 404, "text/plain; charset=utf-8", "Not found.");
      return;
    }
    send(
      res,
      200,
      TYPES[path.extname(absolutePath)] || "application/octet-stream",
      req.method === "HEAD" ? "" : body,
      { "Cache-Control": absolutePath.endsWith("index.html") ? "no-cache" : "public, max-age=300" },
    );
  });
});

server.listen(PORT, HOST, () => {
  process.stdout.write(`A11yLens Web listening on ${HOST}:${PORT}\n`);
});
