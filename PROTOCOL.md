# Android phone-use protocol v1

## Transport and ownership

One UTF-8 JSON object followed by LF per connection; the server returns one JSON object followed by LF. Linux abstract AF_UNIX socket, with name from `ASTRBOT_PHONE_USE_SOCKET`; default `com.astrbot.proot.phoneuse.v1`. Android accepts only peers with its application UID. There is no TCP listener, ADB dependency, shared authentication token, or network fallback.

The user opens a session in the Android UI. Plugin installation and `status` never enable device access. A fresh session has an unpredictable `sessionId`; mutations and screenshot must include it. Closing the UI switch closes the transport and backend. `stop_session` returns its response before requesting host shutdown. App code under the same UID is inside the same trust boundary; this is not isolation from malicious container code.

Request limit: 32 KiB including LF. Response limit: 12 MiB including LF. Screenshot limit: 8 MiB of image bytes. Client timeout: 12 seconds; server socket timeout: 10 seconds. No automatic retry, including on partial reads or timeout: a mutation may already have happened.

## Envelope

Every new client sends `protocolVersion: 1`; every response includes `protocolVersion: 1` and boolean `ok`. Unsupported explicit versions return `unsupported_protocol_version` before dispatch. Android accepts an omitted version for older clients, but this plugin requires a versioned server.

```json
{"protocolVersion":1,"action":"status"}
```

Successful status includes `running`, `sessionId`, `backend` (`shell` or `accessibility`), `displayId`, `width`, `height`, and `paused` while a session is active. Shell adds capture freshness and app-conflict fields when available. No shared screen state or backend capabilities should be inferred across sessions.

## Actions

| Action | Arguments besides protocolVersion/action | Notes |
| --- | --- | --- |
| status | none | Read session and backend before acting. |
| start_session | none | Only available while the user-enabled Android host is alive; does not grant permissions. Normally unnecessary. |
| launch_app | sessionId, packageName | All launchable installed apps; no target app selection. |
| screenshot | sessionId | JPEG `imageBase64`, width, height, sessionId; the plugin converts to MCP image content. |
| tap | sessionId, x, y | Full screenshot coordinates, bounded by Android. |
| swipe | sessionId, x1, y1, x2, y2, durationMs | Gestures target the selected backend. |
| input_text | sessionId, text | Accessibility uses focused input; shell has limited character support. |
| press_key | sessionId, keyCode | Accessibility: Back=4 only. Shell: 4, 66, 67, 61, 19–22. |
| stop_session | sessionId | End the user-enabled session and host. |

Errors use `ok: false` and `error`. Stale session IDs must not be replaced by fetching a new one and blindly replaying the operation. Freshness or occupancy warnings require inspecting current state. No shell-command execution endpoint is exposed.

Android owns this wire interface; changes requiring different semantics need a new protocol version and compatibility tests. This document is kept with the client implementation; Android's implementation notes record the matching contract.
