from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelFile:
    path: str
    size: int
    sha256: str


@dataclass(frozen=True)
class ModelSource:
    name: str
    base_url: str


@dataclass(frozen=True)
class ModelDefinition:
    model_id: str
    display_name: str
    version: str
    install_dir: str
    repo_id: str
    revision: str
    files: tuple[ModelFile, ...]
    sources: tuple[ModelSource, ...]
    legacy_dirs: tuple[str, ...] = ()

    @property
    def size(self) -> int:
        return sum(item.size for item in self.files)


class ModelManifest:
    def __init__(self, models: dict[str, ModelDefinition]) -> None:
        self.models = models

    @classmethod
    def load(cls, path: Path) -> "ModelManifest":
        payload = json.loads(path.read_text(encoding="utf-8"))
        models: dict[str, ModelDefinition] = {}
        for model_id, raw in payload["models"].items():
            files = tuple(ModelFile(**item) for item in raw["files"])
            sources = tuple(ModelSource(**item) for item in raw["sources"])
            models[model_id] = ModelDefinition(
                model_id=model_id,
                display_name=raw["display_name"],
                version=raw["version"],
                install_dir=raw["install_dir"],
                repo_id=raw["repo_id"],
                revision=raw["revision"],
                files=files,
                sources=sources,
                legacy_dirs=tuple(raw.get("legacy_dirs", ())),
            )
        return cls(models)

    def get(self, model_id: str) -> ModelDefinition:
        try:
            return self.models[model_id]
        except KeyError as exc:
            raise KeyError(f"Unknown model: {model_id}") from exc
