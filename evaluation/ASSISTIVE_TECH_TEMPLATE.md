# A11yLens manual keyboard and screen-reader review

Use this checklist with the unpacked extension in Brave and the local pages in [the evaluation guide](README.md). It records observations; it is not a conformance verdict. Do not enter private page content in the record.

## Run details

- Date and time:
- Brave version:
- A11yLens commit:
- Screen reader and version (or “keyboard only”):
- Display scaling / browser zoom:
- Fixture page:
- API state (offline / local / Groq):

## Keyboard-only checks

Start with the extension popup open and use only the keyboard after that point.

| Check | Result (pass / issue / blocked) | What happened |
| --- | --- | --- |
| Tab and Shift+Tab move through controls in a sensible order. |  |  |
| The focused control has a visible focus indicator and is not clipped. |  |  |
| Enter or Space starts a scan when the Scan button is focused. |  |  |
| Scan progress and completion are understandable without relying on color. |  |  |
| After results appear, keyboard navigation can reach summary, findings, and actions. |  |  |
| Finding actions, axe help links, and expandable sample HTML can be operated by keyboard. |  |  |
| Long results can be scrolled to the end without losing the popup controls. |  |  |
| Errors are visible, understandable, and do not trap keyboard focus. |  |  |

## Screen-reader checks

Use the screen reader's normal browse and focus modes. Record its name and version above. Test both fixtures, and test with the API offline and locally available if time allows.

| Check | Result (pass / issue / blocked) | What the screen reader announced |
| --- | --- | --- |
| The popup name, main heading, sections, and controls have useful names. |  |  |
| Scan progress and completion changes are announced at a useful time. |  |  |
| The error message is announced when a scan or guidance request fails. |  |  |
| The result summary and finding headings can be found in a logical reading order. |  |  |
| Violation and manual-review status can be distinguished from text alone. |  |  |
| Manual-review guidance is clearly described as guidance about a possible issue. |  |  |
| Guidance content added after activation can be reached and its change is announced. |  |  |
| The popup can be dismissed and returned to without losing the user's place in the tab. |  |  |

## Notes and follow-up

- Issues to reproduce:
- Improvements to consider:
- Retest result after any change:
- Limitations (browser, screen reader, fixture, or setup):

Keep observed behavior separate from expectations. A pass on these fixtures does not establish that the extension works with every browser, screen reader, page, or assistive technology.
