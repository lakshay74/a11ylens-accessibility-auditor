"use strict";

function createScanCompletionMessage(counts = {}) {
  const count = (value) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? Math.max(0, Math.floor(parsed)) : 0;
  };
  const pluralize = (value, singular) => `${value} ${singular}${value === 1 ? "" : "s"}`;
  const violations = count(counts.violations);
  const affectedElements = count(counts.affectedElements);
  const manualReviewRules = count(counts.incomplete);

  return `Scan complete: ${pluralize(violations, "violation rule")}, ` +
    `${pluralize(affectedElements, "affected element")}, and ` +
    `${pluralize(manualReviewRules, "manual-review rule")}.`;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { createScanCompletionMessage };
} else {
  globalThis.A11yLens = globalThis.A11yLens || {};
  globalThis.A11yLens.createScanCompletionMessage = createScanCompletionMessage;
}
