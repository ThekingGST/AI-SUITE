"""Rich chat message widget with Markdown and syntax highlighting."""

from __future__ import annotations
import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from markdown_it import MarkdownIt
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound

from pygments.util import ClassNotFound

from friday_ai.core.theme import THEME
from shared.logger import get_logger

LOG = get_logger("friday.chat_message")


def _highlight_code(code: str, name: str, attrs: dict) -> str:
    """Syntax highlight a code block using Pygments."""
    if not name:
        name = "text"
    try:
        lexer = get_lexer_by_name(name, stripall=True)
    except ClassNotFound:
        lexer = get_lexer_by_name("text", stripall=True)
        
    # Generate HTML with inline styles so QTextBrowser can render it easily
    formatter = HtmlFormatter(noclasses=True, style="monokai", cssclass="code-block")
    highlighted = highlight(code, lexer, formatter)
    
    # Wrap in our own styled container
    bg = THEME.bg_surface
    return f'<div style="background-color: {bg}; padding: 10px; border-radius: 4px; margin: 8px 0; font-family: monospace;">{highlighted}</div>'


# Initialize markdown parser with pygments highlighting
md = (
    MarkdownIt("commonmark")
    .enable("table")
    .enable("strikethrough")
)
md.options["highlight"] = _highlight_code


class ChatMessageWidget(QWidget):
    """A single message bubble in the AI chat."""

    def __init__(self, role: str, content: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.role = role
        self.raw_content = content
        self._build_ui()
        self.set_content(content)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(THEME.space_lg, THEME.space_lg, THEME.space_lg, THEME.space_lg)
        layout.setSpacing(THEME.space_md)

        # Header: Role + Timestamp
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self._role_label = QLabel()
        self._role_label.setStyleSheet(f"font-weight: bold; font-size: {THEME.font_size_sm}px;")
        
        self._time_label = QLabel(datetime.datetime.now().strftime("%H:%M"))
        self._time_label.setStyleSheet(f"color: {THEME.text_muted}; font-size: {THEME.font_size_xs}px;")
        
        header_layout.addWidget(self._role_label)
        header_layout.addStretch()
        header_layout.addWidget(self._time_label)
        layout.addLayout(header_layout)

        # Content
        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(True)
        self._browser.setFrameStyle(0)
        self._browser.setReadOnly(True)
        self._browser.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: transparent;
                color: {THEME.text_primary};
                font-size: {THEME.font_size_base}px;
                line-height: 1.5;
            }}
            a {{ color: {THEME.accent}; }}
        """)
        
        # Style based on role
        if self.role == "user":
            self._role_label.setText("YOU")
            self._role_label.setStyleSheet(f"color: {THEME.accent}; font-weight: bold; font-size: {THEME.font_size_sm}px;")
            self.setStyleSheet(f"background-color: {THEME.bg_base}; border-radius: {THEME.radius_md}px;")
        elif self.role == "error":
            self._role_label.setText("ERROR")
            self._role_label.setStyleSheet(f"color: #F87171; font-weight: bold; font-size: {THEME.font_size_sm}px;")
            self.setStyleSheet(f"background-color: {THEME.bg_surface}; border: 1px solid #F87171; border-radius: {THEME.radius_md}px;")
        elif self.role == "system":
            self._role_label.setText("SYSTEM")
            self._role_label.setStyleSheet(f"color: {THEME.text_muted}; font-weight: bold; font-size: {THEME.font_size_sm}px;")
            self.setStyleSheet(f"background-color: transparent;")
            self._browser.setStyleSheet(f"color: {THEME.text_secondary}; font-style: italic;")
        else:
            self._role_label.setText("FRIDAY")
            self._role_label.setStyleSheet(f"color: #34D399; font-weight: bold; font-size: {THEME.font_size_sm}px;")
            self.setStyleSheet(f"background-color: {THEME.bg_surface}; border-radius: {THEME.radius_md}px;")

        layout.addWidget(self._browser)
        
        # Adjust height to content
        self._browser.document().documentLayout().documentSizeChanged.connect(self._adjust_height)

    def set_content(self, content: str) -> None:
        """Update the message content."""
        self.raw_content = content
        
        # Parse markdown to HTML
        html = md.render(content)
        
        # Add some base CSS for the document
        base_html = f"""
        <html>
        <head>
        <style>
            body {{ font-family: {THEME.font_family}; padding: 0; margin: 0; }}
            code {{ background-color: {THEME.bg_base}; padding: 2px 4px; border-radius: 3px; font-family: {THEME.font_mono}; }}
            pre {{ margin: 0; padding: 0; }}
            p {{ margin-bottom: 10px; }}
        </style>
        </head>
        <body>{html}</body>
        </html>
        """
        self._browser.setHtml(base_html)

    def append_chunk(self, chunk: str) -> None:
        """Append a streaming chunk to the message."""
        try:
            self.raw_content += chunk
            self.set_content(self.raw_content)
            LOG.debug("ChatMessageWidget.append_chunk(): Appended chunk of length %d", len(chunk))
        except Exception as e:
            LOG.error("ChatMessageWidget.append_chunk(): Error updating UI: %s", e)

    def _adjust_height(self) -> None:
        """Adjust the widget height to fit the text browser content."""
        doc_height = self._browser.document().size().height()
        margins = self.layout().contentsMargins()
        header_height = self._role_label.sizeHint().height() + self.layout().spacing()
        
        total_height = doc_height + margins.top() + margins.bottom() + header_height
        self._browser.setMinimumHeight(int(doc_height))
        self._browser.setMaximumHeight(int(doc_height))
        self.setMinimumHeight(int(total_height))
