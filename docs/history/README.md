# 历史版本记录

本目录保留早期功能与 UI 演进记录，不作为当前实现规范。文中的路径均相对于仓库根目录；部分旧资源与旧类已删除，仅可通过 Git 历史查阅。

当前入口：[项目说明](../../README.md)、[视觉还原与验收](../../UI_VISUAL_RESTORE.md)、[架构拆分记录](../../UI_REFACTOR_CHANGELOG.md)。

- [v0.6 架构](V0_6_ARCHITECTURE.md)
- [v0.7 字幕体验](V0_7_SUBTITLE_UX.md)
- [v0.8 界面与语言](V0_8_UI_AND_LANGUAGES.md)
- [v0.9 变更](V0_9_CHANGELOG.md)
- [v0.9 桌面交互](V0_9_DESKTOP_UX.md)
- [早期像素组件清单](PIXEL_UI_COMPONENTS.md)
- [v0.9.1 UI 重建](V0_9_1_UI_REBUILD.md)
- [v0.9.1 视觉重建](V0_9_1_VISUAL_REBUILD.md)
- [v0.9.2 旧展示板布局](V0_9_2_PIXEL_LAYOUT.md)：固定展示画布已废弃，当前程序使用主窗口与独立浮窗。

清理记录：移除未使用的 `pixel_v092` / `ui_v2` 资源、旧素材生成脚本、两份旧布局 JSON、旧参考图、兼容窗口入口，以及未调用的 `StatusStrip` / `PixelIconLabel`。同步清理打包与启动预检引用。最新十页和两个浮窗的 125% 截图保存在 `docs/screenshots/`；测试输出 `logs/` 已加入忽略规则。
