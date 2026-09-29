# UI 架构重构 · 第一阶段 · 2026-09-29

> 本文件保留阶段历史。后续视觉还原见 [UI_VISUAL_RESTORE.md](UI_VISUAL_RESTORE.md)。文中旧 `ui_v2`、`pixel_v092`、素材生成脚本、兼容入口和旧截图已在清理时移除，不代表当前依赖。

本轮按附件最后的阶段要求交付：架构清理、Pixel Design System、MainWindow Shell、Screen Translation Page，并实际启动验证。其余页面的完整视觉迁移属于后续阶段。

## 审计结论

- 入口为 `main.py → screen_translator.app.run → MainWindow`；Windows 运行脚本先安装依赖、执行 `scripts/preflight.py`，再运行入口。
- 旧主窗口继承旧版 MainWindow，其父构造函数通过虚方法调用新 `_build_ui()`；实际不是两次 UI 构建，但初始化、业务适配、旧页面和新画布高度耦合。
- 根因是固定的 1536×1024 DesignCanvas：主窗口、右边三个展示卡、底部数据/快捷键/托盘/控件展示均用绝对坐标排列。
- `window_frame_full` / `titlebar_full` 包含品牌文字；`lang_dropdown` 包含语言内容；部分按钮、导航素材含占位图形。叠加 Qt 文字会重复。
- 独立 TranslationOverlay、MiniToolbar、WordPopup 和真正的 QSystemTrayIcon 原本已经存在，展示板又复制了一套外观。
- OCR、ASR、Provider、缓存、历史与存储在 `core/` 和 `providers/`。本次不更改这些模块或模型下载策略。

## 本轮实现

- 删除固定画布、右侧预览、底部展示区和未使用的旧屏幕页构建代码；删除整图拉伸控件模块 `pixel_v092.py`。
- 主窗口只构建一次：标题栏、侧栏、中央 QStackedWidget。导航只切页，不重建外壳或浮窗。
- 默认 1280×800、最小 1100×700 logical pixels；布局管理器和中央 ScrollArea 负责伸缩，屏幕页内容最大宽度 1240 并居中，避免大屏下横向无限拉长；自定义标题栏支持拖动/双击最大化，右下角提供 resize grip。
- `TranslatorWindowLogicMixin` 保留原有管线接口；`DesktopActionsMixin` 保留托盘、快捷键、任务取消、浮窗和队列适配；主窗口约 100 行。
- 增加集中 token、文本无关的九宫格素材和通用 Frame/Card/Button/IconButton/ComboBox/SceneButton/TitleBar/Sidebar。
- 字体使用 Microsoft YaHei UI / PingFang SC / Noto Sans CJK SC；正文独立渲染，像素图禁用平滑缩放。
- 屏幕页显示语言、来源、场景、主操作和状态；OCR 参数和单次框选位于可展开的高级设置。最近原文/译文位于可展开区域，保留点词查询、复制、朗读。
- 主按钮执行实时翻译，暂停按钮停止当前实时任务；单次翻译和原有快捷键仍可用。绑定按钮切换到窗口来源并打开窗口列表。
- 修复 UI 适配层原有语言交换无效问题、清空字幕未清除滚动历史问题，以及设置恢复期间覆盖桌面偏好的问题。
- 独立浮窗启动时隐藏，按交互显示；关闭应用同时关闭词汇弹窗。
- PyInstaller spec 包含新 `resources/ui_v2`；启动预检改为检查单一构建入口及新资源，删除对展示板代码的强制依赖。

## 实际验证

Python 3.12.10、PySide6 6.11.2，Windows Qt 原生后端。

