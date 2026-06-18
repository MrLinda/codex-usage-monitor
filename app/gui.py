from __future__ import annotations

import json
import logging
import sys
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from urllib.request import urlopen

import pystray
from PIL import Image, ImageDraw, ImageTk

from app.config import Config, save_config

logger = logging.getLogger("codex_usage_monitor")

DASHBOARD_URL = "http://127.0.0.1:8765"


def _enable_dpi_awareness() -> float:
    """Windows 高 DPI 适配。

    在创建 Tk() 之前调用。返回当前显示器的缩放比例（96 DPI = 1.0），
    供 tk.call('tk', 'scaling', factor) 使用，让字体按真实 DPI 渲染，
    避免位图被 Windows 拉伸导致的模糊。
    """
    if sys.platform != "win32":
        return 1.0
    try:
        import ctypes
        # Per-Monitor V2：多显示器切换时也能重新适配
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)  # PER_MONITOR_AWARE_V2
        except Exception:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_DPI_AWARE
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
        # 读取主显示器的 DPI
        hdc = ctypes.windll.user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        ctypes.windll.user32.ReleaseDC(0, hdc)
        return max(1.0, dpi / 96.0)
    except Exception as e:
        logger.warning("DPI awareness 设置失败: %s", e)
        return 1.0


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


def create_icon_image(size: int = 64) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    s = size / 64
    draw.rounded_rectangle([4*s, 4*s, 60*s, 60*s], radius=12*s, fill="#1f6feb")
    points = [(16*s, 40*s), (24*s, 28*s), (32*s, 34*s), (40*s, 20*s), (48*s, 26*s)]
    draw.line(points, fill="white", width=int(2.5*s))
    for px, py in points[1:-1]:
        draw.ellipse([px-2.5*s, py-2.5*s, px+2.5*s, py+2.5*s], fill="white")
    draw.line([(16*s, 44*s), (48*s, 44*s)], fill="white", width=int(1.5*s))
    draw.line([(16*s, 20*s), (16*s, 44*s)], fill="white", width=int(1.5*s))
    return img


def _fmt_countdown(iso_str: str | None) -> str:
    if not iso_str:
        return "-"
    from datetime import datetime
    diff = datetime.fromisoformat(iso_str) - datetime.now(datetime.now().astimezone().tzinfo)
    total_min = int(diff.total_seconds() / 60)
    if total_min <= 0:
        return "已重置"
    days, remainder = divmod(total_min, 1440)
    hours, mins = divmod(remainder, 60)
    if days > 0:
        return f"{days}天{hours}小时{mins}分"
    if hours > 0:
        return f"{hours}小时{mins}分"
    return f"{mins}分钟"


def _fetch_quota() -> dict | None:
    try:
        print(f"[DEBUG] Fetching quota from {DASHBOARD_URL}/api/quota/status")
        logger.info("Fetching quota from %s/api/quota/status", DASHBOARD_URL)
        with urlopen(f"{DASHBOARD_URL}/api/quota/status", timeout=3) as resp:
            data = json.loads(resp.read())
            print(f"[DEBUG] Quota fetched: plan={data.get('plan_type')}")
            logger.info("Quota fetched: plan=%s", data.get("plan_type"))
            return data
    except Exception as e:
        print(f"[DEBUG] Failed to fetch quota: {e}")
        logger.error("Failed to fetch quota: %s", e)
        return None


