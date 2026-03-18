import logging
import os

try:
    from PyQt5.QtCore import QObject, pyqtSignal
    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False

if HAS_PYQT:
    class LogSignalProxy(QObject):
        """Proxy to safely emit signals from logging thread to GUI."""
        log_msg_signal = pyqtSignal(str)
    
    log_proxy = LogSignalProxy()

    class GuiLogHandler(logging.Handler):
        """Custom logging handler to send logs to the PyQt GUI."""
        def emit(self, record):
            msg = self.format(record)
            if log_proxy:
                log_proxy.log_msg_signal.emit(msg)
else:
    log_proxy = None

def setup_logger():
    """Sets up global logging configuration."""
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    logger = logging.getLogger("MediaBot")
    logger.setLevel(logging.INFO)

    # Avoid adding handlers multiple times when reloading
    if not logger.handlers:
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

        # File handler
        file_handler = logging.FileHandler(os.path.join(logs_dir, "app.log"), encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # GUI handler (only if PyQt5 is available)
        if HAS_PYQT:
            gui_handler = GuiLogHandler()
            gui_handler.setFormatter(formatter)
            logger.addHandler(gui_handler)
        
    return logger

logger = setup_logger()
