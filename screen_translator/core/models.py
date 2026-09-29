from pathlib import Path
from .model_manager import ModelManager


class TranslationModelManager:
    """Compatibility adapter for the translation provider.

    Downloads are initiated by the UI through ModelManager. Inference code can only request an
    already installed local path.
    """

    MODEL_ID = "translation-nllb"

    def __init__(self, manager: ModelManager | None = None) -> None:
        self.manager = manager or ModelManager()

    def is_ready(self) -> bool:
        return self.manager.is_installed(self.MODEL_ID)

    def local_path(self) -> Path:
        return self.manager.get_model_path(self.MODEL_ID)
