from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QProgressBar, QPushButton, QPlainTextEdit, QVBoxLayout, QWidget

from ...constants import PERFORMANCE_PROFILE_ORDER, PERFORMANCE_PROFILES
from ...core.performance import profile_requirements_text


class PreservedPagesMixin:
    """Performance controls retain their behavior and use the shared pixel skin."""

    def _build_performance_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        live_group = QGroupBox("实时资源占用")
        live_grid = QGridLayout(live_group)
        self.system_cpu_bar = QProgressBar()
        self.system_cpu_bar.setRange(0, 100)
        self.system_ram_bar = QProgressBar()
        self.system_ram_bar.setRange(0, 100)
        self.process_cpu_label = QLabel("应用 CPU：--")
        self.process_ram_label = QLabel("应用内存：--")
        live_grid.addWidget(QLabel("系统 CPU"), 0, 0)
        live_grid.addWidget(self.system_cpu_bar, 0, 1)
        live_grid.addWidget(QLabel("系统内存"), 1, 0)
        live_grid.addWidget(self.system_ram_bar, 1, 1)
        live_grid.addWidget(self.process_cpu_label, 2, 0, 1, 2)
        live_grid.addWidget(self.process_ram_label, 3, 0, 1, 2)
        self.runtime_backend_label = QLabel("推理后端：等待模型加载")
        self.runtime_backend_label.setWordWrap(True)
        live_grid.addWidget(self.runtime_backend_label, 4, 0, 1, 2)
        layout.addWidget(live_group)

        detect_group = QGroupBox("本机检测与自动推荐")
        detect_layout = QVBoxLayout(detect_group)
        self.hardware_text = QPlainTextEdit()
        self.hardware_text.setReadOnly(True)
        self.hardware_text.setMaximumHeight(130)
        detect_layout.addWidget(self.hardware_text)

        row = QHBoxLayout()
        row.addWidget(QLabel("性能档位"))
        self.performance_combo = QComboBox()
        self.performance_combo.addItem("自动推荐", "auto")
        for key in PERFORMANCE_PROFILE_ORDER:
            self.performance_combo.addItem(PERFORMANCE_PROFILES[key]["label"], key)
        self.performance_combo.addItem("自定义", "custom")
        self.performance_combo.currentIndexChanged.connect(self._performance_profile_changed)
        row.addWidget(self.performance_combo, 1)
        detect_btn = QPushButton("重新检测硬件")
        detect_btn.clicked.connect(self._redetect_hardware)
        row.addWidget(detect_btn)
        detect_layout.addLayout(row)

        self.performance_recommend_label = QLabel()
        self.performance_recommend_label.setWordWrap(True)
        self.performance_recommend_label.setStyleSheet("font-weight:600;")
        detect_layout.addWidget(self.performance_recommend_label)
        self.performance_details_label = QLabel()
        self.performance_details_label.setWordWrap(True)
        self.performance_details_label.setStyleSheet("color:#666;")
        detect_layout.addWidget(self.performance_details_label)
        layout.addWidget(detect_group)

        req_group = QGroupBox("Windows / macOS 档位建议")
        req_layout = QVBoxLayout(req_group)
        requirements = QPlainTextEdit()
        requirements.setReadOnly(True)
        requirements.setPlainText(profile_requirements_text())
        requirements.setMinimumHeight(210)
        req_layout.addWidget(requirements)
        layout.addWidget(req_group)
        layout.addStretch(1)
        return tab


