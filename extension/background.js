const UNSUPPORTED_PAGE_PREFIXES = [
  "chrome://",
  "chrome-extension://",
  "https://chrome.google.com/webstore",
  "https://chromewebstore.google.com/",
  "devtools://"
];

function isSupportedPage(url) {
  return typeof url === "string" &&
    !UNSUPPORTED_PAGE_PREFIXES.some((prefix) => url.startsWith(prefix));
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id || !isSupportedPage(tab.url)) {
    throw new Error("This browser page cannot be scanned. Open a regular website and try again.");
  }
  return tab;
}

async function ensureScannerIsInjected(tabId) {
  const [axeState] = await chrome.scripting.executeScript({
    target: { tabId },
    func: () => Boolean(globalThis.axe?.run)
  });

  if (!axeState?.result) {
    await chrome.scripting.executeScript({
      target: { tabId },
      files: ["vendor/axe.min.js"]
    });
  }

  await chrome.scripting.executeScript({
    target: { tabId },
    files: ["content.js"]
  });
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "A11YLENS_SCAN_ACTIVE_TAB") {
    return false;
  }

  (async () => {
    const tab = await getActiveTab();
    await ensureScannerIsInjected(tab.id);
    const scan = await chrome.tabs.sendMessage(tab.id, { type: "A11YLENS_RUN_SCAN" });

    if (!scan?.ok) {
      throw new Error(scan?.error || "The page scan did not complete.");
    }

    const savedScan = {
      ...scan,
      pageTitle: tab.title || "Current page",
      pageUrl: tab.url || "",
      scannedAt: new Date().toISOString()
    };

    await chrome.storage.session.set({ [`a11ylens-scan-${tab.id}`]: savedScan });
    sendResponse({ ok: true, tabId: tab.id, scan: savedScan });
  })().catch((error) => {
    sendResponse({ ok: false, error: error.message || "Could not scan this page." });
  });

  return true;
});
