"""Focused tests for the local API launcher's port readiness check."""

from __future__ import annotations

import io
import socket
import unittest
from unittest.mock import patch
from urllib.error import URLError

from backend.startup import api_port_status


class StartupStatusTests(unittest.TestCase):
    def test_recognizes_a_healthy_a11ylens_api(self) -> None:
        response = io.BytesIO(b'{"status":"ok","service":"A11yLens API"}')
        with patch("backend.startup.urlopen", return_value=response) as request:
            with patch("backend.startup.socket.create_connection") as connect:
                self.assertEqual(api_port_status(), "running")
        request.assert_called_once()
        connect.assert_not_called()

    def test_distinguishes_another_listener_from_a_free_port(self) -> None:
        with patch("backend.startup.urlopen", side_effect=URLError("not the API")):
            with patch("backend.startup.socket.create_connection") as connect:
                connect.return_value.__enter__.return_value = None
                self.assertEqual(api_port_status(), "occupied")

        with patch("backend.startup.urlopen", side_effect=URLError("not the API")):
            with patch("backend.startup.socket.create_connection", side_effect=OSError("refused")):
                self.assertEqual(api_port_status(), "available")

    def test_does_not_accept_a_different_health_service(self) -> None:
        response = io.BytesIO(b'{"status":"ok","service":"Other API"}')
        with patch("backend.startup.urlopen", return_value=response):
            with patch("backend.startup.socket.create_connection") as connect:
                connect.return_value.__enter__.return_value = None
                self.assertEqual(api_port_status(), "occupied")

    def test_detects_a_real_listener_on_an_ephemeral_port(self) -> None:
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            port = listener.getsockname()[1]
            self.assertEqual(api_port_status(port=port, timeout=0.1), "occupied")


if __name__ == "__main__":
    unittest.main()
