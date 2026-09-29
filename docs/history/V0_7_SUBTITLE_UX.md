# Screen Translator v0.7 — Subtitle UX

v0.7 focuses on readability and visual stability rather than adding another recognition engine.

## Added

- Partial / Final smooth updates: provisional audio translations render with reduced opacity; final text settles into the rolling history.
- Text outline + shadow: usable even when subtitle background opacity is 0%.
- Independent bilingual styles: source and Chinese translation have separate font size and color.
- Rolling subtitles: keep the latest 2 or 3 finalized captions on screen.
- Subtitle presets: Course, Movie, Game, Minimal.
- Smart reading duration: retention time scales with caption length; fixed 3/5/8s and never-hide modes are also available.
- Low-jitter layout: bottom-positioned captions keep their bottom edge anchored while text grows/shrinks.
- Custom fonts: choose any installed system font or import TTF/OTF/TTC at runtime.

## Rendering model

The old QLabel subtitle renderer has been replaced by a custom QPainter-based canvas. This is what makes outline, per-layer opacity, rolling history and partial/final transitions possible without changing the translation pipeline.

## Recommended course preset

- Original + Chinese
- Latest 3 captions
- Smart retention
- 42% background
- 22px Chinese / 15px original
- 2px black outline + shadow
- Bottom / 800px / centered
