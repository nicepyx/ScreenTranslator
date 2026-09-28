import os
from pathlib import Path
from typing import Callable, Optional

from huggingface_hub import snapshot_download

from ..constants import DEFAULT_TRANSLATION_MODEL_REPO, MODEL_SUBDIR
from .paths import models_dir

StatusCallback = Optional[Callable[[str], None]]


class TranslationModelManager:
    REQUIRED_FILES = (
        "model.bin",
        "config.json",
        "shared_vocabulary.json",
        "sentencepiece.bpe.model",
    )

    def __init__(self) -> None:
        self.repo_id = os.getenv(
            "SCREEN_TRANSLATOR_MODEL_REPO", DEFAULT_TRANSLATION_MODEL_REPO
        )
        self.local_dir = models_dir() / MODEL_SUBDIR

    def is_ready(self) -> bool:
        return all((self.local_dir / name).exists() for name in self.REQUIRED_FILES)

    def ensure_downloaded(self, status: StatusCallback = None) -> Path:
        if self.is_ready():
            return self.local_dir

        self.local_dir.mkdir(parents=True, exist_ok=True)
        if status:
            status("首次使用：正在下载约 650MB 的本地翻译模型…")

        snapshot_download(
            repo_id=self.repo_id,
            local_dir=str(self.local_dir),
            allow_patterns=list(self.REQUIRED_FILES) + ["*.json", "*.model"],
        )

        missing = [
            name for name in self.REQUIRED_FILES if not (self.local_dir / name).exists()
        ]
        if missing:
            raise RuntimeError("翻译模型文件不完整：" + ", ".join(missing))
        return self.local_dir
