#!/usr/bin/env python3
"""Same-UID Android phone-control client; no ADB server or TCP listener required."""

from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import sys
from pathlib import Path

MAX_REQUEST = 32 * 1024
MAX_RESPONSE = 12 * 1024 * 1024


def request(payload: dict, socket_name: str | None = None) -> dict:
    name = socket_name or os.environ.get(
        "ASTRBOT_PHONE_USE_SOCKET", "com.astrbot.proot.phoneuse.v1"
    )
    if not isinstance(payload, dict):
        raise ValueError("invalid_request")
    if not isinstance(name, str) or not name or "\0" in name or len(name.encode("utf-8")) > 100:
        raise ValueError("invalid_socket_name")
    payload = dict(payload)
    payload["protocolVersion"] = 1
    wire = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"
    if len(wire) > MAX_REQUEST:
        raise ValueError("request_too_large")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(12)
        connection.connect("\0" + name)
        connection.sendall(wire)
        response = bytearray()
        while True:
            chunk = connection.recv(64 * 1024)
            if not chunk:
                raise ConnectionError(
                    "incomplete_response; action outcome may be unknown, do not replay"
                )
            response.extend(chunk)
            if len(response) > MAX_RESPONSE:
                raise ValueError("response_too_large")
            if b"\n" in chunk:
                break
    result = json.loads(response.split(b"\n", 1)[0])
    if not isinstance(result, dict) or not isinstance(result.get("ok"), bool):
        raise ValueError("invalid_response")
    if result.get("protocolVersion") != 1:
        raise ValueError("unsupported_protocol_version")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "request_json", help='JSON action; obtain sessionId from {"action":"status"}'
    )
    parser.add_argument("--out", type=Path, help="Save screenshot bytes to this path")
    args = parser.parse_args()
    try:
        result = request(json.loads(args.request_json))
        if args.out and result.get("ok") and "imageBase64" in result:
            image = base64.b64decode(result.pop("imageBase64"), validate=True)
            # Exclusive creation avoids replacing an unrelated file or following a symlink.
            with args.out.open("xb") as target:
                target.write(image)
            result["imagePath"] = str(args.out)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["ok"] else 1
    except (OSError, ValueError, ConnectionError) as error:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": type(error).__name__,
                    "outcome": "unknown; never automatically retry",
                }
            )
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
