from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class RuleItem(QWidget):
    def __init__(
        self,
        rule_str: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.widget = QWidget(parent)
        # self.widget.setFixedWidth(100)
        layout = QHBoxLayout()
        layout.setContentsMargins(0,0,0,0)

        rule_text = QLabel(rule_str)
        rule_text.setWordWrap(True)
        font = QFont()
        font.setPixelSize(16)
        rule_text.setFont(font)

        del_button = QPushButton()
        del_button.setText("删除")

        layout.addWidget(rule_text)
        layout.addWidget(del_button)
        # layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.setLayout(layout)
