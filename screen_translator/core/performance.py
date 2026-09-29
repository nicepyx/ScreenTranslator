from __future__ import annotations

from dataclasses import dataclass
import os
import platform
import re
import subprocess
from typing import Optional

import psutil

from ..constants import PERFORMANCE_PROFILES


@dataclass(frozen=True)
class HardwareInfo:
    os_name: str
    os_version: str
    architecture: str
    cpu_name: str
    physical_cores: int
    logical_cores: int
    memory_gb: float
    gpu_name: str
    apple_chip: str

    @property
    def summary(self) -> str:
        lines = [
            f"系统：{self.os_name} {self.os_version} ({self.architecture})",
            f"CPU：{self.cpu_name or '未识别'}",
            f"核心：{self.physical_cores or '?'} 物理 / {self.logical_cores or '?'} 逻辑",
            f"内存：{self.memory_gb:.1f} GB",
        ]
        if self.apple_chip:
            lines.append(f"Apple 芯片：{self.apple_chip}")
        if self.gpu_name:
            lines.append(f"GPU：{self.gpu_name}")
        gpu_low = self.gpu_name.lower()
        arch_low = self.architecture.lower()
        if "nvidia" in gpu_low:
            lines.append("加速：检测到 NVIDIA；Whisper 会尝试 CUDA，NLLB 翻译固定使用 CPU INT8。")
        elif self.apple_chip or arch_low in {"arm64", "aarch64"} and self.os_name == "macOS":
            lines.append("加速：Apple Silicon 优先使用 MLX Whisper；NLLB 翻译固定使用 CPU INT8。")
        else:
            lines.append("加速：Whisper 与 NLLB 将使用 CPU；NLLB 计算类型固定为 INT8。")
        return "\n".join(lines)


def _run_text(cmd: list[str], timeout: float = 4.0) -> str:
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return (completed.stdout or "").strip()
    except Exception:
        return ""


def _windows_cpu_gpu() -> tuple[str, str]:
    cpu = _run_text([
        "powershell", "-NoProfile", "-Command",
        "(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)"
    ])
    gpu = _run_text([
        "powershell", "-NoProfile", "-Command",
        "((Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name) -join ' | ')"
    ])
    return cpu, gpu


def _mac_hardware() -> tuple[str, str, str]:
    text = _run_text(["system_profiler", "SPHardwareDataType", "SPDisplaysDataType"], timeout=8.0)
    chip = ""
    gpu = ""
    cpu = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Chip:") and not chip:
            chip = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Processor Name:") and not cpu:
            cpu = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Chipset Model:") and not gpu:
            gpu = stripped.split(":", 1)[1].strip()
    if not cpu:
        cpu = chip or _run_text(["sysctl", "-n", "machdep.cpu.brand_string"])
    return cpu, gpu, chip


def detect_hardware() -> HardwareInfo:
    system = platform.system()
    cpu_name = platform.processor() or ""
    gpu_name = ""
    apple_chip = ""
    if system == "Windows":
        win_cpu, gpu_name = _windows_cpu_gpu()
        cpu_name = win_cpu or cpu_name
    elif system == "Darwin":
        mac_cpu, gpu_name, apple_chip = _mac_hardware()
        cpu_name = mac_cpu or cpu_name

    physical = psutil.cpu_count(logical=False) or 0
    logical = psutil.cpu_count(logical=True) or (os.cpu_count() or 0)
    memory_gb = psutil.virtual_memory().total / (1024 ** 3)

    return HardwareInfo(
        os_name="macOS" if system == "Darwin" else system,
        os_version=platform.release(),
        architecture=platform.machine(),
        cpu_name=re.sub(r"\s+", " ", cpu_name).strip(),
        physical_cores=int(physical),
        logical_cores=int(logical),
        memory_gb=float(memory_gb),
        gpu_name=re.sub(r"\s+", " ", gpu_name).strip(),
        apple_chip=apple_chip,
    )


