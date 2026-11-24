"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { guidanceErrorMessage, showGuidanceError } = require("../guidance-errors.js");

test("explains when the local guidance backend cannot be reached", () => {
  assert.match(guidanceErrorMessage(new TypeError("Failed to fetch")), /run start-api\.cmd/);
  assert.match(guidanceErrorMessage(new TypeError("Failed to fetch")), /127\.0\.0\.1:8000/);
});

test("renders backend failures inline as an announced alert", () => {
  let rendered;
  const container = { replaceChildren: (element) => { rendered = element; } };
  const documentRef = {
    createElement: (tag) => ({
      tag,
      attributes: {},
      setAttribute(name, value) { this.attributes[name] = value; }
    })
  };

  showGuidanceError(container, new Error("The explanation service is temporarily unavailable."), documentRef);

  assert.equal(rendered.tag, "p");
  assert.equal(rendered.className, "error-message");
  assert.equal(rendered.textContent, "The explanation service is temporarily unavailable.");
  assert.equal(rendered.attributes.role, "alert");
});
