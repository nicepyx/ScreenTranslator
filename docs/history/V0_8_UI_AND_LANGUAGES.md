# Screen Translator v0.8 — Multi-language & Modern Pixel UI

## Multi-language

Translation cache, context sessions and history now include both `source_lang` and `target_lang`.
This prevents an English→Chinese cache entry from being reused for English→French.

Default packs: `zh`, `en`, `fr`, `ja`.
Optional packs: `de`, `es`, `ko`, `it`, `pt`, `ru`.

The current NLLB model is multilingual, so optional packs share the base translation model. Pack installation is intentionally separated behind `LanguagePackManager` so future language-specific OCR rules, glossaries or dedicated models can be downloaded without changing the main UI.

## UI

The v0.7 tab layout is retained internally as reusable page builders but v0.8 presents it through a new sidebar + stacked-page shell.

Pixel assets live in:

```text
screen_translator/resources/pixel/
```

They are resized to compact UI assets and included by the PyInstaller spec.

## Theme

`ui_theme` is stored in `QSettings` and currently supports `dark` and `light`.
