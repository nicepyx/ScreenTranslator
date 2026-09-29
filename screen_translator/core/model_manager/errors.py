from __future__ import annotations


class ModelManagerError(RuntimeError):
    def __init__(self, user_message: str, details: str = "") -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.details = details or user_message


class ModelNotInstalledError(ModelManagerError):
    pass


class ModelDownloadError(ModelManagerError):
    pass


class ModelVerificationError(ModelManagerError):
    pass


class ModelInstallError(ModelManagerError):
    pass


class ModelBrokenError(ModelManagerError):
    pass


class InsufficientDiskSpaceError(ModelManagerError):
    pass


class AllDownloadSourcesFailedError(ModelDownloadError):
    pass


class ModelDownloadCancelled(ModelManagerError):
    pass


def user_error_message(exc: Exception) -> str:
    if isinstance(exc, ModelManagerError):
        return exc.user_message
    return str(exc)
