from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from ..core.model_manager import DownloadControl, DownloadProgress, ModelManager, ModelManagerError
from ..core.storage import format_bytes
from .assets import pixel_pixmap


class ModelRequirementDialog(QDialog):
    DOWNLOAD = 1
    IMPORT = 2

    def __init__(self, manager: ModelManager, model_id: str, parent=None) -> None:
        super().__init__(parent)
        model = manager.definition(model_id)
        self.choice = 0
        self.setWindowTitle("需要安装模型")
        self.setModal(True)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(pixel_pixmap("app_logo", 52))
        header.addWidget(icon)
        copy = QVBoxLayout()
        title = QLabel("需要安装" + ("翻译模型" if model_id == "translation-nllb" else "语音识别模型"))
        title.setObjectName("SectionTitle")
        copy.addWidget(title)
        name = QLabel(model.display_name)
        name.setObjectName("Muted")
        copy.addWidget(name)
        header.addLayout(copy, 1)
        layout.addLayout(header)

        details = QLabel(
            f"大小：{format_bytes(model.size)}\n"
            f"保存位置：{manager.root / model.install_dir}\n\n"
            "安装完成后可完全离线使用。下载只会在你确认后开始。"
        )
        details.setWordWrap(True)
        layout.addWidget(details)

        buttons = QHBoxLayout()
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        local = QPushButton("从本地 ZIP 安装")
        local.clicked.connect(lambda: self._finish(self.IMPORT))
        download = QPushButton("下载并继续")
        download.setObjectName("PrimaryButton")
        download.clicked.connect(lambda: self._finish(self.DOWNLOAD))
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(local)
        buttons.addWidget(download)
        layout.addLayout(buttons)

    def _finish(self, choice: int) -> None:
        self.choice = choice
        self.accept()


class ModelTaskSignals(QObject):
    progress = Signal(object)
    installed = Signal(str)
    failed = Signal(str, str)


class ModelTaskWorker(QRunnable):
    def __init__(
        self,
        manager: ModelManager,
        model_id: str,
        control: DownloadControl,
        archive: Path | None = None,
    ) -> None:
        super().__init__()
        self.manager = manager
        self.model_id = model_id
        self.control = control
        self.archive = archive
        self.signals = ModelTaskSignals()

    @Slot()
    def run(self) -> None:
        try:
            callback = lambda value: self.signals.progress.emit(value)
            if self.archive is None:
                path = self.manager.download(self.model_id, callback, self.control)
            else:
                path = self.manager.install_archive(self.model_id, self.archive, callback, self.control)
            self.signals.installed.emit(str(path))
        except ModelManagerError as exc:
            self.signals.failed.emit(exc.user_message, exc.details)
        except Exception as exc:
            self.signals.failed.emit(
                "模型安装失败，请重试或改用本地模型包。",
                f"{type(exc).__name__}: {exc}",
            )


class ModelDownloadDialog(QDialog):
    def __init__(
        self,
        manager: ModelManager,
        model_id: str,
        archive: Path | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.manager = manager
        self.model_id = model_id
        self.archive = archive
        self.control: DownloadControl | None = None
        self._running = False
        self._paused = False
        model = manager.definition(model_id)

        self.setWindowTitle("安装模型")
        self.setModal(True)
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        title = QLabel(model.display_name)
        title.setObjectName("SectionTitle")
        layout.addWidget(title)
        self.status = QLabel("正在准备…")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        layout.addWidget(self.progress)
        self.stats = QLabel()
        self.stats.setObjectName("Muted")
        layout.addWidget(self.stats)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(120)
        self.details.hide()
        layout.addWidget(self.details)

        buttons = QHBoxLayout()
        self.detail_button = QPushButton("查看详细错误")
        self.detail_button.clicked.connect(lambda: self.details.setVisible(not self.details.isVisible()))
        self.detail_button.hide()
        self.pause_button = QPushButton("暂停")
        self.pause_button.clicked.connect(self._toggle_pause)
        self.action_button = QPushButton("取消")
        self.action_button.clicked.connect(self._cancel_or_retry)
        buttons.addWidget(self.detail_button)
        buttons.addStretch(1)
        buttons.addWidget(self.pause_button)
        buttons.addWidget(self.action_button)
        layout.addLayout(buttons)
        QTimer.singleShot(0, self._start)

    def _start(self) -> None:
        self.control = DownloadControl()
        self._running = True
        self._paused = False
        self.progress.setValue(0)
        self.pause_button.setText("暂停")
        self.pause_button.setEnabled(True)
        self.action_button.setText("取消")
        self.detail_button.hide()
        self.details.hide()
        worker = ModelTaskWorker(self.manager, self.model_id, self.control, self.archive)
        worker.signals.progress.connect(self._on_progress)
        worker.signals.installed.connect(self._on_installed)
        worker.signals.failed.connect(self._on_failed)
        QThreadPool.globalInstance().start(worker)

    def _on_progress(self, value: DownloadProgress) -> None:
        total = max(1, value.total_bytes)
        self.progress.setValue(min(1000, int(value.downloaded_bytes * 1000 / total)))
        self.status.setText(value.message)
        speed = f"{format_bytes(int(value.speed))}/s" if value.speed > 0 else "--"
        eta = f"剩余约 {int(value.eta_seconds)} 秒" if value.eta_seconds is not None else ""
        self.stats.setText(
            f"{format_bytes(value.downloaded_bytes)} / {format_bytes(value.total_bytes)}  ·  "
            f"{speed}  ·  {eta}  ·  {value.source_name}"
        )

    def _on_installed(self, _path: str) -> None:
        self._running = False
        self.progress.setValue(1000)
        self.status.setText("模型已安装，可以离线使用。")
        self.pause_button.setEnabled(False)
        self.action_button.setText("完成")
        QTimer.singleShot(350, self.accept)

    def _on_failed(self, message: str, details: str) -> None:
        self._running = False
        self.status.setText(message)
        self.details.setPlainText(details)
        self.detail_button.show()
        self.pause_button.setEnabled(False)
        self.action_button.setText("重试")

    def _toggle_pause(self) -> None:
        if self.control is None or not self._running:
            return
        self._paused = not self._paused
        if self._paused:
            self.control.pause()
            self.pause_button.setText("继续")
            self.status.setText("下载已暂停。")
        else:
            self.control.resume()
            self.pause_button.setText("暂停")

    def _cancel_or_retry(self) -> None:
        if self._running:
            if self.control is not None:
                self.control.cancel()
            self.reject()
        elif self.action_button.text() == "重试":
            self._start()
        else:
            self.accept()

    def reject(self) -> None:
        if self._running and self.control is not None:
            self.control.cancel()
        elif self.manager.is_installed(self.model_id):
            self.accept()
            return
        super().reject()


def request_model(parent, manager: ModelManager, model_id: str) -> bool:
    requirement = ModelRequirementDialog(manager, model_id, parent)
    if requirement.exec() != QDialog.DialogCode.Accepted:
        return False
    archive = None
    if requirement.choice == ModelRequirementDialog.IMPORT:
        selected, _ = QFileDialog.getOpenFileName(parent, "选择模型 ZIP 安装包", "", "ZIP 文件 (*.zip)")
        if not selected:
            return False
        archive = Path(selected)
    dialog = ModelDownloadDialog(manager, model_id, archive, parent)
    return dialog.exec() == QDialog.DialogCode.Accepted and manager.is_installed(model_id)
