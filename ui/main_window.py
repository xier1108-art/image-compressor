"""
Main application window for 사진 압축기.
All UI components: header, drop-zone, file list, quality selector,
format panel, action bar, and progress/result panel.
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import __version__ as PIL_VERSION

from core.utils import (
    format_size, get_output_path, ensure_dir, SUPPORTED_EXTENSIONS
)
from core.compressor import compress_image

# ---------------------------------------------------------------------------
# Design tokens  (identical to PDF compression tool)
# ---------------------------------------------------------------------------
BG         = "#FAFAFA"
ACCENT     = "#E74C3C"
ACCENT_DK  = "#C0392B"
TEXT       = "#2C3E50"
SUBTEXT    = "#95A5A6"
BORDER     = "#DCDDE1"
LIST_BG    = "#FFFFFF"
LIST_HDR   = "#F5F6FA"
ACTION_BG  = "#ECEFF1"
SUCCESS    = "#27AE60"
ERROR_CLR  = "#E74C3C"

_CANDIDATES = ["Malgun Gothic", "맑은 고딕", "Arial Unicode MS", "TkDefaultFont"]
FONT = _CANDIDATES[0]

# Output extension per output_format choice
_OUT_EXT = {
    "jpeg":    ".jpg",
    "webp":    ".webp",
    "original": None,   # keep source extension (special-cased for BMP)
}


class MainWindow:
    def __init__(self, root: tk.Tk, has_dnd: bool = False):
        self.root = root
        self.has_dnd = has_dnd
        self.files: dict = {}
        self.output_dir = os.path.join(os.path.expanduser("~"), "Desktop", "이미지압축결과")
        self.mode = tk.StringVar(value="recommended")
        self.output_format = tk.StringVar(value="jpeg")
        self.max_dim_enabled = tk.BooleanVar(value=False)
        self.max_dim_value = tk.StringVar(value="1920")
        self.is_compressing = False
        self._open_btn = None

        self._setup_window()
        self._setup_style()
        self._build_header()
        self._build_drop_zone()
        self._build_file_list()
        self._build_quality_panel()
        self._build_format_panel()
        self._build_action_bar()
        self._build_progress_panel()

    # ------------------------------------------------------------------
    # Window / style setup
    # ------------------------------------------------------------------

    def _setup_window(self):
        self.root.title("사진 압축기")
        self.root.geometry("720x660")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"720x660+{(sw-720)//2}+{(sh-660)//2}")

    def _setup_style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure("Files.Treeview",
                        background=LIST_BG, foreground=TEXT,
                        fieldbackground=LIST_BG,
                        font=(FONT, 9), rowheight=26)
        style.configure("Files.Treeview.Heading",
                        background=LIST_HDR, foreground=TEXT,
                        font=(FONT, 9, "bold"), relief="flat")
        style.map("Files.Treeview",
                  background=[("selected", "#EEF2FF")],
                  foreground=[("selected", TEXT)])

        style.configure("Red.Horizontal.TProgressbar",
                        background=ACCENT, troughcolor="#E0E0E0", thickness=8)

        style.configure("Mode.TRadiobutton",
                        background=BG, foreground=TEXT,
                        font=(FONT, 9))
        style.map("Mode.TRadiobutton",
                  background=[("active", BG)])

        style.configure("Mode.TCheckbutton",
                        background=BG, foreground=TEXT,
                        font=(FONT, 9))
        style.map("Mode.TCheckbutton",
                  background=[("active", BG)])

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=ACCENT, height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="  사진 압축기",
                 bg=ACCENT, fg="white",
                 font=(FONT, 14, "bold")).pack(side="left", padx=12, pady=12)

        tk.Label(hdr, text=f" Pillow {PIL_VERSION} ",
                 bg=ACCENT_DK, fg="white",
                 font=(FONT, 8, "bold"),
                 relief="flat", padx=4).pack(side="right", padx=8, pady=14)

    # ------------------------------------------------------------------
    # Drop zone
    # ------------------------------------------------------------------

    def _build_drop_zone(self):
        outer = tk.Frame(self.root, bg=BG, padx=16, pady=10)
        outer.pack(fill="x")

        self.drop_canvas = tk.Canvas(outer, width=688, height=100,
                                     bg=BG, highlightthickness=0,
                                     cursor="hand2")
        self.drop_canvas.pack()
        self._draw_drop_zone(active=False)

        self.drop_canvas.bind("<Button-1>", lambda _e: self._browse_files())
        self.drop_canvas.bind("<Enter>",    lambda _e: self._draw_drop_zone(active=True))
        self.drop_canvas.bind("<Leave>",    lambda _e: self._draw_drop_zone(active=False))

        if self.has_dnd:
            try:
                from tkinterdnd2 import DND_FILES
                self.drop_canvas.drop_target_register(DND_FILES)
                self.drop_canvas.dnd_bind("<<Drop>>", self._on_dnd_drop)
                self.drop_canvas.dnd_bind("<<DragEnter>>",
                                          lambda _e: self._draw_drop_zone(active=True))
                self.drop_canvas.dnd_bind("<<DragLeave>>",
                                          lambda _e: self._draw_drop_zone(active=False))
            except Exception:
                pass

    def _draw_drop_zone(self, *, active: bool):
        c = self.drop_canvas
        c.delete("all")
        border = ACCENT if active else BORDER
        fill   = "#FFF5F5" if active else BG

        c.configure(bg=fill)
        c.create_rectangle(2, 2, 686, 98,
                           outline=border, width=2, dash=(8, 4), fill=fill)

        arrow_clr = ACCENT if active else SUBTEXT
        c.create_text(344, 36, text="▼",
                      font=(FONT, 18), fill=arrow_clr)

        if self.has_dnd:
            main_txt = "이미지 파일을 여기에 드래그하거나 클릭하여 선택"
        else:
            main_txt = "클릭하여 이미지 파일 선택 (여러 파일 가능)"

        c.create_text(344, 66, text=main_txt,
                      font=(FONT, 9),
                      fill=TEXT if active else SUBTEXT)
        c.create_text(344, 84, text="※ 원본 파일은 변경되지 않습니다",
                      font=(FONT, 8), fill=SUBTEXT)

    # ------------------------------------------------------------------
    # File list
    # ------------------------------------------------------------------

    def _build_file_list(self):
        outer = tk.Frame(self.root, bg=BG, padx=16)
        outer.pack(fill="x")

        tk.Label(outer, text="파일 목록",
                 bg=BG, fg=TEXT,
                 font=(FONT, 9, "bold")).pack(anchor="w", pady=(0, 4))

        border_frame = tk.Frame(outer, bg=BORDER, padx=1, pady=1)
        border_frame.pack(fill="x")

        inner = tk.Frame(border_frame, bg=LIST_BG)
        inner.pack(fill="both")

        cols = ("filename", "original", "compressed", "ratio")
        self.tree = ttk.Treeview(inner, columns=cols,
                                  show="headings",
                                  style="Files.Treeview",
                                  height=5)

        self.tree.heading("filename",   text="파일명")
        self.tree.heading("original",   text="원본 크기")
        self.tree.heading("compressed", text="압축 크기")
        self.tree.heading("ratio",      text="압축률")

        self.tree.column("filename",   width=372, anchor="w",      stretch=False)
        self.tree.column("original",   width=94,  anchor="center", stretch=False)
        self.tree.column("compressed", width=94,  anchor="center", stretch=False)
        self.tree.column("ratio",      width=94,  anchor="center", stretch=False)

        sb = ttk.Scrollbar(inner, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.tree.bind("<Delete>", self._remove_selected)

        hint = tk.Frame(self.root, bg=BG, padx=16)
        hint.pack(fill="x")
        tk.Label(hint, text="Delete 키로 목록에서 제거",
                 bg=BG, fg=SUBTEXT, font=(FONT, 8)).pack(anchor="e")

    # ------------------------------------------------------------------
    # Quality panel
    # ------------------------------------------------------------------

    def _build_quality_panel(self):
        outer = tk.Frame(self.root, bg=BG, padx=16, pady=6)
        outer.pack(fill="x")

        tk.Label(outer, text="압축 수준:",
                 bg=BG, fg=TEXT,
                 font=(FONT, 9, "bold")).pack(side="left", padx=(0, 14))

        options = [
            ("extreme",     "극한  (최대 압축)"),
            ("recommended", "권장  (균형)"),
            ("low",         "저압축  (화질 우선)"),
        ]
        for value, label in options:
            ttk.Radiobutton(outer, text=label,
                            variable=self.mode, value=value,
                            style="Mode.TRadiobutton").pack(side="left", padx=10)

    # ------------------------------------------------------------------
    # Format panel (new vs PDF tool)
    # ------------------------------------------------------------------

    def _build_format_panel(self):
        outer = tk.Frame(self.root, bg=BG, padx=16, pady=4)
        outer.pack(fill="x")

        # Row 1: output format selection
        row1 = tk.Frame(outer, bg=BG)
        row1.pack(fill="x")

        tk.Label(row1, text="출력 형식:",
                 bg=BG, fg=TEXT,
                 font=(FONT, 9, "bold")).pack(side="left", padx=(0, 14))

        for value, label in [
            ("jpeg",     "JPEG로 변환  (권장)"),
            ("webp",     "WebP로 변환"),
            ("original", "원본 형식 유지"),
        ]:
            ttk.Radiobutton(row1, text=label,
                            variable=self.output_format, value=value,
                            style="Mode.TRadiobutton").pack(side="left", padx=8)

        # Row 2: optional resize
        row2 = tk.Frame(outer, bg=BG)
        row2.pack(fill="x", pady=(6, 0))

        ttk.Checkbutton(row2, text="최대 크기 제한:",
                        variable=self.max_dim_enabled,
                        style="Mode.TCheckbutton").pack(side="left")

        self.max_dim_entry = ttk.Entry(row2, textvariable=self.max_dim_value,
                                       width=6, font=(FONT, 9))
        self.max_dim_entry.pack(side="left", padx=4)

        tk.Label(row2, text="px  (가로/세로 최대)",
                 bg=BG, fg=SUBTEXT, font=(FONT, 8)).pack(side="left")

    # ------------------------------------------------------------------
    # Action bar
    # ------------------------------------------------------------------

    def _build_action_bar(self):
        outer = tk.Frame(self.root, bg=ACTION_BG, padx=16, pady=10)
        outer.pack(fill="x")

        left = tk.Frame(outer, bg=ACTION_BG)
        left.pack(side="left", fill="x", expand=True)

        tk.Label(left, text="저장 위치:",
                 bg=ACTION_BG, fg=TEXT,
                 font=(FONT, 9)).pack(side="left")

        self.output_label = tk.Label(left,
                                      text=self._shorten_path(self.output_dir),
                                      bg=ACTION_BG, fg=ACCENT,
                                      font=(FONT, 9), cursor="hand2")
        self.output_label.pack(side="left", padx=(4, 0))
        self.output_label.bind("<Button-1>", lambda _e: self._change_output_dir())

        self.compress_btn = tk.Button(
            outer, text="이미지 압축",
            bg=ACCENT, fg="white",
            activebackground=ACCENT_DK, activeforeground="white",
            font=(FONT, 10, "bold"),
            relief="flat", cursor="hand2",
            padx=20, pady=6,
            command=self._start_compression,
        )
        self.compress_btn.pack(side="right")

    # ------------------------------------------------------------------
    # Progress / result panel
    # ------------------------------------------------------------------

    def _build_progress_panel(self):
        self.prog_frame = tk.Frame(self.root, bg=BG, padx=16, pady=8)
        self.prog_frame.pack(fill="x")

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            self.prog_frame,
            variable=self.progress_var,
            style="Red.Horizontal.TProgressbar",
            mode="determinate",
            length=688,
        )

        self.status_label = tk.Label(self.prog_frame, text="",
                                      bg=BG, fg=SUBTEXT,
                                      font=(FONT, 9), anchor="w")
        self.status_label.pack(fill="x")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _browse_files(self):
        if self.is_compressing:
            return
        exts = " ".join(f"*{e}" for e in SUPPORTED_EXTENSIONS)
        paths = filedialog.askopenfilenames(
            title="이미지 파일 선택",
            filetypes=[
                ("이미지 파일", exts),
                ("모든 파일", "*.*"),
            ],
        )
        if paths:
            self._add_files(list(paths))

    def _on_dnd_drop(self, event):
        if self.is_compressing:
            return
        raw: str = event.data
        import re
        if "{" in raw:
            paths = re.findall(r"\{([^}]+)\}", raw)
        else:
            paths = raw.split()
        valid = [p for p in paths
                 if os.path.splitext(p)[1].lower() in SUPPORTED_EXTENSIONS
                 and os.path.isfile(p)]
        self._add_files(valid)
        self._draw_drop_zone(active=False)

    def _add_files(self, paths: list):
        for path in paths:
            if path in self.files:
                continue
            if os.path.splitext(path)[1].lower() not in SUPPORTED_EXTENSIONS:
                continue
            size = os.path.getsize(path)
            iid = self.tree.insert("", "end", values=(
                os.path.basename(path),
                format_size(size),
                "—",
                "—",
            ))
            self.files[path] = {
                "original_size": size,
                "compressed_size": None,
                "tree_id": iid,
            }

    def _remove_selected(self, _event=None):
        for iid in self.tree.selection():
            for path, info in list(self.files.items()):
                if info["tree_id"] == iid:
                    del self.files[path]
                    break
            self.tree.delete(iid)

    def _change_output_dir(self):
        path = filedialog.askdirectory(title="저장 위치 선택",
                                       initialdir=self.output_dir)
        if path:
            self.output_dir = path
            self.output_label.configure(text=self._shorten_path(path))

    def _start_compression(self):
        if self.is_compressing:
            return
        if not self.files:
            messagebox.showwarning("파일 없음", "압축할 이미지 파일을 먼저 추가하세요.")
            return

        # Read UI options before spawning thread
        output_format = self.output_format.get()
        max_dim = None
        if self.max_dim_enabled.get():
            try:
                max_dim = int(self.max_dim_value.get())
            except ValueError:
                max_dim = None

        self._worker_output_format = output_format
        self._worker_max_dim = max_dim

        ensure_dir(self.output_dir)
        self.is_compressing = True
        self.compress_btn.configure(state="disabled", bg="#AAAAAA")

        # Reset compressed columns
        for path, info in self.files.items():
            self.tree.item(info["tree_id"], values=(
                os.path.basename(path),
                format_size(info["original_size"]),
                "—", "—",
            ))
            info["compressed_size"] = None

        # Show progress bar
        if self._open_btn:
            self._open_btn.destroy()
            self._open_btn = None
        self.progress_var.set(0)
        self.progress_bar.pack(fill="x", pady=(0, 4))
        self.status_label.configure(text="준비 중...", fg=SUBTEXT)

        t = threading.Thread(target=self._worker, daemon=True)
        t.start()

    # ------------------------------------------------------------------
    # Background worker
    # ------------------------------------------------------------------

    def _worker(self):
        entries = list(self.files.items())
        total_files = len(entries)
        total_orig = 0
        total_comp = 0
        mode = self.mode.get()
        output_format = self._worker_output_format
        max_dim = self._worker_max_dim

        for fi, (path, info) in enumerate(entries):
            fname = os.path.basename(path)
            self.root.after(0, lambda t=fname, i=fi, n=total_files:
                            self.status_label.configure(
                                text=f"처리 중: {t}  ({i+1}/{n})", fg=SUBTEXT))

            # Determine output extension
            target_ext = _OUT_EXT.get(output_format)
            # BMP always converts to JPEG even in "original" mode
            if output_format == "original":
                src_ext = os.path.splitext(path)[1].lower()
                if src_ext == ".bmp":
                    target_ext = ".jpg"
            out_path = get_output_path(path, self.output_dir, target_ext)

            def _make_cb(fi, total_files):
                def cb(cur, tot):
                    pct = (fi + cur / tot) / total_files * 100
                    self.root.after(0, self.progress_var.set, pct)
                return cb

            try:
                in_sz, out_sz, was_skipped = compress_image(
                    path, out_path, mode, output_format, max_dim,
                    _make_cb(fi, total_files)
                )
                total_orig += in_sz
                total_comp += out_sz
                ratio = (1 - out_sz / in_sz) * 100 if in_sz else 0
                ratio_text = "건너뜀" if was_skipped else f"-{ratio:.1f}%"
                iid = info["tree_id"]
                self.root.after(0, lambda i=iid, p=path, s=in_sz, o=out_sz, rt=ratio_text:
                                self.tree.item(i, values=(
                                    os.path.basename(p),
                                    format_size(s),
                                    format_size(o),
                                    rt,
                                )))
                info["compressed_size"] = out_sz

            except Exception:
                iid = info["tree_id"]
                self.root.after(0, lambda i=iid, p=path, s=info["original_size"]:
                                self.tree.item(i, values=(
                                    os.path.basename(p),
                                    format_size(s),
                                    "오류", "",
                                )))

        self.root.after(0, self._done, total_files, total_orig, total_comp)

    def _done(self, n_files, total_orig, total_comp):
        self.is_compressing = False
        self.compress_btn.configure(state="normal", bg=ACCENT)
        self.progress_var.set(100)

        ratio = (1 - total_comp / total_orig) * 100 if total_orig else 0
        self.status_label.configure(
            fg=SUCCESS,
            text=(f"{n_files}개 파일 완료  |  "
                  f"{format_size(total_orig)} → {format_size(total_comp)}"
                  f"  ({ratio:.1f}% 감소)"),
        )

        self._open_btn = tk.Button(
            self.prog_frame, text="결과 폴더 열기  ▸",
            bg=LIST_BG, fg=ACCENT,
            activebackground="#FFF5F5", activeforeground=ACCENT_DK,
            relief="flat", cursor="hand2",
            font=(FONT, 9, "bold"),
            padx=10, pady=3,
            command=self._open_output_dir,
        )
        self._open_btn.pack(anchor="e", pady=(4, 0))

    def _open_output_dir(self):
        try:
            os.startfile(self.output_dir)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _shorten_path(path: str, max_len: int = 48) -> str:
        return path if len(path) <= max_len else "…" + path[-(max_len - 1):]
