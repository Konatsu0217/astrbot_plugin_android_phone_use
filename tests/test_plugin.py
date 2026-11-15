import importlib.util
import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ASSETS = Path(__file__).resolve().parents[1]


class PhoneUsePluginTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        shutil.copy(ASSETS / "main.py", root / "main.py")
        shutil.copytree(ASSETS / "phone_use", root / "phone_use")
        modules = {
            name: types.ModuleType(name)
            for name in (
                "mcp",
                "mcp.types",
                "astrbot",
                "astrbot.api",
                "astrbot.api.event",
                "astrbot.api.star",
            )
        }
        modules["mcp"].types = modules["mcp.types"]
        for name in ("CallToolResult", "TextContent", "ImageContent"):
            setattr(modules["mcp.types"], name, lambda **kwargs: types.SimpleNamespace(**kwargs))
        modules["astrbot.api.event"].AstrMessageEvent = object
        modules["astrbot.api.event"].filter = types.SimpleNamespace(
            llm_tool=lambda **kwargs: lambda fn: fn
        )
        modules["astrbot.api.star"].Context = object
        modules["astrbot.api.star"].Star = type(
            "Star", (), {"__init__": lambda self, context: None}
        )
        modules["astrbot.api.star"].register = lambda *args: lambda cls: cls
        spec = importlib.util.spec_from_file_location(
            "phone_use_plugin_fixture", root / "main.py", submodule_search_locations=[str(root)]
        )
        self.module = importlib.util.module_from_spec(spec)
        modules[spec.name] = self.module
        with patch.dict(sys.modules, modules):
            spec.loader.exec_module(self.module)
        android_environment = patch.dict("os.environ", {"ASTRBOT_CLIENT": "astrbot-android"})
        android_environment.start()
        self.addCleanup(android_environment.stop)
        self.plugin = self.module.AndroidPhoneUse(object())
        self.event = types.SimpleNamespace(is_admin=lambda: True)

    async def test_non_admin_never_reaches_bridge(self):
        self.event.is_admin = lambda: False
        with patch.object(self.module._client, "request") as call:
            result = await self.plugin.phone_use(self.event, "tap", {"x": 1, "y": 2})
        self.assertEqual(json.loads(result)["error"], "administrator_required")
        call.assert_not_called()

    async def test_action_and_installation_transport_are_bound(self):
        with patch.object(self.module._client, "request", return_value={"ok": True}) as call:
            await self.plugin.phone_use(self.event, "status", {"action": "launch_app"})
        call.assert_called_once_with({"action": "status"})

    async def test_screenshot_is_multimodal_tool_result(self):
        with patch.object(
            self.module._client, "request", return_value={"ok": True, "imageBase64": "aW1hZ2U="}
        ):
            result = await self.plugin.phone_use(self.event, "screenshot", {"sessionId": "fixture"})
        self.assertEqual(result.content[1].mimeType, "image/jpeg")
        self.assertEqual(result.content[1].data, "aW1hZ2U=")
        self.assertNotIn("imageBase64", result.content[0].text)

    async def test_non_android_environment_never_reaches_bridge(self):
        with patch.dict("os.environ", {"ASTRBOT_CLIENT": "other"}):
            with patch.object(self.module._client, "request") as call:
                result = await self.plugin.phone_use(self.event, "status", {})
        self.assertEqual(json.loads(result)["error"], "android_only")
        call.assert_not_called()

    async def test_invalid_arguments_do_not_reach_bridge(self):
        with patch.object(self.module._client, "request") as call:
            result = await self.plugin.phone_use(self.event, "tap", [])
        self.assertEqual(json.loads(result)["error"], "invalid_arguments")
        call.assert_not_called()

    async def test_timeout_returns_unknown_without_retry(self):
        with patch.object(self.module._client, "request", side_effect=TimeoutError()) as call:
            result = await self.plugin.phone_use(
                self.event, "tap", {"sessionId": "fixture", "x": 1, "y": 2}
            )
        self.assertFalse(json.loads(result)["retry"])
        self.assertEqual(call.call_count, 1)


if __name__ == "__main__":
    unittest.main()
