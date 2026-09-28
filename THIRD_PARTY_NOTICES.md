# Third-party notices

Screen Translator is a prototype that combines several third-party projects. Before public or commercial distribution, verify the exact licenses of the versions and model weights actually packaged. This file is informational and is not a substitute for the upstream license texts.

Key components include:

- PySide6 / Qt for Python — Qt licensing terms apply (LGPL/GPL/commercial options depending on distribution and use).
- RapidOCR — local OCR integration and model runtime.
- ONNX Runtime — ONNX model execution.
- PyWinRT / Windows.Media.Ocr — Windows native OCR bindings.
- PyObjC / Vision / Quartz — macOS Vision OCR and window APIs.
- CTranslate2 — local Transformer inference, CPU/CUDA runtime.
- Faster-Whisper — local Whisper ASR implemented with CTranslate2.
- MLX Whisper — Apple Silicon Whisper inference path.
- PyAudioWPatch — Windows WASAPI microphone/system-output loopback capture.
- SoundCard — non-Windows audio capture where supported.
- psutil — hardware/resource monitoring.
- Pillow / NumPy — image/audio preprocessing.
- Hugging Face Hub — model download/cache utilities.
- SentencePiece — NLLB tokenization.
- Lingua — lightweight language detection.

## Model weights

The current default translation model is a CTranslate2 build derived from Meta NLLB-200 distilled 600M. Its upstream model family is CC-BY-NC-4.0 and is used here for non-commercial prototyping. Do not treat this default model as suitable for commercial distribution without replacing/reviewing it.

Whisper/MLX model weights are downloaded separately at runtime. Review the model card and license of the exact repository/version distributed or cached by your release.

## Distribution note

If Screen Translator is publicly distributed, bundle the exact upstream license notices for every dependency/model included in the installer and re-check transitive native libraries (Qt, ONNX Runtime, PortAudio/WASAPI wrappers, CUDA/cuDNN when applicable).

## Project artwork

The pixel-art application/navigation assets under `screen_translator/resources/pixel/` were generated specifically for this Screen Translator prototype and are not copied from the GitHub reference projects used for architectural research.
