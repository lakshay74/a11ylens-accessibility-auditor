const API_URL = "http://127.0.0.1:8000";

const scanButton = document.getElementById("scan-button");
const scanStatus = document.getElementById("scan-status");
const errorMessage = document.getElementById("error-message");
const resultsPanel = document.getElementById("results-panel");
const findingList = document.getElementById("finding-list");
const summary = document.getElementById("summary");
const pageTitle = document.getElementById("page-title");
const previewNotice = document.getElementById("preview-notice");
const exportButton = document.getElementById("export-report");
let currentScan = null;
const IS_EXTENSION_CONTEXT = Boolean(
  globalThis.chrome?.runtime?.id &&
  typeof globalThis.chrome.runtime.sendMessage === "function" &&
  typeof globalThis.chrome.tabs?.query === "function"
);

function showError(message) {
  errorMessage.textContent = message;
  errorMessage.hidden = false;
}

function clearError() {
  errorMessage.textContent = "";
  errorMessage.hidden = true;
}

function sendRuntimeMessage(message) {
  return new Promise((resolve, reject) => {
    if (!IS_EXTENSION_CONTEXT) {
      reject(new Error("This is a preview file. Load the extension folder as an unpacked extension in Brave to scan pages."));
      return;
    }

    chrome.runtime.sendMessage(message, (response) => {
      const runtimeError = chrome.runtime.lastError;
      if (runtimeError) {
        reject(new Error(runtimeError.message));
        return;
      }
      resolve(response);
    });
  });
}

function sendTabMessage(tabId, message) {
  return new Promise((resolve, reject) => {
    if (!IS_EXTENSION_CONTEXT) {
      reject(new Error("Load A11yLens as an unpacked extension in Brave to inspect page elements."));
      return;
    }

    chrome.tabs.sendMessage(tabId, message, (response) => {
      const runtimeError = chrome.runtime.lastError;
      if (runtimeError) {
        reject(new Error(runtimeError.message));
        return;
      }
      resolve(response);
    });
  });
}

function createElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function selectorForNode(node) {
  if (!Array.isArray(node?.target)) return null;
  const target = Array.isArray(node.target[0]) ? node.target[0] : node.target;
  return target.length ? target : null;
}

function renderSummary(counts) {
  summary.replaceChildren();
  const cells = [
    [counts.violations, "rule violations"],
    [counts.affectedElements, "affected elements"],
    [counts.incomplete, "manual review"]
  ];

  for (const [value, label] of cells) {
    const cell = createElement("div", "summary-cell");
    cell.append(createElement("strong", "", String(value)));
    cell.append(createElement("span", "", label));
    summary.append(cell);
  }
}

function scanEntries(scan) {
  return [
    ...(scan.violations || []).map((finding) => ({ finding, category: "violation" })),
    ...(scan.incomplete || []).map((finding) => ({ finding, category: "manual-review" }))
  ];
}

function makeReport(scan) {
  let pageUrl = "";
  try {
    const parsedUrl = new URL(scan.pageUrl);
    parsedUrl.username = "";
    parsedUrl.password = "";
    parsedUrl.search = "";
    parsedUrl.hash = "";
    pageUrl = parsedUrl.href;
  } catch {
    // Keep the report useful when a browser does not provide a standard page URL.
  }

  return {
    format: "a11ylens-report-v1",
    scannedAt: scan.scannedAt || null,
    page: {
      title: scan.pageTitle || "Current page",
      url: pageUrl
    },
    summary: { ...(scan.counts || {}) },
    findings: scanEntries(scan).map(({ finding, category }) => ({
      category,
      ruleId: finding.id,
      impact: finding.impact || "unknown",
      description: finding.description || "",
      affectedElementCount: Number(finding.totalNodes) || 0,
      helpUrl: finding.helpUrl || ""
    }))
  };
}

function exportReport() {
  if (!currentScan) return;

  const report = makeReport(currentScan);
  const blob = new Blob([`${JSON.stringify(report, null, 2)}\n`], {
    type: "application/json"
  });
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const hostname = (() => {
    try {
      return new URL(report.page.url).hostname.replace(/[^a-z0-9.-]/gi, "-") || "page";
    } catch {
      return "page";
    }
  })();
  const scanDate = (report.scannedAt || new Date().toISOString()).slice(0, 10);

  link.href = objectUrl;
  link.download = `a11ylens-${hostname}-${scanDate}.json`;
  link.hidden = true;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
  scanStatus.textContent = "JSON report downloaded. It excludes page HTML and URL query parameters.";
}

