import sys
import os
import json
import vlc
import win32gui
import win32con
import winreg
import win32api
from win32api import GetSystemMetrics
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QSystemTrayIcon, QMenu, QFileDialog,
    QDialog, QCheckBox, QLabel, QListWidget, QFrame, QLineEdit, QTableWidget, QTableWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, QEvent, QPoint, QSize, QRectF
from PyQt6.QtGui import QIcon, QAction, QPainter, QPainterPath, QColor
import pathlib
import ctypes
import random
import urllib.parse
import logging
import PyQt6.sip as sip

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

logging.basicConfig(level=logging.CRITICAL)

VERSION = "0.9.8"

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
QPushButton#playButton, QPushButton#stopButton, QPushButton#prevButton, QPushButton#nextButton,
QPushButton#repeatButton, QPushButton#playlistButton, QPushButton#muteButton,
QPushButton#settingsButton, QPushButton#aboutButton {
    width: 48px;
    height: 48px;
    border-radius: 24px;
}
QPushButton#okButton, QPushButton#cancelButton, QPushButton#addButton, QPushButton#removeButton,
QPushButton#moveUpButton, QPushButton#moveDownButton, QPushButton#shuffleButton, QPushButton#clearButton,
QPushButton#saveButton, QPushButton#loadButton, QPushButton#manageButton, QPushButton#renameButton,
QPushButton#deleteButton, QPushButton#playSelectedButton, QPushButton#hotkeysButton {
    width: 80px;
    height: 32px;
    border-radius: 16px;
}
QPushButton:hover {
    background-color: #252525;
    border: none;
}
QPushButton#minimizeButton, QPushButton#closeButton, QPushButton#dialogCloseButton {
    background-color: transparent;
    width: 24px;
    height: 24px;
    border-radius: 12px;
}
QPushButton#minimizeButton:hover, QPushButton#closeButton:hover, QPushButton#dialogCloseButton:hover {
    background-color: #252525;
    border: none;
}
QSlider::groove:horizontal {
    height: 4px;
    background: #666666;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background-color: white;
    width: 16px;
    height: 16px;
    border-radius: 8px;
    margin: -6px 0;
}
QSlider::sub-page:horizontal {
    background: #F0F0F0;
    border-radius: 2px;
}
QSlider#volumeSlider::groove:horizontal {
    height: 3px;
    background: #666666;
    border-radius: 1.5px;
}
QSlider#volumeSlider::handle:horizontal {
    background-color: white;
    width: 12px;
    height: 12px;
    border-radius: 6px;
    margin: -4.5px 0;
}
QSlider#volumeSlider::sub-page:horizontal {
    background: #F0F0F0;
    border-radius: 1.5px;
}
QLabel {
    color: white;
}
QCheckBox {
    background-color: #353535;
    color: white;
}
QListWidget, QInputDialog, QLineEdit {
    background-color: #252525;
    color: white;
}
QToolTip {
    background-color: #353535;
    color: white;
    border: 1px solid white;
    padding: 2px;
}
QLabel#supportLabel a, QLabel#supportLabel a:link, QLabel#supportLabel a:visited, QLabel#supportLabel a:hover, QLabel#supportLabel a:active {
    color: #4A90E2;
    text-decoration: none;
}
QTableWidget {
    background-color: #252525;
    color: white;
}
QTableWidget::item {
    background-color: #252525;
    color: white;
}
"""
QSS_STYLE += """
QPushButton#fullscreenButton {
    background-color: transparent;
    width: 48px;
    height: 48px;
    border-radius: 24px;
}
QPushButton#fullscreenButton:hover {
    background-color: #252525;
    border: none;
}
QWidget#fullscreenControlDialog {
    background-color: #353535;
}
QPushButton#exitFullscreenButton {
    background-color: transparent;
    width: 48px;
    height: 48px;
    border-radius: 24px;
}
QPushButton#exitFullscreenButton:hover {
    background-color: #252525;
    border: none;
}
"""

class CustomEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())
    def __init__(self, video_name, index):
        super().__init__(self.EVENT_TYPE)
        self.video_name = video_name
        self.index = index

class DialogBase(QDialog):
    def __init__(self, parent, title):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowOpacity(0.9)
        self.setWindowIcon(QIcon(resource_path("icons/tray_icon.png")))
        self.dragging = False
        self.drag_position = QPoint()
        self.list_widget = None
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        self.content_frame = QFrame()
        self.content_frame.setObjectName("dialogFrame")
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addWidget(self.content_frame)
        self.installEventFilter(self)
        QTimer.singleShot(0, self.adjustSize)
        QTimer.singleShot(0, self.adjust_position)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            focused_widget = QApplication.focusWidget()
            if not isinstance(focused_widget, (QLineEdit, QListWidget)):
                self.accept()
        elif event.key() == Qt.Key.Key_Escape:
            self.reject()
        super().keyPressEvent(event)

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

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            if self.list_widget and obj is self.list_widget.viewport():
                item = self.list_widget.itemAt(event.pos())
                if not item:
                    self.list_widget.clearSelection()
            elif obj is self:
                widget = QApplication.widgetAt(event.globalPosition().toPoint())
                if widget is self or not widget or not isinstance(widget, (QPushButton, QListWidget)):
                    if self.list_widget:
                        self.list_widget.clearSelection()
                    focused_widget = QApplication.focusWidget()
                    if focused_widget:
                        focused_widget.clearFocus()
        return super().eventFilter(obj, event)

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

class SavePlaylistDialog(DialogBase):
    def __init__(self, parent):
        super().__init__(parent, "Save Playlist")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter playlist name")
        self.content_layout.addWidget(self.name_input)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        save_button = QPushButton("Save")
        save_button.setObjectName("saveButton")
        save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        save_button.setDefault(True)
        save_button.setAutoDefault(True)
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("cancelButton")
        cancel_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        self.content_layout.addLayout(button_layout)
        self.name_input.returnPressed.connect(self.accept)
        QTimer.singleShot(0, lambda: self.name_input.setFocus())

    def accept(self):
        if not self.name_input.text().strip():
            return
        super().accept()

    def get_name(self):
        return self.name_input.text().strip()

class RenamePlaylistDialog(DialogBase):
    def __init__(self, parent, default_text):
        super().__init__(parent, "Rename Playlist")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter new playlist name")
        self.name_input.setText(default_text)
        self.content_layout.addWidget(self.name_input)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        ok_button = QPushButton("OK")
        ok_button.setObjectName("okButton")
        ok_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        ok_button.setDefault(True)
        ok_button.setAutoDefault(True)
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("cancelButton")
        cancel_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        self.content_layout.addLayout(button_layout)
        self.name_input.returnPressed.connect(self.accept)
        QTimer.singleShot(0, lambda: self.name_input.setFocus())
        QTimer.singleShot(0, lambda: self.name_input.selectAll())

    def get_name(self):
        return self.name_input.text()

class HotkeysDialog(DialogBase):
    def __init__(self, parent):
        super().__init__(parent, "Hotkeys")
        self.hotkeys_table = QTableWidget()
        self.hotkeys_table.setColumnCount(2)
        self.hotkeys_table.horizontalHeader().setVisible(False)
        self.hotkeys_table.verticalHeader().setVisible(False)
        self.hotkeys_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.hotkeys_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.content_layout.addWidget(self.hotkeys_table)
        self.populate_hotkeys()
        ok_button = QPushButton("OK")
        ok_button.setObjectName("okButton")
        ok_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        ok_button.setDefault(True)
        ok_button.setAutoDefault(True)
        ok_button.clicked.connect(self.accept)
        self.content_layout.addWidget(ok_button)
        QTimer.singleShot(0, lambda: self.hotkeys_table.setCurrentCell(-1, -1))
        QTimer.singleShot(0, lambda: self.hotkeys_table.setFocus())

    def populate_hotkeys(self):
        hotkeys = [
            ("Global Hotkeys", ""),
            ("Space", "Play/Pause"),
            ("Left", "Seek back 10s"),
            ("Right", "Seek forward 10s"),
            ("Up", "Volume up"),
            ("Down", "Volume down"),
            ("Q", "Playlist"),
            ("S", "Stop"),
            ("P", "Previous"),
            ("N", "Next"),
            ("L", "Loop"),
            ("M", "Mute"),
            ("F12", "Settings"),
            ("F1", "About"),
            ("Ctrl+F4", "Quit"),
            ("", ""),
            ("Playlist Hotkeys", ""),
            ("Ctrl+N", "Add"),
            ("Del", "Remove"),
            ("Ctrl+U", "Move up"),
            ("Ctrl+D", "Move down"),
            ("Ctrl+P", "Play selected"),
            ("Ctrl+R", "Shuffle"),
            ("Ctrl+E", "Clear"),
            ("Ctrl+S", "Save"),
            ("Ctrl+O", "Load"),
            ("Ctrl+M", "Manage"),
            ("", ""),
            ("Playlist Manager Hotkeys", ""),
            ("Ctrl+R", "Rename"),
            ("Del", "Delete"),
            ("", ""),
            ("Settings Hotkeys", ""),
            ("A", "Toggle autostart"),
            ("H", "Hotkeys")
        ]
        self.hotkeys_table.setRowCount(len(hotkeys))
        for row, (hotkey, function) in enumerate(hotkeys):
            self.hotkeys_table.setItem(row, 0, QTableWidgetItem(hotkey))
            self.hotkeys_table.setItem(row, 1, QTableWidgetItem(function))
        self.hotkeys_table.resizeColumnsToContents()

class SettingsDialog(DialogBase):
    def __init__(self, parent):
        super().__init__(parent, "Settings")
        self.parent = parent
        self.autostart_cb = QCheckBox("Autostart on system startup (A)")
        self.autostart_cb.setChecked(parent.is_autostart_enabled())
        self.autostart_cb.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.content_layout.addWidget(self.autostart_cb)
        self.hotkeys_button = QPushButton("Hotkeys")
        self.hotkeys_button.setObjectName("hotkeysButton")
        self.hotkeys_button.setToolTip("Hotkeys (H)")
        self.hotkeys_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.hotkeys_button.clicked.connect(self.open_hotkeys)
        self.content_layout.addWidget(self.hotkeys_button)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        ok_button = QPushButton("OK")
        ok_button.setObjectName("okButton")
        ok_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        ok_button.setDefault(True)
        ok_button.setAutoDefault(True)
        ok_button.clicked.connect(self.handle_ok)
        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("cancelButton")
        cancel_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        self.content_layout.addLayout(button_layout)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.handle_ok()
        elif event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() == Qt.Key.Key_A:
            self.autostart_cb.setChecked(not self.autostart_cb.isChecked())
        elif event.key() == Qt.Key.Key_H:
            self.open_hotkeys()
        super().keyPressEvent(event)

    def handle_ok(self):
        autostart_enabled = self.autostart_cb.isChecked()
        autostart_changed = autostart_enabled != self.parent.is_autostart_enabled()

        if autostart_changed:
            self.parent.toggle_autostart(autostart_enabled)

        self.accept()

    def open_hotkeys(self):
        dialog = HotkeysDialog(self)
        dialog.exec()

class AboutDialog(DialogBase):
    def __init__(self, parent):
        super().__init__(parent, "About")
        info_label = QLabel(f"LDB Player\nVersion {VERSION}\nLicense: MIT\nDeveloped by @kakao90g")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(info_label)
        credits_label = QLabel(
            'Credits and Acknowledgments:<br>'
            '- Powered by VLC media player (libvlc) from VideoLAN: <a href="https://www.videolan.org/vlc/" style="color: #4A90E2; text-decoration: none;">https://www.videolan.org/vlc/</a><br>'
            '- Built with PyQt6 from Riverbank Computing: <a href="https://www.riverbankcomputing.com/software/pyqt/" style="color: #4A90E2; text-decoration: none;">https://www.riverbankcomputing.com/software/pyqt/</a><br>'
            '- Utilizes Windows APIs via pywin32 for system integration<br>'
            '- Other dependencies: Python standard libraries (sys, os, json, etc.), vlc.py bindings, and more'
        )
        credits_label.setTextFormat(Qt.TextFormat.RichText)
        credits_label.setObjectName("creditsLabel")
        credits_label.setOpenExternalLinks(True)
        credits_label.setWordWrap(True)
        credits_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(credits_label)
        support_label = QLabel(
            'Support the project:<br>'
            '- GitHub: <a href="https://github.com/kakao90g" style="color: #4A90E2; text-decoration: none;">https://github.com/kakao90g</a><br>'
            '- PayPal: <a href="https://paypal.me/kakao90g" style="color: #4A90E2; text-decoration: none;">https://paypal.me/kakao90g</a>'
        )
        support_label.setTextFormat(Qt.TextFormat.RichText)
        support_label.setObjectName("supportLabel")
        support_label.setOpenExternalLinks(True)
        support_label.setWordWrap(True)
        support_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(support_label)
        community_label = QLabel(
            'Join the community:<br>'
            '- Discord: <a href="https://discord.gg/EBqnchP9" style="color: #4A90E2; text-decoration: none;">https://discord.gg/EBqnchP9</a>'
        )
        community_label.setTextFormat(Qt.TextFormat.RichText)
        community_label.setObjectName("communityLabel")
        community_label.setOpenExternalLinks(True)
        community_label.setWordWrap(True)
        community_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(community_label)
        ok_button = QPushButton("OK")
        ok_button.setObjectName("okButton")
        ok_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        ok_button.setDefault(True)
        ok_button.setAutoDefault(True)
        ok_button.clicked.connect(self.accept)
        self.content_layout.addWidget(ok_button)

class LoadPlaylistDialog(DialogBase):
    def __init__(self, parent, playlist_dir):
        super().__init__(parent, "Load Playlist")
        self.playlist_dir = playlist_dir
        self.selected_file = None
        self.playlist_list = QListWidget()
        self.list_widget = self.playlist_list
        self.playlist_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.playlist_list.viewport().installEventFilter(self)
        self.update_playlist_list()
        self.playlist_list.itemDoubleClicked.connect(self.accept)
        self.content_layout.addWidget(self.playlist_list)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        load_button = QPushButton("Load")
        load_button.setObjectName("loadButton")
        load_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        load_button.setDefault(True)
        load_button.setAutoDefault(True)
        load_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("cancelButton")
        cancel_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(load_button)
        button_layout.addWidget(cancel_button)
        self.content_layout.addLayout(button_layout)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.playlist_list.selectedItems():
                self.accept()
        elif event.key() == Qt.Key.Key_Escape:
            self.reject()
        super().keyPressEvent(event)

    def update_playlist_list(self):
        selected_row = self.playlist_list.currentRow()
        self.playlist_list.clear()
        try:
            for file in os.listdir(self.playlist_dir):
                if file.endswith('.json'):
                    display_name = os.path.splitext(file)[0]
                    self.playlist_list.addItem(display_name)
            if selected_row >= 0 and selected_row < self.playlist_list.count():
                self.playlist_list.setCurrentRow(selected_row)
                self.playlist_list.setFocus()
        except FileNotFoundError:
            os.makedirs(self.playlist_dir, exist_ok=True)

    def accept(self):
        if self.playlist_list.selectedItems():
            selected = self.playlist_list.currentItem()
            self.selected_file = os.path.join(self.playlist_dir, selected.text() + '.json')
            super().accept()
        else:
            return

    def get_selected_file(self):
        return self.selected_file

class PlaylistManager(DialogBase):
    def __init__(self, parent, playlist_dir):
        super().__init__(parent, "Playlist Manager")
        self.parent = parent
        self.playlist_dir = playlist_dir
        self.playlist_list = QListWidget()
        self.list_widget = self.playlist_list
        self.playlist_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.playlist_list.viewport().installEventFilter(self)
        self.update_playlist_list()
        self.playlist_list.clearSelection()
        self.content_layout.addWidget(self.playlist_list)
        button_layout1 = QHBoxLayout()
        button_layout1.setSpacing(10)
        rename_button = QPushButton("Rename")
        rename_button.setObjectName("renameButton")
        rename_button.setToolTip("Rename (Ctrl+R)")
        rename_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        rename_button.clicked.connect(self.rename_playlist)
        delete_button = QPushButton("Delete")
        delete_button.setObjectName("deleteButton")
        delete_button.setToolTip("Delete (Del)")
        delete_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        delete_button.clicked.connect(self.delete_playlist)
        button_layout1.addWidget(rename_button)
        button_layout1.addWidget(delete_button)
        self.content_layout.addLayout(button_layout1)
        button_layout2 = QHBoxLayout()
        button_layout2.setSpacing(10)
        ok_button = QPushButton("OK")
        ok_button.setObjectName("okButton")
        ok_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        ok_button.setDefault(True)
        ok_button.setAutoDefault(True)
        ok_button.clicked.connect(self.accept)
        button_layout2.addWidget(ok_button)
        self.content_layout.addLayout(button_layout2)

    def keyPressEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_R:
            self.rename_playlist()
        elif event.key() == Qt.Key.Key_Delete:
            self.delete_playlist()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accept()
        elif event.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)

    def update_playlist_list(self):
        selected_row = self.playlist_list.currentRow()
        self.playlist_list.clear()
        try:
            for file in os.listdir(self.playlist_dir):
                if file.endswith('.json'):
                    display_name = os.path.splitext(file)[0]
                    self.playlist_list.addItem(display_name)
            if selected_row >= 0 and selected_row < self.playlist_list.count():
                self.playlist_list.setCurrentRow(selected_row)
                self.playlist_list.setFocus()
        except FileNotFoundError:
            os.makedirs(self.playlist_dir, exist_ok=True)

    def rename_playlist(self):
        if self.playlist_list.count() == 0 or not self.playlist_list.selectedItems():
            return
        selected = self.playlist_list.currentItem()
        selected_row = self.playlist_list.currentRow()
        if selected:
            old_name = selected.text()
            dialog = RenamePlaylistDialog(self, old_name)
            result = dialog.exec()
            if result == QDialog.DialogCode.Accepted:
                new_name = dialog.get_name()
                if new_name:
                    new_name = new_name + '.json' if not new_name.endswith('.json') else new_name
                    try:
                        os.rename(
                            os.path.join(self.playlist_dir, old_name + '.json'),
                            os.path.join(self.playlist_dir, new_name)
                        )
                        self.update_playlist_list()
                        if self.playlist_list.count() > 0:
                            new_row = min(selected_row, self.playlist_list.count() - 1)
                            self.playlist_list.setCurrentRow(new_row)
                            self.playlist_list.setFocus()
                    except Exception as e:
                        dialog = MessageDialog(self, "Error", f"Failed to rename playlist: {str(e)}")
                        dialog.exec()
            else:
                if selected_row >= 0 and selected_row < self.playlist_list.count():
                    self.playlist_list.setCurrentRow(selected_row)
                    self.playlist_list.setFocus()

    def delete_playlist(self):
        if self.playlist_list.count() == 0 or not self.playlist_list.selectedItems():
            return
        selected = self.playlist_list.currentItem()
        selected_row = self.playlist_list.currentRow()
        if selected:
            dialog = ConfirmDialog(self, "Confirm Delete", f"Are you sure you want to delete {selected.text()}?")
            result = dialog.exec()
            if result == QDialog.DialogCode.Accepted:
                try:
                    os.remove(os.path.join(self.playlist_dir, selected.text() + '.json'))
                    self.update_playlist_list()
                    if self.playlist_list.count() > 0:
                        new_row = min(selected_row, self.playlist_list.count() - 1)
                        self.playlist_list.setCurrentRow(new_row)
                        self.playlist_list.setFocus()
                except Exception as e:
                    dialog = MessageDialog(self, "Error", f"Failed to delete playlist: {str(e)}")
                    dialog.exec()
            else:
                if selected_row >= 0 and selected_row < self.playlist_list.count():
                    self.playlist_list.setCurrentRow(selected_row)
                    self.playlist_list.setFocus()

    def accept(self):
        super().accept()

class PlaylistDialog(DialogBase):
    def __init__(self, parent):
        super().__init__(parent, "Playlist")
        self.setModal(True)
        self.parent = parent
        self.temp_playlist = self.parent.playlist.copy()
        self.setAcceptDrops(True)
        self.playlist_widget = QListWidget()
        self.list_widget = self.playlist_widget
        self.playlist_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.playlist_widget.viewport().installEventFilter(self)
        self.update_playlist_display()
        self.playlist_widget.clearSelection()
        self.playlist_widget.itemDoubleClicked.connect(self.play_selected)
        self.content_layout.addWidget(self.playlist_widget)
        button_layout1 = QHBoxLayout()
        button_layout1.setSpacing(10)
        self.add_button = QPushButton("Add")
        self.add_button.setObjectName("addButton")
        self.add_button.setToolTip("Add Videos (Ctrl+N)")
        self.add_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.add_button.clicked.connect(self.add_files)
        self.remove_button = QPushButton("Remove")
        self.remove_button.setObjectName("removeButton")
        self.remove_button.setToolTip("Remove (Del)")
        self.remove_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.remove_button.clicked.connect(self.remove_file)
        self.move_up_button = QPushButton("Move Up")
        self.move_up_button.setObjectName("moveUpButton")
        self.move_up_button.setToolTip("Move Up (Ctrl+U)")
        self.move_up_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.move_up_button.clicked.connect(self.move_up)
        self.move_down_button = QPushButton("Move Down")
        self.move_down_button.setObjectName("moveDownButton")
        self.move_down_button.setToolTip("Move Down (Ctrl+D)")
        self.move_down_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.move_down_button.clicked.connect(self.move_down)
        self.play_selected_button = QPushButton()
        self.play_selected_button.setObjectName("playSelectedButton")
        self.play_selected_button.setIcon(QIcon(resource_path("icons/play_icon.png")))
        self.play_selected_button.setToolTip("Play Selected (Ctrl+P)")
        self.play_selected_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.play_selected_button.clicked.connect(self.play_selected)
        button_layout1.addWidget(self.add_button)
        button_layout1.addWidget(self.remove_button)
        button_layout1.addWidget(self.move_up_button)
        button_layout1.addWidget(self.move_down_button)
        button_layout1.addWidget(self.play_selected_button)
        self.content_layout.addLayout(button_layout1)
        button_layout2 = QHBoxLayout()
        button_layout2.setSpacing(10)
        self.shuffle_button = QPushButton("Shuffle")
        self.shuffle_button.setObjectName("shuffleButton")
        self.shuffle_button.setToolTip("Shuffle (Ctrl+R)")
        self.shuffle_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.shuffle_button.clicked.connect(self.shuffle_playlist)
        self.clear_button = QPushButton("Clear")
        self.clear_button.setObjectName("clearButton")
        self.clear_button.setToolTip("Clear (Ctrl+E)")
        self.clear_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.clear_button.clicked.connect(self.clear_playlist)
        self.save_button = QPushButton("Save")
        self.save_button.setObjectName("saveButton")
        self.save_button.setToolTip("Save (Ctrl+S)")
        self.save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.save_button.clicked.connect(self.save_playlist)
        self.load_button = QPushButton("Load")
        self.load_button.setObjectName("loadButton")
        self.load_button.setToolTip("Load (Ctrl+O)")
        self.load_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.load_button.clicked.connect(self.load_playlist)
        self.manage_button = QPushButton("Manage")
        self.manage_button.setObjectName("manageButton")
        self.manage_button.setToolTip("Manage (Ctrl+M)")
        self.manage_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.manage_button.clicked.connect(self.open_playlist_manager)
        button_layout2.addWidget(self.shuffle_button)
        button_layout2.addWidget(self.clear_button)
        button_layout2.addWidget(self.save_button)
        button_layout2.addWidget(self.load_button)
        button_layout2.addWidget(self.manage_button)
        self.content_layout.addLayout(button_layout2)
        button_layout3 = QHBoxLayout()
        button_layout3.setSpacing(10)
        self.ok_button = QPushButton("OK")
        self.ok_button.setObjectName("okButton")
        self.ok_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ok_button.setDefault(True)
        self.ok_button.setAutoDefault(True)
        self.ok_button.clicked.connect(self.handle_ok)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cancel_button.clicked.connect(self.reject)
        button_layout3.addWidget(self.ok_button)
        button_layout3.addWidget(self.cancel_button)
        self.content_layout.addLayout(button_layout3)

    def handle_ok(self):
        if self.playlist_widget.selectedItems():
            self.play_selected()
        else:
            self.accept()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.playlist_widget.selectedItems():
                self.play_selected()
            else:
                self.accept()
        elif event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_N:
            self.add_files()
        elif event.key() == Qt.Key.Key_Delete:
            self.remove_file()
        elif event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_U:
            self.move_up()
        elif event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_D:
            self.move_down()
        elif event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_P:
            self.play_selected()
        elif event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_R:
            self.shuffle_playlist()
        elif event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_E:
            self.clear_playlist()
        elif event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_S:
            self.save_playlist()
        elif event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_O:
            self.load_playlist()
        elif event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_M:
            self.open_playlist_manager()
        else:
            super().keyPressEvent(event)

    def update_playlist_display(self):
        selected_row = self.playlist_widget.currentRow()
        has_selection = bool(self.playlist_widget.selectedItems())
        self.playlist_widget.clear()
        for i, file in enumerate(self.temp_playlist, start=1):
            filename = os.path.basename(file)
            directory = os.path.dirname(file)
            self.playlist_widget.addItem(f"{i}. {filename} ({directory})")
        if has_selection and selected_row >= 0 and selected_row < len(self.temp_playlist):
            self.playlist_widget.setCurrentRow(selected_row)
            self.playlist_widget.setFocus()
        self.adjustSize()

    def is_duplicate_file(self, new_file, existing_files):
        new_name = os.path.basename(new_file)
        new_dir = os.path.dirname(new_file)
        for existing_file in existing_files:
            existing_name = os.path.basename(existing_file)
            existing_dir = os.path.dirname(existing_file)
            if new_name == existing_name and new_dir == existing_dir:
                return True
        return False

    def add_files(self):
        selected_row = self.playlist_widget.currentRow()
        default_dir = self.parent.last_video_dir if self.parent.last_video_dir else os.path.join(self.parent.config_dir, 'playlists')
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Add Videos",
            default_dir,
            "Video Files (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm *.mpeg *.mpg *.m4v)"
        )
        if files:
            self.parent.last_video_dir = os.path.dirname(files[0])
            self.parent.save_config()
            new_files = [f for f in files if not self.is_duplicate_file(f, self.temp_playlist)]
            self.temp_playlist.extend(new_files)
            self.update_playlist_display()
        else:
            if self.playlist_widget.selectedItems() and selected_row >= 0 and selected_row < len(self.temp_playlist):
                self.update_playlist_display()
                self.playlist_widget.setCurrentRow(selected_row)
                self.playlist_widget.setFocus()

    def remove_file(self):
        if not self.temp_playlist or not self.playlist_widget.selectedItems():
            return
        selected = self.playlist_widget.currentRow()
        if selected >= 0:
            self.temp_playlist.pop(selected)
            self.update_playlist_display()
            if self.temp_playlist:
                new_row = min(selected, len(self.temp_playlist) - 1)
                self.playlist_widget.setCurrentRow(new_row)
                self.playlist_widget.setFocus()

    def move_up(self):
        if not self.temp_playlist or not self.playlist_widget.selectedItems():
            return
        selected = self.playlist_widget.currentRow()
        if selected > 0:
            self.temp_playlist[selected], self.temp_playlist[selected - 1] = self.temp_playlist[selected - 1], self.temp_playlist[selected]
            self.update_playlist_display()
            self.playlist_widget.setCurrentRow(selected - 1)
            self.playlist_widget.setFocus()

    def move_down(self):
        if not self.temp_playlist or not self.playlist_widget.selectedItems():
            return
        selected = self.playlist_widget.currentRow()
        if selected >= 0 and selected < len(self.temp_playlist) - 1:
            self.temp_playlist[selected], self.temp_playlist[selected + 1] = self.temp_playlist[selected + 1], self.temp_playlist[selected]
            self.update_playlist_display()
            self.playlist_widget.setCurrentRow(selected + 1)
            self.playlist_widget.setFocus()

    def shuffle_playlist(self):
        random.shuffle(self.temp_playlist)
        self.update_playlist_display()

    def clear_playlist(self):
        self.temp_playlist = []
        self.update_playlist_display()

    def save_playlist(self):
        if not self.temp_playlist:
            dialog = MessageDialog(self, "Save Playlist", "No videos in playlist to save.")
            dialog.exec()
            return
        selected_row = self.playlist_widget.currentRow()
        dialog = SavePlaylistDialog(self)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            name = dialog.get_name()
            if name:
                playlist_dir = os.path.join(self.parent.config_dir, 'playlists')
                os.makedirs(playlist_dir, exist_ok=True)
                file_path = os.path.join(playlist_dir, name + '.json' if not name.endswith('.json') else name)
                if os.path.exists(file_path):
                    confirm_dialog = ConfirmDialog(self, "Confirm Overwrite", f"Playlist '{name}' already exists. Overwrite?")
                    confirm_result = confirm_dialog.exec()
                    if confirm_result != QDialog.DialogCode.Accepted:
                        if self.playlist_widget.selectedItems() and selected_row >= 0 and selected_row < len(self.temp_playlist):
                            self.update_playlist_display()
                            self.playlist_widget.setCurrentRow(selected_row)
                            self.playlist_widget.setFocus()
                        return
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(self.temp_playlist, f)
                    dialog = MessageDialog(self, "Success", "Playlist saved successfully.")
                    dialog.exec()
                except Exception as e:
                    dialog = MessageDialog(self, "Error", f"Failed to save playlist: {str(e)}")
                    dialog.exec()
        if self.playlist_widget.selectedItems() and selected_row >= 0 and selected_row < len(self.temp_playlist):
            self.update_playlist_display()
            self.playlist_widget.setCurrentRow(selected_row)
            self.playlist_widget.setFocus()

    def load_playlist(self):
        selected_row = self.playlist_widget.currentRow()
        playlist_dir = os.path.join(self.parent.config_dir, 'playlists')
        dialog = LoadPlaylistDialog(self, playlist_dir)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            file = dialog.get_selected_file()
            if file:
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        self.temp_playlist = json.load(f)
                        self.temp_playlist = [f for f in self.temp_playlist if os.path.exists(f)]
                    self.update_playlist_display()
                except Exception as e:
                    dialog = MessageDialog(self, "Error", f"Failed to load playlist: {str(e)}")
                    dialog.exec()
        else:
            if self.playlist_widget.selectedItems() and selected_row >= 0 and selected_row < len(self.temp_playlist):
                self.update_playlist_display()
                self.playlist_widget.setCurrentRow(selected_row)
                self.playlist_widget.setFocus()

    def open_playlist_manager(self):
        selected_row = self.playlist_widget.currentRow()
        playlist_dir = os.path.join(self.parent.config_dir, 'playlists')
        dialog = PlaylistManager(self, playlist_dir)
        dialog.exec()
        if self.playlist_widget.selectedItems() and selected_row >= 0 and selected_row < len(self.temp_playlist):
            self.update_playlist_display()
            self.playlist_widget.setCurrentRow(selected_row)
            self.playlist_widget.setFocus()

    def play_selected(self):
        if not self.temp_playlist or not self.playlist_widget.selectedItems():
            return
        selected = self.playlist_widget.currentRow()
        self.parent.playlist = self.temp_playlist.copy()
        self.parent.original_playlist = self.temp_playlist.copy()
        self.parent.save_config()
        self.parent.load_playlist()
        self.parent.current_video_index = selected
        if not hasattr(self.parent, 'video_window') or not self.parent.video_window or sip.isdeleted(self.parent.video_window):
            self.parent.setup_video_window(is_fullscreen=self.parent.is_fullscreen)
        self.parent.video_window.show()
        self.parent.list_player.play_item_at_index(selected)
        self.parent.play_pause_button.setIcon(QIcon(resource_path("icons/pause_icon.png")))
        self.parent.play_pause_button.setToolTip("Pause (Space)")
        video_name = os.path.basename(self.temp_playlist[selected])
        self.parent.current_video_label.setText(self.parent.truncate_label_text(video_name))
        QTimer.singleShot(100, self.parent.ensure_playing_and_set_audio)
        self.parent.skip_audio_poll = True
        self.accept()

    def accept(self):
        current_video = (self.parent.playlist[self.parent.current_video_index]
                        if self.parent.playlist and 0 <= self.parent.current_video_index < len(self.parent.playlist)
                        else None)
        self.parent.playlist = self.temp_playlist.copy()
        self.parent.original_playlist = self.temp_playlist.copy()
        self.parent.save_config()
        self.parent.load_playlist()

        if not self.temp_playlist:
            self.parent.stop()
            self.parent.current_video_label.setText(self.parent.truncate_label_text("Playlist is empty"))
        elif current_video and current_video in self.temp_playlist:
            new_index = self.temp_playlist.index(current_video)
            self.parent.current_video_index = new_index
            if not hasattr(self.parent, 'video_window') or not self.parent.video_window or sip.isdeleted(self.parent.video_window):
                self.parent.setup_video_window(is_fullscreen=self.parent.is_fullscreen)
            self.parent.video_window.show()
            self.parent.list_player.play_item_at_index(new_index)
            self.parent.play_pause_button.setIcon(QIcon(resource_path("icons/pause_icon.png")))
            self.parent.play_pause_button.setToolTip("Pause (Space)")
            video_name = os.path.basename(self.temp_playlist[new_index])
            self.parent.current_video_label.setText(self.parent.truncate_label_text(video_name))
            if not self.parent.skip_audio_poll:
                QTimer.singleShot(100, self.parent.ensure_playing_and_set_audio)
        else:
            self.parent.current_video_index = 0
            if not hasattr(self.parent, 'video_window') or not self.parent.video_window or sip.isdeleted(self.parent.video_window):
                self.parent.setup_video_window(is_fullscreen=self.parent.is_fullscreen)
            self.parent.video_window.show()
            self.parent.list_player.play_item_at_index(0)
            self.parent.play_pause_button.setIcon(QIcon(resource_path("icons/pause_icon.png")))
            self.parent.play_pause_button.setToolTip("Pause (Space)")
            video_name = os.path.basename(self.temp_playlist[0]) if self.temp_playlist else "Playlist is empty"
            self.parent.current_video_label.setText(self.parent.truncate_label_text(video_name))
            if not self.parent.skip_audio_poll:
                QTimer.singleShot(100, self.parent.ensure_playing_and_set_audio)
        self.parent.skip_audio_poll = False
        super().accept()

    def reject(self):
        super().reject()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            supported_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mpeg', '.mpg', '.m4v')
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if file_path.lower().endswith(supported_extensions):
                        event.acceptProposedAction()
                        return
        event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        supported_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mpeg', '.mpg', '.m4v')
        files = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                file_path = url.toLocalFile()
                if file_path.lower().endswith(supported_extensions):
                    files.append(file_path)
        if files:
            self.parent.last_video_dir = os.path.dirname(files[0])
            self.parent.save_config()
            new_files = [f for f in files if not self.is_duplicate_file(f, self.temp_playlist)]
            self.temp_playlist.extend(new_files)
            self.update_playlist_display()
            event.acceptProposedAction()
        else:
            event.ignore()

class FullscreenControlDialog(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("fullscreenControlDialog")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(0.9)
        self.setWindowIcon(QIcon(resource_path("icons/tray_icon.png")))
        self.parent = parent
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)
        self.is_visible = False
        self.initial_show = False
        self.init_ui()
        self.adjust_position()

    def show_dialog(self):
        if not self.is_visible:
            self.is_visible = True
            self.initial_show = True
            self.adjust_position()
            self.show()
            self.raise_()
            QTimer.singleShot(3000, self.start_hide_timer)

    def start_hide_timer(self):
        self.initial_show = False
        self.reset_hide_timer()

    def hide(self):
        if self.is_visible:
            self.is_visible = False
            self.initial_show = False
            super().hide()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        main_layout.addSpacing(10)
        video_layout = QHBoxLayout()
        video_layout.setSpacing(10)
        self.current_video_label = QLabel(self.parent.current_video_label.text())
        self.current_video_label.setFixedWidth(400)
        self.current_video_label.setMinimumHeight(32)
        video_layout.addWidget(self.current_video_label)
        main_layout.addWidget(self.current_video_label)
        main_layout.addSpacing(10)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(1000)
        self.slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        def slider_mouse_press_event(event):
            if event.button() == Qt.MouseButton.LeftButton and self.parent.player.get_state() in (vlc.State.Playing, vlc.State.Paused):
                slider_width = self.slider.width()
                click_x = event.position().x()
                value_range = 1000 - 0
                new_value = 0 + int((click_x / slider_width) * value_range)
                new_value = max(0, min(1000, new_value))
                handle_width = 16
                current_value = self.slider.value()
                handle_pos = (current_value / value_range) * slider_width
                handle_rect = QRectF(handle_pos - handle_width / 2, 0, handle_width, self.slider.height())
                self.slider.setValue(new_value)
                self.parent.seek(new_value)
                QSlider.mousePressEvent(self.slider, event)
            else:
                QSlider.mousePressEvent(self.slider, event)

        def slider_wheel_event(event):
            if self.parent.player.get_state() in (vlc.State.Playing, vlc.State.Paused):
                delta = event.angleDelta().y()
                current_time = self.parent.player.get_time()
                jump_ms = 10000
                new_time = current_time + (jump_ms if delta > 0 else -jump_ms)
                new_time = max(0, min(new_time, self.parent.player.get_length()))
                self.parent.player.set_time(new_time)
                event.accept()

        def handle_slider_pressed():
            if self.parent.player.get_state() == vlc.State.Playing:
                self.parent.was_playing_before_drag = True
                self.parent.list_player.pause()
                self.parent.is_paused = True
            else:
                self.parent.was_playing_before_drag = False

        def handle_slider_released():
            if hasattr(self.parent, 'was_playing_before_drag') and self.parent.was_playing_before_drag:
                self.parent.list_player.play()
                self.parent.is_paused = False
                QTimer.singleShot(100, self.parent.ensure_playing_and_set_audio)
            self.parent.was_playing_before_drag = False

        self.slider.mousePressEvent = slider_mouse_press_event
        self.slider.wheelEvent = slider_wheel_event
        self.slider.sliderPressed.connect(handle_slider_pressed)
        self.slider.sliderReleased.connect(handle_slider_released)
        self.slider.sliderMoved.connect(self.parent.seek)
        main_layout.addWidget(self.slider)
        control_layout = QHBoxLayout()
        control_layout.setSpacing(10)
        self.playlist_button = QPushButton()
        self.playlist_button.setObjectName("playlistButton")
        self.playlist_button.setFixedSize(48, 48)
        self.playlist_button.setIcon(QIcon(resource_path("icons/playlist_icon.png")))
        self.playlist_button.setToolTip("Playlist (Q)")
        self.playlist_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.playlist_button.clicked.connect(self.parent.open_playlist)
        control_layout.addWidget(self.playlist_button)
        self.play_pause_button = QPushButton()
        self.play_pause_button.setObjectName("playButton")
        self.play_pause_button.setFixedSize(48, 48)
        self.play_pause_button.setIcon(QIcon(resource_path("icons/play_icon.png")))
        self.play_pause_button.setToolTip("Play (Space)")
        self.play_pause_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.play_pause_button.clicked.connect(self.parent.play_pause)
        control_layout.addWidget(self.play_pause_button)
        self.stop_button = QPushButton()
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setFixedSize(48, 48)
        self.stop_button.setIcon(QIcon(resource_path("icons/stop_icon.png")))
        self.stop_button.setToolTip("Stop (S)")
        self.stop_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.stop_button.clicked.connect(self.parent.stop)
        control_layout.addWidget(self.stop_button)
        self.prev_button = QPushButton()
        self.prev_button.setObjectName("prevButton")
        self.prev_button.setFixedSize(48, 48)
        self.prev_button.setIcon(QIcon(resource_path("icons/prev_icon.png")))
        self.prev_button.setToolTip("Previous (P)")
        self.prev_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.prev_button.clicked.connect(self.parent.play_previous)
        control_layout.addWidget(self.prev_button)
        self.next_button = QPushButton()
        self.next_button.setObjectName("nextButton")
        self.next_button.setFixedSize(48, 48)
        self.next_button.setIcon(QIcon(resource_path("icons/next_icon.png")))
        self.next_button.setToolTip("Next (N)")
        self.next_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.next_button.clicked.connect(self.parent.play_next)
        control_layout.addWidget(self.next_button)
        self.repeat_button = QPushButton()
        self.repeat_button.setObjectName("repeatButton")
        self.repeat_button.setFixedSize(48, 48)
        self.repeat_button.setIcon(QIcon(resource_path(f"icons/repeat_{self.parent.repeat_mode}_icon.png")))
        self.repeat_button.setToolTip("Loop (L)")
        self.repeat_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.repeat_button.clicked.connect(lambda: self.parent.toggle_repeat(None))
        control_layout.addWidget(self.repeat_button)
        self.mute_button = QPushButton()
        self.mute_button.setObjectName("muteButton")
        self.mute_button.setFixedSize(48, 48)
        self.mute_button.setIcon(QIcon(resource_path("icons/mute_icon.png" if self.parent.is_muted else "icons/unmute_icon.png")))
        self.mute_button.setToolTip("Mute (M)")
        self.mute_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.mute_button.clicked.connect(self.parent.toggle_mute)
        control_layout.addWidget(self.mute_button)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setObjectName("volumeSlider")
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(200)
        self.volume_slider.setValue(self.parent.volume_slider.value())
        self.volume_slider.setFixedWidth(150)
        self.volume_slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.volume_slider.valueChanged.connect(self.parent.set_volume)

        def volume_mouse_press_event(event):
            if event.button() == Qt.MouseButton.LeftButton:
                slider_width = self.volume_slider.width()
                click_x = event.position().x()
                value_range = 200 - 0
                new_value = 0 + int((click_x / slider_width) * value_range)
                new_value = max(0, min(200, new_value))
                self.volume_slider.setValue(new_value)
                self.parent.set_volume(new_value)
                QSlider.mousePressEvent(self.volume_slider, event)
            else:
                QSlider.mousePressEvent(self.volume_slider, event)

        def volume_wheel_event(event):
            delta = event.angleDelta().y()
            self.parent.adjust_volume_by_wheel(delta)
            event.accept()

        self.volume_slider.mousePressEvent = volume_mouse_press_event
        self.volume_slider.wheelEvent = volume_wheel_event
        self.volume_slider.valueChanged.connect(self.parent.set_volume)
        control_layout.addWidget(self.volume_slider)
        self.volume_label = QLabel(self.parent.volume_label.text())
        self.volume_label.setObjectName("volumeLabel")
        control_layout.addWidget(self.volume_label)
        control_layout.addSpacing(20)
        self.duration_label = QLabel(self.parent.duration_label.text())
        self.duration_label.setObjectName("durationLabel")
        control_layout.addWidget(self.duration_label)
        control_layout.addSpacing(20)
        self.exit_fullscreen_button = QPushButton()
        self.exit_fullscreen_button.setObjectName("exitFullscreenButton")
        self.exit_fullscreen_button.setFixedSize(48, 48)
        self.exit_fullscreen_button.setIcon(QIcon(resource_path("icons/exit_fullscreen_icon.png")))
        self.exit_fullscreen_button.setToolTip("Exit Fullscreen (F)")
        self.exit_fullscreen_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.exit_fullscreen_button.clicked.connect(self.parent.toggle_fullscreen)
        self.exit_fullscreen_button.setEnabled(bool(self.parent.playlist))
        control_layout.addWidget(self.exit_fullscreen_button)
        main_layout.addLayout(control_layout)

    def adjust_position(self):
        screen = QApplication.primaryScreen().geometry()
        dialog_size = self.sizeHint()
        if dialog_size.width() == 0 or dialog_size.height() == 0:
            dialog_size = QSize(600, 100)
        x = (screen.width() - dialog_size.width()) // 2
        y = screen.height() - dialog_size.height() - 20
        self.setGeometry(x, y, dialog_size.width(), dialog_size.height())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        rect = self.rect()
        radius = 12
        path.addRoundedRect(QRectF(rect), radius, radius)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#353535"))
        painter.drawPath(path)
        super().paintEvent(event)

    def enterEvent(self, event):
        self.hide_timer.stop()
        super().enterEvent(event)

    def mouseMoveEvent(self, event):
        self.hide_timer.stop()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.reset_hide_timer()
        super().leaveEvent(event)

    def reset_hide_timer(self):
        if self.is_visible and not self.initial_show:
            self.hide_timer.start(3000)

class VideoWindow(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setStyleSheet("background-color: black;")
        self.setWindowIcon(QIcon(resource_path("icons/tray_icon.png")))
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_control_dialog)
        self.is_dialog_visible = False
        self.initial_show = False

    def enter_fullscreen(self):
        self.hide()
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setGeometry(QApplication.primaryScreen().geometry())
        self.showFullScreen()

    def enter_desktop(self):
        self.parent.set_wallpaper("")
        self.parent.set_bg_color("0 0 0")
        self.hide()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setGeometry(0, 0, GetSystemMetrics(0), GetSystemMetrics(1))
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)

        progman = win32gui.FindWindow("Progman", None)
        win32gui.SendMessage(progman, 0x052C, 0, 0)
        def_view = win32gui.FindWindowEx(progman, 0, "SHELLDLL_DefView", None)
        video_hwnd = int(self.winId())
        win32gui.SetParent(video_hwnd, progman)
        screen_width = GetSystemMetrics(0)
        screen_height = GetSystemMetrics(1)
        win32gui.SetWindowPos(video_hwnd, win32con.HWND_TOP, 0, 0, screen_width, screen_height, win32con.SWP_SHOWWINDOW | win32con.SWP_NOACTIVATE)

    def start_hide_timer(self):
        self.initial_show = False
        self.reset_hide_timer()

    def hide_control_dialog(self):
        if self.is_dialog_visible:
            self.is_dialog_visible = False
            self.initial_show = False
            self.parent.fullscreen_control_dialog.hide()

    def reset_hide_timer(self):
        if self.is_dialog_visible and not self.initial_show:
            self.hide_timer.start(3000)

    def keyPressEvent(self, event):
        if self.parent.fullscreen_enabled:
            if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_F):
                self.parent.toggle_fullscreen()
        if event.key() == Qt.Key.Key_Space:
            self.parent.play_pause()
        elif event.key() == Qt.Key.Key_Left:
            if self.parent.player.get_state() in (vlc.State.Playing, vlc.State.Paused):
                current_time = self.parent.player.get_time()
                new_time = max(0, current_time - 10000)
                self.parent.player.set_time(new_time)
        elif event.key() == Qt.Key.Key_Right:
            if self.parent.player.get_state() in (vlc.State.Playing, vlc.State.Paused):
                current_time = self.parent.player.get_time()
                new_time = min(self.parent.player.get_length(), current_time + 10000)
                self.parent.player.set_time(new_time)
        elif event.key() == Qt.Key.Key_Up:
            current_volume = self.parent.volume_slider.value()
            new_volume = min(200, current_volume + 5)
            self.parent.set_volume(new_volume)
        elif event.key() == Qt.Key.Key_Down:
            current_volume = self.parent.volume_slider.value()
            new_volume = max(0, current_volume - 5)
            self.parent.set_volume(new_volume)
        elif event.key() == Qt.Key.Key_Q:
            self.parent.open_playlist()
        elif event.key() == Qt.Key.Key_S:
            self.parent.stop()
        elif event.key() == Qt.Key.Key_P:
            self.parent.play_previous()
        elif event.key() == Qt.Key.Key_N:
            self.parent.play_next()
        elif event.key() == Qt.Key.Key_L:
            self.parent.toggle_repeat(None)
        elif event.key() == Qt.Key.Key_M:
            self.parent.toggle_mute()
        elif event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_F4:
            self.parent.quit_application()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        self.parent.adjust_volume_by_wheel(delta)
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.parent.fullscreen_enabled:
            self.parent.toggle_fullscreen()
            event.accept()

class LDBPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(resource_path("icons/tray_icon.png")))
        self.setWindowTitle("LDB Player")
        self.setWindowOpacity(0.9)
        self.original_wallpaper = self.get_current_wallpaper()
        self.original_bg_color = self.get_current_bg_color()
        self.repeat_mode = 'one'
        self.is_muted = False
        self.original_playlist = []
        self.last_video_dir = None
        instance_args = "--no-plugins-cache --quiet"
        self.instance = vlc.Instance(instance_args)
        self.media_list = self.instance.media_list_new()
        self.list_player = self.instance.media_list_player_new()
        self.player = self.list_player.get_media_player()
        self.list_player.set_playback_mode(vlc.PlaybackMode.repeat)
        self.playlist = []
        self.current_video_index = 0
        self.is_paused = False
        self.is_fullscreen = False
        self.fullscreen_enabled = False
        self.config_dir = os.path.join(pathlib.Path.home(), 'AppData', 'Local', 'LDBPlayer')
        self.config_file = os.path.join(self.config_dir, 'ldb_player_config.json')
        self.volume_debounce_timer = QTimer(self)
        self.volume_debounce_timer.setSingleShot(True)
        self.skip_audio_poll = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_slider)
        self.timer.start(100)
        self.dragging = False
        self.drag_position = QPoint()
        self.setAcceptDrops(True)
        self.current_wallpaper = self.get_current_wallpaper()
        self.current_bg_color = self.get_current_bg_color()
        self.video_window_initialized = False
        self.last_known_position = 0.0
        self.is_toggling_fullscreen = False
        self.just_toggled_fullscreen = False
        self.init_ui()
        self.installEventFilter(self)
        self.central_frame.installEventFilter(self)
        self.init_system_tray()
        self.load_config()
        self.update_tray_actions()
        if self.current_wallpaper == "" and self.playback_state in ['playing', 'paused']:
            self.original_wallpaper = self.saved_original_wallpaper
            self.original_bg_color = self.saved_original_bg_color
        self.event_manager = self.player.event_manager()
        self.event_manager.event_attach(vlc.EventType.MediaPlayerPlaying, lambda event: self.handle_playing_event(event))
        self.event_manager.event_attach(vlc.EventType.MediaPlayerStopped, lambda event: self.handle_stop_event(event))
        self.event_manager.event_attach(vlc.EventType.MediaPlayerEncounteredError, lambda event: self.handle_error_event(event))
        self.event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, lambda event: self.handle_end_reached_event(event))
        self.update_tray_actions()
        if self.fullscreen_enabled:
            self.fullscreen_control_dialog = FullscreenControlDialog(self)
            self.fullscreen_control_dialog.hide()
        self.autoplay_last_video()
        self.update_tray_actions()
        if '--autostart' not in sys.argv:
            QTimer.singleShot(50, self.bring_to_front)

    def bring_to_front(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()

    def truncate_label_text(self, text):
        font_metrics = self.current_video_label.fontMetrics()
        available_width = self.current_video_label.width()
        truncated_text = font_metrics.elidedText(text, Qt.TextElideMode.ElideRight, available_width)
        if font_metrics.horizontalAdvance(text) > available_width:
            self.current_video_label.setToolTip(text)
        else:
            self.current_video_label.setToolTip("")
        return truncated_text

    def is_duplicate_file(self, new_file, existing_files):
        new_name = os.path.basename(new_file)
        new_dir = os.path.dirname(new_file)
        for existing_file in existing_files:
            existing_name = os.path.basename(existing_file)
            existing_dir = os.path.dirname(existing_file)
            if new_name == existing_name and new_dir == existing_dir:
                return True
        return False

    def dragEnterEvent(self, event):
        if QApplication.activeModalWidget():
            event.ignore()
            return
        if event.mimeData().hasUrls():
            supported_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mpeg', '.mpg', '.m4v')
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if file_path.lower().endswith(supported_extensions):
                        event.acceptProposedAction()
                        return
        event.ignore()

    def dragMoveEvent(self, event):
        if QApplication.activeModalWidget():
            event.ignore()
            return
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if QApplication.activeModalWidget():
            event.ignore()
            return
        supported_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mpeg', '.mpg', '.m4v')
        files = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                file_path = url.toLocalFile()
                if file_path.lower().endswith(supported_extensions):
                    files.append(file_path)
        if files:
            self.last_video_dir = os.path.dirname(files[0])
            self.save_config()
            state = self.player.get_state()
            was_playing = state in (vlc.State.Playing, vlc.State.Paused)
            was_paused = state == vlc.State.Paused
            was_empty = not self.playlist
            new_files = [f for f in files if not self.is_duplicate_file(f, self.playlist)]
            self.playlist.extend(new_files)
            self.original_playlist.extend(new_files)
            self.save_config()
            self.load_playlist()
            if was_empty:
                self.current_video_index = 0
                if not hasattr(self, 'video_window') or not self.video_window or sip.isdeleted(self.video_window):
                    self.setup_video_window(is_fullscreen=self.is_fullscreen)
                self.video_window.show()
                self.list_player.play_item_at_index(self.current_video_index)
                self.play_pause_button.setIcon(QIcon(resource_path("icons/pause_icon.png")))
                self.play_pause_button.setToolTip("Pause (Space)")
                self.is_paused = False
                video_name = os.path.basename(self.playlist[self.current_video_index])
                self.current_video_label.setText(self.truncate_label_text(video_name))
                QTimer.singleShot(100, self.ensure_playing_and_set_audio)
            elif was_playing:
                if was_paused:
                    self.play_pause_button.setIcon(QIcon(resource_path("icons/play_icon.png")))
                    self.play_pause_button.setToolTip("Play (Space)")
                    self.is_paused = True
                    video_name = os.path.basename(self.playlist[self.current_video_index])
                    self.current_video_label.setText(self.truncate_label_text(video_name))
                else:
                    self.play_pause_button.setIcon(QIcon(resource_path("icons/pause_icon.png")))
                    self.play_pause_button.setToolTip("Pause (Space)")
                    self.is_paused = False
                    video_name = os.path.basename(self.playlist[self.current_video_index])
                    self.current_video_label.setText(self.truncate_label_text(video_name))
                    QTimer.singleShot(100, self.ensure_playing_and_set_audio)
                self.video_window.show()
            event.acceptProposedAction()
            self.update_control_dialog()
        else:
            event.ignore()

    def get_current_wallpaper(self):
        SPI_GETDESKWALLPAPER = 0x0073
        buffer = ctypes.create_unicode_buffer(260)
        ctypes.windll.user32.SystemParametersInfoW(SPI_GETDESKWALLPAPER, 260, buffer, 0)
        return buffer.value

    def get_current_bg_color(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Colors")
            value, _ = winreg.QueryValueEx(key, "Background")
            winreg.CloseKey(key)
            return value
        except (FileNotFoundError, OSError):
            return "0 0 0"

    def set_wallpaper(self, path):
        SPI_SETDESKWALLPAPER = 0x0014
        ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, path, 3)

    def set_bg_color(self, rgb_str):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Colors", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "Background", 0, winreg.REG_SZ, rgb_str)
            winreg.CloseKey(key)
            ctypes.windll.user32.SystemParametersInfoW(0x0014, 0, None, 3)
        except Exception as e:
            logging.error(f"Failed to set background color: {e}")

    def init_ui(self):
        central_frame = QFrame(self)
        central_frame.setObjectName("centralFrame")
        central_frame.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.central_frame = central_frame
        self.setCentralWidget(central_frame)
        main_layout = QVBoxLayout(central_frame)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        video_layout = QHBoxLayout()
        video_layout.setSpacing(10)
        self.current_video_label = QLabel("No video playing")
        self.current_video_label.setFixedWidth(400)
        self.current_video_label.setMinimumHeight(32)
        video_layout.addWidget(self.current_video_label)
        main_layout.addLayout(video_layout)
        main_layout.addSpacing(10)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(1000)
        self.slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        def slider_mouse_press_event(player_instance, slider, event):
            if event.button() == Qt.MouseButton.LeftButton and player_instance.player.get_state() in (vlc.State.Playing, vlc.State.Paused):
                slider_width = slider.width()
                click_x = event.position().x()
                value_range = 1000 - 0
                new_value = 0 + int((click_x / slider_width) * value_range)
                new_value = max(0, min(1000, new_value))
                handle_width = 16
                current_value = slider.value()
                handle_pos = (current_value / value_range) * slider_width
                handle_rect = QRectF(handle_pos - handle_width / 2, 0, handle_width, slider.height())
                slider.setValue(new_value)
                player_instance.seek(new_value)
                QSlider.mousePressEvent(slider, event)
            else:
                QSlider.mousePressEvent(slider, event)

        def slider_wheel_event(player_instance, slider, event):
            if player_instance.player.get_state() in (vlc.State.Playing, vlc.State.Paused):
                delta = event.angleDelta().y()
                current_time = player_instance.player.get_time()
                jump_ms = 10000
                new_time = current_time + (jump_ms if delta > 0 else -jump_ms)
                new_time = max(0, min(new_time, player_instance.player.get_length()))
                player_instance.player.set_time(new_time)
                event.accept()

        def handle_slider_pressed():
            if self.player.get_state() == vlc.State.Playing:
                self.was_playing_before_drag = True
                self.list_player.pause()
                self.is_paused = True
            else:
                self.was_playing_before_drag = False

        def handle_slider_released():
            if hasattr(self, 'was_playing_before_drag') and self.was_playing_before_drag:
                self.list_player.play()
                self.is_paused = False
                QTimer.singleShot(100, self.ensure_playing_and_set_audio)
            self.was_playing_before_drag = False

        from functools import partial
        self.slider.mousePressEvent = partial(slider_mouse_press_event, self, self.slider)
        self.slider.wheelEvent = partial(slider_wheel_event, self, self.slider)
        self.slider.sliderPressed.connect(handle_slider_pressed)
        self.slider.sliderReleased.connect(handle_slider_released)
        self.slider.sliderMoved.connect(self.seek)
        main_layout.addWidget(self.slider)
        control_layout = QHBoxLayout()
        control_layout.setSpacing(10)
        self.playlist_button = QPushButton()
        self.playlist_button.setObjectName("playlistButton")
        self.playlist_button.setFixedSize(48, 48)
        self.playlist_button.setIcon(QIcon(resource_path("icons/playlist_icon.png")))
        self.playlist_button.setToolTip("Playlist (Q)")
        self.playlist_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.playlist_button.clicked.connect(self.open_playlist)
        self.play_pause_button = QPushButton()
        self.play_pause_button.setObjectName("playButton")
        self.play_pause_button.setFixedSize(48, 48)
        self.play_pause_button.setIcon(QIcon(resource_path("icons/play_icon.png")))
        self.play_pause_button.setToolTip("Play (Space)")
        self.play_pause_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.play_pause_button.clicked.connect(self.play_pause)
        self.stop_button = QPushButton()
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setFixedSize(48, 48)
        self.stop_button.setIcon(QIcon(resource_path("icons/stop_icon.png")))
        self.stop_button.setToolTip("Stop (S)")
        self.stop_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.stop_button.clicked.connect(self.stop)
        self.prev_button = QPushButton()
        self.prev_button.setObjectName("prevButton")
        self.prev_button.setFixedSize(48, 48)
        self.prev_button.setIcon(QIcon(resource_path("icons/prev_icon.png")))
        self.prev_button.setToolTip("Previous (P)")
        self.prev_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.prev_button.clicked.connect(self.play_previous)
        self.next_button = QPushButton()
        self.next_button.setObjectName("nextButton")
        self.next_button.setFixedSize(48, 48)
        self.next_button.setIcon(QIcon(resource_path("icons/next_icon.png")))
        self.next_button.setToolTip("Next (N)")
        self.next_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.next_button.clicked.connect(self.play_next)
        self.repeat_button = QPushButton()
        self.repeat_button.setObjectName("repeatButton")
        self.repeat_button.setFixedSize(48, 48)
        self.repeat_button.setIcon(QIcon(resource_path(f"icons/repeat_{self.repeat_mode}_icon.png")))
        self.repeat_button.setToolTip("Loop (L)")
        self.repeat_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.repeat_button.clicked.connect(lambda: self.toggle_repeat(None))
        control_layout.addWidget(self.playlist_button)
        control_layout.addWidget(self.play_pause_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.prev_button)
        control_layout.addWidget(self.next_button)
        control_layout.addWidget(self.repeat_button)
        main_layout.addLayout(control_layout)
        volume_layout = QHBoxLayout()
        volume_layout.setSpacing(10)
        self.mute_button = QPushButton()
        self.mute_button.setObjectName("muteButton")
        self.mute_button.setFixedSize(48, 48)
        self.mute_button.setIcon(QIcon(resource_path("icons/mute_icon.png" if self.is_muted else "icons/unmute_icon.png")))
        self.mute_button.setToolTip("Mute (M)")
        self.mute_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.mute_button.clicked.connect(self.toggle_mute)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setObjectName("volumeSlider")
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(200)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(150)
        self.volume_slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.volume_slider.valueChanged.connect(self.set_volume)

        def volume_mouse_press_event(player_instance, slider, event):
            if event.button() == Qt.MouseButton.LeftButton:
                slider_width = slider.width()
                click_x = event.position().x()
                value_range = 200 - 0
                new_value = 0 + int((click_x / slider_width) * value_range)
                new_value = max(0, min(200, new_value))
                slider.setValue(new_value)
                player_instance.set_volume(new_value)
                QSlider.mousePressEvent(slider, event)
            else:
                QSlider.mousePressEvent(slider, event)

        def volume_wheel_event(player_instance, slider, event):
            delta = event.angleDelta().y()
            player_instance.adjust_volume_by_wheel(delta)
            event.accept()

        self.volume_slider.mousePressEvent = partial(volume_mouse_press_event, self, self.volume_slider)
        self.volume_slider.wheelEvent = partial(volume_wheel_event, self, self.volume_slider)

        self.volume_label = QLabel("100%")
        self.volume_label.setObjectName("volumeLabel")
        self.duration_label = QLabel("--:-- / --:--")
        self.duration_label.setObjectName("durationLabel")
        self.fullscreen_button = QPushButton()
        self.fullscreen_button.setObjectName("fullscreenButton")
        self.fullscreen_button.setFixedSize(48, 48)
        self.fullscreen_button.setIcon(QIcon(resource_path("icons/fullscreen_icon.png")))
        self.fullscreen_button.setToolTip("Fullscreen (F)")
        self.fullscreen_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.fullscreen_button.clicked.connect(self.toggle_fullscreen)
        self.fullscreen_button.setEnabled(bool(self.playlist))
        self.fullscreen_button.setVisible(self.fullscreen_enabled)
        settings_button = QPushButton()
        settings_button.setObjectName("settingsButton")
        settings_button.setFixedSize(48, 48)
        settings_button.setIcon(QIcon(resource_path("icons/settings_icon.png")))
        settings_button.setToolTip("Settings (F12)")
        settings_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        settings_button.clicked.connect(self.open_settings)
        about_button = QPushButton()
        about_button.setObjectName("aboutButton")
        about_button.setFixedSize(48, 48)
        about_button.setIcon(QIcon(resource_path("icons/about_icon.png")))
        about_button.setToolTip("About (F1)")
        about_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        about_button.clicked.connect(self.open_about)
        volume_layout.addWidget(self.mute_button)
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addWidget(self.volume_label)
        volume_layout.addSpacing(20)
        volume_layout.addWidget(self.duration_label)
        volume_layout.addSpacing(20)
        if self.fullscreen_enabled:
            volume_layout.addWidget(self.fullscreen_button)
        volume_layout.addWidget(settings_button)
        volume_layout.addWidget(about_button)
        main_layout.addLayout(volume_layout)
        main_layout.addSpacing(10)
        self.setMinimumSize(550, 250)
        QTimer.singleShot(0, self.adjustSize)

    def update_fullscreen_button_state(self):
        if not self.fullscreen_enabled:
            return
        state = self.player.get_state()
        has_playlist = bool(self.playlist)
        is_playable = has_playlist and state in (vlc.State.Playing, vlc.State.Paused)
        self.fullscreen_button.setEnabled(is_playable)
        if hasattr(self, 'fullscreen_control_dialog') and not sip.isdeleted(self.fullscreen_control_dialog):
            self.fullscreen_control_dialog.exit_fullscreen_button.setEnabled(is_playable)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            if obj in (self, self.central_frame):
                focused_widget = QApplication.focusWidget()
                if focused_widget:
                    focused_widget.clearFocus()
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if self.isActiveWindow():
            if self.fullscreen_enabled and event.key() == Qt.Key.Key_F:
                state = self.player.get_state()
                has_playlist = bool(self.playlist)
                is_playable = has_playlist and state in (vlc.State.Playing, vlc.State.Paused)
                if is_playable:
                    self.toggle_fullscreen()
            elif event.key() == Qt.Key.Key_Space:
                self.play_pause()
            elif event.key() == Qt.Key.Key_Left:
                if self.player.get_state() in (vlc.State.Playing, vlc.State.Paused):
                    current_time = self.player.get_time()
                    new_time = max(0, current_time - 10000)
                    self.player.set_time(new_time)
            elif event.key() == Qt.Key.Key_Right:
                if self.player.get_state() in (vlc.State.Playing, vlc.State.Paused):
                    current_time = self.player.get_time()
                    new_time = min(self.player.get_length(), current_time + 10000)
                    self.player.set_time(new_time)
            elif event.key() == Qt.Key.Key_Up:
                current_volume = self.volume_slider.value()
                new_volume = min(200, current_volume + 5)
                self.set_volume(new_volume)
            elif event.key() == Qt.Key.Key_Down:
                current_volume = self.volume_slider.value()
                new_volume = max(0, current_volume - 5)
                self.set_volume(new_volume)
            elif event.key() == Qt.Key.Key_Q:
                self.open_playlist()
            elif event.key() == Qt.Key.Key_S:
                self.stop()
            elif event.key() == Qt.Key.Key_P:
                self.play_previous()
            elif event.key() == Qt.Key.Key_N:
                self.play_next()
            elif event.key() == Qt.Key.Key_L:
                self.toggle_repeat(None)
            elif event.key() == Qt.Key.Key_M:
                self.toggle_mute()
            elif event.key() == Qt.Key.Key_F12:
                self.open_settings()
            elif event.key() == Qt.Key.Key_F1:
                self.open_about()
            elif event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_F4:
                self.quit_application()
        super().keyPressEvent(event)

    def customEvent(self, event):
        if event.type() == CustomEvent.EVENT_TYPE:
            self.update_ui(event.video_name, event.index)

    def init_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip("LDB Player")
        tray_menu = QMenu()
        tray_menu.setStyleSheet("""
            QMenu {
                background-color: #353535;
                color: white;
                border: 1px solid #555555;
                border-radius: 5px;
            }
            QMenu::item {
                background-color: #353535;
                color: white;
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #252525;
            }
            QMenu::item:disabled {
                color: #666666;
                background-color: #353535;
            }
        """)
        self.play_action = QAction("Play", self)
        self.play_action.triggered.connect(self.tray_play)
        tray_menu.addAction(self.play_action)
        self.stop_action = QAction("Stop", self)
        self.stop_action.triggered.connect(self.stop)
        tray_menu.addAction(self.stop_action)
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.restore_window)
        tray_menu.addAction(show_action)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)
        self.tray_icon.setIcon(QIcon(resource_path("icons/tray_icon.png")))
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_activated)
        self.tray_icon.show()

    def tray_play(self):
        if not self.playlist or self.media_list.count() == 0:
            return
        if not hasattr(self, 'video_window') or not self.video_window or sip.isdeleted(self.video_window):
            self.setup_video_window(is_fullscreen=self.is_fullscreen)
        self.video_window.show()
        if self.is_paused or self.player.get_state() != vlc.State.Playing:
            self.list_player.play_item_at_index(self.current_video_index)
            self.play_pause_button.setIcon(QIcon(resource_path("icons/pause_icon.png")))
            self.play_pause_button.setToolTip("Pause (Space)")
            self.is_paused = False
            video_name = os.path.basename(self.playlist[self.current_video_index])
            self.current_video_label.setText(self.truncate_label_text(video_name))
            QTimer.singleShot(100, self.ensure_playing_and_set_audio)
        self.update_tray_actions()
        self.update_control_dialog()
        self.update_fullscreen_button_state()

    def update_tray_actions(self):
        if self.play_action and self.stop_action:
            state = self.player.get_state()
            has_playlist = bool(self.playlist)
            is_playing = state == vlc.State.Playing
            self.play_action.setEnabled(has_playlist and not is_playing)
            self.stop_action.setEnabled(has_playlist and (is_playing or state == vlc.State.Paused))

    def restore_window(self):
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.activateWindow()

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.restore_window()

    def closeEvent(self, event):
        self.save_config()
        self.hide()
        event.ignore()

    def is_autostart_enabled(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            value, value_type = winreg.QueryValueEx(key, "LDB Player")
            winreg.CloseKey(key)
            return True
        except (FileNotFoundError, OSError):
            return False

    def toggle_autostart(self, enabled):
        if enabled:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            app_path = os.path.abspath(sys.argv[0])
            winreg.SetValueEx(key, "LDB Player", 0, winreg.REG_SZ, f'"{app_path}" --autostart')
            winreg.CloseKey(key)
        else:
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
                winreg.DeleteValue(key, "LDB Player")
                winreg.CloseKey(key)
            except FileNotFoundError:
                pass

    def setup_video_window(self, is_fullscreen=False):
        if hasattr(self, 'video_window') and self.video_window:
            try:
                self.player.set_hwnd(0)
                self.video_window.hide()
                self.video_window.close()
                self.video_window.deleteLater()
                QTimer.singleShot(100, lambda: self._force_delete_window())
            except:
                pass
            finally:
                del self.video_window
                self.video_window = None

        self.video_window = VideoWindow(self)
        if is_fullscreen:
            self.video_window.enter_fullscreen()
        else:
            self.video_window.enter_desktop()
        win_id = int(self.video_window.winId())
        self.player.set_hwnd(win_id)
        if not is_fullscreen:
            self.video_window.hide()
            QTimer.singleShot(50, lambda: (self.activateWindow(), self.setFocus()))

    def _force_delete_window(self):
        if hasattr(self, 'video_window') and self.video_window and not sip.isdeleted(self.video_window):
            try:
                self.video_window.close()
                self.video_window.deleteLater()
            except:
                pass

    def toggle_fullscreen(self):
        if not self.fullscreen_enabled:
            return
        if hasattr(self, 'is_toggling') and self.is_toggling:
            return
        self.is_toggling = True
        self.is_toggling_fullscreen = True
        try:
            state = self.player.get_state()
            was_playing = state in (vlc.State.Playing, vlc.State.Paused)
            was_paused = state == vlc.State.Paused
            current_position = self.player.get_position() if was_playing and self.player.get_position() >= 0 else 0.0
            self.last_known_position = current_position
            current_index = self.current_video_index
            video_name = os.path.basename(self.playlist[current_index]) if self.playlist and 0 <= current_index < len(self.playlist) else "No video playing"

            self.player.set_hwnd(0)
            self.video_window.hide()
            self.is_fullscreen = not self.is_fullscreen
            if self.is_fullscreen:
                self.video_window.enter_fullscreen()
            else:
                self.video_window.enter_desktop()
            self.player.set_hwnd(int(self.video_window.winId()))
            self.video_window.show()
            if was_playing:
                self.list_player.play()
                if was_paused:
                    self.list_player.pause()
                    self.is_paused = True
                    self.play_pause_button.setIcon(QIcon(resource_path("icons/play_icon.png")))
                    self.play_pause_button.setToolTip("Play (Space)")
                else:
                    self.is_paused = False
                    self.play_pause_button.setIcon(QIcon(resource_path("icons/pause_icon.png")))
                    self.play_pause_button.setToolTip("Pause (Space)")
                QTimer.singleShot(100, self.ensure_playing_and_set_audio)
                self.current_video_label.setText(self.truncate_label_text(video_name))
            else:
                self.play_pause_button.setIcon(QIcon(resource_path("icons/play_icon.png")))
                self.play_pause_button.setToolTip("Play (Space)")
                self.is_paused = False
                self.current_video_label.setText(self.truncate_label_text("No video playing" if self.playlist else "Playlist is empty"))
            self.fullscreen_button.setIcon(QIcon(resource_path("icons/exit_fullscreen_icon.png" if self.is_fullscreen else "icons/fullscreen_icon.png")))
            self.fullscreen_button.setToolTip("Exit Fullscreen (F)" if self.is_fullscreen else "Fullscreen (F)")
            self._finalize_toggle()
        finally:
            self.is_toggling = False

    def _finalize_toggle(self):
        if self.is_fullscreen:
            self.hide()
            if hasattr(self, 'fullscreen_control_dialog') and not sip.isdeleted(self.fullscreen_control_dialog):
                self.fullscreen_control_dialog.adjust_position()
                QTimer.singleShot(300, self.fullscreen_control_dialog.show_dialog)
                QTimer.singleShot(350, lambda: (self.video_window.activateWindow(), self.video_window.setFocus()))
        else:
            if hasattr(self, 'fullscreen_control_dialog') and not sip.isdeleted(self.fullscreen_control_dialog):
                self.fullscreen_control_dialog.hide()
            self.show()

    def update_control_dialog(self):
        if not self.fullscreen_enabled:
            return
        if hasattr(self, 'is_toggling_fullscreen') and self.is_toggling_fullscreen:
            return
        if hasattr(self, 'fullscreen_control_dialog') and not sip.isdeleted(self.fullscreen_control_dialog) and self.is_fullscreen:
            try:
                self.fullscreen_control_dialog.slider.setValue(int(self.player.get_position() * 1000))
                self.fullscreen_control_dialog.play_pause_button.setIcon(
                    QIcon(resource_path("icons/play_icon.png" if self.is_paused else "icons/pause_icon.png"))
                )
                self.fullscreen_control_dialog.play_pause_button.setToolTip(
                    "Play (Space)" if self.is_paused else "Pause (Space)"
                )
                self.fullscreen_control_dialog.mute_button.setIcon(
                    QIcon(resource_path("icons/mute_icon.png" if self.is_muted else "icons/unmute_icon.png"))
                )
                self.fullscreen_control_dialog.mute_button.setToolTip(
                    "Unmute (M)" if self.is_muted else "Mute (M)"
                )
                self.fullscreen_control_dialog.volume_slider.setValue(self.volume_slider.value())
                self.fullscreen_control_dialog.volume_label.setText(self.volume_label.text())
                self.fullscreen_control_dialog.duration_label.setText(self.duration_label.text())
                self.fullscreen_control_dialog.repeat_button.setIcon(
                    QIcon(resource_path(f"icons/repeat_{self.repeat_mode}_icon.png"))
                )
                video_name = os.path.basename(self.playlist[self.current_video_index])
                self.fullscreen_control_dialog.current_video_label.setText(self.truncate_label_text(video_name))
            except Exception:
                pass

    def load_config(self):
        os.makedirs(self.config_dir, exist_ok=True)
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.original_playlist = [f for f in config.get('playlist', []) if os.path.exists(f)]
                self.playlist = self.original_playlist.copy()
                self.current_video_index = config.get('current_video_index', 0)
                self.repeat_mode = config.get('repeat_mode', 'one')
                self.last_video_dir = config.get('last_video_dir', None)
                volume = config.get('volume', 100)
                self.volume_slider.setValue(volume)
                self.volume_label.setText(f"{volume}%")
                self.is_muted = config.get('is_muted', False)
                self.mute_button.setIcon(QIcon(resource_path("icons/mute_icon.png" if self.is_muted else "icons/unmute_icon.png")))
                self.mute_button.setToolTip("Mute (M)" if not self.is_muted else "Unmute (M)")
                self.repeat_button.setIcon(QIcon(resource_path(f"icons/repeat_{self.repeat_mode}_icon.png")))
                try:
                    self.player.audio_set_mute(self.is_muted)
                except:
                    pass
                window_pos = config.get('window_pos', None)
                window_size = config.get('window_size', None)
                if window_pos and window_size:
                    self.resize(QSize(window_size['width'], window_size['height']))
                    self.move(QPoint(window_pos['x'], window_pos['y']))
                    self.adjust_position()
                self.playback_state = config.get('playback_state', 'stopped')
                self.saved_original_wallpaper = config.get('saved_original_wallpaper', self.original_wallpaper)
                self.saved_original_bg_color = config.get('saved_original_bg_color', self.original_bg_color)
                if self.repeat_mode not in ['one', 'all']:
                    self.repeat_mode = 'one'
                if self.current_video_index >= len(self.playlist):
                    self.current_video_index = 0
                self.load_playlist()
                if self.repeat_mode == 'one':
                    self.list_player.set_playback_mode(vlc.PlaybackMode.repeat)
                else:
                    self.list_player.set_playback_mode(vlc.PlaybackMode.loop)
        except (FileNotFoundError, json.JSONDecodeError):
            self.repeat_mode = 'one'
            self.playback_state = 'stopped'
            self.list_player.set_playback_mode(vlc.PlaybackMode.repeat)
            self.current_video_label.setText(self.truncate_label_text("Playlist is empty"))

    def save_config(self):
        state = self.player.get_state()
        if state == vlc.State.Playing:
            playback_state = 'playing'
        elif state == vlc.State.Paused:
            playback_state = 'paused'
        else:
            playback_state = 'stopped'
        config = {
            'playlist': self.original_playlist,
            'current_video_index': self.current_video_index,
            'repeat_mode': self.repeat_mode,
            'volume': self.volume_slider.value(),
            'is_muted': self.is_muted,
            'last_video_dir': self.last_video_dir,
            'window_pos': {'x': self.pos().x(), 'y': self.pos().y()},
            'window_size': {'width': self.size().width(), 'height': self.size().height()},
            'playback_state': playback_state,
            'saved_original_wallpaper': self.original_wallpaper,
            'saved_original_bg_color': self.original_bg_color,
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f)

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

    def ensure_playing_and_set_audio(self):
        if self.player.get_state() in (vlc.State.Playing, vlc.State.Paused):
            self.set_volume(self.volume_slider.value())
            self.player.audio_set_mute(self.is_muted)
        else:
            QTimer.singleShot(50, self.ensure_playing_and_set_audio)

    def autoplay_last_video(self):
        if (self.playback_state in ['playing', 'paused'] and self.repeat_mode in ['one', 'all'] and
            self.playlist and 0 <= self.current_video_index < len(self.playlist) and
            os.path.exists(self.playlist[self.current_video_index])):
            if self.media_list.count() == 0:
                self.load_playlist()
            if not hasattr(self, 'video_window') or not self.video_window or sip.isdeleted(self.video_window):
                self.setup_video_window(is_fullscreen=self.is_fullscreen)
            self.video_window.show()
            QTimer.singleShot(200, lambda: self.list_player.play_item_at_index(self.current_video_index))
            self.play_pause_button.setIcon(QIcon(resource_path("icons/pause_icon.png")))
            self.play_pause_button.setToolTip("Pause (Space)")
            self.is_paused = False
            video_name = os.path.basename(self.playlist[self.current_video_index])
            self.current_video_label.setText(self.truncate_label_text(video_name))
            QTimer.singleShot(300, self.ensure_playing_and_set_audio)
        else:
            if hasattr(self, 'video_window') and self.video_window:
                self.video_window.hide()
            self.update_tray_actions()

    def open_settings(self):
        try:
            dialog = SettingsDialog(self)
            dialog.show()
            dialog.exec()
        except Exception as e:
            dialog = MessageDialog(self, "Error", f"Failed to open Settings dialog: {str(e)}")
            dialog.exec()

    def open_about(self):
        try:
            dialog = AboutDialog(self)
            dialog.show()
            dialog.exec()
        except Exception as e:
            dialog = MessageDialog(self, "Error", f"Failed to open About dialog: {str(e)}")
            dialog.exec()

    def open_playlist(self):
        try:
            dialog = PlaylistDialog(self)
            dialog.show()
            dialog.exec()
        except Exception as e:
            dialog = MessageDialog(self, "Error", f"Failed to open Playlist dialog: {str(e)}")
            dialog.exec()

    def load_playlist(self):
        self.media_list.lock()
        while self.media_list.count() > 0:
            self.media_list.remove_index(0)
        self.media_list.unlock()
        for path in self.playlist:
            if os.path.exists(path):
                file_url = urllib.parse.quote(path, safe='/:')
                file_url = f"file:///{file_url}"
                media = self.instance.media_new(file_url)
                self.media_list.add_media(media)
        self.list_player.set_media_list(self.media_list)
        state = self.player.get_state()
        if state in (vlc.State.Playing, vlc.State.Paused) and self.playlist and 0 <= self.current_video_index < len(self.playlist):
            video_name = os.path.basename(self.playlist[self.current_video_index])
            self.current_video_label.setText(self.truncate_label_text(video_name))
        else:
            self.current_video_index = min(self.current_video_index, len(self.playlist) - 1) if self.playlist else 0
            self.current_video_label.setText(self.truncate_label_text("No video playing" if self.playlist else "Playlist is empty"))
        self.update_fullscreen_button_state()

    def play_pause(self):
        if self.list_player.is_playing():
            self.list_player.pause()
            self.play_pause_button.setIcon(QIcon(resource_path("icons/play_icon.png")))
            self.play_pause_button.setToolTip("Play (Space)")
            self.is_paused = True
        else:
            if not self.playlist or self.media_list.count() == 0:
                self.update_fullscreen_button_state()
                return
            if not hasattr(self, 'video_window') or not self.video_window or sip.isdeleted(self.video_window):
                self.setup_video_window(is_fullscreen=self.is_fullscreen)
            self.video_window.show()
            if self.is_paused:
                if hasattr(self, 'just_toggled_fullscreen') and self.just_toggled_fullscreen and self.last_known_position > 0:
                    self.player.set_position(self.last_known_position)
                self.list_player.pause()
                self.play_pause_button.setIcon(QIcon(resource_path("icons/pause_icon.png")))
                self.play_pause_button.setToolTip("Pause (Space)")
                self.is_paused = False
                self.just_toggled_fullscreen = False
                QTimer.singleShot(100, self.ensure_playing_and_set_audio)
            else:
                self.list_player.play_item_at_index(self.current_video_index)
                self.play_pause_button.setIcon(QIcon(resource_path("icons/pause_icon.png")))
                self.play_pause_button.setToolTip("Pause (Space)")
                self.is_paused = False
                self.just_toggled_fullscreen = False
                video_name = os.path.basename(self.playlist[self.current_video_index])
                self.current_video_label.setText(self.truncate_label_text(video_name))
                QTimer.singleShot(100, self.ensure_playing_and_set_audio)
        self.update_control_dialog()
        self.update_fullscreen_button_state()
        self.update_tray_actions()

    def stop(self):
        self.list_player.stop()
        if hasattr(self, 'video_window') and self.video_window and not sip.isdeleted(self.video_window):
            self.player.set_hwnd(0)
            self.video_window.hide()
            self.video_window.close()
            self.video_window.deleteLater()
            del self.video_window
            self.video_window = None
        self.slider.setValue(0)
        self.play_pause_button.setIcon(QIcon(resource_path("icons/play_icon.png")))
        self.play_pause_button.setToolTip("Play (Space)")
        self.is_paused = False
        self.current_video_label.setText(self.truncate_label_text("No video playing" if self.playlist else "Playlist is empty"))
        self.duration_label.setText("--:-- / --:--")
        if self.original_bg_color:
            self.set_bg_color(self.original_bg_color)
        if self.original_wallpaper:
            self.set_wallpaper(self.original_wallpaper)
        if self.fullscreen_enabled and self.is_fullscreen:
            self.toggle_fullscreen()
        self.update_control_dialog()
        self.update_fullscreen_button_state()
        self.update_tray_actions()

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        try:
            if self.is_muted:
                self.player.audio_set_mute(True)
            else:
                self.player.audio_set_volume(0)
                self.player.audio_set_mute(False)
                self.player.audio_set_volume(self.volume_slider.value())
        except:
            pass
        self.mute_button.setIcon(QIcon(resource_path("icons/mute_icon.png" if self.is_muted else "icons/unmute_icon.png")))
        self.mute_button.setToolTip("Unmute (M)" if self.is_muted else "Mute (M)")
        self.update_control_dialog()

    def set_volume(self, value):
        self.volume_slider.setValue(value)
        self.volume_label.setText(f"{value}%")
        if not self.is_muted:
            try:
                if value > 0:
                    QTimer.singleShot(30, lambda: self.player.audio_set_volume(value))
                else:
                    self.player.audio_set_volume(0)
            except:
                pass
        self.update_control_dialog()

    def adjust_volume_by_wheel(self, delta):
        current_volume = self.volume_slider.value()
        new_volume = max(0, min(200, current_volume + (5 if delta > 0 else -5)))
        self.set_volume(new_volume)

    def wheelEvent(self, event):
        if not self.slider.geometry().contains(self.mapFromGlobal(event.globalPosition().toPoint())):
            delta = event.angleDelta().y()
            self.adjust_volume_by_wheel(delta)
            event.accept()

    def toggle_repeat(self, mode):
        modes = ['one', 'all']
        if mode is None:
            current_index = modes.index(self.repeat_mode) if self.repeat_mode in modes else 0
            self.repeat_mode = modes[(current_index + 1) % len(modes)]
        else:
            self.repeat_mode = mode
        self.repeat_button.setIcon(QIcon(resource_path(f"icons/repeat_{self.repeat_mode}_icon.png")))
        self.repeat_button.setToolTip("Loop")
        self.list_player.set_playback_mode(vlc.PlaybackMode.repeat if self.repeat_mode == 'one' else vlc.PlaybackMode.loop)
        self.save_config()

    def play_next(self):
        if not self.playlist or self.media_list.count() == 0:
            return
        self.current_video_index = (self.current_video_index + 1) % len(self.playlist)
        if not hasattr(self, 'video_window') or not self.video_window or sip.isdeleted(self.video_window):
            self.setup_video_window(is_fullscreen=self.is_fullscreen)
        self.video_window.show()
        self.list_player.play_item_at_index(self.current_video_index)
        self.play_pause_button.setIcon(QIcon(resource_path("icons/pause_icon.png")))
        self.play_pause_button.setToolTip("Pause (Space)")
        self.is_paused = False
        video_name = os.path.basename(self.playlist[self.current_video_index])
        self.current_video_label.setText(self.truncate_label_text(video_name))
        QTimer.singleShot(100, self.ensure_playing_and_set_audio)
        self.save_config()
        self.update_control_dialog()

    def play_previous(self):
        if not self.playlist or self.media_list.count() == 0:
            return
        self.current_video_index = (self.current_video_index - 1) % len(self.playlist)
        if not hasattr(self, 'video_window') or not self.video_window or sip.isdeleted(self.video_window):
            self.setup_video_window(is_fullscreen=self.is_fullscreen)
        self.video_window.show()
        self.list_player.play_item_at_index(self.current_video_index)
        self.play_pause_button.setIcon(QIcon(resource_path("icons/pause_icon.png")))
        self.play_pause_button.setToolTip("Pause (Space)")
        self.is_paused = False
        video_name = os.path.basename(self.playlist[self.current_video_index])
        self.current_video_label.setText(self.truncate_label_text(video_name))
        QTimer.singleShot(100, self.ensure_playing_and_set_audio)
        self.save_config()
        self.update_control_dialog()

    def seek(self, position):
        pos = position / 1000.0
        self.player.set_position(pos)
        self.update_control_dialog()

    def format_time(self, ms):
        if ms < 0:
            return "--:--"
        seconds = int(ms / 1000)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    def update_slider(self):
        state = self.player.get_state()
        if state in (vlc.State.Playing, vlc.State.Buffering, vlc.State.Paused):
            pos = self.player.get_position() * 1000
            self.slider.setValue(min(int(pos), 1000))
            current_time = self.player.get_time()
            total_time = self.player.get_length()
            current_str = self.format_time(current_time)
            total_str = self.format_time(total_time)
            self.duration_label.setText(f"{current_str} / {total_str}")
            if state == vlc.State.Paused:
                self.last_known_position = self.player.get_position()
            self.update_control_dialog()
        elif state == vlc.State.Stopped:
            self.slider.setValue(0)
            self.duration_label.setText("--:-- / --:--")
            self.last_known_position = 0.0
            self.update_control_dialog()

    def handle_playing_event(self, event):
        if self.player.get_state() != vlc.State.Playing:
            return
        current_media = self.player.get_media()
        if current_media and self.media_list.count() > 0:
            media_path = urllib.parse.unquote(current_media.get_mrl().replace('file:///', ''))
            media_path = os.path.normpath(media_path)
            for i, path in enumerate(self.playlist):
                if os.path.normpath(path) == media_path:
                    self.current_video_index = i
                    break
            else:
                self.current_video_index = 0
                self.list_player.stop()
                self.current_video_label.setText(self.truncate_label_text("No video playing"))
                self.video_window.hide()
                self.play_pause_button.setIcon(QIcon(resource_path("icons/play_icon.png")))
                self.play_pause_button.setToolTip("Play (Space)")
                self.is_paused = False
                self.save_config()
                return
        if not self.playlist:
            video_name = "Playlist is empty"
            self.current_video_index = 0
        elif 0 <= self.current_video_index < len(self.playlist):
            video_name = os.path.basename(self.playlist[self.current_video_index])
        else:
            video_name = "No video playing"
            self.current_video_index = 0
        self.current_video_label.setText(self.truncate_label_text(video_name))
        QApplication.postEvent(self, CustomEvent(video_name, self.current_video_index))
        self.update_tray_actions()

    def update_ui(self, video_name, index):
        if self.player.get_state() == vlc.State.Playing:
            self.current_video_index = index
            self.current_video_label.setText(self.truncate_label_text(video_name))
            self.video_window.show()
            self.play_pause_button.setIcon(QIcon(resource_path("icons/pause_icon.png")))
            self.play_pause_button.setToolTip("Pause (Space)")
            self.is_paused = False
            self.update_fullscreen_button_state()

    def handle_stop_event(self, event):
        self.video_window.hide()
        self.current_video_label.setText(self.truncate_label_text("No video playing" if self.playlist else "Playlist is empty"))
        self.duration_label.setText("--:-- / --:--")
        if self.original_bg_color:
            self.set_bg_color(self.original_bg_color)
        if self.original_wallpaper:
            self.set_wallpaper(self.original_wallpaper)
        self.update_tray_actions()

    def handle_error_event(self, event):
        dialog = MessageDialog(self, "Playback Error", "An error occurred during playback.")
        dialog.exec()
        self.stop()

    def handle_end_reached_event(self, event):
        pass

    def quit_application(self):
        if self.original_bg_color:
            self.set_bg_color(self.original_bg_color)
        if self.original_wallpaper:
            self.set_wallpaper(self.original_wallpaper)
        self.stop()
        self.save_config()
        QApplication.quit()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("icons/tray_icon.png")))
    app.setStyleSheet(QSS_STYLE)
    ex = LDBPlayer()
    sys.exit(app.exec())