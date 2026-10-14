"""Model selection dropdown for the AI Panel."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal as Signal
from PyQt5.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from friday_ai.core.signals import signals
from friday_ai.core.theme import THEME
from friday_ai.services.provider_manager import ProviderManager


class ModelSelector(QWidget):
    """Dropdown to select the active AI provider and model."""

    def __init__(self, provider_manager: ProviderManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.pm = provider_manager
        self._build_ui()
        self.refresh_models()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(THEME.space_sm)

        # Status indicator
        self._status = QLabel("●")
        self._status.setStyleSheet(f"color: {THEME.text_muted};")
        layout.addWidget(self._status)

        # Dropdown
        self._combo = QComboBox()
        self._combo.setStyleSheet(f"""
            QComboBox {{
                background: {THEME.bg_surface};
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_default};
                border-radius: {THEME.radius_sm}px;
                padding: 2px 8px;
            }}
            QComboBox::drop-down {{ border: none; }}
        """)
        self._combo.currentIndexChanged.connect(self._on_selection_changed)
        layout.addWidget(self._combo, stretch=1)
        
        # Refresh button
        self._btn_refresh = QPushButton("↻")
        self._btn_refresh.setFixedSize(24, 24)
        self._btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {THEME.text_muted};
                border: none;
            }}
            QPushButton:hover {{ color: {THEME.accent}; }}
        """)
        self._btn_refresh.clicked.connect(self.refresh_models)
        layout.addWidget(self._btn_refresh)

    def refresh_models(self) -> None:
        """Fetch models from ProviderManager and populate the combo box."""
        self._combo.blockSignals(True)
        self._combo.clear()
        
        models_by_provider = self.pm.get_all_models()
        status = self.pm.provider_status()
        
        # Track if any provider is online
        any_online = False
        
        # Populate
        idx = 0
        target_idx = 0
        current_p = self.pm.current_provider
        current_m = self.pm.current_model
        
        # Map provider keys to display names
        category_map = {
            "ollama": "Local",
            "openrouter": "Cloud (Free)"
        }
        
        for provider_name, models in models_by_provider.items():
            is_online = status.get(provider_name, False)
            if is_online:
                any_online = True
                
            # Add a category header (disabled item)
            cat_name = category_map.get(provider_name, provider_name.capitalize())
            status_text = " (Online)" if is_online else " (Offline)"
            self._combo.addItem(f"--- {cat_name}{status_text} ---", userData=None)
            idx += 1
            
            # Show friendly message if no free models are available
            if not models:
                self._combo.addItem("  (No models available)", userData=None)
                idx += 1
                continue
            
            for m in models:
                # UserData is a tuple of (provider, model_id)
                self._combo.addItem(f"  {m.name}", userData=(provider_name, m.id))
                if provider_name == current_p and m.id == current_m:
                    target_idx = idx
                idx += 1
                
        self._combo.setCurrentIndex(target_idx)
        self._combo.blockSignals(False)
        
        if any_online:
            self._status.setStyleSheet("color: #34D399;") # Green
        else:
            self._status.setStyleSheet("color: #F87171;") # Red

    def _on_selection_changed(self, index: int) -> None:
        data = self._combo.itemData(index)
        if data:
            provider, model = data
            signals.ai_model_changed.emit(provider, model)
            
            status = self.pm.provider_status()
            if status.get(provider, False):
                self._status.setStyleSheet("color: #34D399;")
            else:
                self._status.setStyleSheet("color: #F87171;")
