from __future__ import annotations

import logging
import threading
import tkinter as tk
from tkinter import scrolledtext

import pystray
from PIL import Image, ImageDraw

logger = logging.getLogger("codex_usage_monitor")

DASHBOARD_URL = "http://127.0.0.1:8765"


class LogHandler(logging.Handler):
    def __init__(self, widget: scrolledtext.ScrolledText):
        super().__init__()
        self.widget = widget

    def emit(self, record):
        msg = self.format(record)
        self.widget.after(0, self._append, msg)

    def _append(self, msg):
        self.widget.configure(state="normal")
        self.widget.insert(tk.END, msg + "\n")
        self.widget.see(tk.END)
        self.widget.configure(state="disabled")


def create_tray_icon() -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([8, 8, 56, 56], radius=8, fill="#58a6ff")
    draw.text((20, 16), "C", fill="white")
    return img


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Codex Usage Monitor")
        self.root.geometry("600x400")
        self.root.configure(bg="#0d1117")
        self.root.protocol("WM_DELETE_WINDOW", self._minimize_to_tray)

        self._build_ui()
        self._setup_logging()
        self._setup_tray()

    def _build_ui(self):
        top_frame = tk.Frame(self.root, bg="#161b22", pady=8, padx=12)
        top_frame.pack(fill=tk.X)

        tk.Label(
            top_frame, text="Codex Usage Monitor", fg="#f0f6fc",
            bg="#161b22", font=("Segoe UI", 14, "bold"),
        ).pack(side=tk.LEFT)

        tk.Button(
            top_frame, text="打开控制台", command=self._open_dashboard,
            bg="#1f6feb", fg="white", relief=tk.FLAT, padx=12, pady=4,
            cursor="hand2",
        ).pack(side=tk.RIGHT, padx=(0, 8))

        tk.Button(
            top_frame, text="最小化到托盘", command=self._minimize_to_tray,
            bg="#21262d", fg="#c9d1d9", relief=tk.FLAT, padx=12, pady=4,
            cursor="hand2",
        ).pack(side=tk.RIGHT, padx=(0, 8))

        self.log_area = scrolledtext.ScrolledText(
            self.root, state="disabled", bg="#0d1117", fg="#c9d1d9",
            font=("Consolas", 10), relief=tk.FLAT, insertbackground="#c9d1d9",
        )
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    def _setup_logging(self):
        handler = LogHandler(self.log_area)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    def _setup_tray(self):
        self._tray_icon = self._create_tray_icon()
        threading.Thread(target=self._tray_icon.run, daemon=True).start()

    def _create_tray_icon(self):
        icon_image = create_tray_icon()
        menu = pystray.Menu(
            pystray.MenuItem("打开控制台", lambda: self._open_dashboard()),
            pystray.MenuItem("显示窗口", lambda: self._show_window()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", lambda: self._quit()),
        )
        icon = pystray.Icon("codex-monitor", icon_image, "Codex Usage Monitor", menu)
        icon.on_activate = lambda: self._show_window()
        return icon

    def _open_dashboard(self):
        import webbrowser
        webbrowser.open(DASHBOARD_URL)

    def _minimize_to_tray(self):
        self.root.withdraw()

    def _show_window(self):
        self.root.after(0, self.root.deiconify)

    def _quit(self):
        self._tray_icon.stop()
        self.root.after(0, self.root.destroy)

    def run(self):
        self.root.mainloop()
