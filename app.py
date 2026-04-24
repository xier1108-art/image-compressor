"""
사진 압축기 – entry point (PyQt6).

Run:
    python app.py
"""

import sys


# ── Silence subprocess console pop-ups on frozen Windows builds ──────────────
# When PyInstaller builds a `--windowed` (no-console) app on Windows, any
# subprocess started by the app (Pillow/pillow-heif/oxipng or our own tooling)
# briefly flashes a black cmd window. Patch subprocess.Popen globally to pass
# CREATE_NO_WINDOW by default so no console is allocated for children.
if sys.platform == "win32":
    import subprocess
    _CREATE_NO_WINDOW = 0x08000000
    _orig_popen = subprocess.Popen

    class _NoConsolePopen(_orig_popen):
        def __init__(self, *args, **kwargs):
            cf = kwargs.get("creationflags", 0) or 0
            kwargs["creationflags"] = cf | _CREATE_NO_WINDOW
            super().__init__(*args, **kwargs)

    subprocess.Popen = _NoConsolePopen


def main():
    from PyQt6.QtWidgets import QApplication
    from ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("사진 압축기")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
