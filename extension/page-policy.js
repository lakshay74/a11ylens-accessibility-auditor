"use strict";

const WEB_PROTOCOLS = new Set(["http:", "https:"]);

function isSupportedPage(url) {
  if (typeof url !== "string" || !url) return false;

  try {
    const page = new URL(url);
    if (!WEB_PROTOCOLS.has(page.protocol)) return false;

    const hostname = page.hostname.toLowerCase().replace(/\.$/, "");
    const path = page.pathname.toLowerCase();
    if (hostname === "chromewebstore.google.com") return false;
    if (hostname === "chrome.google.com" && (path === "/webstore" || path.startsWith("/webstore/"))) {
      return false;
    }
    return true;
  } catch {
    return false;
  }
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { isSupportedPage };
} else {
  globalThis.A11yLensPagePolicy = { isSupportedPage };
}
