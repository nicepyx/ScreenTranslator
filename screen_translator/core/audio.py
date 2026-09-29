from __future__ import annotations

from dataclasses import dataclass
import os
import platform
import threading
from typing import Callable, Optional, TYPE_CHECKING

import numpy as np

from .model_manager import ModelManager

if TYPE_CHECKING:
    from faster_whisper import WhisperModel


@dataclass(frozen=True)
class AudioDeviceInfo:
    key: str
    name: str
    is_loopback: bool


def _is_windows() -> bool:
    return platform.system() == "Windows"


def _list_windows_audio_devices(kind: str) -> list[AudioDeviceInfo]:
    # PyAudioWPatch uses PortAudio/WASAPI and does not pre-initialize the Qt GUI
    # thread's COM apartment like SoundCard does on Windows.
    import pyaudiowpatch as pyaudio

    result: list[AudioDeviceInfo] = []
    seen: set[str] = set()
    with pyaudio.PyAudio() as pa:
        if kind == "system":
            devices = pa.get_loopback_device_info_generator()
        else:
            devices = pa.get_device_info_generator()

        for dev in devices:
            try:
                is_loopback = bool(dev.get("isLoopbackDevice", False))
                max_input = int(dev.get("maxInputChannels", 0) or 0)
                if kind == "system":
                    if not is_loopback or max_input <= 0:
                        continue
                else:
                    if is_loopback or max_input <= 0:
                        continue

                index = int(dev["index"])
                name = str(dev.get("name") or f"Audio device {index}")
            except Exception:
                continue

            fingerprint = f"{name}|{int(dev.get('defaultSampleRate', 0) or 0)}|{max_input}"
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            result.append(AudioDeviceInfo(key=str(index), name=name, is_loopback=is_loopback))

    return result


def _list_soundcard_devices(kind: str) -> list[AudioDeviceInfo]:
    import soundcard as sc

    devices = sc.all_microphones(include_loopback=True)
    wanted_loopback = kind == "system"
    result: list[AudioDeviceInfo] = []
    seen: set[str] = set()
    for dev in devices:
        try:
            is_loopback = bool(dev.isloopback)
            name = str(dev.name)
            key = str(dev.id)
        except Exception:
            continue
        if is_loopback != wanted_loopback:
            continue
        fingerprint = f"{key}|{name}"
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        result.append(AudioDeviceInfo(key=key, name=name, is_loopback=is_loopback))
    return result


def list_audio_devices(kind: str) -> list[AudioDeviceInfo]:
    """Return microphones or system-output loopback devices."""
    if _is_windows():
        return _list_windows_audio_devices(kind)
    return _list_soundcard_devices(kind)


