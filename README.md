# Android 手机操控

AstrBot 插件，连接 **AstrBot Android Launcher** 内置的手机操控服务，为对话 Agent 提供打开应用、截图、点击、滑动、文字输入和返回等工具。

## 使用

本插件由 Konatsu0217 维护。AstrBot Android Launcher 随 APK 内置固定版本并自动部署，用户无需单独安装；源码在本仓库独立维护。

1. 使用内置版本时，更新 Android 启动器并启动 AstrBot 即可。开发或独立安装时，可将本工程放入 AstrBot 的 `data/plugins/astrbot_plugin_android_phone_use`，再重载插件或重启 AstrBot。
2. 在同一手机的 Android 启动器进入「工作台 → 手机操控」，配置独立模式（Shizuku）或无障碍模式，并启用总开关。
3. 由 AstrBot 管理员发起操控请求；聊天模型需要支持工具调用与图像输入。

安装插件不代表授权手机操控。Android 服务、授权界面和会话总开关由启动器内置，本仓库不安装 Android 组件、不获取权限，也不会自动开启会话。

要求 AstrBot 4.29.4 至 4.x、支持协议 v1 的 Android 启动器，并在该启动器的同 UID 容器中运行。普通电脑、远程服务器上的 AstrBot 无法直接连接手机。启动器通过 `ASTRBOT_PHONE_USE_SOCKET` 自动传入本安装的通道名，不需要用户配置；变量缺省值仅适配正式包名。

## 架构

- `main.py`：AstrBot 插件入口、工具说明、管理员校验、多模态结果。
- `phone_use/client.py`：有大小限制和超时的本地 Unix Socket 客户端，无设备逻辑。
- `tests/`：真实 Unix Socket 分帧/错误边界测试及插件权限、多模态返回测试。
- Android 工程：内置设备后端、同 UID 校验、会话及系统权限管理；仅在启动 AstrBot 前自动部署固定版本；保留已有手动安装或修改过的插件。

独立安装版本通过 AstrBot 插件管理维护；内置版本随 APK 固定，部署时不覆盖手动安装和修改，也不修改插件启停配置。接口详见 [PROTOCOL.md](PROTOCOL.md)。开发规范参考 [AstrBot 官方插件指南](https://docs.astrbot.app/dev/star/plugin-new.html)。

## 限制与隐私

内置工具仅允许 AstrBot 管理员调用，但同 Android UID 下的其他容器代码共享系统权限边界。通道不监听 TCP、不使用固定认证密钥。仅在信任容器代码和管理员的情况下启用。

截图及操作结果会返回 Agent，可能发送给所配置的模型服务。截图不写入插件目录；对话上下文或模型服务可能保留内容。同一应用可能共享任务和数据；独立模式并不保证应用多实例。无障碍模式占用主屏，锁屏/熄屏暂停，仅支持返回键，截图要求 Android 11+。shell 模式文本输入不保证 Unicode；锁屏持续渲染未全面验证。不能绕过应用及系统的安全限制。

失败、超时或取消后的动作结果可能未知，**不得自动重放操作**。关闭启动器总开关会结束会话并关闭通道；系统权限应在系统设置中撤销。

## 开发

```sh
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
```

单元测试不连接手机、不需要凭据，并以轻量替身验证 AstrBot 入口。真实 AstrBot 加载与模型截图链路需另外验收。

## 许可

AGPL-3.0-only，见 [LICENSE](LICENSE)。本工程从 AstrBot Android Launcher 开发中的 Python 操控工具拆出，与 Android 工程共同遵循协议 v1；AstrBot 插件 API 及开发规范来自上游 AstrBot。
