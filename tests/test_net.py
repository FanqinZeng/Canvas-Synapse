import io
import socket
import unittest
from urllib.error import HTTPError
from unittest.mock import Mock, patch

from synapse.net import NoRedirect, open_request, read_limited, validate_url


def address(ip):
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    return (family, socket.SOCK_STREAM, 6, "", (ip, 443))


class NetworkBoundaryTests(unittest.TestCase):
    def test_image_requests_cannot_reach_local_or_reserved_networks(self):
        for target in ("127.0.0.1", "10.0.0.1", "169.254.169.254", "192.168.1.1", "::1", "fc00::1", "0.0.0.0"):
            with self.subTest(target=target), patch("synapse.net.socket.getaddrinfo", return_value=[address(target)]):
                with self.assertRaisesRegex(ValueError, "局域网|保留"):
                    validate_url("https://image.example/slide.png")
        # A mixed A/AAAA answer cannot hide a private destination amongst public ones.
        with patch("synapse.net.socket.getaddrinfo", return_value=[address("1.1.1.1"), address("::1")]):
            with self.assertRaises(ValueError):
                validate_url("https://image.example/slide.png")

    def test_only_explicit_local_model_requests_may_use_http(self):
        with self.assertRaises(ValueError):
            validate_url("http://localhost:11434/v1")
        self.assertEqual(validate_url("http://localhost:11434/v1", local=True), "http://localhost:11434/v1")
        with self.assertRaises(ValueError):
            validate_url("http://models.example/v1", local=True)
        with self.assertRaises(ValueError):
            validate_url("https://user:secret@models.example/v1")

    def test_redirect_never_forwards_model_authorization(self):
        self.assertIsNone(NoRedirect().redirect_request(
            Mock(), None, 307, "Temporary redirect", {}, "https://elsewhere.example/v1"))
        failure = HTTPError("https://models.example/v1", 307, "redirect", {"Location": "https://elsewhere.example/v1"}, io.BytesIO())
        opener = Mock()
        opener.open.side_effect = failure
        with patch("synapse.net.validate_url"), patch("synapse.net.build_opener", return_value=opener):
            with self.assertRaises(ValueError):
                open_request("https://models.example/v1", headers={"Authorization": "Bearer test-secret"})
        self.assertEqual(opener.open.call_count, 1)

    def test_provider_error_bodies_and_urls_are_not_reflected(self):
        failure = HTTPError("https://models.example/private?token=do-not-show", 401,
                            "Bearer do-not-show", {}, io.BytesIO(b'{"error":"do-not-show"}'))
        opener = Mock()
        opener.open.side_effect = failure
        with patch("synapse.net.validate_url"), patch("synapse.net.build_opener", return_value=opener):
            with self.assertRaises(ValueError) as caught:
                open_request("https://models.example/v1", headers={"Authorization": "Bearer do-not-show"})
        self.assertNotIn("do-not-show", str(caught.exception))
        self.assertNotIn("models.example", str(caught.exception))
        self.assertIn("401", str(caught.exception))

    def test_asset_read_rejects_oversized_payload(self):
        self.assertEqual(read_limited(io.BytesIO(b"1234"), 4), b"1234")
        with self.assertRaisesRegex(ValueError, "上限"):
            read_limited(io.BytesIO(b"12345"), 4)


if __name__ == "__main__":
    unittest.main()
