"""Small readiness check used by the Windows API launcher."""

from __future__ import annotations

import argparse
import json
import socket
from urllib.error import URLError
from urllib.request import urlopen


def api_port_status(
    host: str = "127.0.0.1", port: int = 8000, timeout: float = 3.0
) -> str:
    """Return ``running``, ``occupied``, or ``available`` for the local API port."""
    try:
        with urlopen(f"http://{host}:{port}/health", timeout=timeout) as response:
            payload = json.load(response)
        if (
            isinstance(payload, dict)
            and payload.get("status") == "ok"
            and payload.get("service") == "A11yLens API"
        ):
            return "running"
    except (OSError, URLError, TimeoutError, ValueError):
        pass

    try:
        with socket.create_connection((host, port), timeout=0.5):
            return "occupied"
    except OSError:
        return "available"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--timeout", type=float, default=3.0)
    args = parser.parse_args()
    print(api_port_status(args.host, args.port, args.timeout))


if __name__ == "__main__":
    main()
