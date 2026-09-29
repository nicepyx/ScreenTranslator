# Screen Translator v0.9 Changelog

## Desktop UX
- Removed Home page; launch restores the last-used page.
- Light pixel theme only.
- System tray mode.
- Global hotkey center.
- Restore previous work state, including language direction, source window, audio device, page, subtitle settings and mini-toolbar position.
- Source-window binding with pause/resume and profile-key rebinding after application restarts.
- Always-on-top mini control bar.
- Pixel status feedback strip.
- Soft task cancellation plus coalescing screen-translation queue.
- Quick actions for source/translation text.
- Searchable translation history.

## Vocabulary learning
- Click a word in source or translated text.
- Local-model meaning lookup.
- System TTS pronunciation playback.
- Save terms to local vocabulary database.
- Vocabulary management page.

## Data management
- Standard data path or custom path.
- Migration in either direction.
- Free-space validation.
- Per-category disk usage.
- Cache cleanup.
- Settings moved from OS QSettings to `settings.json` under the selected data root, with one-time legacy import.

## Pixel UI System
- New light palette and pixel control skin.
- Pixel assets for checkbox/radio/toggle/slider/dropdown/status and mini-toolbar actions.
- New pixel navigation art for vocabulary, data and shortcuts.
- UI design reference image included under `screen_translator/resources/pixel/ui_reference_v09.png`.
