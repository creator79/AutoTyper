"""
Auto Typer Pro - PyQt5 Edition
Author: Auto Typer Pro - Enhanced (adapted for Vivek)
Version: 3.0.0

Requirements:
    pip install pyqt5 pynput pyautogui psutil
    (optional on Windows) pip install pywin32

Notes:
 - This uses pynput.GlobalHotKeys to register a start/stop hotkey pair.
 - Start Delay (seconds) is user-editable and accepts floats >= 0.
 - Typing speed is seconds between keystrokes (0.000 to 2.0).
 - "Type in ANY window" disables window-focus checks; otherwise it will attempt to ensure user focused target window.
"""

import sys
import threading
import time
import json
import os
from datetime import datetime

from PyQt5 import QtWidgets, QtCore, QtGui

# Input emulation
import pyautogui

# Hotkeys
from pynput import keyboard

# Optional: Windows focus detection
WIN32_AVAILABLE = False
try:
    import win32gui
    import win32process
    WIN32_AVAILABLE = True
except Exception:
    WIN32_AVAILABLE = False

# Optional: psutil to help with process name lookup
try:
    import psutil
    PSUTIL_AVAILABLE = True
except Exception:
    PSUTIL_AVAILABLE = False

pyautogui.FAILSAFE = False  # disable moving mouse to corner to abort (user choice)


SETTINGS_FILE = "auto_typer_pyqt_settings.json"


# ---------------------------
# Utility Functions
# ---------------------------
def pretty_hotkey_display(hk_text: str) -> str:
    """Turn ctrl+shift+s -> Ctrl+Shift+S for display"""
    return "+".join(part.capitalize() for part in hk_text.split("+"))


def to_pynput_hotkey(hk_text: str) -> str:
    """
    Convert user style 'ctrl+shift+s' into pynput style '<ctrl>+<shift>+s'
    Minimal validation - caller should ensure non-empty.
    """
    parts = [p.strip().lower() for p in hk_text.split("+") if p.strip()]
    # last part is the key
    if len(parts) == 0:
        raise ValueError("Empty hotkey")
    if len(parts) == 1:
        # Single key - allowed but should be explicit
        return parts[0]
    converted = []
    for p in parts[:-1]:
        # modifiers
        if p in ("ctrl", "control"):
            converted.append("<ctrl>")
        elif p in ("alt",):
            converted.append("<alt>")
        elif p in ("shift",):
            converted.append("<shift>")
        else:
            # treat as literal modifier but wrap it
            converted.append(f"<{p}>")
    # append final key (do not wrap)
    converted.append(parts[-1])
    return "+".join(converted)