- 全部现有 `scripts/self_test.py` 检查通过：文本合并、稳定检测、上下文、模糊缓存、VAD。
- 修复 self-test 在 Windows 删除临时数据库时的清理时序：临时目录退出前回收已释放的 SQLite 连接；数据库实现未修改。
- `scripts/preflight.py` 通过：Python 语法、单构建入口、资源存在、QSS 求值、运行时导入、spec 新资源声明。
- 新 `scripts/ui_smoke_test.py` 使用临时数据目录，禁用全局快捷键注册，保留真实窗口/组件/适配器/数据库。不启动模型下载、OCR 或麦克风采集。
- Windows 原生 DPR 1.0、1.25、1.5，每档覆盖 1100×700、1280×800、1440×900、1920×1080。确认实际 DPR 后测试；使用 Qt 环境变量控制 DPR，未修改 Windows 显示设置。
- 检查单页可见、外壳身份不变、浮窗独立且初始隐藏、屏幕页无横向溢出、主按钮与语言内容宽度；实际导出并查看主窗口截图。
- 交互覆盖：语言交换、场景切换、区域选择/ESC 取消、迷你条跨页存活、注入翻译结果进入历史、词汇收藏、清空字幕、展开高级设置、原生下拉菜单。
- 新建第二个 MainWindow 验证页面、语言、托盘关闭选项、自动迷你条、来源绑定状态恢复。
- `git diff --check` 通过。

运行命令（仓库根目录）：

```powershell
.venv\Scripts\python.exe scripts/preflight.py
.venv\Scripts\python.exe scripts/self_test.py
.venv\Scripts\python.exe scripts/ui_smoke_test.py
.venv\Scripts\python.exe scripts/ui_smoke_test.py --native --scale 1 --output logs/ui-refactor/native
.venv\Scripts\python.exe scripts/ui_smoke_test.py --native --scale 1.25 --output logs/ui-refactor/native
.venv\Scripts\python.exe scripts/ui_smoke_test.py --native --scale 1.5 --output logs/ui-refactor/native
```

截图位于 `logs/ui-refactor/native/main-{宽}x{高}-{DPR}.png`。

## 修改文件清单

只列本轮修改，不把接手前已有的其它脏工作区内容算作本轮成果。

- 替换：`screen_translator/ui/main_window.py`。
- 修改：`screen_translator/ui/legacy_main_window.py`（仅兼容导出）、`screen_translator/ui/pixel_theme.py`、`screen_translator/app.py`、`ScreenTranslator.spec`、`scripts/preflight.py`、`scripts/self_test.py`、`README.md`。
- 删除：`screen_translator/ui/pixel_v092.py`。
- 新增：`screen_translator/ui/window_logic.py`、`screen_translator/ui/desktop_actions.py`、`screen_translator/ui/theme.py`。
- 新增：`screen_translator/ui/components/__init__.py`、`pixel.py`、`shell.py`。
- 新增：`screen_translator/ui/pages/__init__.py`、`screen_page.py`、`existing_pages.py`、`preserved_pages.py`。
- 新增：`screen_translator/resources/ui_v2/README.md` 及 15 张派生 PNG。
- 新增：`scripts/prepare_ui_assets.py`、`scripts/ui_smoke_test.py`、本文件；`logs/ui-refactor/` 为本地验证截图输出。

## 已知范围与后续阶段

- 其它九页保留原控件和逻辑，仅移入中央页面容器；未宣称这些页面已完成新版设计。浮窗外观也仍是原实现。
- 当前核心实际只有通用、游戏、网课、高质量四个场景。显示对应四个按钮；没有沿用原展示板把会议/自定义悄悄映射成通用的假按钮。会议/自定义待产品和核心行为确定后实现。
- 屏幕页 OCR/翻译引擎/延迟指标仍使用原先的占位值；本阶段未扩展核心的指标接口。
- 最小窗口下高级选项通过中央页面滚动访问；1366×768 是物理屏幕尺寸时，还取决于系统缩放。最小 1100×700 logical pixels 在 150% 下需要更大的物理工作区，此轮遵循附件指定的最小尺寸。
- 未执行真实 OCR/NLLB/Whisper 模型推理、系统音频录制、完整安装包构建、macOS 运行、跨显示器 DPI 切换。spec 只完成静态资源检查。
- 离屏后端截图在此环境缺少字体，视觉验收使用 Windows 原生后端截图。
- 现有 SQLite core 连接依赖垃圾回收释放的问题未在本次 UI 重构中修改；自测只修复临时目录清理时序。
