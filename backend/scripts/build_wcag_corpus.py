"""Build the local WCAG 2.2 A/AA corpus from W3C WAI Understanding pages.

The corpus intentionally stores only each criterion's title, conformance level,
short "In Brief" guidance, and source URL. W3C marks Understanding documents as
informative; consult the linked standard when making conformance decisions.
"""

from __future__ import annotations

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


BASE_URL = "https://www.w3.org/WAI/WCAG22/Understanding/"
INDEX_URL = BASE_URL
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "wcag.json"
USER_AGENT = "A11yLens-WCAG-corpus-builder/0.1 (local educational project)"


def fetch(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


class UnderstandingIndexParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str, str]] = []
        self.href = ""
        self.anchor_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self.href = dict(attrs).get("href") or ""
            self.anchor_text = []

    def handle_data(self, data: str) -> None:
        if self.href:
            self.anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self.href:
            return
        href = urljoin(INDEX_URL, self.href)
        path = urlparse(href).path
        text = clean(" ".join(self.anchor_text))
        match = re.match(r"^(\d+\.\d+\.\d+)\s+(.+)$", text)
        base_path = urlparse(BASE_URL).path
        if path.startswith(base_path) and path != base_path and match:
            source_url = href if path.endswith(".html") else f"{href}.html"
            self.links.append((match.group(1), match.group(2), source_url))
        self.href = ""
        self.anchor_text = []


class UnderstandingPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.h1_text: list[str] = []
        self.in_h1 = False
        self.in_brief = False
        self.h2_text: list[str] = []
        self.in_h2 = False
        self.capture: str | None = None
        self.capture_text: list[str] = []
        self.last_label = ""
        self.brief: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "h1":
            self.in_h1 = True
        elif tag == "h2":
            if self.in_brief:
                self.in_brief = False
            self.in_h2 = True
            self.h2_text = []
        elif self.in_brief and tag in {"dt", "dd"}:
            self.capture = tag
            self.capture_text = []

    def handle_data(self, data: str) -> None:
        if self.in_h1:
            self.h1_text.append(data)
        if self.in_h2:
            self.h2_text.append(data)
        if self.capture:
            self.capture_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1":
            self.in_h1 = False
        elif tag == "h2":
            heading = clean(" ".join(self.h2_text)).lower()
            if heading == "in brief":
                self.in_brief = True
            self.in_h2 = False
            self.h2_text = []
        elif tag == "dt" and self.capture == "dt":
            self.last_label = clean(" ".join(self.capture_text)).lower()
            self.capture = None
            self.capture_text = []
        elif tag == "dd" and self.capture == "dd":
            if self.last_label:
                self.brief[self.last_label] = clean(" ".join(self.capture_text))
            self.capture = None
            self.capture_text = []


def parse_criterion(item: tuple[str, str, str]) -> dict[str, str] | None:
    criterion_id, title, source_url = item
    for attempt in range(3):
        try:
            parser = UnderstandingPageParser()
            parser.feed(fetch(source_url))
            heading = clean(" ".join(parser.h1_text))
            level_match = re.search(r"\(Level\s+(A{1,3})\)", heading, re.IGNORECASE)
            if not level_match:
                return None  # Excludes obsolete criteria and non-criterion pages.
            level = level_match.group(1).upper()
            if level not in {"A", "AA"}:
                return None

            what_to_do = parser.brief.get("what to do", "")
            why_it_matters = parser.brief.get("why it's important", "")
            if not why_it_matters:
                why_it_matters = parser.brief.get("why it’s important", "")
            if not what_to_do:
                what_to_do = parser.brief.get("goal", "")
            summary = clean(" ".join(part for part in (what_to_do, why_it_matters) if part))
            if not summary:
                raise ValueError(f"No In Brief summary found for {criterion_id}")

            return {
                "id": criterion_id,
                "title": title,
                "level": level,
                "summary": summary,
                "source_url": source_url,
                "source_type": "W3C WAI Understanding guidance (informative)",
            }
        except (HTTPError, URLError, TimeoutError, ValueError) as error:
            if attempt == 2:
                print(f"Skipping {criterion_id}: {error}", file=sys.stderr)
                return None
            time.sleep(0.5 * (attempt + 1))
    return None


def main() -> None:
    index_parser = UnderstandingIndexParser()
    index_parser.feed(fetch(INDEX_URL))
    unique = {criterion_id: (criterion_id, title, url) for criterion_id, title, url in index_parser.links}
    candidates = list(unique.values())
    print(f"Found {len(candidates)} W3C criterion pages; collecting A/AA summaries…")

    records: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        jobs = [executor.submit(parse_criterion, item) for item in candidates]
        for job in as_completed(jobs):
            record = job.result()
            if record:
                records.append(record)

    records.sort(key=lambda item: tuple(int(part) for part in item["id"].split(".")))
    if not records:
        raise RuntimeError("No WCAG A/AA records were collected; the existing corpus was left untouched.")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = OUTPUT_PATH.with_suffix(".json.tmp")
    temporary_path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary_path.replace(OUTPUT_PATH)
    print(f"Wrote {len(records)} WCAG 2.2 A/AA criteria to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
