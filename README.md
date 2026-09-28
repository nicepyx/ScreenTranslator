# Screen Translator v0.8

本地优先的 Windows / macOS 实时翻译工具。支持屏幕 OCR、游戏窗口、系统声音 / 麦克风、VAD 自动断句、流式 Partial / Final 字幕、上下文翻译、翻译历史和可定制字幕叠加层。

v0.8 集中完成两项升级：**自由选择目标语言 + 语言包管理**，以及 **现代像素风桌面 UI**。

## v0.8 主要变化

### 1. 多语言自由互译

核心语言默认安装：

- 简体中文
- English
- Français
- 日本語

这些语言现在都可以作为源语言或目标语言，例如：

- English → 简体中文
- 简体中文 → English
- Français → 日本語
- 日本語 → Français

屏幕翻译和声音翻译都提供 `源语言 ⇄ 目标语言` 控件。源语言仍支持自动检测。

### 2. 扩展语言包

语言包页面提供以下扩展语言：

- Deutsch
- Español
- 한국어
- Italiano
- Português
- Русский

安装后会自动加入屏幕翻译和声音翻译的源/目标语言列表。删除语言包不会删除翻译历史。

当前 NLLB-200、Whisper 和 RapidOCR 都是多语言共享运行时，因此扩展语言包不会为每一种语言重复下载数百 MB 大模型。语言包负责启用语言配置、OCR / ASR 提示和后续可扩展的专用规则。

开发版内置兼容语言包配置；正式发布时可设置环境变量：

```text
SCREEN_TRANSLATOR_PACK_BASE_URL=https://your-cdn.example.com/language-packs
```

程序会优先尝试下载 `<语言代码>.json`，远程不可用时自动回退内置配置。

### 3. 现代像素风 UI

v0.8 不再使用顶部 Qt Tab 作为主要导航，改为左侧现代侧边栏：

- 主页
- 屏幕翻译
- 声音翻译
- 翻译记录
- 语言包
- 字幕
- 性能
- 设置

同时加入一组专门为 Screen Translator 生成的像素风美术素材：应用 Logo、主页、屏幕翻译、声音翻译、历史、语言包、字幕、性能和设置图标。

像素风只用于品牌和导航视觉；主要文本、设置和字幕保持现代高可读性排版。

支持：

- 深色主题
- 浅色主题
- 卡片式信息层级
- 主页快捷入口
- 实时翻译方向提示
- 字幕设置实时预览
- 像素风侧边栏图标

## 运行开发版

Windows：

```text
scripts\run_windows.bat
```

macOS：

```text
scripts/run_macos.command
```

首次运行会安装 Python 依赖。首次实际翻译时会下载本地 NLLB 翻译模型；声音翻译首次使用某个 Whisper 模型时会额外下载对应 ASR 模型。之后可离线运行。

## 推荐测试流程

### 多语言

1. 屏幕翻译：`English → 简体中文`
2. 点击 `⇄`：测试 `简体中文 → English`
3. 进入“语言包”，安装 Deutsch
4. 返回屏幕翻译，确认 Deutsch 已出现在源语言和目标语言列表
5. 测试 English → Deutsch / Deutsch → 简体中文

### 声音翻译

1. 选择系统声音或麦克风
2. 选择源语言 / 目标语言
3. 使用“实时课程 · 低延迟”模式
4. 检查 Partial 字幕和 Final 字幕是否按目标语言显示

### UI

1. 切换深色 / 浅色主题
2. 检查不同窗口尺寸下侧边栏和页面是否正常
3. 测试字幕页面实时预览
4. 检查像素风图标在 Windows 缩放 100% / 125% / 150% 下是否清晰

## 核心架构

屏幕翻译：

```text
Capture
→ Native OCR / RapidOCR fallback
→ OCR Correction
→ Smart Text Merge
→ Stable Text Detector
→ Fuzzy Cache
→ Entity / Terminology
→ Context Session
→ Translator Provider
→ History / Overlay
```

声音翻译：

```text
Continuous Audio Capture
→ VAD
→ Partial ASR
→ Partial Translation
→ Final ASR
→ Context Session
→ Final Translation
→ History / Overlay
```

## 打包

Windows：

```powershell
scripts\build_windows.ps1
```

如果安装了 Inno Setup，会生成：

```text
release/ScreenTranslator-v0.8.0-Windows-Setup.exe
```

macOS：

```bash
scripts/build_macos.sh
```

生成：

```text
release/ScreenTranslator-v0.8.0-macOS.dmg
```

GitHub Actions 也已配置 Windows / macOS 双平台构建。

## 注意

- 当前默认 NLLB-200 量化模型为非商业用途许可；公开商业发布前应替换为符合商业授权要求的翻译模型。
- macOS 系统内部音频仍需要继续完善 ScreenCaptureKit 原生音频捕获路线；麦克风翻译可直接使用。
- Windows / macOS 原生 OCR 能力取决于系统安装的语言支持；识别质量不足时会回退 RapidOCR。
- 未安装的扩展语言如果被自动检测到，程序会提示先到“语言包”页面安装。

## 测试

```bash
python scripts/self_test.py
```

当前自检覆盖：

- Smart Text Merge
- Stable Text Detector
- Context Session（含目标语言隔离）
- Fuzzy Cache（含源/目标语言隔离）
- VAD 自动断句
