"""Tools for the Android launcher's explicitly enabled phone-control session."""

import asyncio
import json

import mcp.types
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

from .phone_use import client as _client


@register("astrbot_plugin_android_phone_use", "Konatsu0217", "Android phone-control tools", "0.1.1")
class AndroidPhoneUse(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.llm_tool(name="android_phone_use")
    async def phone_use(self, event: AstrMessageEvent, action: str, arguments: dict):
        """Operate the Android launcher's user-enabled phone-control session. First use status to get
        sessionId. All launchable installed apps are available without a manual app selection.
        Then use launch_app(packageName), screenshot, tap(x,y), swipe(x1,y1,x2,y2,durationMs),
        input_text(text), press_key(keyCode), or stop_session. Put sessionId in every action except
        status/start_session. Coordinates use full screenshot pixels. Check status.backend before acting.
        Accessibility supports only Back=4; shell also
        supports Enter=66, Delete=67, Tab=61, arrows=19..22. Do not replay a failed or timed-out action.
        Never assume Unicode or lock-screen operation is supported. A conflict notice is advisory.

        Args:
            action(string): Action name, for example status or screenshot.
            arguments(object): Action parameters including sessionId when required.
        """
        # Match the upstream administrator role before allowing a remote chat to control the device.
        if not event.is_admin():
            return json.dumps({"ok": False, "error": "administrator_required"})
        try:
            if not isinstance(arguments, dict) or not isinstance(action, str):
                return json.dumps({"ok": False, "error": "invalid_arguments"})
            payload = dict(arguments)
            payload["action"] = action
            result = await asyncio.to_thread(_client.request, payload)
            image = result.pop("imageBase64", None)
            if image is not None:
                return mcp.types.CallToolResult(
                    content=[
                        mcp.types.TextContent(type="text", text=json.dumps(result)),
                        mcp.types.ImageContent(type="image", data=image, mimeType="image/jpeg"),
                    ]
                )
            return json.dumps(result, ensure_ascii=False)
        except (OSError, ValueError, ConnectionError):
            return json.dumps(
                {"ok": False, "error": "bridge_unavailable_or_outcome_unknown", "retry": False}
            )
