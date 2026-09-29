from __future__ import annotations

import json
import os
import shutil
import zipfile
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Callable

from ..paths import data_dir
from .downloader import DownloadControl, DownloadProgress, ResumableDownloader, file_is_valid
from .errors import (
    AllDownloadSourcesFailedError,
    InsufficientDiskSpaceError,
    ModelBrokenError,
    ModelDownloadCancelled,
    ModelInstallError,
    ModelManagerError,
    ModelNotInstalledError,
    ModelVerificationError,
)
from .manifest import ModelDefinition, ModelManifest


class ModelStatus(str, Enum):
    NOT_INSTALLED = "not_installed"
    CHECKING = "checking"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    VERIFYING = "verifying"
    INSTALLING = "installing"
    READY = "ready"
    UPDATE_AVAILABLE = "update_available"
    BROKEN = "broken"
    ERROR = "error"


ProgressCallback = Callable[[DownloadProgress], None]


class ModelManager:
    def __init__(self, root: Path | None = None, manifest_path: Path | None = None) -> None:
        self.root = Path(root or data_dir())
        self.models_root = self.root / "models"
        self.downloads_root = self.root / "downloads"
        self.models_root.mkdir(parents=True, exist_ok=True)
        self.downloads_root.mkdir(parents=True, exist_ok=True)
        resource = Path(__file__).resolve().parents[2] / "resources" / "model_manifest.json"
        self.manifest = ModelManifest.load(Path(manifest_path or resource))
        self.registry_path = self.models_root / "registry.json"
        self._registry = self._load_registry()
        self._downloader = ResumableDownloader()
        self._register_existing_models()

    def definition(self, model_id: str) -> ModelDefinition:
        return self.manifest.get(model_id)

    def get_size(self, model_id: str) -> int:
        return self.definition(model_id).size

    def get_installed_version(self, model_id: str) -> str | None:
        entry = self._registry.get(model_id, {})
        return str(entry.get("version")) if entry else None

    def get_status(self, model_id: str) -> ModelStatus:
        model = self.definition(model_id)
        path = self._find_existing_path(model)
        if path is not None:
            return ModelStatus.READY
        if self._registry.get(model_id, {}).get("status") == ModelStatus.READY.value:
            return ModelStatus.BROKEN
        return ModelStatus.NOT_INSTALLED

    def is_installed(self, model_id: str) -> bool:
        return self.get_status(model_id) == ModelStatus.READY

    def get_model_path(self, model_id: str) -> Path:
        model = self.definition(model_id)
        path = self._find_existing_path(model)
        if path is None:
            if self.get_status(model_id) == ModelStatus.BROKEN:
                raise ModelBrokenError(f"{model.display_name} 已损坏，请重新安装。")
            raise ModelNotInstalledError(f"{model.display_name} 尚未安装。")
        return path

    def download(
        self,
        model_id: str,
        progress: ProgressCallback | None = None,
        control: DownloadControl | None = None,
    ) -> Path:
        model = self.definition(model_id)
        control = control or DownloadControl()
        self._check_disk_space(model)
        download_dir = self.downloads_root / model_id
        failures: list[str] = []
        for source in model.sources:
            try:
                if progress:
                    progress(DownloadProgress(
                        self._downloaded_size(download_dir, model), model.size, 0.0, None,
                        source.name, f"正在连接 {source.name}…",
                    ))
                self._downloader.download(model, source, download_dir, progress, control)
                return self._install_from_directory(model, download_dir, progress, source.name)
            except ModelDownloadCancelled:
                raise
            except ModelManagerError as exc:
                failures.append(exc.details)
        raise AllDownloadSourcesFailedError(
            f"无法下载 {model.display_name}。请检查网络后重试，或从本地导入模型包。",
            "\n".join(failures),
        )

    def install_archive(
        self,
        model_id: str,
        archive: Path,
        progress: ProgressCallback | None = None,
        control: DownloadControl | None = None,
    ) -> Path:
        model = self.definition(model_id)
        archive = Path(archive)
        control = control or DownloadControl()
        if not zipfile.is_zipfile(archive):
            raise ModelInstallError("所选文件不是有效的模型 ZIP 安装包。")
        download_dir = self.downloads_root / model_id
        download_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as bundle:
            names = [
                PurePosixPath(name)
                for name in bundle.namelist()
                if not name.endswith("/") and "__MACOSX" not in PurePosixPath(name).parts
            ]
            copied = 0
            for item in model.files:
                control.checkpoint()
                expected = PurePosixPath(item.path)
                matches = [name for name in names if name == expected or str(name).endswith("/" + str(expected))]
                if not matches:
                    raise ModelInstallError(
                        "模型安装包与当前版本不兼容。",
                        f"Missing {item.path}",
                    )
                target = download_dir / item.path
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(str(matches[0])) as source, target.open("wb") as output:
                    while True:
                        control.checkpoint()
                        block = source.read(1024 * 1024)
                        if not block:
                            break
                        output.write(block)
                        copied += len(block)
                        if progress:
                            progress(DownloadProgress(
                                copied, model.size, 0.0, None, "本地文件", f"正在读取 {item.path}",
                            ))
        return self._install_from_directory(model, download_dir, progress, "本地文件")

    def verify(self, model_id: str) -> bool:
        model = self.definition(model_id)
        path = self.get_model_path(model_id)
        invalid = [item.path for item in model.files if not file_is_valid(path / item.path, item)]
        if invalid:
            raise ModelVerificationError(
                f"{model.display_name} 校验失败，请重新安装。",
                "Invalid files: " + ", ".join(invalid),
            )
        return True

    def delete(self, model_id: str) -> None:
        model = self.definition(model_id)
        target = self.root / model.install_dir
        if target.exists():
            shutil.rmtree(target)
        self._registry.pop(model_id, None)
        self._save_registry()

    def repair(self, model_id: str, progress: ProgressCallback | None = None) -> Path:
        return self.download(model_id, progress)

    def _install_from_directory(
        self,
        model: ModelDefinition,
        source_dir: Path,
        progress: ProgressCallback | None,
        source_name: str,
    ) -> Path:
        if progress:
            progress(DownloadProgress(model.size, model.size, 0.0, 0.0, source_name, "正在校验模型…"))
        invalid = [item.path for item in model.files if not file_is_valid(source_dir / item.path, item)]
        if invalid:
            raise ModelVerificationError(
                "模型文件校验失败，未修改现有模型。",
                "Invalid files: " + ", ".join(invalid),
            )

        target = self.root / model.install_dir
        staging = target.parent / f".{target.name}-installing"
        backup = target.parent / f".{target.name}-previous"
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True, exist_ok=True)
        try:
            if progress:
                progress(DownloadProgress(model.size, model.size, 0.0, 0.0, source_name, "正在安装模型…"))
            for item in model.files:
                destination = staging / item.path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_dir / item.path, destination)
            if backup.exists():
                shutil.rmtree(backup)
            if target.exists():
                os.replace(target, backup)
            os.replace(staging, target)
            if backup.exists():
                shutil.rmtree(backup)
        except Exception as exc:
            if not target.exists() and backup.exists():
                os.replace(backup, target)
            raise ModelInstallError(
                f"{model.display_name} 安装失败，原有模型未被破坏。",
                f"{type(exc).__name__}: {exc}",
            ) from exc

        self._registry[model.model_id] = {
            "version": model.version,
            "status": ModelStatus.READY.value,
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "path": model.install_dir,
        }
        self._save_registry()
        shutil.rmtree(source_dir, ignore_errors=True)
        return target

    def _check_disk_space(self, model: ModelDefinition) -> None:
        required = int(model.size * 2.1) + 64 * 1024 * 1024
        free = shutil.disk_usage(self.root).free
        if free < required:
            raise InsufficientDiskSpaceError(
                f"磁盘空间不足。安装 {model.display_name} 至少需要 {self._format_bytes(required)}，当前可用 {self._format_bytes(free)}。"
            )

    def _find_existing_path(self, model: ModelDefinition) -> Path | None:
        candidates = [self.root / model.install_dir, *(self.root / path for path in model.legacy_dirs)]
        for path in candidates:
            if all((path / item.path).is_file() and (path / item.path).stat().st_size == item.size for item in model.files):
                return path
        return None

    def _register_existing_models(self) -> None:
        changed = False
        for model_id, model in self.manifest.models.items():
            path = self._find_existing_path(model)
            if path is not None and model_id not in self._registry:
                self._registry[model_id] = {
                    "version": model.version,
                    "status": ModelStatus.READY.value,
                    "installed_at": datetime.now(timezone.utc).isoformat(),
                    "path": str(path.relative_to(self.root)),
                }
                changed = True
        if changed:
            self._save_registry()

    def _load_registry(self) -> dict:
        if not self.registry_path.exists():
            return {}
        try:
            payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_registry(self) -> None:
        temporary = self.registry_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(self._registry, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, self.registry_path)

    @staticmethod
    def _downloaded_size(path: Path, model: ModelDefinition) -> int:
        total = 0
        for item in model.files:
            final = path / item.path
            part = final.with_name(final.name + ".part")
            if final.exists():
                total += min(final.stat().st_size, item.size)
            elif part.exists():
                total += min(part.stat().st_size, item.size)
        return total

    @staticmethod
    def _format_bytes(value: int) -> str:
        amount = float(value)
        for unit in ("B", "KB", "MB", "GB"):
            if amount < 1024 or unit == "GB":
                return f"{amount:.1f} {unit}"
            amount /= 1024
        return f"{amount:.1f} GB"
