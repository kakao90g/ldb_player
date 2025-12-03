import sys
import os
import requests
import logging
import time
import subprocess
from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFrame
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QIcon

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.FileHandler("output.log", mode='a'), logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger()

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

QSS_STYLE = """
QMainWindow, QDialog {
    background-color: #353535;
}
QFrame#centralFrame, QWidget#dialogFrame {
    background-color: #353535;
}
QWidget#titleBar {
    background-color: transparent;
}
QPushButton {
    background-color: #353535;
    border: none;
    border-radius: 16px;
    color: white;
}
QPushButton#okButton, QPushButton#cancelButton {
    width: 80px;
    height: 32px;
    border-radius: 16px;
}
QPushButton:hover {
    background-color: #252525;
    border: none;
}
QLabel {
    color: white;
}
QToolTip {
    background-color: #353535;
    color: white;
    border: 1px solid white;
    padding: 2px;
}
QLabel a, QLabel a:link, QLabel a:visited, QLabel a:hover, QLabel a:active {
    color: #4A90E2;
    text-decoration: none;
}
"""

class DialogBase(QDialog):
    def __init__(self, parent=None, title=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(resource_path("icons/tray_icon.png")))
        self.setWindowOpacity(0.9)
        self.dragging = False
        self.drag_position = QPoint()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        self.content_frame = QFrame()
        self.content_frame.setObjectName("dialogFrame")
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addWidget(self.content_frame)
        QTimer.singleShot(0, self.adjustSize)
        QTimer.singleShot(0, self.adjust_position)

    def adjust_position(self):
        screen = QApplication.primaryScreen().availableGeometry()
        window_rect = self.geometry()
        if window_rect.right() > screen.right():
            window_rect.moveRight(screen.right())
        if window_rect.bottom() > screen.bottom():
            window_rect.moveBottom(screen.bottom())
        if window_rect.left() < screen.left():
            window_rect.moveLeft(screen.left())
        if window_rect.top() < screen.top():
            window_rect.moveTop(screen.top())
        self.setGeometry(window_rect)

class MessageDialog(DialogBase):
    def __init__(self, parent, title, message):
        super().__init__(parent, title)
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(message_label)
        ok_button = QPushButton("OK")
        ok_button.setObjectName("okButton")
        ok_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        ok_button.setDefault(True)
        ok_button.setAutoDefault(True)
        ok_button.clicked.connect(self.accept)
        self.content_layout.addWidget(ok_button)

class ConfirmDialog(DialogBase):
    def __init__(self, parent, title, message):
        super().__init__(parent, title)
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(message_label)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        yes_button = QPushButton("Yes")
        yes_button.setObjectName("okButton")
        yes_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        yes_button.setDefault(True)
        yes_button.setAutoDefault(True)
        yes_button.clicked.connect(self.accept)
        no_button = QPushButton("No")
        no_button.setObjectName("cancelButton")
        no_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        no_button.clicked.connect(self.reject)
        button_layout.addWidget(yes_button)
        button_layout.addWidget(no_button)
        self.content_layout.addLayout(button_layout)

class LinkMessageDialog(DialogBase):
    def __init__(self, parent, title, message, link=None):
        super().__init__(parent, title)
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(message_label)
        if link:
            link_label = QLabel(f'<a href="{link}" style="color: #4A90E2; text-decoration: none;">{link}</a>')
            link_label.setTextFormat(Qt.TextFormat.RichText)
            link_label.setOpenExternalLinks(True)
            link_label.setWordWrap(True)
            link_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_layout.addWidget(link_label)
        ok_button = QPushButton("OK")
        ok_button.setObjectName("okButton")
        ok_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        ok_button.setDefault(True)
        ok_button.setAutoDefault(True)
        ok_button.clicked.connect(self.accept)
        self.content_layout.addWidget(ok_button)

def update_app(new_version):
    logger.info("Updater launched.")
    time.sleep(5)
    app = QApplication(sys.argv)
    app.setStyleSheet(QSS_STYLE)
    parent = None
    current_exe = os.path.join(os.path.dirname(sys.executable), "LDBPlayer.exe")
    github_link = "https://github.com/kakao90g/ldb_player/releases"
    def proceed():
        logger.info(f"Starting update to v{new_version}.")
        time.sleep(2)
        try:
            new_exe = os.path.join(os.path.dirname(current_exe), "LDBPlayer_new.exe")
            exe_url = f"https://github.com/kakao90g/ldb_player/releases/download/v{new_version}/LDBPlayer.exe"
            response = requests.get(exe_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30, stream=True)
            response.raise_for_status()
            with open(new_exe, "wb") as f:
                f.write(response.content)
            if os.path.getsize(new_exe) <= 0:
                raise ValueError("Downloaded file is empty")
            if os.path.exists(current_exe):
                os.remove(current_exe)
            os.rename(new_exe, current_exe)
            logger.info("Download successful, starting LDBPlayer.exe.")
            subprocess.Popen(current_exe)
        except Exception as e:
            logger.error(f"Update failed: {str(e)}")
            if os.path.exists(new_exe):
                os.remove(new_exe)
            dialog = LinkMessageDialog(parent, "Update Error",
                                "Download failed. Get it from:",
                                link=github_link)
            dialog.exec()
        finally:
            sys.exit(0)
    def on_no():
        dialog = LinkMessageDialog(parent, "Update",
                            "Please download manually from:",
                            link=github_link)
        dialog.exec()
    update_dialog = ConfirmDialog(parent, "Updater",
                                  f"LDB Player will update to v{new_version}. Proceed?")
    if update_dialog.exec() == QDialog.DialogCode.Accepted:
        proceed()
    else:
        on_no()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        app = QApplication(sys.argv)
        app.setStyleSheet(QSS_STYLE)
        dialog = MessageDialog(None, "Updater Error",
                              "Invalid arguments. Please run via LDBPlayer.exe.")
        dialog.exec()
        sys.exit(1)
    new_version = sys.argv[1]
    update_app(new_version)