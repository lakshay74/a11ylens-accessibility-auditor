"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { createScanCompletionMessage } = require("../scan-status.js");

test("announces singular result counts", () => {
  assert.equal(
    createScanCompletionMessage({ violations: 1, affectedElements: 1, incomplete: 1 }),
    "Scan complete: 1 violation rule, 1 affected element, and 1 manual-review rule."
  );
});

test("announces plural counts and treats invalid counts as zero", () => {
  assert.equal(
    createScanCompletionMessage({ violations: 2, affectedElements: 4, incomplete: "unknown" }),
    "Scan complete: 2 violation rules, 4 affected elements, and 0 manual-review rules."
  );
});
