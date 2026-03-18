import os
import sys
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QLineEdit, QTextEdit, QTabWidget, QFormLayout, 
    QMessageBox, QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QFont, QColor, QPalette

from utils.logger import log_proxy, logger
from config.settings import SettingsManager
from gui.worker import BotThread, ManualDownloadThread
from utils.database import init_db, get_recent_downloads, get_stats, clear_history

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_manager = SettingsManager()
        self.bot_thread = None
        self.dl_thread = None
        
        # Initialize SQLite DB
        init_db()
        
        self.init_ui()
        self.apply_dark_theme()
        
        # Connect signals
        log_proxy.log_msg_signal.connect(self.append_log)
        
        logger.info("Application initialized.")

    def init_ui(self):
        self.setWindowTitle('Media Downloader Bot')
        self.resize(800, 600)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Initialize Tabs
        self.tab_dashboard = QWidget()
        self.tab_manual_dl = QWidget()
        self.tab_history = QWidget()
        self.tab_settings = QWidget()
        
        self.tabs.addTab(self.tab_dashboard, "Bot Dashboard")
        self.tabs.addTab(self.tab_manual_dl, "Manual Download")
        self.tabs.addTab(self.tab_history, "Download History")
        self.tabs.addTab(self.tab_settings, "Settings")
        
        self.setup_dashboard_tab()
        self.setup_manual_dl_tab()
        self.setup_history_tab()
        self.setup_settings_tab()

        # Connect tab change to refresh history
        self.tabs.currentChanged.connect(self.on_tab_changed)

    def setup_dashboard_tab(self):
        layout = QVBoxLayout(self.tab_dashboard)
        
        # Control panel
        control_layout = QHBoxLayout()
        self.lbl_status = QLabel("Bot Status: OFFLINE")
        self.lbl_status.setFont(QFont("Arial", 12, QFont.Bold))
        self.lbl_status.setStyleSheet("color: #ff4757;")
        
        self.btn_start = QPushButton("Start Bot")
        self.btn_start.setMinimumHeight(40)
        self.btn_start.clicked.connect(self.start_bot)
        
        self.btn_stop = QPushButton("Stop Bot")
        self.btn_stop.setMinimumHeight(40)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_bot)
        
        control_layout.addWidget(self.lbl_status)
        control_layout.addStretch()
        control_layout.addWidget(self.btn_start)
        control_layout.addWidget(self.btn_stop)
        
        layout.addLayout(control_layout)
        
        # Stats panel
        self.lbl_stats = QLabel("Downloads: ? | Active Users: ?")
        self.lbl_stats.setFont(QFont("Arial", 10))
        self.lbl_stats.setStyleSheet("color: #74b9ff; margin-bottom: 5px;")
        layout.addWidget(self.lbl_stats)
        
        # Logs
        layout.addWidget(QLabel("Application Logs:"))
        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setStyleSheet("background-color: #1e1e1e; color: #a4b0be; font-family: 'Menlo', 'Consolas', monospace;")
        layout.addWidget(self.txt_logs)
        
        # Clear Logs Button
        btn_clear_logs = QPushButton("Clear Logs")
        btn_clear_logs.clicked.connect(lambda: self.txt_logs.clear())
        layout.addWidget(btn_clear_logs, alignment=Qt.AlignRight)

    def setup_manual_dl_tab(self):
        layout = QVBoxLayout(self.tab_manual_dl)
        
        form_layout = QFormLayout()
        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText("https://www.youtube.com/watch?v=...")
        form_layout.addRow("Video URL:", self.txt_url)
        layout.addLayout(form_layout)
        
        btns_layout = QHBoxLayout()
        self.btn_dl_vid = QPushButton("Download Video")
        self.btn_dl_vid.clicked.connect(lambda: self.start_manual_download(False))
        self.btn_dl_aud = QPushButton("Download Audio")
        self.btn_dl_aud.clicked.connect(lambda: self.start_manual_download(True))
        
        btns_layout.addWidget(self.btn_dl_vid)
        btns_layout.addWidget(self.btn_dl_aud)
        layout.addLayout(btns_layout)
        
        # Progress section
        self.lbl_progress = QLabel("Status: Idle")
        layout.addWidget(self.lbl_progress)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        layout.addStretch()

    def setup_history_tab(self):
        layout = QVBoxLayout(self.tab_history)
        
        self.table_history = QTableWidget(0, 5)
        self.table_history.setHorizontalHeaderLabels(["Filename", "URL", "Format", "Size (MB)", "Date"])
        self.table_history.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_history.setEditTriggers(QTableWidget.NoEditTriggers)
        
        layout.addWidget(self.table_history)
        
        # Top buttons
        btns = QHBoxLayout()
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.load_history)
        
        btn_clear = QPushButton("Clear History")
        btn_clear.clicked.connect(self.clear_all_history)
        btn_clear.setStyleSheet("background-color: #d63031;")
        
        btn_open_folder = QPushButton("Open Download Folder")
        btn_open_folder.clicked.connect(self.open_dl_folder)
        
        btns.addWidget(btn_refresh)
        btns.addWidget(btn_clear)
        btns.addWidget(btn_open_folder)
        layout.addLayout(btns)
        
        self.load_history()

    def setup_settings_tab(self):
        layout = QFormLayout(self.tab_settings)
        
        self.inp_token = QLineEdit(self.config_manager.get("bot_token", ""))
        self.inp_token.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        layout.addRow("Telegram Bot Token:", self.inp_token)
        
        dl_layout = QHBoxLayout()
        self.inp_dl_folder = QLineEdit(self.config_manager.get("download_path", "downloads/"))
        btn_browse_dl = QPushButton("Browse")
        btn_browse_dl.clicked.connect(self.browse_dl_folder)
        dl_layout.addWidget(self.inp_dl_folder)
        dl_layout.addWidget(btn_browse_dl)
        layout.addRow("Download Folder:", dl_layout)
        
        ff_layout = QHBoxLayout()
        self.inp_ff_path = QLineEdit(self.config_manager.get("ffmpeg_path", ""))
        self.inp_ff_path.setPlaceholderText("Path to folder containing ffmpeg.exe")
        btn_browse_ff = QPushButton("Browse")
        btn_browse_ff.clicked.connect(self.browse_ff_folder)
        ff_layout.addWidget(self.inp_ff_path)
        ff_layout.addWidget(btn_browse_ff)
        layout.addRow("FFmpeg Bin Path (Optional):", ff_layout)
        
        self.inp_max_size = QLineEdit(str(self.config_manager.get("max_file_size", 50)))
        layout.addRow("Max Telegram File Size (MB):", self.inp_max_size)
        
        btn_save = QPushButton("Save Settings")
        btn_save.clicked.connect(self.save_settings)
        btn_save.setMinimumHeight(40)
        layout.addRow("", btn_save)

    def apply_dark_theme(self):
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        app.setStyle("Fusion")
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(45, 45, 45))
        dark_palette.setColor(QPalette.WindowText, QColor(212, 212, 212))
        dark_palette.setColor(QPalette.Base, QColor(30, 30, 30))
        dark_palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, QColor(212, 212, 212))
        dark_palette.setColor(QPalette.Button, QColor(45, 45, 45))
        dark_palette.setColor(QPalette.ButtonText, QColor(212, 212, 212))
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        app.setPalette(dark_palette)
        self.setStyleSheet("""
            QPushButton { background-color: #0984e3; color: white; border: none; padding: 5px 15px; border-radius: 4px; }
            QPushButton:hover { background-color: #74b9ff; }
            QPushButton:disabled { background-color: #636e72; color: #b2bec3; }
            QLineEdit, QTextEdit, QTableWidget { border: 1px solid #636e72; padding: 4px; border-radius: 4px; }
            QTabWidget::pane { border: 1px solid #636e72; border-radius: 4px; }
            QTabBar::tab { background: #2d3436; color: #dfe6e9; padding: 8px 15px; margin-right: 2px; }
            QTabBar::tab:selected { background: #0984e3; }
        """)

    # --- Slot methods ---

    @pyqtSlot(str)
    def append_log(self, msg):
        self.txt_logs.append(msg)
        self.txt_logs.verticalScrollBar().setValue(self.txt_logs.verticalScrollBar().maximum())

    def start_bot(self):
        token = self.config_manager.get("bot_token")
        if not token:
            QMessageBox.warning(self, "Warning", "Please configure Telegram Bot Token in Settings first.")
            return
            
        self.bot_thread = BotThread(self.config_manager)
        self.bot_thread.status_signal.connect(self.update_bot_status)
        self.bot_thread.start()

    def stop_bot(self):
        if self.bot_thread:
            self.bot_thread.stop()

    @pyqtSlot(str)
    def update_bot_status(self, status):
        if status == "RUNNING":
            self.lbl_status.setText("Bot Status: ONLINE")
            self.lbl_status.setStyleSheet("color: #2ed573;")
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
        elif status == "STOPPED" or status == "ERROR":
            self.lbl_status.setText("Bot Status: OFFLINE")
            self.lbl_status.setStyleSheet("color: #ff4757;")
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)

    def start_manual_download(self, is_audio):
        url = self.txt_url.text().strip()
        if not url:
            QMessageBox.warning(self, "Warning", "Please enter a valid URL.")
            return
        
        self.btn_dl_vid.setEnabled(False)
        self.btn_dl_aud.setEnabled(False)
        self.progress_bar.setValue(0)
        self.lbl_progress.setText("Status: Downloading...")
        
        format_type = 'mp3' if is_audio else 'mp4'
        self.dl_thread = ManualDownloadThread(url, format_type, None, self.config_manager)
        self.dl_thread.progress_signal.connect(self.update_dl_progress)
        self.dl_thread.finished_signal.connect(self.dl_finished)
        self.dl_thread.start()

    @pyqtSlot(int, str, str)
    def update_dl_progress(self, percent, speed, eta):
        self.progress_bar.setValue(percent)
        self.lbl_progress.setText(f"Status: Downloading... {speed} ETA: {eta}")

    @pyqtSlot(bool, str)
    def dl_finished(self, success, msg):
        self.btn_dl_vid.setEnabled(True)
        self.btn_dl_aud.setEnabled(True)
        if success:
            self.lbl_progress.setText("Status: Finished")
            self.progress_bar.setValue(100)
            QMessageBox.information(self, "Success", msg)
        else:
            self.lbl_progress.setText("Status: Error")
            QMessageBox.critical(self, "Error", msg)

    def browse_dl_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Directory")
        if folder:
            self.inp_dl_folder.setText(folder)

    def browse_ff_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select FFmpeg bin Directory")
        if folder:
            self.inp_ff_path.setText(folder)

    def save_settings(self):
        self.config_manager.set("bot_token", self.inp_token.text().strip())
        self.config_manager.set("download_path", self.inp_dl_folder.text().strip())
        self.config_manager.set("ffmpeg_path", self.inp_ff_path.text().strip())
        try:
            self.config_manager.set("max_file_size", float(self.inp_max_size.text().strip()))
        except ValueError:
            pass
        
        QMessageBox.information(self, "Settings", "Settings saved successfully! Restart the bot if it was running.")
        logger.info("Settings saved by user.")

    def on_tab_changed(self, index):
        if index == 2:  # History tab
            self.load_history()

    def load_history(self):
        self.table_history.setRowCount(0)
        rows = get_recent_downloads()
        for i, row in enumerate(rows):
            self.table_history.insertRow(i)
            # filename, url, format, size_mb, download_date
            self.table_history.setItem(i, 0, QTableWidgetItem(row[0]))
            self.table_history.setItem(i, 1, QTableWidgetItem(row[1]))
            self.table_history.setItem(i, 2, QTableWidgetItem(row[2]))
            self.table_history.setItem(i, 3, QTableWidgetItem(f"{row[3]:.2f}"))
            self.table_history.setItem(i, 4, QTableWidgetItem(row[4]))
            
        try:
            dl_cnt, user_cnt = get_stats()
            self.lbl_stats.setText(f"Downloads: {dl_cnt} | Active Users: {user_cnt}")
        except Exception:
            pass

    def clear_all_history(self):
        clear_history()
        self.load_history()
        QMessageBox.information(self, "Success", "History has been cleared locally.")

    def open_dl_folder(self):
        folder = self.config_manager.get("download_path", "downloads/")
        if os.path.exists(folder):
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", folder])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", folder])

    def closeEvent(self, event):
        """Cleanup before window closes."""
        if self.bot_thread and self.bot_thread.isRunning():
            self.bot_thread.stop()
            self.bot_thread.wait()
        event.accept()

