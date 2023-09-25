from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QWidget


class RankItem(QWidget):
    def __init__(
        self,
        nickname: str,
        score: int,
        prompt: Optional[str],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.widget = QWidget(parent)
        layout = QHBoxLayout()

        self.nickname = QLabel(nickname)

        self.score = QLabel(str(score))

        self.has_prompt = QCheckBox()
        self.has_prompt.setText("")
        if prompt:
            self.has_prompt.setChecked(True)

        layout.addWidget(self.nickname, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.score, 0, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.has_prompt, 0, Qt.AlignmentFlag.AlignRight)
        layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.setLayout(layout)
