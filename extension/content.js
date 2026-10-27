(() => {
  if (globalThis.__a11yLensContentReady) {
    return;
  }

  globalThis.__a11yLensContentReady = true;
  const originalStyles = new WeakMap();
  let highlightedElement = null;

  function selectorPathFor(target) {
    if (Array.isArray(target)) {
      const first = target[0];
      return Array.isArray(first) ? first : target;
    }
    return typeof target === "string" ? [target] : [];
  }

  function findTarget(target) {
    const selectors = selectorPathFor(target);
    let root = document;
    let element = null;

    for (let index = 0; index < selectors.length; index += 1) {
      try {
        element = root.querySelector(selectors[index]);
      } catch {
        return null;
      }

      if (!element) {
        return null;
      }

      if (index < selectors.length - 1) {
        root = element.shadowRoot;
        if (!root) {
          return null;
        }
      }
    }

    return element;
  }

  function restoreHighlight() {
    if (!highlightedElement) {
      return;
    }

    const saved = originalStyles.get(highlightedElement);
    if (saved) {
      if (saved.outline) {
        highlightedElement.style.setProperty("outline", saved.outline, saved.outlinePriority);
      } else {
        highlightedElement.style.removeProperty("outline");
      }

      if (saved.outlineOffset) {
        highlightedElement.style.setProperty("outline-offset", saved.outlineOffset, saved.offsetPriority);
      } else {
        highlightedElement.style.removeProperty("outline-offset");
      }
    }

    highlightedElement = null;
  }

  function highlight(target) {
    restoreHighlight();
    const element = findTarget(target);

    if (!element) {
      return { ok: false, error: "That element is no longer on the page." };
    }

    originalStyles.set(element, {
      outline: element.style.getPropertyValue("outline"),
      outlinePriority: element.style.getPropertyPriority("outline"),
      outlineOffset: element.style.getPropertyValue("outline-offset"),
      offsetPriority: element.style.getPropertyPriority("outline-offset")
    });
    element.style.setProperty("outline", "3px solid #c6283d", "important");
    element.style.setProperty("outline-offset", "3px", "important");
    element.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
    highlightedElement = element;
    return { ok: true };
  }

  function serializeRule(rule, category) {
    return {
      id: rule.id,
      impact: rule.impact || "unknown",
      description: rule.help,
      helpUrl: rule.helpUrl,
      category,
      nodes: rule.nodes.slice(0, 25).map((node) => ({
        target: node.target,
        html: String(node.html || "").slice(0, 2000),
        failureSummary: String(node.failureSummary || "").slice(0, 1200)
      })),
      totalNodes: rule.nodes.length
    };
  }

  async function runScan() {
    if (!globalThis.axe?.run) {
      throw new Error("The local axe-core scanner did not load. Reload the page and try again.");
    }

    const results = await globalThis.axe.run(document, {
      runOnly: {
        type: "tag",
        values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]
      },
      resultTypes: ["violations", "incomplete"]
    });

    return {
      ok: true,
      violations: results.violations.map((rule) => serializeRule(rule, "violation")),
      incomplete: results.incomplete.map((rule) => serializeRule(rule, "manual-review")),
      counts: {
        violations: results.violations.length,
        incomplete: results.incomplete.length,
        affectedElements: results.violations.reduce((total, rule) => total + rule.nodes.length, 0)
      }
    };
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type === "A11YLENS_RUN_SCAN") {
      runScan()
        .then(sendResponse)
        .catch((error) => sendResponse({ ok: false, error: error.message || "Scan failed." }));
      return true;
    }

    if (message?.type === "A11YLENS_HIGHLIGHT") {
      sendResponse(highlight(message.target));
      return false;
    }

    if (message?.type === "A11YLENS_CLEAR_HIGHLIGHT") {
      restoreHighlight();
      sendResponse({ ok: true });
      return false;
    }

    return false;
  });
})();
