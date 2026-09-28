from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable
from urllib.request import urlopen

from ..constants import CORE_LANGUAGE_CODES, LANGUAGE_CATALOG
from .paths import data_dir

ProgressCallback = Callable[[int, str], None]


class LanguagePackManager:
    """Manage optional language packs.

    The current NLLB/Whisper/RapidOCR runtimes are multilingual and shared between languages.
    A language pack therefore installs the language metadata, OCR hints, correction rules and
    glossary namespace rather than duplicating the large base models. The API intentionally keeps
    a download/install boundary so future releases can point a language to a remote package URL
    without changing the UI.
    """

    def __init__(self) -> None:
        self.root = data_dir() / "language_packs"
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "installed.json"
        self._installed = self._load()
        self._installed.update(CORE_LANGUAGE_CODES)
        self._save()

    def _load(self) -> set[str]:
        if not self.state_path.exists():
            return set()
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            return {str(x) for x in data.get("installed", []) if str(x) in LANGUAGE_CATALOG}
        except Exception:
            return set()

    def _save(self) -> None:
        self.state_path.write_text(
            json.dumps({"installed": sorted(self._installed)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def installed_codes(self) -> list[str]:
        return [code for code in LANGUAGE_CATALOG if code in self._installed]

    def is_installed(self, code: str) -> bool:
        return code in self._installed

    def catalog(self) -> list[dict]:
        result = []
        for code, info in LANGUAGE_CATALOG.items():
            result.append({"code": code, **info, "installed": code in self._installed})
        return result

    def install(self, code: str, progress: ProgressCallback | None = None) -> None:
        if code not in LANGUAGE_CATALOG:
            raise KeyError(code)
        if progress:
            progress(15, "准备语言包…")
        pack_dir = self.root / code
        pack_dir.mkdir(parents=True, exist_ok=True)
        info = dict(LANGUAGE_CATALOG[code])
        info["code"] = code
        info["format_version"] = 1
        info["shared_models"] = ["NLLB-200", "Whisper", "RapidOCR"]

        # Release builds can host tiny language-pack JSON files independently from the app by
        # setting SCREEN_TRANSLATOR_PACK_BASE_URL. Development/offline builds use the embedded
        # catalog as a fallback, so the language remains usable even before a public pack CDN is set.
        base_url = os.getenv("SCREEN_TRANSLATOR_PACK_BASE_URL", "").strip().rstrip("/")
        if base_url:
            try:
                if progress:
                    progress(35, "正在下载语言包配置…")
                with urlopen(f"{base_url}/{code}.json", timeout=15) as response:
                    remote = json.loads(response.read().decode("utf-8"))
                if isinstance(remote, dict):
                    info.update(remote)
            except Exception:
                if progress:
                    progress(45, "远程语言包不可用，使用内置兼容配置…")
        if progress:
            progress(65, "写入语言配置与 OCR / ASR 提示…")
        (pack_dir / "pack.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        self._installed.add(code)
        self._save()
        if progress:
            progress(100, "语言包已安装")

    def remove(self, code: str) -> None:
        if code in CORE_LANGUAGE_CODES:
            raise ValueError("核心语言包不能删除。")
        self._installed.discard(code)
        self._save()
        pack_dir = self.root / code
        if pack_dir.exists():
            for child in pack_dir.iterdir():
                try:
                    child.unlink()
                except OSError:
                    pass
            try:
                pack_dir.rmdir()
            except OSError:
                pass

    def label(self, code: str) -> str:
        return str(LANGUAGE_CATALOG.get(code, {}).get("label", code))

    def storage_summary(self) -> str:
        # The big multilingual models are shared, so optional packs are intentionally tiny.
        count = max(0, len(self._installed) - len(CORE_LANGUAGE_CODES))
        return f"已安装 {len(self._installed)} 种语言（扩展 {count}）· 大模型跨语言共享，不会为每个语言重复占用数百 MB"