# ---------------------------
# Main Worker - Typing Logic
# ---------------------------
class TypingWorker(QtCore.QObject):
    """Typing worker runs in a separate thread and emits signals to update UI."""
    finished = QtCore.pyqtSignal(str)
    progress = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)

    def __init__(self, text: str, speed: float, language: str, start_delay: float,
                 stop_flag: threading.Event, type_any_window: bool):
        super().__init__()
        self.text = text
        self.speed = max(0.0, float(speed))
        self.language = language
        self.start_delay = max(0.0, float(start_delay))
        self.stop_flag = stop_flag
        self.type_any_window = type_any_window

    # Simple formatting functions (preserve indentation, remove trailing whitespace lines)
    def format_python(self, txt):
        lines = txt.splitlines()
        # keep indentation; just strip trailing spaces
        return "\n".join(line.rstrip() for line in lines)

    def format_c_style(self, txt):
        lines = txt.splitlines()
        return "\n".join(line.rstrip() for line in lines)

    def format_text(self, txt):
        return txt.rstrip("\n")

    def run(self):
        try:
            # Pre-format based on language
            if self.language == "python":
                text = self.format_python(self.text)
            elif self.language in ("c++", "java", "javascript", "c#"):
                text = self.format_c_style(self.text)
            else:
                text = self.format_text(self.text)

            # Inform starting
            self.progress.emit(f"Starting in {self.start_delay:.3f} s. Click in target window.")
            # Wait for start_delay but allow early stop
            waited = 0.0
            wait_step = 0.05
            while waited < self.start_delay:
                if self.stop_flag.is_set():
                    self.finished.emit("Stopped before typing (user requested stop).")
                    return
                time.sleep(wait_step)
                waited += wait_step

            # If focus checking is enabled, verify target window unless type_any_window is True.
            if not self.type_any_window and WIN32_AVAILABLE:
                # Try to get current foreground window process name for user info
                try:
                    fg = win32gui.GetForegroundWindow()
                    pid = win32process.GetWindowThreadProcessId(fg)[1]
                    proc_name = None
                    if PSUTIL_AVAILABLE:
                        proc_name = psutil.Process(pid).name()
                    self.progress.emit(f"Typing into process: {proc_name or pid}")
                except Exception:
                    # not fatal
                    pass

            # Type character by character with handling of tabs/newlines
            lines = text.split("\n")
            for li, line in enumerate(lines):
                if self.stop_flag.is_set():
                    self.finished.emit("Stopped by user during typing.")
                    return

                # Optionally verify that window focus hasn't changed and stop if so
                if not self.type_any_window and WIN32_AVAILABLE:
                    # Could check focus here if desired; for now we allow typing to continue
                    pass

                for ch in line:
                    if self.stop_flag.is_set():
                        self.finished.emit("Stopped by user during typing.")
                        return

                    if ch == "\t":
                        pyautogui.press("tab")
                    else:
                        # pyautogui.write supports sending strings
                        pyautogui.write(ch)
                    # sleep between keystrokes; keep responsive to stop_flag
                    slept = 0.0
                    while slept < self.speed:
                        if self.stop_flag.is_set():
                            self.finished.emit("Stopped by user during typing.")
                            return
                        step = min(0.01, self.speed - slept)
                        time.sleep(step)
                        slept += step

                # After each line except last, press enter
                if li < len(lines) - 1:
                    pyautogui.press("enter")
                    # short pause for newline
                    slept = 0.0
                    nl_delay = max(0.001, self.speed * 0.6)
                    while slept < nl_delay:
                        if self.stop_flag.is_set():
                            self.finished.emit("Stopped by user during typing.")
                            return
                        time.sleep(0.01)
                        slept += 0.01

            self.finished.emit("Typing completed successfully.")
        except Exception as e:
            self.error.emit(f"Typing error: {e}")