function appendExplanation(container, data) {
  const section = createElement("section", "explanation");
  section.setAttribute("aria-live", "polite");
  section.append(createElement("p", "mode-note", data.mode === "groq"
    ? "AI-assisted explanation with retrieved WCAG guidance. Review the suggested fix before using it."
    : "Local guidance from the WCAG 2.2 reference corpus. Add a Groq key for AI explanations and code suggestions."));

  section.append(createElement("h4", "", "What the issue means"));
  section.append(createElement("p", "", data.explanation || "No explanation was returned."));

  if (data.why_it_matters) {
    section.append(createElement("h4", "", "Why it matters"));
    section.append(createElement("p", "", data.why_it_matters));
  }

  if (data.recommendation) {
    section.append(createElement("h4", "", "Suggested next step"));
    section.append(createElement("p", "", data.recommendation));
  }

  if (data.fixed_html) {
    section.append(createElement("h4", "", "Suggested HTML"));
    section.append(createElement("pre", "", data.fixed_html));
  }

  if (Array.isArray(data.criteria) && data.criteria.length) {
    section.append(createElement("h4", "", "Retrieved WCAG criteria"));
    for (const criterion of data.criteria) {
      const link = createElement("a", "", `${criterion.id} ${criterion.title} (${criterion.level})`);
      link.href = criterion.source_url;
      link.target = "_blank";
      link.rel = "noreferrer";
      const item = createElement("p", "");
      item.append(link);
      if (criterion.summary) item.append(document.createTextNode(` — ${criterion.summary}`));
      section.append(item);
    }
  }

  container.append(section);
}

function createFindingCard(finding, category, tabId, index) {
  const card = createElement("article", "finding-card");
  const titleRow = createElement("div", "finding-title-row");
  titleRow.append(createElement("h3", "finding-title", finding.description || finding.id));
  titleRow.append(createElement("span", `impact impact-${finding.impact || "unknown"}`, finding.impact || "unknown"));
  card.append(titleRow);

  const noun = category === "manual-review" ? "Needs manual review" : "Rule";
  card.append(createElement("p", "rule-meta", `${noun}: ${finding.id} · ${finding.totalNodes} affected element${finding.totalNodes === 1 ? "" : "s"}`));

  const elementActions = createElement("div", "element-actions");
  const sampleNodes = finding.nodes.slice(0, 3);
  sampleNodes.forEach((node, nodeIndex) => {
    const target = selectorForNode(node);
    if (!target) return;

    const inspect = createElement("button", "element-action", `Inspect element ${nodeIndex + 1}`);
    inspect.type = "button";
    inspect.addEventListener("click", async () => {
      try {
        const response = await sendTabMessage(tabId, { type: "A11YLENS_HIGHLIGHT", target });
        if (!response?.ok) showError(response?.error || "Could not find that element on the page.");
        else clearError();
      } catch {
        showError("The page changed after the scan. Run the scan again.");
      }
    });
    elementActions.append(inspect);
  });

  if (elementActions.childElementCount) card.append(elementActions);

  if (sampleNodes[0]?.html) {
    const snippet = createElement("details", "snippet");
    const summaryLine = createElement("summary", "element-action", "View sample HTML");
    snippet.append(summaryLine, createElement("pre", "", sampleNodes[0].html));
    card.append(snippet);
  }

  if (category === "violation") {
    const explain = createElement("button", "secondary-button", "Get WCAG guidance");
    explain.type = "button";
    const explanationContainer = createElement("div", "");
    explain.addEventListener("click", async () => {
      if (!sampleNodes[0]) {
        showError("No affected HTML was available for this finding.");
        return;
      }

      explain.disabled = true;
      explain.textContent = "Preparing explanation…";
      clearError();
      try {
        const response = await fetch(`${API_URL}/explain`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            id: finding.id,
            description: finding.description || "",
            impact: finding.impact || "unknown",
            html: sampleNodes[0].html || "",
            failure_summary: sampleNodes[0].failureSummary || "",
            target: selectorForNode(sampleNodes[0])?.join(" >>> ") || ""
          })
        });

        if (!response.ok) {
          throw new Error(response.status === 503
            ? "The explanation service is temporarily unavailable."
            : "The backend could not explain this finding. Check that it is running.");
        }

        const data = await response.json();
        explanationContainer.replaceChildren();
        appendExplanation(explanationContainer, data);
        if (!explanationContainer.isConnected) card.append(explanationContainer);
      } catch (error) {
        showError(error.name === "TypeError"
          ? "Could not reach the local backend. Start FastAPI on 127.0.0.1:8000, then try again."
          : error.message);
      } finally {
        explain.disabled = false;
        explain.textContent = "Get WCAG guidance";
      }
    });
    card.append(explain, explanationContainer);
  }

  card.dataset.findingIndex = String(index);
  return card;
}

