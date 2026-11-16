"""Headless Chromium scanner with request, redirect, time, and size guards."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx

try:  # Support both ``backend.scanner`` and the existing ``main:app`` launch.
    from .scan_logic import validate_public_url
except ImportError:
    from scan_logic import validate_public_url


MAX_NAVIGATION_SECONDS = 18
MAX_REDIRECTS = 5
MAX_REQUESTS = 80
MAX_DOCUMENT_BYTES = 5 * 1024 * 1024
MAX_RESOURCE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 12 * 1024 * 1024
MAX_NODES_PER_RULE = 25
BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}
AXE_PATH = Path(__file__).with_name("axe.min.js")


def _system_chromium_executable() -> Path | None:
    """Find a system Chromium browser on Windows when Playwright's browser is absent."""

    configured = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
    if configured:
        executable = Path(configured).expanduser()
        if not executable.is_file():
            raise ScanError(
                "PLAYWRIGHT_CHROMIUM_EXECUTABLE does not point to an existing file."
            )
        return executable

    if os.name != "nt":
        return None

    candidates = [
        Path(os.environ.get("PROGRAMFILES", ""))
        / "BraveSoftware/Brave-Browser/Application/brave.exe",
        Path(os.environ.get("PROGRAMFILES", ""))
        / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", ""))
        / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "BraveSoftware/Brave-Browser/Application/brave.exe",
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Google/Chrome/Application/chrome.exe",
    ]
    return next((path for path in candidates if path.is_file()), None)


class ScanError(Exception):
    """A scan failed before it could produce axe results."""


class ScanBlockedError(ScanError):
    """Navigation was blocked by URL or response-size policy."""


class ScanTimedOutError(ScanError):
    """The browser did not finish within the scan budget."""


def validate_redirect_target(current_url: str, location: str) -> str:
    """Resolve and validate one redirect before allowing the browser to follow it."""

    next_url = urljoin(current_url, location)
    checked_next = validate_public_url(next_url)
    if urlsplit(current_url).scheme == "https" and urlsplit(checked_next).scheme == "http":
        raise ScanBlockedError(
            "This page downgrades from HTTPS to HTTP during a redirect. "
            "Enter its final HTTPS address and try again."
        )
    return checked_next


async def _validate_request_url(url: str) -> str:
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(validate_public_url, url), timeout=3.0
        )
    except asyncio.TimeoutError as error:
        raise ValueError("The URL host took too long to validate.") from error


def _redirect_hops(request: Any) -> int:
    """Count the redirects Playwright followed to reach this request."""

    count = 0
    previous = request.redirected_from
    while previous is not None and count <= MAX_REDIRECTS:
        count += 1
        previous = previous.redirected_from
    return count


