import importlib.util
import json
import socket
import threading
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

CLIENT = Path(__file__).resolve().parents[1] / "phone_use/client.py"
spec = importlib.util.spec_from_file_location("phone_use_client", CLIENT)
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


class PhoneUseClientTest(unittest.TestCase):
    def exchange(self, response, payload=None):
        name = "astrbot-phone-use-test-" + uuid.uuid4().hex
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind("\0" + name)
        server.listen(1)
        seen = []

        def serve():
            with server:
                connection, _ = server.accept()
                with connection:
                    wire = bytearray()
                    while not wire.endswith(b"\n"):
                        wire.extend(connection.recv(4096))
                    seen.append(json.loads(wire))
                    # Split a response to exercise fragmented stream reads.
                    for offset in range(0, len(response), 7):
                        try:
                            connection.sendall(response[offset : offset + 7])
                        except BrokenPipeError:
                            break

        thread = threading.Thread(target=serve)
        thread.start()
        try:
            return client.request(payload or {"action": "status"}, name), seen
        finally:
            thread.join(timeout=3)
            self.assertFalse(thread.is_alive())

    def test_fragmented_unicode_response_and_targeted_action(self):
        result, seen = self.exchange(
            '{"ok":true,"protocolVersion":1,"name":"虚拟屏幕"}\n'.encode(),
            {
                "action": "tap",
                "sessionId": "session-fixture",
                "x": 10,
                "y": 20,
            },
        )
        self.assertEqual(result["name"], "虚拟屏幕")
        self.assertEqual(
            seen,
            [
                {
                    "action": "tap",
                    "sessionId": "session-fixture",
                    "x": 10,
                    "y": 20,
                    "protocolVersion": 1,
                }
            ],
        )

    def test_incomplete_response_is_not_retried(self):
        with self.assertRaisesRegex(ConnectionError, "do not replay"):
            self.exchange(b'{"ok":')

    def test_failure_is_returned_without_replay(self):
        result, seen = self.exchange(b'{"ok":false,"protocolVersion":1,"error":"stale_session"}\n')
        self.assertFalse(result["ok"])
        self.assertEqual(len(seen), 1)

    def test_request_limit_and_nonfinite_coordinates_fail_before_connect(self):
        with patch.object(client.socket, "socket") as connect:
            with self.assertRaisesRegex(ValueError, "request_too_large"):
                client.request({"action": "input_text", "text": "a" * client.MAX_REQUEST})
            with self.assertRaises(ValueError):
                client.request({"action": "tap", "x": float("nan")})
            connect.assert_not_called()

    def test_installation_socket_is_read_from_environment(self):
        with patch.dict(client.os.environ, {"ASTRBOT_PHONE_USE_SOCKET": "fixture.phoneuse.v1"}):
            with patch.object(client.socket, "socket") as factory:
                connection = factory.return_value.__enter__.return_value
                connection.recv.return_value = b'{"ok":true,"protocolVersion":1}\n'
                client.request({"action": "status"})
                connection.connect.assert_called_once_with("\0fixture.phoneuse.v1")

    def test_missing_or_incompatible_protocol_is_rejected_without_retry(self):
        for response in (b'{"ok":true}\n', b'{"ok":true,"protocolVersion":2}\n'):
            with self.assertRaisesRegex(ValueError, "unsupported_protocol_version"):
                self.exchange(response)

    def test_invalid_transport_and_payload_fail_before_connect(self):
        with patch.object(client.socket, "socket") as connect:
            for name in ("bad\0name", "x" * 101):
                with self.assertRaisesRegex(ValueError, "invalid_socket_name"):
                    client.request({"action": "status"}, name)
            with self.assertRaisesRegex(ValueError, "invalid_request"):
                client.request([])
            connect.assert_not_called()

    def test_response_schema_and_size_are_bounded(self):
        with self.assertRaisesRegex(ValueError, "invalid_response"):
            self.exchange(b'{"ok":"true"}\n')
        with patch.object(client, "MAX_RESPONSE", 32):
            with self.assertRaisesRegex(ValueError, "response_too_large"):
                self.exchange(b'{"ok":true,"data":"' + b"x" * 100 + b'"}\n')


if __name__ == "__main__":
    unittest.main()
