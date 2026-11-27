"""Run the local fixture pages with the same bundled axe options as the extension."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.scanner import _system_chromium_executable  # noqa: E402


AXE_PATH = ROOT / "backend" / "axe.min.js"
FIXTURES = (
    ROOT / "evaluation" / "demo-pages" / "accessible-baseline.html",
    ROOT / "evaluation" / "demo-pages" / "intentional-issues.html",
)
WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]


async def scan_fixtures() -> dict[str, Any]:
    """Scan the checked-in pages without making network requests or using the API."""
    if not AXE_PATH.is_file():
        raise FileNotFoundError(f"Bundled axe-core file is missing: {AXE_PATH}")

    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        launch_options: dict[str, Any] = {"headless": True}
        system_browser = _system_chromium_executable()
        if system_browser is not None:
            launch_options["executable_path"] = str(system_browser)

        browser = await playwright.chromium.launch(**launch_options)
        context = await browser.new_context()

        async def block_remote_requests(route: Any) -> None:
            if route.request.url.startswith(("http://", "https://")):
                await route.abort()
            else:
                await route.continue_()

        await context.route("**/*", block_remote_requests)
        outcomes: dict[str, Any] = {}

        try:
            for fixture in FIXTURES:
                page = await context.new_page()
                html = fixture.read_text(encoding="utf-8")
                try:
                    await page.set_content(html, wait_until="load")
                    await page.add_script_tag(path=str(AXE_PATH))
                    result = await page.evaluate(
                        """async (tags) => {
                          const result = await axe.run(document, {
                            runOnly: { type: "tag", values: tags },
                            resultTypes: ["violations", "incomplete"]
                          });
                          const summarize = (rules) => rules.map((rule) => ({
                            id: rule.id,
                            impact: rule.impact || "unknown",
                            nodes: rule.nodes.length
                          }));
                          return {
                            axeVersion: axe.version,
                            violations: summarize(result.violations),
                            manualReview: summarize(result.incomplete)
                          };
                        }""",
                        WCAG_TAGS,
                    )
                    outcomes[fixture.name] = result
                finally:
                    await page.close()

            return {
                "browserVersion": browser.version,
                "axeVersion": next(iter(outcomes.values()))["axeVersion"],
                "scanProfile": {
                    "tags": WCAG_TAGS,
                    "resultTypes": ["violations", "incomplete"],
                    "api": "not used",
                    "networkRequests": "blocked",
                },
                "fixtures": outcomes,
            }
        finally:
            await context.close()
            await browser.close()


def main() -> None:
    print(json.dumps(asyncio.run(scan_fixtures()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
