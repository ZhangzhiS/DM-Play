from loguru import logger
from PySide6.QtCore import QSize, Qt, QThreadPool, QTimer, Slot
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QLabel, QListWidgetItem

from dmplay.components.dymj_ui import Ui_Form
from dmplay.components.msg_box import MessageBox
from dmplay.components.rank_item import RankItem
from dmplay.core.config import config
from dmplay.core.window_base import WindowBase
from dmplay.core.windows_manager import window_manager
from dmplay.utils.download_thread import DownloadThread
from dmplay.utils.dy_mj_worker import WebSocketWorker
from dmplay.utils.item_enum import SendMsg


class DYMJWindow(WindowBase):
    def __init__(self) -> None:
        super().__init__()

        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.ui.closeButton.clicked.connect(self.custom_close)
        self.ui.connectButton.clicked.connect(self.change_connect_status)

        self.ui.topBar.mousePressEvent = self.on_mouse_press
        self.ui.topBar.mouseMoveEvent = self.on_mouse_move
        window_manager.show_dymj.connect(self.custom_show)

        # self.show()

        self.message_box = MessageBox(self)
        self.message_box.setModal(False)
        # self.message_box.setButtonText(1, "确认(3秒后自动关闭)")

        self.ui.progressBar.setRange(0, 100)
        self.ui.progressBar.setValue(100)

        self.worker = None
        self.threadpool = QThreadPool()
        self.tips_timer = QTimer()
        self.tips_timer.timeout.connect(self.tips_countdown)
        self.task_timer = QTimer()
        self.task_timer.timeout.connect(self.start_refresh_generate_task)
        self.connect_button_timer = QTimer()
        self.connect_button_timer.timeout.connect(self.enable_connect_button)

        self.msg_box_timer = QTimer()

        self.rank_list = []
        self.websocket_status = False
        self.task_status = False
        self.live_room_id = ""

        self.preview_img_url = None
        self.generate_task_id = None
        self.generate_progress = 0
        self.countdown_count = 0

    def custom_show(self):
        self.show()
        if not config.LIVE_URL_ID:
            self.show_alt_msg("未配置抖音直播链接的ID")
            self.ui.connectButton.setDisabled(True)
        else:
            self.ui.connectButton.setDisabled(False)

    def show_alt_msg(self, msg):
        self.message_box.msg.setText(msg)
        self.message_box.show()
        self.msg_box_timer.setSingleShot(True)
        self.msg_box_timer.timeout.connect(self.message_box.hide)
        self.msg_box_timer.start(3000)

    def custom_close(self):
        if self.task_timer.isActive():
            self.task_timer.stop()
        if self.tips_timer.isActive():
            self.tips_timer.stop()
        if self.worker:
            self.worker.close_websocket()
        self.threadpool.clear()
        self.close_websocket_worker()
        self.close()
        window_manager.show_home.emit()

    def start_websocket_worker(self):
        # 将信号连接到更新UI的槽函数
        # if not self.worker:
        self.worker = WebSocketWorker()
        self.worker.signals.refresh_rank_list.connect(self.parse_refresh_rank_list)
        self.worker.signals.refresh_room_info.connect(self.parse_refresh_live_room_info)
        self.worker.signals.do_alt_msg.connect(self.parse_alt_msg)
        self.worker.signals.refresh_generating_info.connect(
            self.parse_refresh_generate_task
        )
        self.worker.signals.refresh_start_task.connect(self.parse_start_task)
        self.worker.signals.on_open_connect.connect(self.parse_on_connect)

        # 启动子线程
        self.threadpool.start(self.worker)

    def close_websocket_worker(self):
        if self.worker:
            self.worker.close_websocket()
            self.threadpool.clear()
        if self.tips_timer.isActive():
            self.tips_timer.stop()
            self.countdown_count = 0
        if self.task_timer.isActive():
            self.task_timer.stop()

        self.websocket_status = False
        self.task_status = False
        icon = QIcon()
        icon.addFile(":/icons/icons/wifi-sharp-red.png", QSize())
        self.ui.connectButton.setIcon(icon)
        self.ui.tips_content.setText("已断开")
        self.ui.connectButton.setText("点击连接")

    def enable_connect_button(self):
        logger.info("set enabled connect button")
        self.ui.connectButton.setEnabled(True)

    def change_connect_status(self):
        """
        修改连接状态
        """
        if self.websocket_status:
            self.close_websocket_worker()
        else:
            self.start_websocket_worker()
        self.ui.connectButton.setEnabled(False)
        logger.info("set disenabled connect button")
        self.connect_button_timer.setSingleShot(True)
        self.connect_button_timer.start(2000)

    def start_generate_task(self, data):
        send_info = {
            "type": SendMsg.START_GENERATE.value,
            "nickname": data["nickname"],
            "prompt": data["prompt"],
            "user_id": data["user_id"],
            "sys_user_id": config.SYS_USER_ID,
            "room_id": self.live_room_id,
            "task_id": "start",
        }
        if self.worker:
            self.worker.send(send_info)

    def start_refresh_generate_task(self):
        if self.generate_task_id:
            data = {
                "task_id": self.generate_task_id,
                "type": SendMsg.REFRESH_GENERATE_INFO.value,
            }
            if self.worker:
                self.worker.send(data)

    @Slot(bool)
    def parse_on_connect(self, status):
        logger.info(status)
        self.websocket_status = status
        if status:
            icon = QIcon()
            icon.addFile(":/icons/icons/wifi-sharp-green.png", QSize())
            self.ui.connectButton.setIcon(icon)
            self.ui.connectButton.setText("已连接")
            self.ui.tips_content.setText("已连接")
        else:
            self.close_websocket_worker()

    @Slot(dict)
    def parse_start_task(self, data):
        self.generate_task_id = data.get("task_id")
        self.ui.previewInfo.clear()
        nickname = data.get("nickname")
        self.ui.previewInfo.addItem(QListWidgetItem(nickname))
        prompt = data.get("prompt")
        self.ui.previewInfo.addItem(QListWidgetItem(prompt))
        self.generate_task_id = data.get("task_id")
        self.ui.progressBar.setValue(0)
        self.task_timer.start(5000)
        self.task_status = True

    @Slot(dict)
    def parse_refresh_generate_task(self, data: dict):
        image_url = data.get("image_url", "")
        task_id = data.get("task_id")
        status = data.get("status")
        name = f"{data.get('nickname')}-{task_id}"
        if image_url != self.preview_img_url:
            self.preview_img_url = image_url
            if image_url:
                download_thread = DownloadThread(self.preview_img_url, status, name)
                download_thread.signal.finished.connect(self.render_preview_img)
                download_thread.signal.history.connect(self.render_history)
                self.threadpool.start(download_thread)
                self.preview_img_url = image_url
        if self.generate_task_id is not None and task_id == self.generate_task_id:
            # 新任务，刷新昵称，进度条和提示词的显示
            # self.generate_task_id = data.get("task_id")
            self.ui.progressBar.setFormat("生成中....")
            self.ui.tips_content.setText("正在生成中")
        if data.get("progress") != self.generate_progress:
            self.ui.progressBar.setValue(data.get("progress", 0))
            self.generate_progress = data.get("progress")
        if data.get("status") == 1:
            logger.info("generate_task done")
            self.task_timer.stop()
            self.ui.progressBar.setFormat("已完成")
            self.countdown_count = 60
            self.tips_timer.start(1000)

    @Slot(bytes)
    def render_preview_img(self, content: bytes):
        width = self.ui.image.width()
        pixmap = QPixmap()
        pixmap.loadFromData(content)
        pixmap.scaled(
            QSize(width, width),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.ui.image.setPixmap(pixmap)
        self.ui.image.setScaledContents(True)
        self.ui.image.setSizeIncrement(
            QSize(width, width),
        )
        self.ui.image.setFixedWidth(width)
        self.ui.image.setFixedHeight(width)

    @Slot(bytes)
    def render_history(self, content):
        label = QLabel()
        width = self.ui.historyList.width()
        pixmap = QPixmap()
        pixmap.loadFromData(content)

        pixmap.scaled(
            QSize(width, width),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setScaledContents(True)
        history_item = QListWidgetItem(self.ui.historyList)
        history_item.setSizeHint(QSize(width, width))
        self.ui.historyList.addItem(history_item)
        self.ui.historyList.setItemWidget(history_item, label)

    def tips_countdown(self):
        if self.countdown_count > 0:
            self.countdown_count -= 1
            self.ui.tips_content.setText(f"预览倒计时：{self.countdown_count}")
        else:
            self.tips_timer.stop()
            if self.rank_list:
                self.start_generate_task(self.rank_list[0])
            else:
                self.task_status = False

    def set_next_generate_ui(self):
        if self.rank_list:
            self.ui.nextUser.setText(self.rank_list[0].get("nickname", ""))
            self.ui.textBrowser.setText(self.rank_list[0].get("prompt", ""))

    @Slot(list)
    def parse_refresh_rank_list(self, new_list: list):
        if new_list and self.task_status is False:
            self.start_generate_task(new_list[0])
            new_list.pop(0)
            # self.set_next_generate_ui()
        # elif new_list and self.task_status:
        self.rank_list = new_list
        self.set_next_generate_ui()
        self.ui.rankScoreList.clear()
        for item in new_list:
            rend_item = RankItem(
                nickname=item.get("nickname"),
                score=item.get("rank_score"),
                prompt=item.get("prompt"),
            )
            list_item = QListWidgetItem(self.ui.rankScoreList)
            list_item.setSizeHint(rend_item.sizeHint())
            self.ui.rankScoreList.addItem(list_item)
            self.ui.rankScoreList.setItemWidget(list_item, rend_item)

    @Slot(str)
    def parse_alt_msg(self, text):
        self.show_alt_msg(text)

    @Slot(dict)
    def parse_refresh_live_room_info(self, data):
        """
        更新直播间信息
        """
        self.live_room_id = data.get("live_room_id")
        nickname = data.get("live_room_anchor_nickname")
        self.ui.nickname.setText(nickname)
        title = data.get("live_room_title")
        self.ui.title.setText(title)
        self.ui.countNum.display(data.get("socia_count", -1))
        if data.get("socia_count", -1) == -1:
            self.show_alt_msg("请先开启直播💋")
            self.close_websocket_worker()

        # anchor_ava = data.get("live_room_anchor_ava", "")
        # if anchor_ava:
        #     download_thread = DownloadThread(anchor_ava)
        #     download_thread.finished.connect(self.render_ava)
        #     download_thread.start()

    def render_ava(self, content):
        """更新头像"""
        pixmap = QPixmap()
        pixmap.loadFromData(content)
        self.ui.avaImg.setPixmap(pixmap)