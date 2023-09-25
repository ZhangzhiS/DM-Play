import os
from loguru import logger
import requests

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from dmplay.core.config import config


class DownLoadSignal(QObject):
    finished = Signal(bytes)
    history = Signal(bytes)


class DownloadThread(QRunnable):
    def __init__(self, url, status, name) -> None:
        super().__init__()
        self.url = url
        self.signal = DownLoadSignal()
        self.task_status = status
        self.filename = name

    @Slot()
    def run(self):
        res = self.download()
        if res:
            if self.task_status == 1:
                save_path = os.path.join(config.DOWNLOAD_PATH, f"{self.filename}.png")
                logger.info(save_path)
                with open(save_path, "wb") as f:
                    f.write(res)
                self.signal.history.emit(res)
            self.signal.finished.emit(res)

    def download(self):
        response = requests.get(self.url)
        if response.status_code == 200:
            return response.content