class WindowsAudioRecorder:
    """Blocking recorder backed by PyAudioWPatch / WASAPI."""

    def __init__(self, device_key: str) -> None:
        self.device_index = int(device_key)
        self._pa = None
        self._stream = None
        self.sample_rate = 16000
        self.channels = 1

    def __enter__(self) -> "WindowsAudioRecorder":
        import pyaudiowpatch as pyaudio

        self._pyaudio = pyaudio
        self._pa = pyaudio.PyAudio()
        info = self._pa.get_device_info_by_index(self.device_index)
        self.sample_rate = max(8000, int(float(info.get("defaultSampleRate", 16000))))
        self.channels = max(1, int(info.get("maxInputChannels", 1) or 1))
        self._stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            input_device_index=self.device_index,
            frames_per_buffer=max(512, int(self.sample_rate * 0.05)),
        )
        return self

    def record(self, numframes: int) -> np.ndarray:
        if self._stream is None:
            raise RuntimeError("音频设备尚未打开。")
        raw = self._stream.read(int(numframes), exception_on_overflow=False)
        arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        if self.channels > 1:
            usable = (arr.size // self.channels) * self.channels
            arr = arr[:usable].reshape(-1, self.channels)
        return arr

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        try:
            if self._stream is not None:
                self._stream.stop_stream()
                self._stream.close()
        finally:
            self._stream = None
            if self._pa is not None:
                self._pa.terminate()
            self._pa = None


class SoundCardAudioRecorder:
    """Recorder used on non-Windows platforms."""

    def __init__(self, device_key: str, kind: str, sample_rate: int = 16000) -> None:
        self.device_key = device_key
        self.kind = kind
        self.sample_rate = sample_rate
        self._ctx = None
        self._recorder = None

    def __enter__(self) -> "SoundCardAudioRecorder":
        import soundcard as sc

        include_loopback = self.kind == "system"
        try:
            device = sc.get_microphone(self.device_key, include_loopback=include_loopback)
        except Exception:
            device = None
            for info in _list_soundcard_devices(self.kind):
                if info.key == self.device_key:
                    device = sc.get_microphone(info.name, include_loopback=include_loopback)
                    break
            if device is None:
                raise
        self._ctx = device.recorder(samplerate=self.sample_rate)
        self._recorder = self._ctx.__enter__()
        return self

    def record(self, numframes: int) -> np.ndarray:
        if self._recorder is None:
            raise RuntimeError("音频设备尚未打开。")
        return self._recorder.record(numframes=int(numframes))

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self._ctx is not None:
            self._ctx.__exit__(exc_type, exc_value, traceback)
        self._ctx = None
        self._recorder = None


def open_audio_recorder(device_key: str, kind: str):
    if _is_windows():
        return WindowsAudioRecorder(device_key)
    return SoundCardAudioRecorder(device_key, kind)


class AudioTranscriber:
    """ASR provider facade with automatic CUDA / Apple Silicon acceleration."""

    def __init__(self, model_manager: ModelManager | None = None) -> None:
        self._model_manager = model_manager or ModelManager()
        self._models: dict[tuple[str, str], "WhisperModel"] = {}
        self._lock = threading.Lock()
        self._cpu_threads = max(1, min(6, (os.cpu_count() or 4) - 1))
        self._beam_size = 2
        self._prefer_gpu = True
        self._backend_preference = "auto"
        self._resolved_backend = "cpu"
        self._backend_note = ""

    def configure(
        self,
        *,
        cpu_threads: int | None = None,
        beam_size: int | None = None,
        prefer_gpu: bool | None = None,
        backend: str | None = None,
    ) -> None:
        new_threads = self._cpu_threads if cpu_threads is None else max(1, int(cpu_threads))
        new_beam = self._beam_size if beam_size is None else max(1, int(beam_size))
        new_gpu = self._prefer_gpu if prefer_gpu is None else bool(prefer_gpu)
        new_backend = self._backend_preference if backend is None else str(backend)
        if new_threads != self._cpu_threads or new_gpu != self._prefer_gpu or new_backend != self._backend_preference:
            self._models.clear()
        self._cpu_threads = new_threads
        self._beam_size = new_beam
        self._prefer_gpu = new_gpu
        self._backend_preference = new_backend

    @staticmethod
    def _is_apple_silicon() -> bool:
        return platform.system() == "Darwin" and platform.machine().lower() in {"arm64", "aarch64"}

    def _choose_backend(self, model_size: str | None = None) -> str:
        if self._backend_preference not in {"", "auto"}:
            return self._backend_preference
        if self._is_apple_silicon():
            try:
                import mlx_whisper  # noqa: F401
                return "mlx"
            except Exception:
                pass
        if self._prefer_gpu:
            try:
                import ctranslate2
                if ctranslate2.get_cuda_device_count() > 0:
                    return "cuda"
            except Exception:
                pass
        return "cpu"

    def required_model_id(self, model_size: str) -> str:
        backend = self._choose_backend(model_size)
        return f"whisper-mlx-{model_size}" if backend == "mlx" else f"whisper-{model_size}"

    def _model(self, model_size: str, status: Optional[Callable[[str], None]] = None) -> "WhisperModel":
        backend = self._choose_backend(model_size)
        if backend == "mlx":
            raise RuntimeError("MLX backend does not use faster-whisper model objects.")
        key = (backend, model_size)
        with self._lock:
            model = self._models.get(key)
            if model is not None:
                self._resolved_backend = backend
                return model
            model_path = self._model_manager.get_model_path(f"whisper-{model_size}")
            if status:
                status(f"正在加载本地 Whisper {model_size}（{backend.upper()}）…")
            from faster_whisper import WhisperModel

            try:
                if backend == "cuda":
                    model = WhisperModel(
                        str(model_path),
                        device="cuda",
                        compute_type="float16",
                        num_workers=1,
                    )
                else:
                    model = WhisperModel(
                        str(model_path),
                        device="cpu",
                        compute_type="int8",
                        cpu_threads=self._cpu_threads,
                        num_workers=1,
                    )
            except Exception as exc:
                if backend != "cuda":
                    raise
                self._backend_note = f"CUDA 回退：{exc}"
                if status:
                    status("Whisper CUDA 不可用，已自动回退 CPU INT8。")
                backend = "cpu"
                key = (backend, model_size)
                model = self._models.get(key)
                if model is None:
                    model = WhisperModel(
                        str(model_path),
                        device="cpu",
                        compute_type="int8",
                        cpu_threads=self._cpu_threads,
                        num_workers=1,
                    )
            self._models[key] = model
            self._resolved_backend = backend
            return model

    def _transcribe_mlx(
        self,
        audio: np.ndarray,
        source_mode: str,
        model_size: str,
        *,
        partial: bool,
        status: Optional[Callable[[str], None]],
        initial_prompt: str | None,
    ) -> tuple[str, str, float]:
        if status:
            status(f"正在使用 Apple Silicon 加速识别语音{'（临时字幕）' if partial else ''}…")
        import mlx_whisper

        model_path = self._model_manager.get_model_path(f"whisper-mlx-{model_size}")
        kwargs = {
            "path_or_hf_repo": str(model_path),
            "verbose": None,
            "language": None if source_mode == "auto" else source_mode,
            "task": "transcribe",
            "condition_on_previous_text": False,
            "fp16": True,
            "beam_size": 1 if partial else self._beam_size,
        }
        if initial_prompt:
            kwargs["initial_prompt"] = initial_prompt[-500:]
        result = mlx_whisper.transcribe(audio.astype(np.float32, copy=False), **kwargs)
        self._resolved_backend = "mlx"
        text = " ".join(str(result.get("text") or "").split())
        lang = source_mode if source_mode != "auto" else str(result.get("language") or "")
        return text, lang, 0.0

    def transcribe(
        self,
        audio: np.ndarray,
        source_mode: str,
        model_size: str,
        status: Optional[Callable[[str], None]] = None,
        *,
        partial: bool = False,
        initial_prompt: str | None = None,
    ) -> tuple[str, str, float]:
        backend = self._choose_backend(model_size)
        if backend == "mlx":
            try:
                return self._transcribe_mlx(
                    audio, source_mode, model_size,
                    partial=partial, status=status, initial_prompt=initial_prompt,
                )
            except Exception as exc:
                self._backend_note = f"MLX 回退：{exc}"
                if self._model_manager.is_installed(f"whisper-{model_size}") and status:
                    status("Apple MLX Whisper 不可用，已回退 faster-whisper CPU。")
                if self._model_manager.is_installed(f"whisper-{model_size}"):
                    self._backend_preference = "cpu"
                else:
                    raise

        model = self._model(model_size, status)
        language = None if source_mode == "auto" else source_mode
        if status:
            label = "临时语音字幕" if partial else "语音"
            status(f"正在识别{label}…")
        kwargs = dict(
            language=language,
            task="transcribe",
            beam_size=1 if partial else self._beam_size,
            vad_filter=not partial,
            condition_on_previous_text=False,
            without_timestamps=True,
        )
        if not partial:
            kwargs["vad_parameters"] = dict(min_silence_duration_ms=280)
        if initial_prompt:
            kwargs["initial_prompt"] = initial_prompt[-500:]
        segments, info = model.transcribe(audio.astype(np.float32, copy=False), **kwargs)
        text = " ".join(seg.text.strip() for seg in segments if seg.text.strip()).strip()
        detected = language or str(info.language or "")
        probability = float(getattr(info, "language_probability", 0.0) or 0.0)
        return text, detected, probability

    def runtime_label(self) -> str:
        label = {
            "mlx": "Apple MLX",
            "cuda": "NVIDIA CUDA",
            "cpu": "CPU INT8",
        }.get(self._resolved_backend, self._resolved_backend)
        return f"Whisper · {label}"

def mono_float32(data: np.ndarray) -> np.ndarray:
    arr = np.asarray(data, dtype=np.float32)
    if arr.ndim == 2:
        if arr.shape[1] == 0:
            return np.empty((0,), dtype=np.float32)
        arr = arr.mean(axis=1)
    return np.clip(arr.reshape(-1), -1.0, 1.0)


def resample_audio(audio: np.ndarray, source_rate: int, target_rate: int = 16000) -> np.ndarray:
    audio = mono_float32(audio)
    if audio.size == 0 or source_rate == target_rate:
        return audio.astype(np.float32, copy=False)
    output_length = max(1, int(round(audio.size * target_rate / source_rate)))
    old_x = np.linspace(0.0, 1.0, num=audio.size, endpoint=False, dtype=np.float64)
    new_x = np.linspace(0.0, 1.0, num=output_length, endpoint=False, dtype=np.float64)
    return np.interp(new_x, old_x, audio).astype(np.float32)


def audio_rms(audio: np.ndarray) -> float:
    if audio.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))))
