"use strict";

const API_BASE_URL = String(window.A11YLENS_CONFIG?.apiBaseUrl || "http://127.0.0.1:8000").replace(/\/+$/, "");
const SCAN_STAGES = [
  [0, "Checking the address and its destination…"],
  [4500, "Opening the page in a secure browser…"],
  [10500, "Running axe-core accessibility checks…"],
  [19000, "Writing plain-language guidance…"],
  [32000, "Finishing the report…"],
];
const IMPACTS = ["critical", "serious", "moderate", "minor"];

const form = document.querySelector("#scan-form");
const urlInput = document.querySelector("#page-url");
const scanButton = document.querySelector("#scan-button");
const errorMessage = document.querySelector("#error-message");
const loadingState = document.querySelector("#loading-state");
const loadingMessage = document.querySelector("#loading-message");
const resultsSection = document.querySelector("#results");
const violationsList = document.querySelector("#violations-list");
const noViolations = document.querySelector("#no-violations");

function make(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function safeHttpUrl(value) {
  try {
    const parsed = new URL(value);
    return ["http:", "https:"].includes(parsed.protocol) ? parsed : null;
  } catch {
    return null;
  }
}

function setError(message) {
  errorMessage.textContent = message;
  errorMessage.hidden = !message;
}

function setLoading(active) {
  loadingState.hidden = !active;
  scanButton.disabled = active;
  scanButton.textContent = active ? "Scanning…" : "Scan page →";
  form.setAttribute("aria-busy", String(active));
}

function errorForResponse(status, body) {
  const detail = typeof body?.detail === "string" ? body.detail : "";
  if (status === 422) return detail || "We can’t scan that address. Use a public HTTP or HTTPS page and try again.";
  if (status === 429) return "You’ve reached the scan limit for now. Please wait a minute, then try again.";
  if (status === 503) return detail || "The scanner is busy or not ready. Please try again shortly.";
  if (status === 504) return detail || "That page took too long to scan. Try a simpler page or retry in a moment.";
  return "The scan service couldn’t complete this request. Please try again.";
}

async function requestScan(url) {
  const response = await fetch(`${API_BASE_URL}/api/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(errorForResponse(response.status, body));
  return body;
}

function setReportLink(urlValue) {
  const link = document.querySelector("#report-url");
  const parsed = safeHttpUrl(urlValue);
  link.textContent = parsed ? `${parsed.hostname}${parsed.pathname}` : "Scanned page";
  if (parsed) {
    link.href = parsed.href;
    link.hidden = false;
  } else {
    link.removeAttribute("href");
    link.hidden = true;
  }
}

function renderImpactCounts(counts = {}) {
  const target = document.querySelector("#impact-counts");
  target.replaceChildren();
  for (const impact of IMPACTS) {
    const item = make("div", `impact-count ${impact}`);
    const count = make("strong", "", String(Number(counts[impact] || 0)));
    const label = make("span", "", impact[0].toUpperCase() + impact.slice(1));
    item.append(count, label);
    target.append(item);
  }
}

function addCodeBlock(parent, label, codeText, options = {}) {
  const block = make("div", "code-block");
  const header = make("div", "fix-header");
  header.append(make("span", "", label));
  if (options.copy) {
    const copy = make("button", "copy-fix", "Copy fix");
    copy.type = "button";
    copy.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(codeText);
        copy.textContent = "Copied";
        window.setTimeout(() => { copy.textContent = "Copy fix"; }, 1800);
      } catch {
        copy.textContent = "Couldn’t copy";
      }
    });
    header.append(copy);
  }
  const pre = make("pre");
  pre.textContent = codeText;
  block.append(header, pre);
  parent.append(block);
  return block;
}

function createViolationCard(violation) {
  const details = make("details", "violation-card");
  const summary = make("summary");
  const impact = String(violation.impact || "unknown").toLowerCase();
  const badge = make("span", `impact-badge ${impact}`, impact);
  const title = make("span", "violation-title", violation.description || violation.id || "Accessibility finding");
  const total = Math.max(0, Number(violation.totalNodes ?? violation.nodes?.length ?? 0));
  const count = make("span", "violation-count", `${total} affected ${total === 1 ? "element" : "elements"}`);
  summary.append(badge, title, count);
  details.append(summary);

  const body = make("div", "violation-body");
  const insight = violation.insight || {};
  const insightGrid = make("div", "insight-grid");
  for (const [heading, value, className] of [
    ["What’s happening", insight.explanation, ""],
    ["Who it affects", insight.who_it_affects, ""],
    ["Why it matters", insight.why_it_matters, "wide"],
    ["Suggested next step", insight.recommendation, "wide"],
  ]) {
    if (!value) continue;
    const block = make("section", `insight-block ${className}`.trim());
    block.append(make("h4", "", heading), make("p", "", value));
    insightGrid.append(block);
  }
  if (insightGrid.childElementCount) body.append(insightGrid);

  if (insight.fixed_html) addCodeBlock(body, "Suggested code", insight.fixed_html, { copy: true });

  const nodes = Array.isArray(violation.nodes) ? violation.nodes : [];
  if (nodes.length) {
    const examples = make("section", "node-examples");
    const fullCount = Math.max(total, nodes.length);
    examples.append(make("h4", "", `Offending HTML · showing ${nodes.length} of ${fullCount}`));
    for (const node of nodes.slice(0, 4)) {
      const item = make("div", "node-example");
      const targetText = Array.isArray(node.target) ? node.target.join(" → ") : String(node.target || "Affected element");
      item.append(make("code", "node-target", targetText));
      addCodeBlock(item, "Current markup", String(node.html || "HTML not supplied by axe-core"));
      if (node.failureSummary) {
        const summaryText = make("p", "field-hint", node.failureSummary);
        item.append(summaryText);
      }
      examples.append(item);
    }
    body.append(examples);
  } else if (violation.offending_html) {
    addCodeBlock(body, "Offending HTML", String(violation.offending_html));
  }

  const criteria = Array.isArray(insight.criteria) ? insight.criteria : [];
  if (criteria.length) {
    const list = make("div", "criteria-list");
    list.setAttribute("aria-label", "Related WCAG references");
    for (const criterion of criteria) {
      const link = safeHttpUrl(criterion.source_url || criterion.source || criterion.url || "");
      const label = `WCAG ${criterion.id}: ${criterion.title}`;
      const reference = make(link ? "a" : "span", "criteria-link", label);
      if (link) {
        reference.href = link.href;
        reference.target = "_blank";
        reference.rel = "noopener noreferrer";
      }
      list.append(reference);
    }
    body.append(list);
  }

  const help = safeHttpUrl(violation.helpUrl || "");
  if (help) {
    const helpLink = make("a", "axe-link", "Read the axe rule help ↗");
    helpLink.href = help.href;
    helpLink.target = "_blank";
    helpLink.rel = "noopener noreferrer";
    body.append(helpLink);
  }

  details.append(body);
  return details;
}

function renderReport(report, { isShared = false } = {}) {
  const score = Math.min(100, Math.max(0, Number(report.score?.score ?? 0)));
  const violations = Array.isArray(report.violations) ? report.violations : [];
  const totalRules = Number(report.score?.violation_rules ?? violations.length);
  const affectedElements = Number(report.score?.affected_elements ?? 0);

  document.querySelector("#report-heading").textContent = report.title ? `Report: ${report.title}` : "Your page report";
  setReportLink(report.url);
  document.querySelector("#score-value").textContent = String(score);
  document.querySelector("#score-ring").setAttribute("aria-label", `A11yLens score: ${score} out of 100`);
  document.querySelector("#score-note").textContent = report.score_note || "This is an A11yLens estimate, not an official WCAG rating.";
  document.querySelector("#score-method").textContent = `Based on ${totalRules} axe rule ${totalRules === 1 ? "finding" : "findings"} and ${affectedElements} affected ${affectedElements === 1 ? "element" : "elements"}.`;
  document.querySelector("#rule-total").textContent = `${totalRules} ${totalRules === 1 ? "rule" : "rules"}`;
  document.querySelector("#finding-count").textContent = `${violations.length} ${violations.length === 1 ? "finding" : "findings"}`;
  renderImpactCounts(report.score?.impact_counts || {});
  const ai = report.ai || {};
  const localCount = Number(ai.local_fallbacks || 0) + Number(ai.local_findings || 0);
  let aiMessage = violations.length === 0
    ? "No violations required an explanation."
    : "Only local WCAG reference guidance is available for this report; contextual Groq explanations are not configured.";
  if (Number(ai.groq_findings || 0) > 0) {
    aiMessage = `Groq explanations are included for ${ai.groq_findings} ${ai.groq_findings === 1 ? "rule" : "rules"}; local reference guidance is used for ${localCount} ${localCount === 1 ? "rule" : "rules"}.`;
  } else if (Number(ai.local_fallbacks || 0) > 0) {
    aiMessage = "Groq could not complete this explanation, so local WCAG reference guidance is shown.";
  }
  document.querySelector("#ai-note").textContent = aiMessage;

  const ringOffset = 289.03 * (1 - score / 100);
  requestAnimationFrame(() => {
    document.querySelector("#ring-progress").style.strokeDashoffset = String(ringOffset);
  });

  violationsList.replaceChildren(...violations.map(createViolationCard));
  noViolations.hidden = violations.length !== 0;

  const saveNotice = document.querySelector("#save-notice");
  const copyShare = document.querySelector("#copy-share");
  if (report.saved && report.share_path) {
    const shareUrl = new URL(report.share_path, window.location.origin).href;
    copyShare.hidden = false;
    copyShare.onclick = async () => {
      try {
        await navigator.clipboard.writeText(shareUrl);
        copyShare.textContent = "Link copied";
        window.setTimeout(() => { copyShare.textContent = "Copy report link"; }, 1800);
      } catch {
        copyShare.textContent = shareUrl;
      }
    };
    saveNotice.hidden = false;
    saveNotice.textContent = isShared ? "You’re viewing a saved report. Anyone with this link can view it." : "Report saved. Copy the link to share this page’s findings.";
    if (!isShared) history.replaceState({}, "", report.share_path);
  } else {
    copyShare.hidden = true;
    saveNotice.hidden = false;
    saveNotice.textContent = "Scan complete. This report could not be saved, so it does not have a share link.";
  }

  resultsSection.hidden = false;
  document.querySelector("#report-heading").focus({ preventScroll: true });
  if (!isShared) resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function loadSharedReport(reportId) {
  setLoading(true);
  loadingMessage.textContent = "Opening the saved report…";
  try {
    const response = await fetch(`${API_BASE_URL}/api/reports/${encodeURIComponent(reportId)}`);
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(response.status === 404 ? "This report link is invalid or no longer available." : errorForResponse(response.status, body));
    renderReport({ ...body, saved: true, share_path: `/r/${reportId}` }, { isShared: true });
  } catch (error) {
    setError(error.message || "This report could not be loaded.");
    document.querySelector("#report-heading").textContent = "Report unavailable";
    resultsSection.hidden = false;
  } finally {
    setLoading(false);
    if (resultsSection.hidden) document.querySelector(".scan-panel").scrollIntoView({ block: "start" });
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setError("");
  const parsed = safeHttpUrl(urlInput.value.trim());
  if (!parsed) {
    setError("Enter a complete public page address starting with http:// or https://.");
    urlInput.focus();
    return;
  }

  history.replaceState({}, "", "/");
  resultsSection.hidden = true;
  setLoading(true);
  let timer = 0;
  const startedAt = Date.now();
  const updateLoading = () => {
    const elapsed = Date.now() - startedAt;
    const stage = [...SCAN_STAGES].reverse().find(([at]) => elapsed >= at);
    if (stage) loadingMessage.textContent = stage[1];
  };
  updateLoading();
  timer = window.setInterval(updateLoading, 800);
  try {
    const report = await requestScan(parsed.href);
    renderReport(report);
  } catch (error) {
    setError(error.message || "The scan could not be completed. Please try again.");
  } finally {
    window.clearInterval(timer);
    setLoading(false);
  }
});

for (const button of document.querySelectorAll(".example-button")) {
  button.addEventListener("click", () => {
    urlInput.value = button.dataset.url || "";
    setError("");
    urlInput.focus();
  });
}

document.querySelector("#scan-another").addEventListener("click", () => {
  history.replaceState({}, "", "/");
  resultsSection.hidden = true;
  setError("");
  urlInput.focus();
  window.scrollTo({ top: 0, behavior: "smooth" });
});

const sharedId = window.location.pathname.match(/^\/r\/([A-Za-z0-9_-]{30,40})\/?$/)?.[1];
if (sharedId) loadSharedReport(sharedId);