async def scan_with_playwright(initial_url: str) -> dict[str, Any]:
    """Load one public page, inject local axe-core, and return capped findings."""

    if not AXE_PATH.is_file():
        raise ScanError("The bundled axe-core scanner is missing from the backend.")

    try:
        from playwright.async_api import Error as PlaywrightError
        from playwright.async_api import async_playwright
    except ImportError as error:
        raise ScanError("Playwright is not installed on this API host.") from error

    safe_url = await _validate_request_url(initial_url)
    request_count = 0
    downloaded_bytes = 0
    request_lock = asyncio.Lock()
    blocked_navigation: str | None = None
    final_url = safe_url

    try:
        async with async_playwright() as playwright:
            launch_options: dict[str, Any] = {
                "headless": True,
                "timeout": 10_000,
                "args": ["--disable-dev-shm-usage"],
            }
            managed_browser = Path(playwright.chromium.executable_path)
            configured_browser = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
            if configured_browser or not managed_browser.is_file():
                system_browser = _system_chromium_executable()
                if system_browser is not None:
                    launch_options["executable_path"] = str(system_browser)
                elif not managed_browser.is_file():
                    raise ScanError(
                        "Chromium is not installed on this API host. Run "
                        "`python -m playwright install chromium` or configure "
                        "PLAYWRIGHT_CHROMIUM_EXECUTABLE."
                    )

            browser = await playwright.chromium.launch(**launch_options)
            outbound = httpx.AsyncClient(
                timeout=httpx.Timeout(7.0),
                follow_redirects=False,
                trust_env=False,
            )
            try:
                context = await browser.new_context(
                    service_workers="block",
                    bypass_csp=True,
                )
                page = await context.new_page()
                page.set_default_timeout(8_000)
                page.set_default_navigation_timeout(MAX_NAVIGATION_SECONDS * 1000)

                async def route_request(route: Any) -> None:
                    nonlocal request_count, downloaded_bytes, blocked_navigation, final_url
                    request = route.request
                    try:
                        is_main_navigation = (
                            request.is_navigation_request() and request.frame == page.main_frame
                        )
                    except PlaywrightError:
                        is_main_navigation = False

                    try:
                        checked_url = await _validate_request_url(request.url)
                        if request.method not in {"GET", "HEAD"}:
                            raise ScanBlockedError(
                                "Only page read requests are allowed during a scan."
                            )

                        async with request_lock:
                            request_count += 1
                            if request_count > MAX_REQUESTS:
                                raise ScanBlockedError("The page requested too many resources.")
                            if request.resource_type in BLOCKED_RESOURCE_TYPES:
                                await route.abort("blockedbyclient")
                                return

                        headers_to_forward = {
                            key: value
                            for key, value in request.headers.items()
                            if key.lower() in {"accept", "accept-language", "referer"}
                        }
                        headers_to_forward["user-agent"] = "A11yLens accessibility scanner/0.1"
                        headers_to_forward["accept-encoding"] = "identity"
                        response = await outbound.send(
                            outbound.build_request(
                                request.method,
                                checked_url,
                                headers=headers_to_forward,
                            ),
                            stream=True,
                        )
                        status_code = response.status_code
                        response_headers = response.headers
                        location = response_headers.get("location")

                        # Hand the redirect back to Chromium only after checking its target.
                        # Chromium then requests the real final URL, preserving the page base URL.
                        if status_code in {301, 302, 303, 307, 308} and location:
                            await response.aclose()
                            if _redirect_hops(request) >= MAX_REDIRECTS:
                                raise ScanBlockedError("The page redirected too many times.")
                            checked_next = await asyncio.wait_for(
                                asyncio.to_thread(
                                    validate_redirect_target, checked_url, location
                                ),
                                timeout=3.5,
                            )
                            await route.fulfill(
                                status=status_code,
                                headers={
                                    "location": checked_next,
                                    "cache-control": "no-store",
                                },
                                body=b"",
                            )
                            return

                        per_response_limit = (
                            MAX_DOCUMENT_BYTES
                            if request.resource_type == "document"
                            else MAX_RESOURCE_BYTES
                        )
                        try:
                            declared_length = int(response_headers.get("content-length", "0"))
                        except ValueError:
                            declared_length = 0
                        if declared_length > per_response_limit:
                            await response.aclose()
                            raise ScanBlockedError(
                                "The page response exceeds the scan size limit."
                            )

                        body_parts: list[bytes] = []
                        body_size = 0
                        try:
                            async for chunk in response.aiter_bytes(chunk_size=16 * 1024):
                                body_size += len(chunk)
                                if body_size > per_response_limit:
                                    raise ScanBlockedError(
                                        "The page response exceeds the scan size limit."
                                    )
                                async with request_lock:
                                    if downloaded_bytes + len(chunk) > MAX_TOTAL_BYTES:
                                        raise ScanBlockedError(
                                            "The page exceeds the total scan size limit."
                                        )
                                    downloaded_bytes += len(chunk)
                                body_parts.append(chunk)
                        finally:
                            await response.aclose()

                        if is_main_navigation:
                            final_url = checked_url
                        safe_headers = {
                            key: value
                            for key, value in response_headers.items()
                            if key.lower()
                            not in {"content-length", "content-encoding", "transfer-encoding"}
                        }
                        await route.fulfill(
                            status=status_code,
                            headers=safe_headers,
                            body=b"".join(body_parts),
                        )
                    except ValueError as error:
                        if is_main_navigation:
                            blocked_navigation = str(error)
                        await route.abort("blockedbyclient")
                    except ScanBlockedError as error:
                        if is_main_navigation:
                            blocked_navigation = str(error)
                        await route.abort("blockedbyclient")
                    except asyncio.TimeoutError:
                        if is_main_navigation:
                            blocked_navigation = "The redirect host took too long to validate."
                        await route.abort("timedout")
                    except httpx.TimeoutException:
                        if is_main_navigation:
                            blocked_navigation = "The page host took too long to respond."
                        await route.abort("timedout")
                    except httpx.HTTPError:
                        await route.abort("failed")
                    except PlaywrightError:
                        await route.abort("failed")

                await context.route("**/*", route_request)
                try:
                    await asyncio.wait_for(
                        page.goto(safe_url, wait_until="domcontentloaded"),
                        timeout=MAX_NAVIGATION_SECONDS + 2,
                    )
                except (PlaywrightError, asyncio.TimeoutError) as error:
                    if blocked_navigation:
                        raise ScanBlockedError(blocked_navigation) from error
                    if isinstance(error, asyncio.TimeoutError):
                        raise ScanTimedOutError("The page took too long to load.") from error
                    raise ScanError("The page could not be loaded for scanning.") from error
                if blocked_navigation:
                    raise ScanBlockedError(blocked_navigation)

                try:
                    await page.add_script_tag(path=str(AXE_PATH))
                    axe_result = await asyncio.wait_for(
                        page.evaluate(
                            """async () => {
                              const results = await axe.run(document, {
                                runOnly: {
                                  type: 'tag',
                                  values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']
                                },
                                resultTypes: ['violations']
                              });
                              return {
                                title: String(document.title || '').slice(0, 300),
                                violations: results.violations.map((rule) => ({
                                  id: rule.id,
                                  impact: rule.impact || 'unknown',
                                  description: rule.help || '',
                                  helpUrl: rule.helpUrl || '',
                                  nodes: rule.nodes.slice(0, 25).map((node) => ({
                                    target: node.target,
                                    html: String(node.html || '').slice(0, 2000),
                                    failureSummary: String(node.failureSummary || '').slice(0, 1200)
                                  })),
                                  totalNodes: rule.nodes.length
                                }))
                              };
                            }"""
                        ),
                        timeout=14,
                    )
                except asyncio.TimeoutError as error:
                    raise ScanTimedOutError(
                        "The accessibility checks took too long."
                    ) from error
                except PlaywrightError as error:
                    raise ScanError("axe-core could not analyze this page.") from error

                return {
                    "url": final_url,
                    "title": axe_result["title"],
                    "violations": axe_result["violations"],
                    "scan_limits": {
                        "requests_checked": request_count,
                        "response_bytes": downloaded_bytes,
                        "nodes_returned_per_rule": MAX_NODES_PER_RULE,
                    },
                }
            finally:
                await outbound.aclose()
                await browser.close()
    except ScanError:
        raise
    except Exception as error:
        raise ScanError(
            "The browser scanner could not start. Check its Chromium install."
        ) from error
