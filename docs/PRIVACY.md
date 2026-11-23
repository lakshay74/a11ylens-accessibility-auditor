# A11yLens privacy disclosure (draft)

This draft describes the current local-development build. Review it against the final code and hosting setup before using it as a Chrome Web Store privacy policy.

## What A11yLens processes

- When you start a scan, the extension runs axe-core in the active page. The scan stays in your browser.
- To restore results when the popup closes, the extension temporarily stores the scan in `chrome.storage.session`. The stored result contains the page title and URL, rule findings, affected-element selectors, and a limited sample of HTML and failure summaries. Browser session storage is not a server-side account or database.
- When you request an explanation for a finding, the extension sends that selected finding's rule ID, description, impact, a short HTML snippet, selector, and axe failure summary to the local API at `127.0.0.1:8000`.
- If you configure `GROQ_API_KEY`, the local API forwards the selected finding and retrieved WCAG references to Groq to generate an explanation. Groq's own privacy terms then apply. Without a key, the API returns local guidance and does not call Groq.
- If you choose **Export JSON**, the browser downloads a report containing the page title, a URL with credentials/query/fragment removed, scan counts, rule summaries, and affected-element counts. The report excludes page HTML, selectors, and failure summaries. It is generated locally and is not uploaded by A11yLens.

## A11yLens Web and optional report storage

- When someone submits a URL in A11yLens Web, the configured API loads that public page in headless Chromium and runs axe-core. The API processes the page response and returns the title, URL path, findings, affected-element HTML samples, selectors, and guidance.
- The API rejects URLs containing embedded credentials. Reports remove the query string and fragment from the displayed URL, but keep the path, which can still contain identifying information.
- If `MONGODB_URI` is configured, the API saves the full report, including its page title, URL path, score, findings, HTML samples, and explanations. With no MongoDB URI, reports are returned to the current visitor but are not saved and do not receive share links.
- A saved report is retrievable without an account at `/api/reports/{id}`. Anyone who has its unguessable share link can view the report. The current code has no automatic expiry or delete endpoint; reports remain in MongoDB until its operator deletes them.
- If `GROQ_API_KEY` is configured for Web scans, the API may send up to 12 violation findings to Groq for explanations. Each sent finding can include its rule, description, impact, target selector, a short HTML sample, axe failure summary, and retrieved WCAG references. The full page is not sent to Groq. Without a key, the API uses local guidance.

## What A11yLens does not do

- The extension does not send complete pages to an A11yLens-hosted service; this project has no hosted backend.
- The extension does not include user accounts, analytics, or advertising in the current implementation.
- It does not send scan data to Groq unless a user configures a Groq key and asks for an explanation.

## Local configuration and retention

The optional Groq key belongs in `backend/.env`, which is excluded from Git. The local FastAPI backend is configured to bind to `127.0.0.1`. Scan restoration data uses browser session storage; downloaded JSON reports are retained wherever the user chooses to save downloads. MongoDB retention applies only when report storage is configured and is controlled manually by the database operator in the current implementation.

The WCAG summary corpus is checked into the project and linked to W3C WAI sources. It is not fetched from W3C during an ordinary scan.

## Current extension permissions

The Manifest V3 extension requests `activeTab`, `scripting`, and `storage`. It uses the active-tab grant to inspect the current tab after the user starts a scan, injects its locally built axe-core and content scripts for that scan, and uses session storage to restore the result in the browser session. Its only host permission is `http://127.0.0.1:8000/*` for the local explanation API. This source review found no broad all-sites host permission. Confirm permissions again against any packaged release build.

## Before public release

The local-backend design, data flows, third-party provider behavior, retention details, and browser-store declarations must be reviewed for the exact release build. Before enabling MongoDB-backed share links for a public deployment, choose a retention period and deletion process and explain that anyone with a report link can view it. If A11yLens is changed to use a hosted API, update this disclosure and explain authentication, logging, retention, and provider processing before deployment.
