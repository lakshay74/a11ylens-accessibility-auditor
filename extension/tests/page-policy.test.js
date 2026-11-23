"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { isSupportedPage } = require("../page-policy.js");

test("allows regular HTTP and HTTPS pages", () => {
  assert.equal(isSupportedPage("https://example.com/path"), true);
  assert.equal(isSupportedPage("http://localhost:8000/"), true);
});

test("rejects browser pages, store pages, malformed URLs, and non-web schemes", () => {
  for (const url of [
    "chrome://extensions/",
    "chrome-extension://abcdefghijklmnop/popup.html",
    "devtools://devtools/bundled/inspector.html",
    "https://chrome.google.com/webstore",
    "https://chrome.google.com/webstore/category/extensions",
    "https://chrome.google.com./webstore/category/extensions",
    "https://chromewebstore.google.com/detail/example",
    "https://chromewebstore.google.com./detail/example",
    "file:///C:/example.html",
    "not a URL"
  ]) {
    assert.equal(isSupportedPage(url), false, url);
  }
});

test("does not block a regular page whose path merely starts with webstore", () => {
  assert.equal(isSupportedPage("https://chrome.google.com/webstore-news/"), true);
});
