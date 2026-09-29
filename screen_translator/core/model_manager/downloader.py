from __future__ import annotations

import hashlib
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import quote
from urllib.request import Request, urlopen

from .errors import ModelDownloadCancelled, ModelDownloadError, ModelVerificationError
from .manifest import ModelDefinition, ModelFile, ModelSource


@dataclass(frozen=True)
class DownloadProgress:
    downloaded_bytes: int
    total_bytes: int
    speed: float
    eta_seconds: float | None
    source_name: str
    message: str


ProgressCallback = Callable[[DownloadProgress], None]


class DownloadControl:
    def __init__(self) -> None:
        self._cancelled = threading.Event()
        self._running = threading.Event()
        self._running.set()

    def cancel(self) -> None:
        self._cancelled.set()
        self._running.set()

    def pause(self) -> None:
        self._running.clear()

    def resume(self) -> None:
        self._running.set()

    def checkpoint(self) -> None:
        while not self._running.wait(0.2):
            if self._cancelled.is_set():
                raise ModelDownloadCancelled("模型下载已取消。")
        if self._cancelled.is_set():
            raise ModelDownloadCancelled("模型下载已取消。")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_is_valid(path: Path, item: ModelFile) -> bool:
    return (
        path.is_file()
        and path.stat().st_size == item.size
        and sha256_file(path).lower() == item.sha256.lower()
    )


class ResumableDownloader:
    CHUNK_SIZE = 1024 * 1024

    def download(
        self,
        model: ModelDefinition,
        source: ModelSource,
        destination: Path,
        progress: ProgressCallback | None,
        control: DownloadControl,
    ) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        completed = 0
        for item in model.files:
            final_path = destination / item.path
            if file_is_valid(final_path, item):
                completed += item.size

        started_at = time.monotonic()
        initial_completed = completed
        for item in model.files:
            final_path = destination / item.path
            if file_is_valid(final_path, item):
                continue
            control.checkpoint()
            final_path.parent.mkdir(parents=True, exist_ok=True)
            part_path = final_path.with_name(final_path.name + ".part")
            if part_path.exists() and part_path.stat().st_size > item.size:
                part_path.unlink()
            if part_path.exists() and part_path.stat().st_size == item.size:
                actual = sha256_file(part_path)
                if actual.lower() == item.sha256.lower():
                    os.replace(part_path, final_path)
                    completed += item.size
                    continue
                part_path.unlink()
            offset = part_path.stat().st_size if part_path.exists() else 0
            url = self._file_url(source, model, item)
            headers = {"User-Agent": "ScreenTranslator/0.9.2"}
            if offset:
                headers["Range"] = f"bytes={offset}-"
            try:
                request = Request(url, headers=headers)
                with urlopen(request, timeout=30) as response:
                    status = getattr(response, "status", 200)
                    if offset and status != 206:
                        offset = 0
                    mode = "ab" if offset and status == 206 else "wb"
                    with part_path.open(mode) as stream:
                        while True:
                            control.checkpoint()
                            block = response.read(self.CHUNK_SIZE)
                            if not block:
                                break
                            stream.write(block)
                            current = offset + stream.tell() if mode == "wb" else stream.tell()
                            downloaded = completed + current
                            elapsed = max(0.001, time.monotonic() - started_at)
                            speed = max(0.0, (downloaded - initial_completed) / elapsed)
                            remaining = max(0, model.size - downloaded)
                            eta = remaining / speed if speed > 0 else None
                            if progress:
                                progress(DownloadProgress(
                                    downloaded, model.size, speed, eta, source.name,
                                    f"正在下载 {item.path}",
                                ))
            except ModelDownloadCancelled:
                raise
            except Exception as exc:
                raise ModelDownloadError(
                    "当前下载源连接失败，正在尝试备用源。",
                    f"{source.name}: {type(exc).__name__}: {exc}",
                ) from exc

            if part_path.stat().st_size != item.size:
                raise ModelDownloadError(
                    "模型文件下载不完整，正在尝试备用源。",
                    f"{source.name}: {item.path} expected {item.size}, got {part_path.stat().st_size}",
                )
            actual = sha256_file(part_path)
            if actual.lower() != item.sha256.lower():
                part_path.unlink()
                raise ModelVerificationError(
                    "模型文件校验失败，已删除损坏文件。",
                    f"{item.path}: expected {item.sha256}, got {actual}",
                )
            os.replace(part_path, final_path)
            completed += item.size

    @staticmethod
    def _file_url(source: ModelSource, model: ModelDefinition, item: ModelFile) -> str:
        base = source.base_url.format(repo_id=model.repo_id, revision=model.revision).rstrip("/")
        return base + "/" + quote(item.path.replace("\\", "/"), safe="/")