def recommend_profile(info: HardwareInfo) -> tuple[str, str]:
    """Conservative recommendation; supported hardware can accelerate Whisper ASR."""
    cores = info.physical_cores or max(1, info.logical_cores // 2)
    ram = info.memory_gb
    cpu_text = f"{info.cpu_name} {info.apple_chip}".lower()

    if ram < 8 or cores <= 4:
        key = "eco"
    elif ram >= 32 and cores >= 12:
        key = "ultra"
    elif ram >= 16 and cores >= 8:
        key = "high"
    else:
        key = "balanced"

    gpu_text = info.gpu_name.lower()
    # Hardware accelerators materially change Whisper throughput. OCR, translation, and the UI
    # still consume CPU and memory, so the recommendation remains conservative.
    if "nvidia" in gpu_text and ram >= 16 and cores >= 6 and key in {"eco", "balanced"}:
        key = "high"

    # Apple Silicon is efficient enough to avoid the lowest tier unless memory is very constrained.
    if "apple m" in cpu_text and key == "eco" and ram >= 8:
        key = "balanced"
    if any(tag in cpu_text for tag in (" pro", " max", " ultra")) and ram >= 16 and cores >= 8 and key == "balanced":
        key = "high"
    if any(tag in cpu_text for tag in (" max", " ultra")) and ram >= 24 and cores >= 10:
        key = "ultra"

    reasons = []
    reasons.append(f"{cores} 个物理核心" if info.physical_cores else f"约 {cores} 个物理核心")
    reasons.append(f"{ram:.0f}GB 内存")
    if info.apple_chip:
        reasons.append(info.apple_chip)
    if "nvidia" in info.gpu_name.lower():
        reasons.append("NVIDIA GPU")
    return key, "、".join(reasons)


def profile_requirements_text() -> str:
    return (
        "Windows\n"
        "• 省资源：4 核级 CPU / 8GB；NLLB CPU INT8；建议 Tiny Whisper。\n"
        "• 均衡：6 核级 CPU / 16GB；Base Whisper；适合通用字幕。\n"
        "• 高性能：8 核+ / 16GB+；若 CUDA 运行库可用，Whisper 会自动尝试 NVIDIA 加速。\n"
        "• 极致：12 核+ / 32GB+，或较新 RTX；适合 Small Whisper 与流式 Partial ASR。\n\n"
        "macOS\n"
        "• Intel：继续使用 faster-whisper CPU；建议 16GB 与均衡档。\n"
        "• Apple Silicon 8GB+：自动尝试 MLX Whisper；Base 模型适合课程。\n"
        "• M Pro/Max/Ultra 16GB+：适合高性能/极致档与更频繁 Partial ASR。\n\n"
        "OCR：Windows 优先 WinRT 原生 OCR，macOS 优先 Vision；识别质量不足自动回退 RapidOCR。\n"
        "说明：NLLB 翻译始终使用 CPU INT8；Whisper 是否启用 GPU/MLX 以“实时资源占用”中的推理后端为准。"
    )


def profile_settings(key: str) -> dict:
    return dict(PERFORMANCE_PROFILES.get(key, PERFORMANCE_PROFILES["balanced"]))


class RuntimePerformanceMonitor:
    """Low-overhead process/system metrics for the performance page."""

    def __init__(self) -> None:
        self._process = psutil.Process(os.getpid())
        # Prime psutil's delta-based CPU counters.
        self._process.cpu_percent(None)
        psutil.cpu_percent(None)

    def sample(self) -> dict:
        try:
            process_cpu = float(self._process.cpu_percent(None))
            process_mem = float(self._process.memory_info().rss / (1024 ** 2))
        except Exception:
            process_cpu = 0.0
            process_mem = 0.0
        vm = psutil.virtual_memory()
        return {
            "process_cpu": process_cpu,
            "process_memory_mb": process_mem,
            "system_cpu": float(psutil.cpu_percent(None)),
            "system_memory_percent": float(vm.percent),
            "system_memory_used_gb": float((vm.total - vm.available) / (1024 ** 3)),
            "system_memory_total_gb": float(vm.total / (1024 ** 3)),
        }