# ---------------------------
# Main Application UI
# ---------------------------
class AutoTyperWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Auto Typer Pro - Created By Vivek Upadhyay")
        self.setMinimumSize(900, 720)
        # icon could be set if provided:
        # self.setWindowIcon(QtGui.QIcon("icon.ico"))

        # Application state
        self.is_typing = False
        self.typing_thread = None
        self.typing_worker = None
        self.stop_event = threading.Event()

        # Hotkey listener
        self.hotkey_listener = None

        # Default settings
        self.settings = {
            "typing_speed": 0.05,
            "language": "text",
            "start_hotkey": "ctrl+shift+s",
            "stop_hotkey": "ctrl+shift+x",
            "hotkeys_enabled": True,
            "start_delay": 3.0,
            "type_any_window": True
        }

        self.load_settings()

        self._build_ui()
        if self.settings.get("hotkeys_enabled", True):
            self.start_hotkey_listener()

    def _build_ui(self):
        # Central widget
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Title
        title = QtWidgets.QLabel("Auto Typer Pro - Created By Vivek Upadhyay")
        title.setFont(QtGui.QFont("Segoe UI", 18, QtGui.QFont.Bold))
        layout.addWidget(title)

        # Status bar like widget
        self.status_label = QtWidgets.QLabel("Ready")
        self.status_label.setStyleSheet("background:#2d2d2d;color:#e8e8e8;padding:8px;border-radius:6px;")
        layout.addWidget(self.status_label)

        # Text edit area with Save/Load
        text_frame = QtWidgets.QFrame()
        text_frame.setStyleSheet("background:#1f1f1f;border-radius:8px;padding:8px;")
        tf_layout = QtWidgets.QVBoxLayout(text_frame)
        tf_layout.setContentsMargins(6, 6, 6, 6)

        header_layout = QtWidgets.QHBoxLayout()
        hlabel = QtWidgets.QLabel("Text to Type:")
        hlabel.setFont(QtGui.QFont("Segoe UI", 11, QtGui.QFont.Bold))
        header_layout.addWidget(hlabel)
        header_layout.addStretch()

        save_btn = QtWidgets.QPushButton("💾 Save")
        save_btn.clicked.connect(self.save_text)
        load_btn = QtWidgets.QPushButton("📁 Load")
        load_btn.clicked.connect(self.load_text)
        header_layout.addWidget(save_btn)
        header_layout.addWidget(load_btn)
        tf_layout.addLayout(header_layout)

        self.text_edit = QtWidgets.QPlainTextEdit()
        self.text_edit.setPlainText(self._default_placeholder())
        self.text_edit.setFont(QtGui.QFont("Consolas", 11))
        tf_layout.addWidget(self.text_edit)

        layout.addWidget(text_frame, stretch=1)

        # Controls (Start/Stop/Clear)
        controls = QtWidgets.QHBoxLayout()
        self.start_btn = QtWidgets.QPushButton("▶ Start Typing")
        self.start_btn.setFixedHeight(40)
        self.start_btn.clicked.connect(self.on_start_clicked)
        self.stop_btn = QtWidgets.QPushButton("⏹ Stop Typing")
        self.stop_btn.setFixedHeight(40)
        self.stop_btn.clicked.connect(self.on_stop_clicked)
        self.clear_btn = QtWidgets.QPushButton("🗑 Clear Text")
        self.clear_btn.setFixedHeight(40)
        self.clear_btn.clicked.connect(self.on_clear_clicked)
        controls.addWidget(self.start_btn)
        controls.addWidget(self.stop_btn)
        controls.addWidget(self.clear_btn)
        layout.addLayout(controls)

        # Settings area
        settings_frame = QtWidgets.QFrame()
        settings_frame.setStyleSheet("background:#2b2b2b;border-radius:8px;padding:8px;")
        s_layout = QtWidgets.QGridLayout(settings_frame)
        s_layout.setColumnStretch(1, 1)

        # Typing speed slider
        s_layout.addWidget(QtWidgets.QLabel("Typing Speed (s per keystroke):"), 0, 0)
        self.speed_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.speed_slider.setMinimum(0)
        self.speed_slider.setMaximum(2000)  # maps to 0.000 - 2.000 seconds
        self.speed_slider.setSingleStep(1)
        self.speed_slider.setValue(int(self.settings.get("typing_speed", 0.05) * 1000))
        self.speed_slider.valueChanged.connect(self.on_speed_changed)
        s_layout.addWidget(self.speed_slider, 0, 1)
        self.speed_label = QtWidgets.QLabel(f"{self.settings.get('typing_speed', 0.05):.3f}s")
        s_layout.addWidget(self.speed_label, 0, 2)

        # Speed presets
        preset_row = QtWidgets.QHBoxLayout()
        for name, speed in [("Ultra Fast", 0.001), ("Very Fast", 0.01), ("Fast", 0.03),
                            ("Normal", 0.05), ("Slow", 0.1), ("Very Slow", 0.3)]:
            b = QtWidgets.QPushButton(name)
            b.setFixedHeight(28)
            b.clicked.connect(lambda _, sp=speed: self.set_speed_preset(sp))
            preset_row.addWidget(b)
        s_layout.addLayout(preset_row, 1, 0, 1, 3)

        # Language formatting combo
        s_layout.addWidget(QtWidgets.QLabel("Language Formatting:"), 2, 0)
        self.lang_combo = QtWidgets.QComboBox()
        self.lang_combo.addItems(["text", "python", "c++", "java", "javascript", "c#"])
        self.lang_combo.setCurrentText(self.settings.get("language", "text"))
        s_layout.addWidget(self.lang_combo, 2, 1)

        # Start delay input
        s_layout.addWidget(QtWidgets.QLabel("Start Delay (seconds):"), 3, 0)
        self.delay_input = QtWidgets.QDoubleSpinBox()
        self.delay_input.setRange(0.0, 60.0)
        self.delay_input.setDecimals(3)
        self.delay_input.setSingleStep(0.1)
        self.delay_input.setValue(self.settings.get("start_delay", 3.0))
        s_layout.addWidget(self.delay_input, 3, 1)

        # Type in any window checkbox
        self.any_window_checkbox = QtWidgets.QCheckBox("Type in ANY window (disable focus checking)")
        self.any_window_checkbox.setChecked(self.settings.get("type_any_window", True))
        s_layout.addWidget(self.any_window_checkbox, 4, 0, 1, 3)

        layout.addWidget(settings_frame)

        # Hotkey config
        hk_frame = QtWidgets.QFrame()
        hk_frame.setStyleSheet("background:#242424;border-radius:8px;padding:8px;")
        hk_layout = QtWidgets.QHBoxLayout(hk_frame)

        self.hotkey_enable_cb = QtWidgets.QCheckBox("Enable Global Hotkeys")
        self.hotkey_enable_cb.setChecked(self.settings.get("hotkeys_enabled", True))
        self.hotkey_enable_cb.stateChanged.connect(self.on_hotkey_toggle)
        hk_layout.addWidget(self.hotkey_enable_cb)

        hk_layout.addStretch()

        self.start_hotkey_input = QtWidgets.QLineEdit(self.settings.get("start_hotkey", "ctrl+shift+s"))
        self.stop_hotkey_input = QtWidgets.QLineEdit(self.settings.get("stop_hotkey", "ctrl+shift+x"))
        self.start_hotkey_input.setFixedWidth(150)
        self.stop_hotkey_input.setFixedWidth(150)
        hk_layout.addWidget(QtWidgets.QLabel("Start Hotkey:"))
        hk_layout.addWidget(self.start_hotkey_input)
        hk_layout.addWidget(QtWidgets.QLabel("Stop Hotkey:"))
        hk_layout.addWidget(self.stop_hotkey_input)

        apply_hk_btn = QtWidgets.QPushButton("Apply Hotkeys")
        apply_hk_btn.clicked.connect(self.on_apply_hotkeys)
        hk_layout.addWidget(apply_hk_btn)

        layout.addWidget(hk_frame)

        # Tips / bottom area
        tips = QtWidgets.QLabel("Tips: Click target window before starting. Use 'Type in ANY window' when switching windows.")
        tips.setStyleSheet("color:#bdbdbd;")
        layout.addWidget(tips)

        # Connect default UI states
        self.on_speed_changed()  # update label

        # Shortcut-style aesthetics
        self._style_buttons()

        # Close behaviour
        self.close_action = QtWidgets.QAction(self)
        self.close_action.triggered.connect(self.closeEvent)
        # Save settings on close
        self.aboutToQuit = False

    def _style_buttons(self):
        # Basic modern styling for buttons
        btns = self.findChildren(QtWidgets.QPushButton)
        for b in btns:
            b.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
            b.setStyleSheet("""
                QPushButton {
                    background: #007acc;
                    color: white;
                    border-radius: 6px;
                    padding: 6px 12px;
                }
                QPushButton:hover { background: #005fa3; }
            """)

        # special style for Stop (make red)
        self.stop_btn.setStyleSheet("""
            QPushButton { background: #f44336;color:white;border-radius:6px;padding:6px 12px; }
            QPushButton:hover { background:#d32f2f; }
        """)
        # Clear as orange
        self.clear_btn.setStyleSheet("""
            QPushButton { background: #ff9800;color:white;border-radius:6px;padding:6px 12px; }
            QPushButton:hover { background:#fb8c00; }
        """)

    def _default_placeholder(self):
        return (
            "Welcome to Auto Typer Pro - PyQt5 Edition!\n\n"
            "This improved version supports:\n"
            "✓ Start Delay (custom seconds)\n"
            "✓ Typing speed presets and fine control (0.001s -> 2s)\n"
            "✓ Global hotkeys (configurable)\n"
            "✓ Formatting for code snippets (python, c++, java, js, c#)\n\n"
            "Example (C++):\n"
            "#include <iostream>\nusing namespace std;\n\nint main() {\n    cout << \"Hello, World!\" << endl;\n    return 0;\n}\n"
        )

    # ---------------------------
    # UI Event Handlers
    # ---------------------------
    def on_speed_changed(self):
        value = self.speed_slider.value() / 1000.0
        self.speed_label.setText(f"{value:.3f}s")
        self.settings['typing_speed'] = value

    def set_speed_preset(self, s):
        self.speed_slider.setValue(int(s * 1000))
        self.settings['typing_speed'] = s
        self.on_speed_changed()

    def on_start_clicked(self):
        if self.is_typing:
            self._set_status("Typing already in progress.")
            return
        text = self.text_edit.toPlainText()
        if not text.strip():
            QtWidgets.QMessageBox.warning(self, "Warning", "Please enter some text to type.")
            return

        # start typing
        self.stop_event.clear()
        self.start_typing(text)

    def on_stop_clicked(self):
        if self.is_typing:
            self.stop_event.set()
            self._set_status("Stopping...")
        else:
            self._set_status("No typing in progress.")

    def on_clear_clicked(self):
        ok = QtWidgets.QMessageBox.question(self, "Confirm", "Clear all text?")
        if ok == QtWidgets.QMessageBox.Yes:
            self.text_edit.clear()

    def on_hotkey_toggle(self, state):
        enabled = bool(state == QtCore.Qt.Checked)
        self.settings['hotkeys_enabled'] = enabled
        if enabled:
            self.start_hotkey_listener()
            self._set_status("Global hotkeys enabled.")
        else:
            self.stop_hotkey_listener()
            self._set_status("Global hotkeys disabled.")

    def on_apply_hotkeys(self):
        start_hk = self.start_hotkey_input.text().strip().lower()
        stop_hk = self.stop_hotkey_input.text().strip().lower()
        if not start_hk or not stop_hk:
            QtWidgets.QMessageBox.critical(self, "Error", "Please enter both start and stop hotkeys.")
            return
        if start_hk == stop_hk:
            QtWidgets.QMessageBox.critical(self, "Error", "Start and stop hotkeys must be different.")
            return
        # Basic validation: must include at least a key and one modifier (recommended)
        self.settings['start_hotkey'] = start_hk
        self.settings['stop_hotkey'] = stop_hk
        self.save_settings()
        self.restart_hotkey_listener()
        self._set_status(f"Hotkeys applied: Start={pretty_hotkey_display(start_hk)} Stop={pretty_hotkey_display(stop_hk)}")

    # ---------------------------
    # Typing orchestration
    # ---------------------------
    def start_typing(self, text):
        self.is_typing = True
        self._set_status("Preparing to type...")
        self._toggle_ui_running(True)
        # create worker
        speed = self.settings.get('typing_speed', 0.05)
        lang = self.lang_combo.currentText()
        start_delay = float(self.delay_input.value())
        type_any = bool(self.any_window_checkbox.isChecked())
        self.stop_event.clear()

        self.typing_worker = TypingWorker(
            text=text,
            speed=speed,
            language=lang,
            start_delay=start_delay,
            stop_flag=self.stop_event,
            type_any_window=type_any
        )

        # move to a QThread
        self.typing_thread = QtCore.QThread()
        self.typing_worker.moveToThread(self.typing_thread)
        # connect signals
        self.typing_thread.started.connect(self.typing_worker.run)
        self.typing_worker.finished.connect(self.handle_typing_finished)
        self.typing_worker.progress.connect(self._set_status)
        self.typing_worker.error.connect(self.handle_typing_error)
        # ensure cleanup
        self.typing_worker.finished.connect(self.typing_thread.quit)
        self.typing_worker.finished.connect(self.typing_worker.deleteLater)
        self.typing_thread.finished.connect(self.typing_thread.deleteLater)
        # start
        self.typing_thread.start()

    def handle_typing_finished(self, msg: str):
        self.is_typing = False
        self._set_status(msg)
        self._toggle_ui_running(False)
        self.stop_event.clear()

    def handle_typing_error(self, err: str):
        self.is_typing = False
        self._set_status(err)
        self._toggle_ui_running(False)
        self.stop_event.clear()
        QtWidgets.QMessageBox.critical(self, "Typing Error", err)

    def _toggle_ui_running(self, running: bool):
        # disable/enable UI controls as appropriate while typing
        self.start_btn.setEnabled(not running)
        self.clear_btn.setEnabled(not running)
        self.start_hotkey_input.setEnabled(not running)
        self.stop_hotkey_input.setEnabled(not running)

    def _set_status(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.status_label.setText(f"[{ts}] {msg}")

    # ---------------------------
    # Hotkey management
    # ---------------------------
    def start_hotkey_listener(self):
        """Start global hotkeys using pynput.GlobalHotKeys"""
        # Stop existing listener
        self.stop_hotkey_listener()

        if not self.settings.get("hotkeys_enabled", True):
            return

        start_hk = self.settings.get("start_hotkey", "ctrl+shift+s")
        stop_hk = self.settings.get("stop_hotkey", "ctrl+shift+x")
        try:
            start_pyn = to_pynput_hotkey(start_hk)
            stop_pyn = to_pynput_hotkey(stop_hk)
        except Exception as e:
            self._set_status(f"Invalid hotkey format: {e}")
            return

        # Compose mapping
        mapping = {
            start_pyn: self._hotkey_start_trigger,
            stop_pyn: self._hotkey_stop_trigger
        }
        try:
            self.hotkey_listener = keyboard.GlobalHotKeys(mapping)
            self.hotkey_listener.start()
            self._set_status(f"Hotkeys registered: Start={pretty_hotkey_display(start_hk)} Stop={pretty_hotkey_display(stop_hk)}")
        except Exception as e:
            self._set_status(f"Failed to register hotkeys: {e}")

    def _hotkey_start_trigger(self):
        # callback from hotkey thread => call GUI in main thread
        QtCore.QMetaObject.invokeMethod(self, "_hotkey_start_in_main_thread", QtCore.Qt.QueuedConnection)

    def _hotkey_stop_trigger(self):
        QtCore.QMetaObject.invokeMethod(self, "_hotkey_stop_in_main_thread", QtCore.Qt.QueuedConnection)

    @QtCore.pyqtSlot()
    def _hotkey_start_in_main_thread(self):
        self.on_start_clicked()

    @QtCore.pyqtSlot()
    def _hotkey_stop_in_main_thread(self):
        self.on_stop_clicked()

    def stop_hotkey_listener(self):
        if self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
            except Exception:
                pass
            self.hotkey_listener = None

    def restart_hotkey_listener(self):
        self.stop_hotkey_listener()
        self.start_hotkey_listener()

    # ---------------------------
    # Save / Load text content
    # ---------------------------
    def save_text(self):
        text = self.text_edit.toPlainText()
        if not text.strip():
            QtWidgets.QMessageBox.warning(self, "Warning", "No text to save.")
            return
        # default filename with timestamp
        fname = QtWidgets.QFileDialog.getSaveFileName(self, "Save text", f"auto_typer_text_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "Text Files (*.txt);;All Files (*)")[0]
        if fname:
            try:
                with open(fname, "w", encoding="utf-8") as f:
                    f.write(text)
                QtWidgets.QMessageBox.information(self, "Saved", f"Text saved to {fname}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save file: {e}")

    def load_text(self):
        fname = QtWidgets.QFileDialog.getOpenFileName(self, "Open text file", "", "Text Files (*.txt);;All Files (*)")[0]
        if fname:
            try:
                with open(fname, "r", encoding="utf-8") as f:
                    data = f.read()
                self.text_edit.setPlainText(data)
                QtWidgets.QMessageBox.information(self, "Loaded", "Text loaded successfully.")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Failed to load file: {e}")

    # ---------------------------
    # Settings persistence
    # ---------------------------
    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # merge with defaults
                self.settings.update(data)
            except Exception:
                pass

    def save_settings(self):
        # gather latest values
        self.settings['typing_speed'] = self.speed_slider.value() / 1000.0
        self.settings['language'] = self.lang_combo.currentText()
        self.settings['start_hotkey'] = self.start_hotkey_input.text().strip()
        self.settings['stop_hotkey'] = self.stop_hotkey_input.text().strip()
        self.settings['hotkeys_enabled'] = self.hotkey_enable_cb.isChecked()
        self.settings['start_delay'] = float(self.delay_input.value())
        self.settings['type_any_window'] = bool(self.any_window_checkbox.isChecked())
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception:
            pass

    # ---------------------------
    # Close / cleanup
    # ---------------------------
    def closeEvent(self, event=None):
        # Ask if typing in progress
        if self.is_typing:
            ans = QtWidgets.QMessageBox.question(self, "Exit", "Typing is in progress. Stop and exit?")
            if ans != QtWidgets.QMessageBox.Yes:
                if event:
                    event.ignore()
                return
        # stop threads and listeners
        self.stop_event.set()
        self.stop_hotkey_listener()
        self.save_settings()
        # ensure worker thread quits
        if self.typing_thread and self.typing_thread.isRunning():
            self.typing_thread.quit()
            self.typing_thread.wait(2000)
        if event:
            event.accept()

# ---------------------------
# App entrypoint
# ---------------------------
def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")

    # Optional dark palette for nicer look
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.Window, QtGui.QColor(30, 30, 30))
    palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(230, 230, 230))
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor(22, 22, 22))
    palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(45, 45, 45))
    palette.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor(255, 255, 255))
    palette.setColor(QtGui.QPalette.ToolTipText, QtGui.QColor(255, 255, 255))
    palette.setColor(QtGui.QPalette.Text, QtGui.QColor(230, 230, 230))
    palette.setColor(QtGui.QPalette.Button, QtGui.QColor(45, 45, 45))
    palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(230, 230, 230))
    app.setPalette(palette)

    window = AutoTyperWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
