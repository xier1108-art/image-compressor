"""
사진 압축기 — PyQt6 메인 윈도우.
프레임리스 윈도우 + 커스텀 타이틀바 + PDF 압축기와 동일한 디자인 시스템.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Optional

from PyQt6.QtCore import (
    QPoint, QRectF, Qt, QThread, QTimer, pyqtSignal, pyqtSlot,
)
from PyQt6.QtGui import (
    QBrush, QColor, QDragEnterEvent, QDropEvent, QFont, QIntValidator,
    QMouseEvent, QPainter, QPainterPath, QPen, QPixmap,
)
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QFileDialog,
    QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QSizePolicy, QStackedLayout,
    QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.compressor import compress_image
from core.utils import SUPPORTED_EXTENSIONS, ensure_dir, format_size, get_output_path

from ui import styles as S


# ─── Custom painted widgets ───────────────────────────────────────────────────

class BrandMark(QLabel):
    """36×36 rounded accent square with mini camera icon."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, 36, 36)

        # Gradient accent square
        path = QPainterPath()
        path.addRoundedRect(rect, 9, 9)
        p.fillPath(path, QBrush(QColor(S.ACCENT)))

        # Camera body (white rounded rect)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("white"))
        p.drawRoundedRect(QRectF(7, 12, 22, 16), 2.5, 2.5)

        # Camera top hump (viewfinder bump)
        p.drawRoundedRect(QRectF(13, 9, 10, 4), 1.5, 1.5)

        # Lens outer ring
        p.setBrush(QColor(S.ACCENT))
        p.drawEllipse(QRectF(12, 15, 12, 12))
        # Lens inner
        p.setBrush(QColor("#fde0db"))
        p.drawEllipse(QRectF(14, 17, 8, 8))
        # Lens highlight
        p.setBrush(QColor("white"))
        p.drawEllipse(QRectF(15.5, 18.5, 3, 3))

        # Flash dot
        p.setBrush(QColor("#fde0db"))
        p.drawEllipse(QRectF(25, 14, 2.5, 2.5))
        p.end()


class ImageIcon(QLabel):
    """Small image file icon for list rows."""
    def __init__(self, size=18, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, int(size * 48 / 40))

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        sx, sy = w / 40, h / 48

        # File outline (rounded rect with folded corner)
        p.setPen(QPen(QColor(S.ACCENT), 1.5))
        p.setBrush(QColor("white"))
        path = QPainterPath()
        path.moveTo(4 * sx, 2 * sy)
        path.lineTo(26 * sx, 2 * sy)
        path.lineTo(36 * sx, 12 * sy)
        path.lineTo(36 * sx, 44 * sy)
        path.quadTo(36 * sx, 46 * sy, 34 * sx, 46 * sy)
        path.lineTo(4 * sx, 46 * sy)
        path.quadTo(2 * sx, 46 * sy, 2 * sx, 44 * sy)
        path.lineTo(2 * sx, 4 * sy)
        path.quadTo(2 * sx, 2 * sy, 4 * sx, 2 * sy)
        p.drawPath(path)

        # Folded corner
        p.setBrush(QColor("#fef4f1"))
        cp = QPainterPath()
        cp.moveTo(26 * sx, 2 * sy)
        cp.lineTo(26 * sx, 12 * sy)
        cp.lineTo(36 * sx, 12 * sy)
        p.drawPath(cp)

        # Mountain + sun inside the file
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(S.ACCENT))
        p.drawEllipse(QRectF(9 * sx, 18 * sy, 6 * sx, 6 * sy))
        tri = QPainterPath()
        tri.moveTo(7 * sx, 38 * sy)
        tri.lineTo(18 * sx, 24 * sy)
        tri.lineTo(25 * sx, 32 * sy)
        tri.lineTo(31 * sx, 26 * sy)
        tri.lineTo(33 * sx, 38 * sy)
        tri.closeSubpath()
        p.drawPath(tri)

        p.setBrush(QColor("#fef4f1"))
        p.drawRect(QRectF(3 * sx, 38 * sy, 33 * sx, 7 * sy))
        p.end()