class App:
    def __init__(self, config: Config | None = None):
        self.config = config
        # Tk() 之前必须先 set DPI awareness，否则字体会因位图缩放变糊
        self._dpi_scale = _enable_dpi_awareness()
        self.root = tk.Tk()
        # 让 tk 的逻辑像素跟随真实 DPI，所有像素 / 字号自动按比例放大
        self.root.tk.call("tk", "scaling", self._dpi_scale * 96.0 / 72.0)
        # 把 tk 的命名字体（messagebox / ttk.Spinbox / 默认控件）也换成中英文兼容的字体
        try:
            import tkinter.font as tkfont
            for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont", "TkSmallCaptionFont", "TkIconFont", "TkTooltipFont"):
                try:
                    tkfont.nametofont(name).configure(family="Microsoft YaHei UI")
                except tk.TclError:
                    pass
        except Exception as e:
            logger.warning("命名字体配置失败: %s", e)
        self.root.title("Codex Usage Monitor")
        # 主窗口物理尺寸也按 DPI 放大，避免 100% 时正常但 150% 时窗口偏小
        w = int(600 * self._dpi_scale)
        h = int(400 * self._dpi_scale)
        self.root.geometry(f"{w}x{h}")
        self.root.configure(bg="#0d1117")
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.protocol("WM_DELETE_WINDOW", self._minimize_to_tray)

        self._icon_img = create_icon_image(64)
        self._icon_photo = ImageTk.PhotoImage(self._icon_img)
        self.root.iconphoto(True, self._icon_photo)

        self._popup = None

        self._build_ui()
        self._setup_logging()
        self._setup_tray()

    def _build_ui(self):
        top_frame = tk.Frame(self.root, bg="#161b22", pady=8, padx=12)
        top_frame.pack(fill=tk.X)

        tk.Label(
            top_frame, text="Codex Usage Monitor", fg="#f0f6fc",
            bg="#161b22", font=("Microsoft YaHei UI", 14, "bold"),
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

        tk.Button(
            top_frame, text="设置", command=self._open_settings,
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
        icon_image = create_icon_image(64)
        # 左键单击在 Windows 上不会触发 on_click，而是调用菜单里第一个
        # default=True 的项。这里放一个不可见的默认项来承接左键点击 → 弹窗。
        menu = pystray.Menu(
            pystray.MenuItem(
                "显示额度弹窗",
                lambda icon: self.root.after(0, self._show_popup),
                default=True,
                visible=False,
            ),
            pystray.MenuItem("打开控制台", lambda icon: self.root.after(0, self._open_dashboard)),
            pystray.MenuItem("显示窗口", lambda icon: self.root.after(0, self._show_window)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", lambda icon: self.root.after(0, self._quit)),
        )
        icon = pystray.Icon("codex-monitor", icon_image, "Codex Usage Monitor", menu)
        return icon

    def _show_popup(self):
        print("[DEBUG] _show_popup called")
        logger.info("_show_popup called")
        if self._popup and self._popup.winfo_exists():
            logger.info("Destroying existing popup")
            self._popup.destroy()
            self._popup = None
            return

        popup = tk.Toplevel(self.root)
        self._popup = popup
        popup.overrideredirect(True)
        popup.configure(bg="#161b22")
        popup.attributes("-topmost", True)

        loading = tk.Label(popup, text="加载中...", fg="#8b949e", bg="#161b22", font=("Microsoft YaHei UI", 10), padx=24, pady=20)
        loading.pack()
        popup.update_idletasks()
        pw, ph = popup.winfo_reqwidth(), popup.winfo_reqheight()
        sx, sy = popup.winfo_screenwidth(), popup.winfo_screenheight()
        popup.geometry(f"{pw}x{ph}+{sx - pw - 16}+{sy - ph - 48}")
        popup.bind("<FocusOut>", lambda e: popup.after(100, self._close_popup))
        popup.focus_force()

        threading.Thread(target=self._load_popup_data, args=(popup,), daemon=True).start()

    def _load_popup_data(self, popup):
        print("[DEBUG] _load_popup_data started")
        q = _fetch_quota()
        print(f"[DEBUG] _load_popup_data result: {q is not None}")
        logger.info("Popup data fetched: %s", "ok" if q else "none")
        if not popup.winfo_exists():
            print("[DEBUG] popup destroyed before data arrived")
            return
        self.root.after(0, self._render_popup_content, popup, q)

    def _render_popup_content(self, popup, q):
        if not popup.winfo_exists():
            return

        for w in popup.winfo_children():
            w.destroy()

        if not q:
            content = tk.Frame(popup, bg="#161b22", padx=24, pady=20)
            content.pack()
            tk.Label(content, text="暂无数据", fg="#8b949e", bg="#161b22", font=("Microsoft YaHei UI", 10)).pack()
            tk.Button(content, text="关闭", command=popup.destroy, bg="#21262d", fg="#c9d1d9", relief=tk.FLAT, padx=8, pady=2, font=("Microsoft YaHei UI", 9), cursor="hand2").pack(pady=(8, 0))
            return

        fh_pct = q.get("five_hour_remaining_pct")
        wk_pct = q.get("weekly_remaining_pct")
        fh_reset = q.get("five_hour_reset_at")
        wk_reset = q.get("weekly_reset_at")
        email = q.get("email", "")
        plan = q.get("plan_type", "-")

        content = tk.Frame(popup, bg="#161b22", padx=16, pady=12)
        content.pack()

        if email:
            tk.Label(content, text=email, fg="#8b949e", bg="#161b22", font=("Microsoft YaHei UI", 9)).pack(anchor="w")
        tk.Label(content, text=f"套餐: {plan}", fg="#f0f6fc", bg="#161b22", font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w", pady=(0, 8))

        tk.Label(content, text="5 小时剩余", fg="#8b949e", bg="#161b22", font=("Microsoft YaHei UI", 9)).pack(anchor="w")
        bar_frame_5h = tk.Frame(content, bg="#161b22")
        bar_frame_5h.pack(fill=tk.X, pady=(0, 2))
        pct_5h = int(fh_pct) if fh_pct is not None else 0
        c_5h = "#3fb950" if pct_5h > 30 else "#d29922" if pct_5h > 15 else "#f85149"
        bg_bar = tk.Frame(bar_frame_5h, bg="#21262d", height=6)
        bg_bar.pack(fill=tk.X, side=tk.LEFT, expand=True)
        fg_bar = tk.Frame(bg_bar, bg=c_5h, height=6)
        fg_bar.place(x=0, y=0, relwidth=max(0.01, pct_5h / 100), relheight=1)
        tk.Label(bar_frame_5h, text=f"{pct_5h}%", fg=c_5h, bg="#161b22", font=("Microsoft YaHei UI", 9), width=4).pack(side=tk.LEFT, padx=(6, 0))
        tk.Label(content, text=f"  还剩 {_fmt_countdown(fh_reset)}", fg="#8b949e", bg="#161b22", font=("Microsoft YaHei UI", 9)).pack(anchor="w", pady=(0, 6))

        tk.Label(content, text="周剩余", fg="#8b949e", bg="#161b22", font=("Microsoft YaHei UI", 9)).pack(anchor="w")
        bar_frame_wk = tk.Frame(content, bg="#161b22")
        bar_frame_wk.pack(fill=tk.X, pady=(0, 2))
        pct_wk = int(wk_pct) if wk_pct is not None else 0
        c_wk = "#3fb950" if pct_wk > 30 else "#d29922" if pct_wk > 15 else "#f85149"
        bg_bar_wk = tk.Frame(bar_frame_wk, bg="#21262d", height=6)
        bg_bar_wk.pack(fill=tk.X, side=tk.LEFT, expand=True)
        fg_bar_wk = tk.Frame(bg_bar_wk, bg=c_wk, height=6)
        fg_bar_wk.place(x=0, y=0, relwidth=max(0.01, pct_wk / 100), relheight=1)
        tk.Label(bar_frame_wk, text=f"{pct_wk}%", fg=c_wk, bg="#161b22", font=("Microsoft YaHei UI", 9), width=4).pack(side=tk.LEFT, padx=(6, 0))
        tk.Label(content, text=f"  还剩 {_fmt_countdown(wk_reset)}", fg="#8b949e", bg="#161b22", font=("Microsoft YaHei UI", 9)).pack(anchor="w", pady=(0, 6))

        btn_frame = tk.Frame(content, bg="#161b22")
        btn_frame.pack(fill=tk.X, pady=(4, 0))
        tk.Button(btn_frame, text="打开控制台", command=lambda: [popup.destroy(), self._open_dashboard()], bg="#1f6feb", fg="white", relief=tk.FLAT, padx=8, pady=2, font=("Microsoft YaHei UI", 9), cursor="hand2").pack(side=tk.LEFT)
        tk.Button(btn_frame, text="显示窗口", command=lambda: [popup.destroy(), self._show_window()], bg="#21262d", fg="#c9d1d9", relief=tk.FLAT, padx=8, pady=2, font=("Microsoft YaHei UI", 9), cursor="hand2").pack(side=tk.LEFT, padx=(8, 0))

        popup.update_idletasks()
        pw, ph = popup.winfo_reqwidth(), popup.winfo_reqheight()
        sx, sy = popup.winfo_screenwidth(), popup.winfo_screenheight()
        popup.geometry(f"{pw}x{ph}+{sx - pw - 16}+{sy - ph - 48}")

    def _close_popup(self):
        if self._popup and self._popup.winfo_exists():
            focused = self._popup.focus_get()
            if focused is None or not str(focused).startswith(str(self._popup)):
                self._popup.destroy()
                self._popup = None

    def _open_dashboard(self):
        import webbrowser
        webbrowser.open(DASHBOARD_URL)

    def _open_settings(self):
        if self.config is None:
            messagebox.showwarning("设置", "未加载配置，无法编辑")
            return
        SettingsDialog(self.root, self.config)

    def _minimize_to_tray(self):
        self.root.withdraw()

    def _show_window(self):
        self.root.after(0, self.root.deiconify)

    def _quit(self):
        self._tray_icon.stop()
        self.root.after(0, self.root.destroy)

    def run(self):
        self.root.mainloop()


class SettingsDialog:
    """模态设置子窗口。

    目前包含：
    - token 采集间隔（秒）
    - 额度采集间隔（分钟）

    保存时：写入 config.toml 持久化，并热更新内存中的 Config 与正在运行的 Poller。
    """

    def __init__(self, parent: tk.Tk, config: Config):
        self.config = config
        self.top = tk.Toplevel(parent)
        self.top.title("设置")
        self.top.configure(bg="#0d1117")
        self.top.transient(parent)
        self.top.grab_set()  # 模态

        self.token_var = tk.IntVar(value=config.app.poll_interval_seconds)
        self.quota_var = tk.IntVar(value=config.app.quota_interval_minutes)

        self._build_ui()

        # 居中
        self.top.update_idletasks()
        w, h = self.top.winfo_reqwidth(), self.top.winfo_reqheight()
        sx, sy = self.top.winfo_screenwidth(), self.top.winfo_screenheight()
        self.top.geometry(f"{w}x{h}+{(sx - w) // 2}+{(sy - h) // 2}")
        self.top.resizable(False, False)

    def _build_ui(self):
        body = tk.Frame(self.top, bg="#0d1117", padx=20, pady=16)
        body.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            body, text="采集间隔", fg="#f0f6fc", bg="#0d1117",
            font=("Microsoft YaHei UI", 11, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        # token 间隔
        tk.Label(
            body, text="Token 采集间隔（秒）", fg="#c9d1d9", bg="#0d1117",
            font=("Microsoft YaHei UI", 9),
        ).grid(row=1, column=0, sticky="w", pady=4)
        token_spin = ttk.Spinbox(body, from_=10, to=14400, increment=10, textvariable=self.token_var, width=8)
        token_spin.grid(row=1, column=1, sticky="w", padx=(8, 0))
        tk.Label(
            body, text="读取 ~/.codex/sessions 的 token 用量（常用：60=1m, 600=10m, 1800=30m）", fg="#6e7681",
            bg="#0d1117", font=("Microsoft YaHei UI", 8),
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 8))

        # quota 间隔
        tk.Label(
            body, text="额度采集间隔（分钟）", fg="#c9d1d9", bg="#0d1117",
            font=("Microsoft YaHei UI", 9),
        ).grid(row=3, column=0, sticky="w", pady=4)
        quota_spin = ttk.Spinbox(body, from_=1, to=240, textvariable=self.quota_var, width=8)
        quota_spin.grid(row=3, column=1, sticky="w", padx=(8, 0))
        tk.Label(
            body, text="调用 ChatGPT API 获取 5h / 周配额", fg="#6e7681",
            bg="#0d1117", font=("Microsoft YaHei UI", 8),
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(0, 12))

        # 按钮
        btn_frame = tk.Frame(body, bg="#0d1117")
        btn_frame.grid(row=5, column=0, columnspan=3, sticky="e", pady=(8, 0))
        tk.Button(
            btn_frame, text="取消", command=self._on_cancel,
            bg="#21262d", fg="#c9d1d9", relief=tk.FLAT, padx=14, pady=4,
            cursor="hand2",
        ).pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(
            btn_frame, text="保存", command=self._on_save,
            bg="#1f6feb", fg="white", relief=tk.FLAT, padx=14, pady=4,
            cursor="hand2",
        ).pack(side=tk.RIGHT)

    def _on_cancel(self):
        self.top.destroy()

    def _on_save(self):
        try:
            token_sec = int(self.token_var.get())
            quota_min = int(self.quota_var.get())
        except (tk.TclError, ValueError):
            messagebox.showerror("设置", "间隔必须是整数")
            return
        if token_sec < 10:
            messagebox.showerror("设置", "Token 采集间隔必须 >= 10 秒")
            return
        if quota_min < 1:
            messagebox.showerror("设置", "额度采集间隔必须 >= 1 分钟")
            return

        # 1) 持久化到 config.toml
        self.config.app.poll_interval_seconds = token_sec
        self.config.app.quota_interval_minutes = quota_min
        try:
            save_config(self.config)
        except Exception as e:
            logger.error("保存 config.toml 失败: %s", e)
            messagebox.showerror("设置", f"保存失败: {e}")
            return

        # 2) 热更新正在运行的 poller
        try:
            import app.server.api as api_module
            if api_module._poller is not None:
                api_module._poller.quota_interval_minutes = quota_min
                # poll_interval_seconds 通过 self.config.app 引用，已在 1) 中更新；
                # poller 每轮重算 step，下个采集周期生效
        except Exception as e:
            logger.warning("热更新 poller 失败（重启后生效）: %s", e)

        logger.info("设置已保存：token=%d 秒, 额度=%d 分钟", token_sec, quota_min)
        self.top.destroy()