function renderScan(scan, tabId) {
  currentScan = scan;
  exportButton.disabled = false;
  clearError();
  pageTitle.textContent = scan.pageTitle || "Current page";
  resultsPanel.hidden = false;
  renderSummary(scan.counts || { violations: 0, incomplete: 0, affectedElements: 0 });
  findingList.replaceChildren();

  const entries = scanEntries(scan);

  if (!entries.length) {
    findingList.append(createElement("p", "muted", "No automated findings came back for these rules. Manual checks are still important."));
    return;
  }

  entries.forEach(({ finding, category }, index) => {
    findingList.append(createFindingCard(finding, category, tabId, index));
  });
}

async function loadBackendStatus() {
  const status = document.getElementById("backend-status");
  try {
    const response = await fetch(`${API_URL}/health`, { method: "GET" });
    if (!response.ok) throw new Error("API unavailable");
    const data = await response.json();
    status.textContent = data.groq_configured ? "AI explanations ready" : "Local explanations ready";
    status.classList.add("online");
  } catch {
    status.textContent = "Scanner ready · API offline";
    status.classList.add("offline");
  }
}

async function restorePreviousScan() {
  if (!IS_EXTENSION_CONTEXT) return;

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return;

  const key = `a11ylens-scan-${tab.id}`;
  const saved = await chrome.storage.session.get(key);
  if (saved[key]?.pageUrl === tab.url) renderScan(saved[key], tab.id);
}

scanButton.addEventListener("click", async () => {
  scanButton.disabled = true;
  scanButton.textContent = "Scanning page…";
  scanStatus.textContent = "Running local accessibility checks.";
  clearError();

  try {
    const response = await sendRuntimeMessage({ type: "A11YLENS_SCAN_ACTIVE_TAB" });
    if (!response?.ok) throw new Error(response?.error || "The scan did not complete.");

    renderScan({ ...response.scan, pageTitle: response.scan.pageTitle || "Current page" }, response.tabId);
    scanStatus.textContent = `Scanned just now${response.scan.counts?.violations ? ". Select a finding to inspect or explain it." : "."}`;
  } catch (error) {
    showError(error.message || "Could not scan this page.");
    scanStatus.textContent = "Try a regular website tab and scan again.";
  } finally {
    scanButton.disabled = false;
    scanButton.textContent = "Scan this page";
  }
});

document.getElementById("clear-highlight").addEventListener("click", async () => {
  if (!IS_EXTENSION_CONTEXT) return;

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab?.id) {
    try {
      await sendTabMessage(tab.id, { type: "A11YLENS_CLEAR_HIGHLIGHT" });
    } catch {
      // The page may have navigated since the scan.
    }
  }
});

exportButton.addEventListener("click", exportReport);

loadBackendStatus();
restorePreviousScan().catch(() => {});

if (!IS_EXTENSION_CONTEXT) {
  previewNotice.textContent = "You're viewing the popup as a local file. To scan a page, open brave://extensions, choose Load unpacked, and select this project's extension folder.";
  previewNotice.hidden = false;
  scanButton.disabled = true;
  scanButton.textContent = "Load extension in Brave";
  scanStatus.textContent = "Scanning is available after Brave loads the extension.";
}