class PlusCircle(QLabel):
    """44×44 white circle with + sign (drop zone icon)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 44)

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(224, 85, 67, 40), 1))
        p.setBrush(QColor("white"))
        p.drawEllipse(QRectF(1, 1, 42, 42))
        p.setPen(QPen(QColor(S.ACCENT), 2.3, cap=Qt.PenCapStyle.RoundCap))
        p.drawLine(22, 14, 22, 30)
        p.drawLine(14, 22, 30, 22)
        p.end()


class PulsingDot(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(6, 6)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._phase = 0

    def start(self):
        self._phase = 0
        self._timer.start(60)

    def stop(self):
        self._timer.stop()
        self.update()

    def _tick(self):
        self._phase = (self._phase + 1) % 20
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._timer.isActive():
            t = self._phase / 10.0 if self._phase < 10 else (20 - self._phase) / 10.0
        else:
            t = 1.0
        r = int(0xf0 + (0xe0 - 0xf0) * t)
        g = int(0xa9 + (0x55 - 0xa9) * t)
        b = int(0x9f + (0x43 - 0x9f) * t)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(r, g, b))
        p.drawEllipse(QRectF(0, 0, 6, 6))
        p.end()


class CheckIcon(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(S.SUCCESS))
        p.drawEllipse(QRectF(0, 0, 36, 36))

        pen = QPen(QColor("white"), 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        path = QPainterPath()
        path.moveTo(10, 18)
        path.lineTo(16, 24)
        path.lineTo(27, 12)
        p.drawPath(path)
        p.end()


class RatioBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(24)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 0, 8, 0)
        lay.setSpacing(8)
        lay.addStretch(1)

        self.bar_bg = QFrame()
        self.bar_bg.setObjectName("ratioBarBg")
        self.bar_bg.setFixedSize(42, 5)
        bar_lay = QHBoxLayout(self.bar_bg)
        bar_lay.setContentsMargins(0, 0, 0, 0)
        bar_lay.setSpacing(0)
        self.bar_fill = QFrame()
        self.bar_fill.setObjectName("ratioBarFill")
        bar_lay.addWidget(self.bar_fill)
        bar_lay.addStretch(1)

        self.text = QLabel("—")
        self.text.setObjectName("ratioText")
        self.text.setMinimumWidth(60)
        self.text.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        lay.addWidget(self.bar_bg)
        lay.addWidget(self.text)

        self.set_pending()

    def _set_flags(self, pending="false", working="false", skipped="false"):
        self.text.setProperty("pending", pending)
        self.text.setProperty("working", working)
        self.text.setProperty("skipped", skipped)
        self.text.style().unpolish(self.text)
        self.text.style().polish(self.text)

    def set_pending(self):
        self.bar_bg.hide()
        self.text.setText("—")
        self._set_flags(pending="true")

    def set_working(self):
        self.bar_bg.hide()
        self.text.setText("처리 중")
        self._set_flags(working="true")

    def set_done(self, ratio: float):
        self.bar_bg.show()
        w_total = 42
        fill_w = max(1, int(min(100, max(0, ratio)) / 100 * w_total))
        self.bar_fill.setFixedWidth(fill_w)
        self.text.setText(f"−{ratio:.1f}%")
        self._set_flags()

    def set_skipped(self):
        self.bar_bg.hide()
        self.text.setText("건너뜀")
        self._set_flags(skipped="true")

    def set_error(self):
        self.bar_bg.hide()
        self.text.setText("오류")
        self._set_flags(pending="true")


class FileNameCell(QWidget):
    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 10, 0)
        lay.setSpacing(10)
        self.icon = ImageIcon(size=18)
        self.label = QLabel(name)
        self.label.setStyleSheet(f"color: {S.INK_900}; font-size: 12px; font-weight: 500;")
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        lay.addWidget(self.icon)
        lay.addWidget(self.label, 1)


class DropZone(QFrame):
    filesDropped = pyqtSignal(list)
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(108)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 14, 20, 14)
        lay.setSpacing(4)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon = PlusCircle()
        self.icon.setObjectName("dzIcon")
        lay.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignHCenter)

        title = QLabel(
            "사진 파일을 드래그하거나 "
            "<span style='background:white; border:1px solid #e5ded0; "
            "border-radius:4px; padding:1px 6px; color:#3a342c; "
            "font-family:Consolas, monospace; font-size:10px;'>클릭</span>"
            " 하여 선택"
        )
        title.setObjectName("dzTitle")
        title.setTextFormat(Qt.TextFormat.RichText)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title, 0, Qt.AlignmentFlag.AlignHCenter)

        self.sub = QLabel("🔒 원본 파일은 변경되지 않습니다 · JPG · PNG · WebP · HEIC · BMP · TIFF")
        self.sub.setObjectName("dzSub")
        lay.addWidget(self.sub, 0, Qt.AlignmentFlag.AlignHCenter)

    def enterEvent(self, _ev):
        self.setProperty("hover", "true"); self._refresh()

    def leaveEvent(self, _ev):
        self.setProperty("hover", "false"); self._refresh()

    def mousePressEvent(self, ev: QMouseEvent):
        if ev.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def dragEnterEvent(self, ev: QDragEnterEvent):
        if ev.mimeData().hasUrls():
            ev.acceptProposedAction()
            self.setProperty("dragActive", "true"); self._refresh()

    def dragLeaveEvent(self, _ev):
        self.setProperty("dragActive", "false"); self._refresh()

    def dropEvent(self, ev: QDropEvent):
        self.setProperty("dragActive", "false"); self._refresh()
        paths = []
        for url in ev.mimeData().urls():
            p = url.toLocalFile()
            if p.lower().endswith(SUPPORTED_EXTENSIONS) and os.path.isfile(p):
                paths.append(p)
        if paths:
            self.filesDropped.emit(paths)

    def _refresh(self):
        self.style().unpolish(self); self.style().polish(self)


# ─── Quality card ────────────────────────────────────────────────────────────

class QualityCard(QFrame):
    clicked = pyqtSignal()

    @dataclass
    class Spec:
        qid: str
        name: str
        spec: str
        est: str

    def __init__(self, spec: Spec, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.setObjectName("qCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 9)
        lay.setSpacing(3)

        top = QHBoxLayout(); top.setSpacing(6); top.setContentsMargins(0, 0, 0, 0)
        self.dot = QFrame(); self.dot.setObjectName("qCardDot")
        self.dot.setFixedSize(8, 8)
        self.name_lbl = QLabel(spec.name); self.name_lbl.setObjectName("qCardName")
        top.addWidget(self.dot); top.addWidget(self.name_lbl); top.addStretch(1)
        wrap_top = QWidget(); wrap_top.setLayout(top)
        lay.addWidget(wrap_top)

        self.spec_lbl = QLabel(spec.spec); self.spec_lbl.setObjectName("qCardSpec")
        lay.addWidget(self.spec_lbl)

        est_row = QHBoxLayout(); est_row.setSpacing(4); est_row.setContentsMargins(0, 2, 0, 0)
        est_prefix = QLabel("예상 감소"); est_prefix.setObjectName("qCardEst")
        est_value = QLabel(spec.est); est_value.setObjectName("qCardEstStrong")
        est_row.addWidget(est_prefix); est_row.addWidget(est_value); est_row.addStretch(1)
        wrap_est = QWidget(); wrap_est.setLayout(est_row)
        lay.addWidget(wrap_est)

        self.est_prefix = est_prefix

    def mousePressEvent(self, ev: QMouseEvent):
        if ev.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def setActive(self, active: bool):
        self.setProperty("active", "true" if active else "false")
        self.dot.setProperty("active", "true" if active else "false")
        self.est_prefix.setProperty("active", "true" if active else "false")
        for w in (self, self.dot, self.est_prefix):
            w.style().unpolish(w); w.style().polish(w)


# ─── Compression worker ──────────────────────────────────────────────────────

class CompressionWorker(QThread):
    fileStarted  = pyqtSignal(int, str)
    fileProgress = pyqtSignal(int, float)
    fileDone     = pyqtSignal(int, int, int, float, bool)  # idx, in, out, ratio, skipped
    fileError    = pyqtSignal(int, str)
    allDone      = pyqtSignal(int, int, int)

    def __init__(self, entries, mode: str, output_format: str,
                 max_dim: Optional[int], output_dir: str):
        super().__init__()
        self.entries = entries
        self.mode = mode
        self.output_format = output_format
        self.max_dim = max_dim
        self.output_dir = output_dir

    def _resolve_target_ext(self, src_path: str) -> str:
        ext = os.path.splitext(src_path)[1].lower()
        if self.output_format == "jpeg":
            return ".jpg"
        if self.output_format == "webp":
            return ".webp"
        if ext in (".bmp", ".heic", ".heif"):
            return ".jpg"
        return ext

    def run(self):
        total = len(self.entries)
        tot_orig = 0
        tot_comp = 0

        for fi, (idx, path) in enumerate(self.entries):
            fname = os.path.basename(path)
            self.fileStarted.emit(idx, fname)

            target_ext = self._resolve_target_ext(path)
            out_path = get_output_path(path, self.output_dir, target_ext=target_ext)

            def _cb(cur, tot, fi=fi):
                pct = (fi + cur / max(tot, 1)) / total * 100
                self.fileProgress.emit(idx, pct)

            try:
                in_sz, out_sz, was_skipped = compress_image(
                    path, out_path,
                    mode=self.mode,
                    output_format=self.output_format,
                    max_dim=self.max_dim,
                    progress_callback=_cb,
                )
                tot_orig += in_sz
                tot_comp += out_sz
                ratio = (1 - out_sz / in_sz) * 100 if in_sz else 0
                self.fileDone.emit(idx, in_sz, out_sz, ratio, was_skipped)
            except Exception as exc:
                self.fileError.emit(idx, str(exc))

            self.fileProgress.emit(idx, (fi + 1) / total * 100)

        self.allDone.emit(total, tot_orig, tot_comp)


# ─── Main window ─────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("rootWindow")
        self.setWindowTitle("사진 압축기")
        self.resize(860, 780)

        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)

        self.files: list[dict] = []
        self.output_dir = os.path.join(
            os.path.expanduser("~"), "Desktop", "이미지압축결과")
        self.current_mode = "recommended"
        self.output_format = "jpeg"
        self.max_dim_enabled = False
        self.max_dim_value = 1920
        self.is_compressing = False
        self._worker: Optional[CompressionWorker] = None
        self._drag_pos: Optional[QPoint] = None

        try:
            from PIL import __version__ as _pil_ver
            self._pil_ver = _pil_ver
        except Exception:
            self._pil_ver = "?"
        self._has_heif = self._check_heif()
        self._has_oxipng = self._check_oxipng()

        self._build_ui()
        self.setStyleSheet(S.QSS)

    # ── Utilities ────────────────────────────────────────────────────────────

    @staticmethod
    def _check_heif() -> bool:
        try:
            import pillow_heif  # noqa: F401
            return True
        except Exception:
            return False

    @staticmethod
    def _check_oxipng() -> bool:
        try:
            import oxipng  # noqa: F401
            return True
        except Exception:
            return False

    @staticmethod
    def _shorten_path(p: str, max_len: int = 50) -> str:
        return p if len(p) <= max_len else "…" + p[-(max_len - 1):]

    # ── UI build ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.frame = QFrame()
        self.frame.setObjectName("winFrame")
        self.setCentralWidget(self.frame)

        lay = QVBoxLayout(self.frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        lay.addWidget(self._build_titlebar())
        lay.addWidget(self._build_app_header())
        lay.addWidget(self._build_main(), 1)
        lay.addWidget(self._build_bottom_stack())
        lay.addWidget(self._build_status_rail())

        self._update_count()

    def _build_titlebar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("titleBar")
        bar.setFixedHeight(34)
        self._titlebar = bar

        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 0, 0, 0)
        lay.setSpacing(8)

        ic = QLabel()
        ic.setFixedSize(14, 14)
        pix = QPixmap(14, 14); pix.fill(Qt.GlobalColor.transparent)
        pn = QPainter(pix); pn.setRenderHint(QPainter.RenderHint.Antialiasing)
        pn.setPen(Qt.PenStyle.NoPen); pn.setBrush(QColor(S.ACCENT))
        pn.drawRoundedRect(QRectF(0, 3, 14, 10), 1.5, 1.5)
        pn.setBrush(QColor("white"))
        pn.drawEllipse(QRectF(4, 5, 6, 6))
        pn.setBrush(QColor(S.ACCENT))
        pn.drawEllipse(QRectF(5.5, 6.5, 3, 3))
        pn.end()
        ic.setPixmap(pix)
        lay.addWidget(ic)

        title = QLabel("사진 압축기"); title.setObjectName("titleText")
        lay.addWidget(title)
        lay.addStretch(1)

        for sym, is_close, cmd in [("─", False, self.showMinimized),
                                      ("□", False, self._toggle_max),
                                      ("✕", True,  self.close)]:
            b = QPushButton(sym)
            b.setObjectName("tbClose" if is_close else "tbBtn")
            b.setFlat(True)
            b.clicked.connect(cmd)
            lay.addWidget(b)

        bar.mouseDoubleClickEvent = lambda e: self._toggle_max()
        return bar

    def _toggle_max(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _build_app_header(self) -> QWidget:
        hdr = QFrame()
        hdr.setObjectName("appHeader")

        lay = QHBoxLayout(hdr)
        lay.setContentsMargins(24, 18, 24, 16)
        lay.setSpacing(12)

        mark = BrandMark()
        lay.addWidget(mark)

        tf = QVBoxLayout(); tf.setSpacing(2); tf.setContentsMargins(0, 0, 0, 0)
        t1 = QLabel("사진 압축기");                     t1.setObjectName("brandTitle")
        t2 = QLabel("오프라인 · 원본 보존 · 배치 처리"); t2.setObjectName("brandSubtitle")
        tf.addWidget(t1); tf.addWidget(t2)
        wrap = QWidget(); wrap.setLayout(tf)
        lay.addWidget(wrap)
        lay.addStretch(1)
        return hdr

    def _build_main(self) -> QWidget:
        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        self.dropzone = DropZone()
        self.dropzone.clicked.connect(self._browse_files)
        self.dropzone.filesDropped.connect(self._add_files)
        lay.addWidget(self.dropzone)

        file_section = QVBoxLayout(); file_section.setSpacing(8); file_section.setContentsMargins(0, 0, 0, 0)

        sh = QHBoxLayout(); sh.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("파일 목록"); lbl.setObjectName("sectionHead")
        self.count_lbl = QLabel("0개 파일"); self.count_lbl.setObjectName("sectionCount")
        sh.addWidget(lbl); sh.addStretch(1); sh.addWidget(self.count_lbl)
        sh_w = QWidget(); sh_w.setLayout(sh)
        file_section.addWidget(sh_w)

        list_wrap = QFrame(); list_wrap.setObjectName("fileListWrap")
        list_wrap.setMinimumHeight(200)
        list_stack = QStackedLayout(list_wrap)
        list_stack.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["파일명", "원본 크기", "압축 크기", "압축률", ""])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setShowGrid(False)
        self.table.setFrameShape(QFrame.Shape.NoFrame)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setMinimumHeight(180)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 115)
        self.table.setColumnWidth(4, 28)
        self.table.setHorizontalHeaderItem(1, QTableWidgetItem("원본 크기"))
        self.table.setHorizontalHeaderItem(2, QTableWidgetItem("압축 크기"))
        self.table.setHorizontalHeaderItem(3, QTableWidgetItem("압축률"))
        for i in (1, 2, 3):
            self.table.horizontalHeaderItem(i).setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.empty_state = QFrame(); self.empty_state.setObjectName("emptyState")
        es_lay = QVBoxLayout(self.empty_state)
        es_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        es_lay.setSpacing(10)
        es_icon = QLabel("⋮⋮"); es_icon.setObjectName("emptyStateIcon")
        es_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        es_txt = QLabel("위에 사진 파일을 드래그해서 시작하세요")
        es_txt.setObjectName("emptyStateText")
        es_txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        es_lay.addWidget(es_icon); es_lay.addWidget(es_txt)

        list_stack.addWidget(self.empty_state)
        list_stack.addWidget(self.table)
        self._list_stack = list_stack
        list_stack.setCurrentIndex(0)

        file_section.addWidget(list_wrap)
        fs_w = QWidget(); fs_w.setLayout(file_section)
        lay.addWidget(fs_w, 1)

        # Quality panel
        q_row = QHBoxLayout(); q_row.setSpacing(14); q_row.setContentsMargins(0, 0, 0, 0)
        q_lbl = QLabel("압축 수준"); q_lbl.setObjectName("qualityLabel")
        q_row.addWidget(q_lbl)

        q_seg = QFrame(); q_seg.setObjectName("qualitySeg")
        q_seg_lay = QHBoxLayout(q_seg); q_seg_lay.setContentsMargins(4, 4, 4, 4); q_seg_lay.setSpacing(6)
        self._q_cards = {}
        specs = [
            QualityCard.Spec("extreme",     "최대 압축", "Q40 · HEIC 1920px", "60–85%"),
            QualityCard.Spec("recommended", "권장",      "Q68 · HEIC 2560px", "35–65%"),
            QualityCard.Spec("low",         "저압축",    "Q82 · 원본 해상도", "15–35%"),
        ]
        for sp in specs:
            card = QualityCard(sp)
            card.clicked.connect(lambda _=False, q=sp.qid: self._set_quality(q))
            q_seg_lay.addWidget(card, 1)
            self._q_cards[sp.qid] = card

        q_row.addWidget(q_seg, 1)
        qw = QWidget(); qw.setLayout(q_row)
        lay.addWidget(qw)

        self._set_quality(self.current_mode)

        # Format + max dim panel
        lay.addWidget(self._build_format_panel())

        self.table.keyPressEvent = self._table_keypress
        return wrap

    def _build_format_panel(self) -> QWidget:
        row = QHBoxLayout(); row.setSpacing(10); row.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel("출력 형식"); lbl.setObjectName("formatLabel")
        row.addWidget(lbl)

        self._fmt_buttons = {}
        fmt_group = QButtonGroup(self)
        fmt_group.setExclusive(True)
        for fid, label in [("jpeg", "JPEG"), ("webp", "WebP"), ("original", "원본 형식")]:
            btn = QPushButton(label)
            btn.setObjectName("fmtChip")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, f=fid: self._set_format(f))
            fmt_group.addButton(btn)
            row.addWidget(btn)
            self._fmt_buttons[fid] = btn
        self._set_format(self.output_format)

        row.addSpacing(16)

        self.max_dim_cb = QCheckBox("최대 크기 제한")
        self.max_dim_cb.setObjectName("maxDimCheck")
        self.max_dim_cb.setChecked(self.max_dim_enabled)
        self.max_dim_cb.toggled.connect(self._on_maxdim_toggled)
        row.addWidget(self.max_dim_cb)

        self.max_dim_edit = QLineEdit(str(self.max_dim_value))
        self.max_dim_edit.setObjectName("maxDimEdit")
        self.max_dim_edit.setFixedWidth(64)
        self.max_dim_edit.setValidator(QIntValidator(100, 16384, self))
        self.max_dim_edit.setEnabled(self.max_dim_enabled)
        row.addWidget(self.max_dim_edit)

        suffix = QLabel("px"); suffix.setObjectName("maxDimSuffix")
        row.addWidget(suffix)

        row.addStretch(1)
        w = QWidget(); w.setLayout(row)
        return w

    def _set_format(self, fid: str):
        self.output_format = fid
        for k, btn in self._fmt_buttons.items():
            btn.setChecked(k == fid)
            btn.setProperty("active", "true" if k == fid else "false")
            btn.style().unpolish(btn); btn.style().polish(btn)

    def _on_maxdim_toggled(self, checked: bool):
        self.max_dim_enabled = checked
        self.max_dim_edit.setEnabled(checked)

    def _table_keypress(self, ev):
        if ev.key() == Qt.Key.Key_Delete and not self.is_compressing:
            self._remove_selected_rows()
        else:
            QTableWidget.keyPressEvent(self.table, ev)

    def _build_bottom_stack(self) -> QWidget:
        self.bottom_stack = QStackedWidget()

        # Action panel
        self.action_panel = QFrame(); self.action_panel.setObjectName("actionBar")
        ab = QHBoxLayout(self.action_panel); ab.setContentsMargins(24, 16, 24, 16); ab.setSpacing(16)

        sp_row = QHBoxLayout(); sp_row.setSpacing(10); sp_row.setContentsMargins(0, 0, 0, 0)
        sp_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        sp_icon = QLabel("📁"); sp_icon.setObjectName("spIcon")
        sp_icon.setFixedSize(26, 26); sp_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sp_row.addWidget(sp_icon, 0, Qt.AlignmentFlag.AlignVCenter)

        sp_txt_lay = QVBoxLayout(); sp_txt_lay.setSpacing(1); sp_txt_lay.setContentsMargins(0, 0, 0, 0)
        sp_txt_lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        sp_lbl = QLabel("저장 위치"); sp_lbl.setObjectName("spLabel")
        sp_val_row = QHBoxLayout(); sp_val_row.setSpacing(6); sp_val_row.setContentsMargins(0, 0, 0, 0)
        self.path_lbl = QLabel(self._shorten_path(self.output_dir)); self.path_lbl.setObjectName("spValue")
        change_btn = QPushButton("변경"); change_btn.setObjectName("spChange")
        change_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        change_btn.clicked.connect(self._change_output_dir)
        sp_val_row.addWidget(self.path_lbl); sp_val_row.addWidget(change_btn); sp_val_row.addStretch(1)
        sp_val_w = QWidget(); sp_val_w.setLayout(sp_val_row)
        sp_txt_lay.addWidget(sp_lbl); sp_txt_lay.addWidget(sp_val_w)
        sp_txt_w = QWidget(); sp_txt_w.setLayout(sp_txt_lay)
        sp_row.addWidget(sp_txt_w, 1)

        sp_w = QWidget(); sp_w.setLayout(sp_row)
        sp_w.setMaximumWidth(520)
        ab.addWidget(sp_w, 1)

        self.compress_btn = QPushButton("사진 압축 시작  →")
        self.compress_btn.setObjectName("btnCompress")
        self.compress_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.compress_btn.clicked.connect(self._start_compression)
        ab.addWidget(self.compress_btn)

        # Progress panel
        self.progress_panel = QFrame(); self.progress_panel.setObjectName("progressPanel")
        pp = QVBoxLayout(self.progress_panel); pp.setContentsMargins(24, 14, 24, 18); pp.setSpacing(10)

        pp_top = QHBoxLayout(); pp_top.setSpacing(8)
        self.pulse_dot = PulsingDot()
        pp_top.addWidget(self.pulse_dot)
        self.pp_status = QLabel("준비 중..."); self.pp_status.setObjectName("progressStatus")
        pp_top.addWidget(self.pp_status)
        self.pp_file = QLabel(""); self.pp_file.setObjectName("progressFile")
        pp_top.addWidget(self.pp_file, 1)
        self.pp_pct = QLabel("0%"); self.pp_pct.setObjectName("progressPct")
        pp_top.addWidget(self.pp_pct)
        pp_top_w = QWidget(); pp_top_w.setLayout(pp_top)
        pp.addWidget(pp_top_w)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        pp.addWidget(self.progress_bar)

        pp_sub = QHBoxLayout()
        self.pp_sub_left = QLabel(""); self.pp_sub_left.setObjectName("progressSub")
        self.pp_sub_right = QLabel(""); self.pp_sub_right.setObjectName("progressSub")
        pp_sub.addWidget(self.pp_sub_left); pp_sub.addStretch(1); pp_sub.addWidget(self.pp_sub_right)
        pp_sub_w = QWidget(); pp_sub_w.setLayout(pp_sub)
        pp.addWidget(pp_sub_w)

        # Success panel
        self.success_panel = QFrame(); self.success_panel.setObjectName("successPanel")
        sp = QHBoxLayout(self.success_panel); sp.setContentsMargins(32, 16, 32, 18); sp.setSpacing(16)
        self.success_check = CheckIcon()
        sp.addWidget(self.success_check)
        sp_msg_lay = QVBoxLayout(); sp_msg_lay.setSpacing(2); sp_msg_lay.setContentsMargins(0, 0, 0, 0)
        self.success_title = QLabel(""); self.success_title.setObjectName("successTitle")
        self.success_stats = QLabel(""); self.success_stats.setObjectName("successStats")
        self.success_stats.setTextFormat(Qt.TextFormat.RichText)
        sp_msg_lay.addWidget(self.success_title); sp_msg_lay.addWidget(self.success_stats)
        sp_msg_w = QWidget(); sp_msg_w.setLayout(sp_msg_lay)
        sp.addWidget(sp_msg_w, 1)
        new_btn = QPushButton("＋  새 압축"); new_btn.setObjectName("btnNewRun")
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.clicked.connect(self._start_new_run)
        sp.addWidget(new_btn)
        open_btn = QPushButton("📁  결과 폴더 열기  →"); open_btn.setObjectName("btnOpenFolder")
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.clicked.connect(self._open_output_dir)
        sp.addWidget(open_btn)

        self.bottom_stack.addWidget(self.action_panel)
        self.bottom_stack.addWidget(self.progress_panel)
        self.bottom_stack.addWidget(self.success_panel)

        for p in (self.action_panel, self.progress_panel, self.success_panel):
            p.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        self.action_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        def _on_stack_changed(idx):
            for i in range(self.bottom_stack.count()):
                w = self.bottom_stack.widget(i)
                w.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Preferred if i == idx else QSizePolicy.Policy.Ignored,
                )
                w.adjustSize()
            self.bottom_stack.adjustSize()

        self.bottom_stack.currentChanged.connect(_on_stack_changed)
        self.bottom_stack.setCurrentWidget(self.action_panel)
        return self.bottom_stack

    def _build_status_rail(self) -> QWidget:
        rail = QFrame(); rail.setObjectName("statusRail"); rail.setFixedHeight(28)
        lay = QHBoxLayout(rail); lay.setContentsMargins(16, 6, 16, 6); lay.setSpacing(6)

        dot = QFrame(); dot.setObjectName("railDot")
        lay.addWidget(dot)
        chip = QLabel("오프라인 모드"); chip.setObjectName("railChip")
        lay.addWidget(chip)
        lay.addStretch(1)

        py_ver = f"Python {sys.version_info.major}.{sys.version_info.minor}"
        engines = [f"Pillow {self._pil_ver}"]
        if self._has_oxipng:
            engines.append("oxipng")
        if self._has_heif:
            engines.append("pillow-heif")
        right = QLabel(f"{py_ver} · {' · '.join(engines)}        {S.APP_VERSION}")
        right.setObjectName("railRight")
        lay.addWidget(right)
        return rail

    # ── Frameless drag ───────────────────────────────────────────────────────

    def mousePressEvent(self, ev: QMouseEvent):
        if ev.button() == Qt.MouseButton.LeftButton and self._is_in_titlebar(ev.pos()):
            self._drag_pos = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()
            ev.accept()

    def mouseMoveEvent(self, ev: QMouseEvent):
        if self._drag_pos is not None and ev.buttons() & Qt.MouseButton.LeftButton:
            self.move(ev.globalPosition().toPoint() - self._drag_pos)
            ev.accept()

    def mouseReleaseEvent(self, _ev):
        self._drag_pos = None

    def _is_in_titlebar(self, pos: QPoint) -> bool:
        if not hasattr(self, "_titlebar"):
            return False
        tb_rect = self._titlebar.rect()
        tb_global = self._titlebar.mapTo(self, tb_rect.topLeft())
        return (tb_global.y() <= pos.y() <= tb_global.y() + tb_rect.height()
                and pos.x() < self._titlebar.width() - 3 * 46)

    # ── File management ──────────────────────────────────────────────────────

    def _browse_files(self):
        if self.is_compressing:
            return
        filt_patterns = " ".join(f"*{e}" for e in SUPPORTED_EXTENSIONS)
        paths, _ = QFileDialog.getOpenFileNames(
            self, "사진 파일 선택", "",
            f"이미지 파일 ({filt_patterns});;모든 파일 (*.*)")
        if paths:
            self._add_files(paths)

    @pyqtSlot(list)
    def _add_files(self, paths: list[str]):
        existing = {f["path"] for f in self.files}
        for path in paths:
            if path in existing or not path.lower().endswith(SUPPORTED_EXTENSIONS):
                continue
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            row = self.table.rowCount()
            self.table.insertRow(row)

            name_cell = FileNameCell(os.path.basename(path))
            self.table.setCellWidget(row, 0, name_cell)

            orig_item = QTableWidgetItem(format_size(size))
            orig_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            orig_item.setForeground(QBrush(QColor(S.INK_700)))
            f = orig_item.font(); f.setFamily("Consolas"); f.setPointSize(9); orig_item.setFont(f)
            self.table.setItem(row, 1, orig_item)

            comp_item = QTableWidgetItem("—")
            comp_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            comp_item.setForeground(QBrush(QColor(S.INK_300)))
            comp_item.setFont(f)
            self.table.setItem(row, 2, comp_item)

            ratio = RatioBar()
            self.table.setCellWidget(row, 3, ratio)

            remove = QPushButton("✕")
            remove.setFlat(True)
            remove.setStyleSheet(f"color: {S.INK_400}; border: 0; background: transparent;"
                                  f"font-size: 11px;")
            remove.setCursor(Qt.CursorShape.PointingHandCursor)
            remove.clicked.connect(lambda _=False, p=path: self._remove_by_path(p))
            self.table.setCellWidget(row, 4, remove)

            self.files.append({
                "path": path,
                "size": size,
                "comp_size": None,
                "row": row,
                "ratio_widget": ratio,
                "comp_item": comp_item,
            })
        self._update_count()

    def _remove_by_path(self, path: str):
        if self.is_compressing:
            return
        for i, f in enumerate(self.files):
            if f["path"] == path:
                self.table.removeRow(f["row"])
                del self.files[i]
                break
        self._reindex_rows()
        self._update_count()

    def _remove_selected_rows(self):
        sel_rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for r in sel_rows:
            for i, f in enumerate(self.files):
                if f["row"] == r:
                    self.table.removeRow(r)
                    del self.files[i]
                    break
        self._reindex_rows()
        self._update_count()

    def _reindex_rows(self):
        for i, f in enumerate(self.files):
            f["row"] = i

    def _update_count(self):
        n = len(self.files)
        if n == 0:
            self.count_lbl.setText("0개 파일")
        else:
            total = sum(f["size"] for f in self.files)
            self.count_lbl.setText(f"{n}개 파일  ·  총 {format_size(total)}")
        self._list_stack.setCurrentIndex(0 if n == 0 else 1)
        if hasattr(self, "compress_btn"):
            self.compress_btn.setEnabled(n > 0 and not self.is_compressing)

    def _change_output_dir(self):
        path = QFileDialog.getExistingDirectory(
            self, "저장 위치 선택", self.output_dir)
        if path:
            self.output_dir = path
            self.path_lbl.setText(self._shorten_path(path))

    # ── Quality ──────────────────────────────────────────────────────────────

    def _set_quality(self, qid: str):
        self.current_mode = qid
        for k, card in self._q_cards.items():
            card.setActive(k == qid)

    # ── Compression lifecycle ────────────────────────────────────────────────

    def _resolve_max_dim(self) -> Optional[int]:
        if not self.max_dim_enabled:
            return None
        try:
            v = int(self.max_dim_edit.text())
            if v < 100:
                return None
            return v
        except (ValueError, AttributeError):
            return None

    def _start_compression(self):
        if self.is_compressing:
            return
        if not self.files:
            QMessageBox.warning(self, "파일 없음", "압축할 사진 파일을 먼저 추가하세요.")
            return

        ensure_dir(self.output_dir)
        self.is_compressing = True
        self.compress_btn.setDisabled(True)

        for f in self.files:
            f["ratio_widget"].set_pending()
            f["comp_item"].setText("—")
            f["comp_item"].setForeground(QBrush(QColor(S.INK_300)))
            f["comp_size"] = None

        self.progress_bar.setValue(0)
        self.pp_status.setText("준비 중...")
        self.pp_file.setText("")
        self.pp_pct.setText("0%")
        self.pp_sub_left.setText("")
        self.pp_sub_right.setText("")
        self.bottom_stack.setCurrentWidget(self.progress_panel)
        self.pulse_dot.start()

        entries = [(f["row"], f["path"]) for f in self.files]
        self._worker = CompressionWorker(
            entries,
            mode=self.current_mode,
            output_format=self.output_format,
            max_dim=self._resolve_max_dim(),
            output_dir=self.output_dir,
        )
        self._worker.fileStarted.connect(self._on_file_started)
        self._worker.fileProgress.connect(self._on_file_progress)
        self._worker.fileDone.connect(self._on_file_done)
        self._worker.fileError.connect(self._on_file_error)
        self._worker.allDone.connect(self._on_all_done)
        self._worker.start()

    @pyqtSlot(int, str)
    def _on_file_started(self, idx: int, fname: str):
        self.pp_status.setText("처리 중:")
        self.pp_file.setText(fname)
        for f in self.files:
            if f["row"] == idx:
                f["ratio_widget"].set_working()
                break
        total = len(self.files)
        done_n = sum(1 for f in self.files if f["comp_size"] is not None) + 1
        self.pp_sub_left.setText(f"{done_n} / {total} 파일")

    @pyqtSlot(int, float)
    def _on_file_progress(self, _idx: int, pct: float):
        self.progress_bar.setValue(int(pct))
        self.pp_pct.setText(f"{pct:.0f}%")
        remaining = max(0, int((100 - pct) / max(pct / 5, 1)))
        self.pp_sub_right.setText(f"예상 남은 시간: {remaining}초")

    @pyqtSlot(int, int, int, float, bool)
    def _on_file_done(self, idx: int, in_sz: int, out_sz: int,
                      ratio: float, was_skipped: bool):
        for f in self.files:
            if f["row"] == idx:
                f["comp_size"] = out_sz
                f["comp_item"].setText(format_size(out_sz))
                f["comp_item"].setForeground(QBrush(QColor(S.INK_900)))
                fnt = f["comp_item"].font(); fnt.setBold(True); f["comp_item"].setFont(fnt)
                if was_skipped:
                    f["ratio_widget"].set_skipped()
                else:
                    f["ratio_widget"].set_done(ratio)
                break

    @pyqtSlot(int, str)
    def _on_file_error(self, idx: int, _msg: str):
        for f in self.files:
            if f["row"] == idx:
                f["comp_item"].setText("오류")
                f["comp_item"].setForeground(QBrush(QColor(S.ACCENT)))
                f["ratio_widget"].set_error()
                break

    @pyqtSlot(int, int, int)
    def _on_all_done(self, n_files: int, tot_orig: int, tot_comp: int):
        self.is_compressing = False
        self.compress_btn.setDisabled(False)
        self.pulse_dot.stop()

        ratio = (1 - tot_comp / tot_orig) * 100 if tot_orig else 0
        saved = tot_orig - tot_comp
        self.success_title.setText(f"{n_files}개 파일 압축 완료")
        self.success_stats.setText(
            f"<span style='color:{S.SUCCESS_DK};font-weight:700'>{format_size(tot_orig)}</span>"
            f" <span style='color:{S.INK_400}'>→</span> "
            f"<span style='color:{S.SUCCESS_DK};font-weight:700'>{format_size(tot_comp)}</span>"
            f"     <span style='color:{S.SUCCESS};font-weight:700'>−{ratio:.1f}% "
            f"({format_size(saved)} 절약)</span>"
        )
        self.bottom_stack.setCurrentWidget(self.success_panel)

    def _open_output_dir(self):
        try:
            os.startfile(self.output_dir)
        except Exception:
            pass

    def _start_new_run(self):
        self.table.setRowCount(0)
        self.files.clear()
        self._update_count()
        self.bottom_stack.setCurrentWidget(self.action_panel)
