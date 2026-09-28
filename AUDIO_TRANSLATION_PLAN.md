# Audio translation status — v0.6

## Implemented

- Windows microphone capture.
- Windows WASAPI loopback through PyAudioWPatch.
- Non-Windows microphone / available loopback through SoundCard.
- Continuous capture while ASR and translation workers are busy.
- Adaptive VAD with pre-roll, silence hangover and maximum-utterance segmentation.
- Partial ASR while speech is still active.
- Partial translation using a low-latency path.
- Final ASR + final correction that replaces the provisional subtitle.
- Queue-based asynchronous Capture → ASR → Translation pipeline.
- Faster-Whisper CPU INT8 fallback.
- Automatic NVIDIA CUDA attempt for Faster-Whisper when CTranslate2 can see a CUDA device.
- Apple Silicon MLX Whisper attempt, with CPU fallback.
- Context/terminology/entity processing for final subtitles.
- Persistent history only for final subtitles.

## Low-latency defaults

The exact values are controlled by usage/performance profiles. Realtime Course generally targets:

- 100 ms VAD analysis blocks.
- Partial ASR after roughly 0.8 s of active speech.
- Partial refresh about every 0.75 s.
- End-of-speech silence around 0.34 s.
- Maximum continuous utterance around 6.5 s.

These are responsiveness targets, not guaranteed end-to-end latency. Actual latency depends on CPU/GPU, model size, audio device buffering and translation backend.

## Still planned

- Native macOS system-audio capture through ScreenCaptureKit.
- Optional neural VAD provider if the lightweight adaptive VAD is insufficient in noisy content.
- Dedicated per-language compact translation models as optional Fast Translation Providers.
- More advanced incremental ASR that reuses encoder state rather than retranscribing a rolling snapshot.
