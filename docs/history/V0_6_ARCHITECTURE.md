# Screen Translator v0.6 architecture

```text
InputSource
├─ ScreenRegion
├─ Window
├─ SystemAudio
└─ Microphone
        │
        ├──────────── image ────────────┐
        │                               ↓
        │                         OCR Router
        │                    ┌──────────┴──────────┐
        │                    │                     │
        │              Native OCR           RapidOCR fallback
        │                    └──────────┬──────────┘
        │                               ↓
        │                        Smart Text Merge
        │                               ↓
        │                    Stable Text Detector
        │                               ↓
        └──────────── audio ───────→ VAD / ASR
                                        ↓
                                  Text Pipeline
                       ┌────────────────┼────────────────┐
                       ↓                ↓                ↓
                 OCR Correction     Glossary       Entity Protect
                       └────────────────┼────────────────┘
                                        ↓
                                 Context Session
                                        ↓
                               Translator Provider
                                        ↓
                             Exact / Fuzzy Cache
                                        ↓
                          History + Overlay + UI
```

## Provider boundaries

- OCR: Windows Native / macOS Vision / RapidOCR.
- ASR: faster-whisper CPU/CUDA; MLX Whisper on Apple Silicon.
- Translation: NLLB Provider today; additional providers can be added without changing capture/UI.

## Context policy

Full session state is retained per channel, but the NLLB provider only gets compact sentence context when the current sentence is likely to depend on earlier dialogue. This avoids paying the latency cost on every subtitle.

## Partial vs final audio path

Partial captions are intentionally disposable: they use fast decoding, do not enter history, and do not mutate long-term context. Final captions use the normal pipeline, are persisted, and replace partial output.
