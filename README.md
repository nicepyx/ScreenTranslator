# Screen Translator v0.9.2

> UI 已按目标图重新还原主窗口与字幕设置，并把共用按钮、下拉框、复选框等替换为像素素材。Design Board 仅作设计参考；字幕、迷你条和词汇弹窗仍是独立窗口。详见 [视觉还原与实际截图](UI_VISUAL_RESTORE.md)；此前的架构拆分记录见 [UI_REFACTOR_CHANGELOG.md](UI_REFACTOR_CHANGELOG.md)。

# Screen Translator v0.9

跨 Windows / macOS 的本地翻译器，支持手动框选屏幕区域进行单次翻译，以及持续声音翻译。v0.9 重点不再扩展翻译模型，而是完成 **Desktop UX / Workflow Upgrade** 与 **Pixel UI System**。

## v0.9 重点变化

### 1. 取消主页
- 左侧导航直接从“屏幕翻译”开始。
- 自动记住最后使用页面，下一次启动恢复。

### 2. 只保留浅色像素主题
- 删除深色主题切换。
- 主窗口、按钮、输入框、下拉框、复选框、滑条、滚动条、进度条、弹窗统一使用浅色像素视觉。
- 翻译正文仍使用系统清晰字体，避免长时间阅读疲劳。
- `design/reference/` 保存当前目标图，`screen_translator/resources/ui_target/` 保存当前像素皮肤素材。
- `screen_translator/resources/pixel_ui/` 为精确可用的小尺寸控件素材。

历史版本说明已归档到 [docs/history](docs/history/README.md)。最新验收截图保存在 `docs/screenshots/`；`logs/` 仅存放可重新生成的本地测试输出，不纳入版本控制。

### 3. 系统托盘模式
关闭主窗口默认只隐藏到系统托盘，声音翻译可以继续运行。托盘菜单支持：
- 打开主窗口
- 框选并翻译一次
- 开始 / 暂停声音翻译
- 迷你控制条
- 退出程序

### 4. 全局快捷键中心
默认快捷键：
- `Ctrl + Alt + Q`：框选并翻译一次
- `Ctrl + Alt + A`：开始 / 暂停声音翻译
- `Ctrl + Alt + D`：显示 / 隐藏字幕
- `Ctrl + Alt + C`：清空字幕
- `Ctrl + Alt + M`：迷你控制条
- `Ctrl + Alt + W`：显示主窗口

可在“快捷键”页面重新绑定。全局快捷键由 `pynput` 实现；macOS 第一次使用可能需要辅助功能权限。

### 5. 记住工作状态
继承 v0.8 的语言、音频设备、性能与字幕设置，并新增：
- 最后使用页面
- 托盘行为
- 迷你控制条位置
- 全局快捷键

### 6. 单次屏幕翻译
点击“框选并翻译一次”后，拖动鼠标选择文字区域。应用仅执行一次截图、OCR 与本地翻译，不会持续轮询屏幕，也不会绑定来源窗口。

### 7. 迷你悬浮控制条
声音翻译时可仅保留小型置顶控制条：
- 当前状态
- 当前翻译方向
- 暂停
- 清空字幕
- 锁定字幕
- 打开主窗口

### 8. 状态反馈系统
状态条区分 Ready / Working / Paused / Error，并显示 OCR、模型加载、监听与翻译状态。

### 9. 任务取消与队列
- 状态条提供“取消任务”。
- 单次翻译忙碌时可以排队一个下一任务。
- 已取消的过期 OCR / 翻译结果会被丢弃。
- 声音翻译继续使用 v0.6 的 Partial 丢弃 / Final 优先队列。

### 10. 翻译结果快捷操作
翻译文本区支持：
- 复制原文
- 复制译文
- 朗读译文
- 清屏
- 点击单词进入词汇学习

### 11. 词汇学习
在原文或译文中点击词语：
- 使用本地翻译模型查询含义
- 使用系统 TTS 播放发音
- 查看当前上下文
- 加入本地词汇记录

“词汇学习”页面可以朗读或删除收藏词汇。

### 12. 本地数据模式
“数据管理”页面支持：
- 标准模式：系统默认用户数据目录
- 自定义路径：例如 `D:\ScreenTranslatorData`
- 更改路径并迁移数据
- 恢复标准路径并迁移回来
- 打开数据目录
- 清理翻译缓存

显示占用分类：
- 翻译 / ASR 模型
- 语言包
- 翻译历史
- 翻译缓存
- 配置与 Profile
- 词汇记录
- 其他

> 数据目录修改后建议重启应用，确保当前进程中的模型和 SQLite 对象全部切换到新路径。

## 继续保留的核心能力
- Windows Native OCR / RapidOCR fallback
- macOS Vision OCR
- OCR 智能行 / 段落合并
- OCR 纠错
- Fuzzy Cache
- Context Session
- Provider 化翻译引擎
- NLLB 多语言互译
- VAD 自动断句
- Partial / Final 实时语音字幕
- NLLB 翻译固定使用 CPU INT8，Whisper 可独立使用受支持的硬件加速路径
- 字幕描边、阴影、双语样式、滚动字幕、智能停留、防抖布局、自定义字体
- 中 / 英 / 法 / 日核心语言与扩展语言包

## Windows 开发运行

```bat
scripts\run_windows.bat
```

Python 3.12 可直接使用。

## macOS 开发运行

```bash
chmod +x scripts/run_macos.command
./scripts/run_macos.command
```

需要授予屏幕录制 / 麦克风等权限。

## 自动构建
GitHub Actions：

```text
.github/workflows/build.yml
```

手动运行 Workflow 或 Push `v*` Tag 即可构建 Windows 与 macOS 测试包。

## 发布注意
- Windows 未签名安装包可能触发 SmartScreen。
- macOS 正式对外发布建议 Developer ID 签名 + Notarization。
- 当前 NLLB 模型许可证需继续按第三方许可说明评估用途。

## 首次安装与模型

- 应用启动只检查本地模型状态，不会访问 Hugging Face，也不依赖用户目录中的 Hugging Face 缓存。
- 用户首次启动屏幕或声音翻译时，应用会先显示模型名称、大小和保存位置；确认后才在后台下载。
- 下载文件保存在数据目录的 `downloads` 中并支持断点续传。SHA-256 校验通过后，模型才会原子安装到 `models`。
- 下载源与固定 revision、文件大小及 SHA-256 位于 `screen_translator/resources/model_manifest.json`。
- 无法联网时可在模型提示窗口选择本地 ZIP。ZIP 可包含一个外层目录，但内部文件必须与 manifest 中该模型的 `files` 一致。
