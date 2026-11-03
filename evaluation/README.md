# A11yLens local evaluation pages

These pages are small, synthetic fixtures for exercising A11yLens. They contain no user data and make no network requests. The baseline is intended to be low-noise; it is not a claim of WCAG conformance. The second page intentionally contains defects.

## Open the pages in Brave

From the repository root, start a local static server:

```powershell
backend/.venv/Scripts/python.exe -m http.server 8001 --directory evaluation --bind 127.0.0.1
```

Open these URLs in Brave:

- `http://127.0.0.1:8001/demo-pages/accessible-baseline.html`
- `http://127.0.0.1:8001/demo-pages/intentional-issues.html`

Load the repository's `extension/` folder as an unpacked extension if needed. On each page, open A11yLens and choose **Scan this page**. The API is not required for scanning. Start FastAPI separately on port 8000 only if you also want to try **Get WCAG guidance**.

## Intended checks

The second page was authored to exercise these axe rules:

| Visible condition in the fixture | Candidate axe rule |
| --- | --- |
| Light gray text on white | `color-contrast` |
| Icon-only link without a name | `link-name` |
| Icon-only button without a name | `button-name` |
| Email input without a label | `label` |
| Image without an `alt` attribute | `image-alt` |
| Invalid `aria-checked` value | `aria-valid-attr-value` |
| List role without required list item child role | `aria-required-children` |
| 16 by 16 pixel button | `target-size` |
| Visible label differs from its accessible name | `label-content-name-mismatch` |

These are candidate expectations based on the authored markup and axe rule purpose. They have **not yet been confirmed by a browser scan**. Record actual rule IDs, category (violation or manual review), and affected node counts in [the results template](RESULTS_TEMPLATE.md). Do not turn a missing candidate finding into a product claim until the test setup and rule behavior have been checked.

## Repeatable procedure

1. Record the date, Brave version, extension commit, and axe-core version.
2. Scan the accessible baseline once and record every violation and manual-review rule. Do not assume it must return zero findings.
3. Scan the intentional-issues page and record each rule ID and its category separately. A manual-review result is not a confirmed violation.
4. Compare the observed IDs with the candidate list above. Review unexpected results instead of silently removing them.
5. To measure a repair, change one issue at a time, rescan the same page, and record whether the intended result disappeared and whether another result appeared.
6. Keep the pages and results local. Use a clean browser profile for any screenshots.

The candidate list is a fixture checklist, not independent ground truth. Axe WCAG tags help map a rule to criteria, but they do not prove that a specific page-level result is correct. A human should verify the authored defect and review false positives or missed findings before summarizing the evaluation.
