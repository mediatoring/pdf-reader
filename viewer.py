import io
import os
import copy
import tempfile
import fitz

APP_VERSION = "1.3"
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QFileDialog,
    QStatusBar, QMessageBox, QColorDialog, QTextEdit,
    QApplication, QLabel, QRubberBand, QPushButton,
)
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtCore import Qt, QSize, QRect, QPoint, QEvent, QTimer
from PyQt6.QtGui import (
    QAction, QColor, QKeySequence, QPainter, QPen, QFont,
    QPixmap, QImage, QShortcut,
)
import icons
from lang import T
from signature_dialog import SignatureDialog

ZOOM_LEVELS = [0.25, 0.33, 0.5, 0.67, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0]
PAGE_SPACING = 3   # matches QPdfView default


# ---------------------------------------------------------------------------
# Drawing overlay — transparent child of QPdfView's viewport
# ---------------------------------------------------------------------------

class DrawOverlay(QWidget):
    """
    Transparent widget that sits on top of QPdfView's viewport.
    - In cursor mode: mouse events pass through (text selection works natively)
    - In drawing mode: captures events, shows real-time stroke preview
    """

    def __init__(self, pdf_view, get_fitz_doc, get_zoom):
        super().__init__(pdf_view.viewport())
        self._pv = pdf_view
        self._get_doc = get_fitz_doc
        self._get_zoom = get_zoom

        self.tool = "none"
        self.draw_color = QColor("#cc0000")
        self.pending_stroke = []
        self.drawing = False
        self._current_page = 0

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setGeometry(pdf_view.viewport().rect())
        self.raise_()

        pdf_view.viewport().installEventFilter(self)
        pdf_view.horizontalScrollBar().valueChanged.connect(self.update)
        pdf_view.verticalScrollBar().valueChanged.connect(self.update)

    # ---- Event filter keeps overlay sized to viewport ---------------------

    def eventFilter(self, obj, event):
        if obj is self._pv.viewport() and event.type() == event.Type.Resize:
            self.setGeometry(obj.rect())
        return False

    # ---- Tool switching ---------------------------------------------------

    def set_tool(self, tool, color=None):
        self.tool = tool
        if color:
            self.draw_color = color
        transparent = (tool in ("none", "edit_text", "text", "rect_select"))
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, transparent)
        cursor = Qt.CursorShape.CrossCursor if not transparent else Qt.CursorShape.ArrowCursor
        self._pv.viewport().setCursor(cursor)

    # ---- Coordinate mapping -----------------------------------------------

    def _page_layouts(self):
        """Return [(y_start, page_height_px, page_width_px, x_start)] for each page."""
        doc = self._get_doc()
        if not doc:
            return []
        zoom = self._get_zoom()
        vp_w = self._pv.viewport().width()
        layouts = []
        y = PAGE_SPACING
        for i in range(len(doc)):
            pw = doc[i].rect.width * zoom
            ph = doc[i].rect.height * zoom
            px = max(0.0, (vp_w - pw) / 2.0)
            layouts.append((y, ph, pw, px))
            y += ph + PAGE_SPACING
        return layouts

    def widget_to_pdf(self, wx, wy):
        """(widget_x, widget_y) → (page_idx, pdf_x, pdf_y) or (None,None,None)."""
        hscroll = self._pv.horizontalScrollBar().value()
        vscroll = self._pv.verticalScrollBar().value()
        ax = wx + hscroll
        ay = wy + vscroll
        zoom = self._get_zoom()
        for i, (y0, ph, pw, px) in enumerate(self._page_layouts()):
            if y0 <= ay <= y0 + ph and px <= ax <= px + pw:
                return i, (ax - px) / zoom, (ay - y0) / zoom
        return None, None, None

    def pdf_to_widget(self, page_idx, pdf_x, pdf_y):
        """(page_idx, pdf_x, pdf_y) → (widget_x, widget_y) or (None,None)."""
        layouts = self._page_layouts()
        if page_idx >= len(layouts):
            return None, None
        y0, ph, pw, px = layouts[page_idx]
        zoom = self._get_zoom()
        hscroll = self._pv.horizontalScrollBar().value()
        vscroll = self._pv.verticalScrollBar().value()
        return px + pdf_x * zoom - hscroll, y0 + pdf_y * zoom - vscroll

    # ---- Mouse events (only active in drawing modes) ----------------------

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        page_idx, pdf_x, pdf_y = self.widget_to_pdf(event.position().x(), event.position().y())
        if page_idx is None:
            return
        self.drawing = True
        self._current_page = page_idx
        self.pending_stroke = [(pdf_x, pdf_y)]

    def mouseMoveEvent(self, event):
        if not self.drawing:
            return
        page_idx, pdf_x, pdf_y = self.widget_to_pdf(event.position().x(), event.position().y())
        if page_idx == self._current_page and pdf_x is not None:
            self.pending_stroke.append((pdf_x, pdf_y))
            self.update()

    def mouseReleaseEvent(self, event):
        if not self.drawing:
            return
        self.drawing = False
        stroke = list(self.pending_stroke)
        self.pending_stroke = []
        self.update()
        if len(stroke) > 1 and self.parent_window:
            self.parent_window._apply_stroke(self._current_page, stroke, self.tool, self.draw_color)

    # ---- Painting ---------------------------------------------------------

    def paintEvent(self, event):
        if not self.pending_stroke:
            return
        zoom = self._get_zoom()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        layouts = self._page_layouts()
        if self._current_page >= len(layouts):
            return
        y0, _, _, px = layouts[self._current_page]
        hscroll = self._pv.horizontalScrollBar().value()
        vscroll = self._pv.verticalScrollBar().value()

        def to_w(pdf_x, pdf_y):
            return (px + pdf_x * zoom - hscroll,
                    y0 + pdf_y * zoom - vscroll)

        color = QColor("#000080") if self.tool == "signature" else self.draw_color
        pen = QPen(color, 2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        pts = self.pending_stroke
        for i in range(1, len(pts)):
            x1, y1 = to_w(*pts[i - 1])
            x2, y2 = to_w(*pts[i])
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

    parent_window = None   # set after construction


# ---------------------------------------------------------------------------
# Draggable text-placement widget (for inserting NEW text)
# ---------------------------------------------------------------------------

class _DragHeader(QLabel):
    """Drag-handle title bar for TextPlacementWidget."""
    def __init__(self, parent_widget):
        super().__init__(T('drag_header'), parent_widget)
        self._widget = parent_widget
        self._drag_pos = None
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setStyleSheet(
            "background:#555555;color:white;padding:3px 6px;font-size:11px;"
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint()
                - self._widget.parent().mapToGlobal(self._widget.pos())
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            self._widget.move(self._widget.parent().mapFromGlobal(new_pos))
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


class TextPlacementWidget(QWidget):
    """Floating draggable overlay for inserting/repositioning text in the PDF."""

    def __init__(self, pos, window, commit_fn=None):
        super().__init__(window)
        self._window = window
        self._commit_fn = commit_fn or window._commit_text_placement
        self._committed = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._header = _DragHeader(self)
        layout.addWidget(self._header)

        self._edit = QTextEdit(self)
        self._edit.setStyleSheet(
            "background:rgba(255,255,200,240);border:none;"
            "font-family:Helvetica;font-size:13px;padding:2px;"
        )
        self._edit.installEventFilter(self)
        layout.addWidget(self._edit)

        btn_bar = QWidget(self)
        btn_bar.setStyleSheet("background:rgba(230,230,190,240);")
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(4, 2, 4, 2)
        self._btn = QPushButton(T('btn_insert'), btn_bar)
        self._btn.setStyleSheet("font-size:11px;padding:2px 10px;")
        self._btn.clicked.connect(lambda: self._commit_fn(self))
        btn_layout.addStretch()
        btn_layout.addWidget(self._btn)
        layout.addWidget(btn_bar)

        self.setStyleSheet("TextPlacementWidget{border:1.5px solid #888;}")
        self.resize(300, 130)
        self.move(pos)
        self.show()
        self.raise_()
        self._edit.setFocus()

    def text(self):
        return self._edit.toPlainText()

    def text_insert_pos(self):
        hdr_h = self._header.sizeHint().height()
        return QPoint(self.pos().x(), self.pos().y() + hdr_h)

    def mark_committed(self):
        self._committed = True
        self._header.setText(T('drag_header_done'))
        self._header.setStyleSheet(
            "background:#2a7a2a;color:white;padding:3px 6px;font-size:11px;"
        )
        self._btn.setText(T('btn_reinsert'))

    def closeEvent(self, event):
        if self._window._text_overlay is self:
            self._window._text_overlay = None
        super().closeEvent(event)

    def eventFilter(self, obj, event):
        if obj is self._edit and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self.close()
                return True
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    self._commit_fn(self)
                    return True
        return False


# ---------------------------------------------------------------------------
# Inline text editor (floats over QPdfView)
# ---------------------------------------------------------------------------

class TextEditOverlay(QTextEdit):
    def __init__(self, text, geom, window):
        super().__init__(window)
        self._window = window
        self.setPlainText(text)
        self.setGeometry(geom)
        self.setStyleSheet(
            "background: rgba(255,255,200,240); border: 1.5px solid #aaa;"
            "font-family: Helvetica; font-size: 13px; padding: 2px;"
        )
        self.show()
        self.raise_()
        self.setFocus()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                # Shift+Enter = nový řádek v editoru
                super().keyPressEvent(event)
            else:
                # Enter = potvrdit změnu
                self._window._commit_text_edit(self)
        else:
            super().keyPressEvent(event)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class PDFViewerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.fitz_doc = None
        self.current_file = None
        self._temp_view = None          # path to temp file for QPdfDocument
        self._zoom_index = 5            # 1.0
        self.active_tool = "none"
        self.draw_color = QColor("#cc0000")

        # Undo / redo: list of {"bytes": b"...", "desc": str}
        self.undo_stack = []
        self.redo_stack = []

        # Pending text-edit block info
        self._text_edit_info = None
        self._text_overlay = None

        # Rectangular text selection state
        self._rect_sel_start = None
        self._rect_sel_active = False

        self.setWindowTitle(f"PDF Reader {APP_VERSION}")
        self.setMinimumSize(960, 720)
        self._build_ui()
        self._build_toolbar()
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(T('open_hint'))
        self._add_status_branding()

    # ---- UI construction --------------------------------------------------

    def _build_ui(self):
        # QPdfDocument + QPdfView
        self.qt_doc = QPdfDocument(self)
        self.pdf_view = QPdfView(self)
        self.pdf_view.setDocument(self.qt_doc)
        self.pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
        self.pdf_view.setZoomFactor(1.0)
        self.pdf_view.setPageSpacing(PAGE_SPACING)
        self.pdf_view.setStyleSheet("background: #606060;")
        self.setCentralWidget(self.pdf_view)

        # Drawing overlay
        self.overlay = DrawOverlay(
            self.pdf_view,
            get_fitz_doc=lambda: self.fitz_doc,
            get_zoom=lambda: ZOOM_LEVELS[self._zoom_index],
        )
        self.overlay.parent_window = self

        # Rubber band for rectangular text selection (always-on event filter)
        self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self.pdf_view.viewport())
        self.pdf_view.viewport().installEventFilter(self)

        # Standard clipboard/selection shortcuts forwarded to the PDF view
        QShortcut(QKeySequence.StandardKey.SelectAll, self, self._select_all)
        QShortcut(QKeySequence.StandardKey.Copy, self, self._copy_selection)
        QShortcut(QKeySequence.StandardKey.Paste, self, self._paste_as_text)

    def _build_toolbar(self):
        tb = QToolBar()
        tb.setIconSize(QSize(22, 22))
        tb.setMovable(False)
        self.addToolBar(tb)

        def act(icon, label, shortcut=None, checkable=False, slot=None):
            a = QAction(icon, label, self)
            if shortcut:
                a.setShortcut(shortcut)
            if checkable:
                a.setCheckable(True)
            if slot:
                a.triggered.connect(slot)
            tb.addAction(a)
            return a

        act(icons.icon_open(),    T('open'),       QKeySequence.StandardKey.Open, slot=self.open_dialog)
        act(icons.icon_save(),    T('save'),       QKeySequence.StandardKey.Save, slot=self.save_file)
        act(icons.icon_save_as(), T('save_as'),    slot=self.save_file_as)
        act(icons.icon_copy(),    T('save_copy'),  slot=self.copy_pdf)

        tb.addSeparator()

        self.act_undo = act(icons.icon_undo(), T('undo'), QKeySequence.StandardKey.Undo, slot=self.undo)
        self.act_redo = act(icons.icon_redo(), T('redo'), QKeySequence.StandardKey.Redo, slot=self.redo)
        self._update_undo_state()

        tb.addSeparator()

        act(icons.icon_zoom_out(), T('zoom_out'), QKeySequence.StandardKey.ZoomOut, slot=self.zoom_out)
        self.zoom_label = QLabel("  100%  ")
        tb.addWidget(self.zoom_label)
        act(icons.icon_zoom_in(), T('zoom_in'), QKeySequence.StandardKey.ZoomIn,  slot=self.zoom_in)

        tb.addSeparator()

        self.act_cursor    = act(icons.icon_cursor(),      T('cursor'),      checkable=True, slot=lambda: self.set_tool("none"))
        self.act_rect_sel  = act(icons.icon_rect_select(), T('select_area'), checkable=True, slot=lambda: self.set_tool("rect_select"))
        self.act_edit_text = act(icons.icon_edit_text(),   T('edit_text'),   checkable=True, slot=lambda: self.set_tool("edit_text"))
        self.act_text      = act(icons.icon_text(),        T('add_text'),    checkable=True, slot=lambda: self.set_tool("text"))
        self.act_comment   = act(icons.icon_comment(),     T('add_comment'), checkable=True, slot=lambda: self.set_tool("comment"))
        self.act_draw      = act(icons.icon_draw(),        T('draw'),        checkable=True, slot=lambda: self.set_tool("draw"))
        self.act_cert_sign = act(icons.icon_cert_sign(),   T('esign'),       slot=self.open_cert_sign_dialog)

        tb.addSeparator()

        self.color_action = act(icons.icon_color(self.draw_color.name()), T('pen_color'), slot=self.pick_color)

        self._tool_actions = [self.act_cursor, self.act_rect_sel, self.act_edit_text, self.act_text, self.act_comment, self.act_draw]
        self.act_cursor.setChecked(True)

    def _add_status_branding(self):
        from PyQt6.QtWidgets import QLabel
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        lbl = QLabel('<a href="https://mediatoring.com" style="color:#888;text-decoration:none;">'
                     'mediatoring.com</a>')
        lbl.setOpenExternalLinks(False)
        lbl.linkActivated.connect(lambda url: QDesktopServices.openUrl(QUrl(url)))
        lbl.setStyleSheet("font-size:11px; padding-right:6px;")
        self.statusBar().addPermanentWidget(lbl)

    # ---- Clipboard shortcuts ----------------------------------------------

    def _select_all(self):
        fw = QApplication.focusWidget()
        if fw and hasattr(fw, 'selectAll'):
            fw.selectAll()
        else:
            self.pdf_view.viewport().setFocus()

    def _copy_selection(self):
        """Ctrl+C: copy selected PDF text, or pass through to focused widget."""
        fw = QApplication.focusWidget()
        if fw and hasattr(fw, 'copy'):
            fw.copy()
            return
        # Try QPdfView selection
        if hasattr(self.pdf_view, 'copySelectionToClipboard'):
            self.pdf_view.copySelectionToClipboard()

    def _paste_as_text(self):
        """Ctrl+V: paste clipboard text as new annotation at current cursor position."""
        text = QApplication.clipboard().text().strip()
        if not text or not self.fitz_doc or self.active_tool not in ("text", "comment"):
            return
        self.statusBar().showMessage(T('paste_hint'))

    # ---- File operations --------------------------------------------------

    def open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, T('open_pdf_dlg'), "", T('pdf_filter'))
        if path:
            self.open_file(path)

    def open_file(self, path):
        try:
            raw = fitz.open(path)
            # Detach from the on-disk file so all subsequent save(BytesIO) calls
            # do a full write. Without this, fitz tries incremental save and fails
            # with "save to original must be incremental" on many real-world PDFs.
            buf = io.BytesIO()
            raw.save(buf, garbage=4, deflate=True)
            raw.close()
            self.fitz_doc = fitz.open("pdf", buf.getvalue())
            self.current_file = path
            self.undo_stack.clear()
            self.redo_stack.clear()
            self._update_undo_state()
            self.setWindowTitle(f"PDF Reader {APP_VERSION} — {os.path.basename(path)}")
            n = len(self.fitz_doc)
            self.statusBar().showMessage(f"{os.path.basename(path)}  •  {n} {T('pages')}")
            self._reload_view()
        except Exception as e:
            QMessageBox.critical(self, T('err_open'), T('err_open_msg', e=e))

    def save_file(self):
        if not self.current_file:
            self.save_file_as()
        else:
            self._write_pdf(self.current_file)

    def save_file_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, T('save_as_dlg'), self.current_file or "", T('pdf_filter')
        )
        if path:
            self.current_file = path
            self._write_pdf(path)

    def copy_pdf(self):
        if not self.fitz_doc:
            return
        base = self.current_file or "document.pdf"
        stem = os.path.splitext(base)[0]
        default = f"{stem}{T('copy_suffix')}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self, T('save_copy_dlg'), default, T('pdf_filter')
        )
        if path:
            self._write_pdf_copy(path)

    def _write_pdf_copy(self, path):
        try:
            self.fitz_doc.save(path, garbage=4, deflate=True)
            self.statusBar().showMessage(T('copy_saved', name=os.path.basename(path)))
        except Exception as e:
            QMessageBox.critical(self, T('err_save_copy'), str(e))

    def _write_pdf(self, path):
        if not self.fitz_doc:
            return
        try:
            self.fitz_doc.save(path, garbage=4, deflate=True)
            self.statusBar().showMessage(T('saved', name=os.path.basename(path)))
        except Exception as e:
            QMessageBox.critical(self, T('err_save'), str(e))

    # ---- View reload (fitz_doc → QPdfDocument) ----------------------------

    def _reload_view(self):
        """Save fitz_doc to temp file and reload QPdfDocument."""
        if self._temp_view and os.path.exists(self._temp_view):
            try:
                os.unlink(self._temp_view)
            except OSError:
                pass
        fd, self._temp_view = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        self.fitz_doc.save(self._temp_view, garbage=4, deflate=True)
        self.qt_doc.close()
        self.qt_doc.load(self._temp_view)

    # ---- Undo / redo ------------------------------------------------------

    def _push_undo(self, desc=""):
        buf = io.BytesIO()
        self.fitz_doc.save(buf, garbage=4, deflate=True)
        self.undo_stack.append({"bytes": buf.getvalue(), "desc": desc})
        self.redo_stack.clear()
        self._update_undo_state()

    def undo(self):
        if not self.undo_stack:
            return
        # Push current to redo
        buf = io.BytesIO()
        self.fitz_doc.save(buf, garbage=4, deflate=True)
        self.redo_stack.append({"bytes": buf.getvalue()})
        # Restore previous
        state = self.undo_stack.pop()
        self.fitz_doc = fitz.open("pdf", state["bytes"])
        self._reload_view()
        self._update_undo_state()
        self.statusBar().showMessage(T('undo_msg', desc=state.get('desc', '')))

    def redo(self):
        if not self.redo_stack:
            return
        buf = io.BytesIO()
        self.fitz_doc.save(buf, garbage=4, deflate=True)
        self.undo_stack.append({"bytes": buf.getvalue()})
        state = self.redo_stack.pop()
        self.fitz_doc = fitz.open("pdf", state["bytes"])
        self._reload_view()
        self._update_undo_state()

    def _update_undo_state(self):
        if hasattr(self, 'act_undo'):
            self.act_undo.setEnabled(bool(self.undo_stack))
            self.act_redo.setEnabled(bool(self.redo_stack))

    # ---- Zoom -------------------------------------------------------------

    def zoom_in(self):
        if self._zoom_index < len(ZOOM_LEVELS) - 1:
            self._zoom_index += 1
            self._apply_zoom()

    def zoom_out(self):
        if self._zoom_index > 0:
            self._zoom_index -= 1
            self._apply_zoom()

    def _apply_zoom(self):
        zoom = ZOOM_LEVELS[self._zoom_index]
        self.pdf_view.setZoomFactor(zoom)
        self.zoom_label.setText(f"  {int(zoom * 100)}%  ")

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    # ---- Tools ------------------------------------------------------------

    def set_tool(self, tool):
        self.active_tool = tool
        for a in self._tool_actions:
            a.setChecked(False)
        mapping = {
            "none":        self.act_cursor,
            "rect_select": self.act_rect_sel,
            "edit_text":   self.act_edit_text,
            "text":        self.act_text,
            "comment":     self.act_comment,
            "draw":        self.act_draw,
        }
        if tool in mapping:
            mapping[tool].setChecked(True)
        self.overlay.set_tool(tool, self.draw_color)

        # Update cursor (event filter is always installed in _build_ui)
        if tool in ("text", "edit_text"):
            self.pdf_view.viewport().setCursor(Qt.CursorShape.IBeamCursor)
        elif tool == "comment":
            self.pdf_view.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        elif tool == "rect_select":
            self.pdf_view.viewport().setCursor(Qt.CursorShape.CrossCursor)
        elif tool == "none":
            self.pdf_view.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def eventFilter(self, obj, event):
        if obj is self.pdf_view.viewport():
            etype = event.type()

            if etype == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                mods = event.modifiers()
                alt = bool(mods & Qt.KeyboardModifier.AltModifier)
                is_rect = (self.active_tool == "rect_select" or
                           (self.active_tool == "none" and alt))

                if is_rect:
                    self._rect_sel_start = event.position().toPoint()
                    self._rect_sel_active = True
                    self._rubber_band.setGeometry(QRect(self._rect_sel_start, QSize(0, 0)))
                    self._rubber_band.show()
                    return True

                elif self.active_tool in ("text", "edit_text", "comment"):
                    pos = event.position()
                    page_idx, pdf_x, pdf_y = self.overlay.widget_to_pdf(pos.x(), pos.y())
                    if page_idx is not None:
                        if self.active_tool == "text":
                            self._place_text(page_idx, pdf_x, pdf_y)
                        elif self.active_tool == "edit_text":
                            self._open_text_editor(page_idx, pdf_x, pdf_y, pos)
                        elif self.active_tool == "comment":
                            self._place_comment(page_idx, pdf_x, pdf_y)
                    return True

            elif etype == QEvent.Type.MouseMove:
                if self._rect_sel_active and self._rect_sel_start:
                    self._rubber_band.setGeometry(
                        QRect(self._rect_sel_start, event.position().toPoint()).normalized()
                    )
                    return True

            elif etype == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                if self._rect_sel_active:
                    end = event.position().toPoint()
                    # Don't hide immediately — _extract_rect_text uses a timer for visual feedback
                    self._extract_rect_text(self._rect_sel_start, end)
                    self._rect_sel_start = None
                    self._rect_sel_active = False
                    return True

        return False

    def _extract_rect_text(self, start_pt, end_pt):
        """Extract text within a widget-coord rectangle and copy to clipboard."""
        if not self.fitz_doc:
            self.statusBar().showMessage(T('open_first'))
            return
        x0 = min(start_pt.x(), end_pt.x())
        y0 = min(start_pt.y(), end_pt.y())
        x1 = max(start_pt.x(), end_pt.x())
        y1 = max(start_pt.y(), end_pt.y())
        if x1 - x0 < 3 or y1 - y0 < 3:
            return

        zoom = ZOOM_LEVELS[self._zoom_index]
        vp_w = self.pdf_view.viewport().width()
        hscroll = self.pdf_view.horizontalScrollBar().value()
        vscroll = self.pdf_view.verticalScrollBar().value()

        texts = []
        y_page = PAGE_SPACING
        for i in range(len(self.fitz_doc)):
            pw = self.fitz_doc[i].rect.width * zoom
            ph = self.fitz_doc[i].rect.height * zoom
            px = max(0.0, (vp_w - pw) / 2.0)
            page_wx0 = px - hscroll
            page_wy0 = y_page - vscroll
            page_wx1 = px + pw - hscroll
            page_wy1 = y_page + ph - vscroll
            y_page += ph + PAGE_SPACING

            if x1 < page_wx0 or x0 > page_wx1 or y1 < page_wy0 or y0 > page_wy1:
                continue

            pdf_x0 = max(0.0, (x0 - page_wx0) / zoom)
            pdf_y0 = max(0.0, (y0 - page_wy0) / zoom)
            pdf_x1 = min(self.fitz_doc[i].rect.width, (x1 - page_wx0) / zoom)
            pdf_y1 = min(self.fitz_doc[i].rect.height, (y1 - page_wy0) / zoom)

            clip = fitz.Rect(pdf_x0, pdf_y0, pdf_x1, pdf_y1)
            text = self.fitz_doc[i].get_text("text", clip=clip).strip()
            if text:
                texts.append(text)

        if texts:
            result = "\n".join(texts)
            QApplication.clipboard().setText(result)
            chars = sum(len(t) for t in texts)
            self.statusBar().showMessage(T('copied_chars', n=chars))
            # Keep rubber band visible 900ms so it's clear this was a SELECTION, not creation
            QTimer.singleShot(900, self._rubber_band.hide)
        else:
            self.statusBar().showMessage(T('no_text_found'))
            QTimer.singleShot(400, self._rubber_band.hide)

    def pick_color(self):
        color = QColorDialog.getColor(self.draw_color, self)
        if color.isValid():
            self.draw_color = color
            self.overlay.draw_color = color
            self.color_action.setIcon(icons.icon_color(color.name()))

    # ---- Stroke application -----------------------------------------------

    def _apply_stroke(self, page_idx, stroke, tool, color):
        """Called by DrawOverlay when a stroke is completed."""
        if not self.fitz_doc or len(stroke) < 2:
            return
        self._push_undo(T('undo_draw'))
        page = self.fitz_doc[page_idx]
        rgb = (color.redF(), color.greenF(), color.blueF())
        for i in range(1, len(stroke)):
            page.draw_line(
                fitz.Point(*stroke[i - 1]),
                fitz.Point(*stroke[i]),
                color=rgb, width=1.5,
            )
        self._reload_view()

    # ---- Text placement ---------------------------------------------------

    def _place_text(self, page_idx, pdf_x, pdf_y, dialog_parent=None):
        if self._text_overlay:
            self._text_overlay.close()
            self._text_overlay = None

        pv_pos = self.pdf_view.pos()
        wx, wy = self.overlay.pdf_to_widget(page_idx, pdf_x, pdf_y)
        if wx is None:
            return

        pos = QPoint(int(pv_pos.x() + wx), int(pv_pos.y() + wy))
        self._text_overlay = TextPlacementWidget(pos, self)

    def _commit_text_placement(self, widget):
        text = widget.text().strip()
        if not text or not self.fitz_doc:
            return

        # If already committed once, undo that insertion before reinserting
        if widget._committed:
            self.undo()

        insert_pt = widget.text_insert_pos()
        pv_pos = self.pdf_view.pos()
        vx = insert_pt.x() - pv_pos.x()
        vy = insert_pt.y() - pv_pos.y()

        page_idx, pdf_x, pdf_y = self.overlay.widget_to_pdf(vx, vy)
        if page_idx is None:
            self.statusBar().showMessage(T('text_outside'))
            return

        self._push_undo(T('undo_add_text'))
        page = self.fitz_doc[page_idx]
        rgb = (self.draw_color.redF(), self.draw_color.greenF(), self.draw_color.blueF())
        page.insert_text(fitz.Point(pdf_x, pdf_y + 12), text, fontsize=12, color=rgb)
        self._reload_view()
        widget.mark_committed()
        widget.raise_()

    # ---- Comment / sticky-note annotations --------------------------------

    def _place_comment(self, page_idx, pdf_x, pdf_y):
        if self._text_overlay:
            self._text_overlay.close()
            self._text_overlay = None
        pv_pos = self.pdf_view.pos()
        wx, wy = self.overlay.pdf_to_widget(page_idx, pdf_x, pdf_y)
        if wx is None:
            return
        pos = QPoint(int(pv_pos.x() + wx), int(pv_pos.y() + wy))
        self._text_overlay = TextPlacementWidget(pos, self, commit_fn=self._commit_comment)

    def _commit_comment(self, widget):
        text = widget.text().strip()
        if not text or not self.fitz_doc:
            return

        if widget._committed:
            self.undo()

        insert_pt = widget.text_insert_pos()
        pv_pos = self.pdf_view.pos()
        vx = insert_pt.x() - pv_pos.x()
        vy = insert_pt.y() - pv_pos.y()

        page_idx, pdf_x, pdf_y = self.overlay.widget_to_pdf(vx, vy)
        if page_idx is None:
            self.statusBar().showMessage(T('comment_outside'))
            return

        self._push_undo(T('undo_add_comment'))
        page = self.fitz_doc[page_idx]
        annot = page.add_text_annot(fitz.Point(pdf_x, pdf_y), text, icon="Note")
        annot.set_colors({"stroke": (1.0, 0.8, 0.0), "fill": (1.0, 0.95, 0.4)})
        annot.update()
        self._reload_view()
        self.statusBar().showMessage(T('comment_added', n=page_idx + 1))
        widget.mark_committed()
        widget.raise_()

    # ---- Inline text editing ----------------------------------------------

    def _open_text_editor(self, page_idx, pdf_x, pdf_y, viewport_pos):
        if self._text_overlay:
            self._text_overlay.close()

        page = self.fitz_doc[page_idx]
        blocks = page.get_text("dict")["blocks"]
        clicked = fitz.Point(pdf_x, pdf_y)
        target = None
        for block in blocks:
            if block.get("type") != 0:
                continue
            if fitz.Rect(block["bbox"]).contains(clicked):
                target = block
                break

        if target is None:
            return

        # Collect text and font size
        text = ""
        font_size = 12.0
        for line in target.get("lines", []):
            for span in line.get("spans", []):
                text += span["text"]
                font_size = span.get("size", 12)
            text += "\n"
        text = text.rstrip("\n")

        # Convert block rect to main window coords
        bx0, by0, bx1, by1 = target["bbox"]
        wx0, wy0 = self.overlay.pdf_to_widget(page_idx, bx0, by0)
        wx1, wy1 = self.overlay.pdf_to_widget(page_idx, bx1, by1)
        if wx0 is None:
            return

        # Map to main window coordinates (pdf_view is the central widget)
        pv_pos = self.pdf_view.pos()
        geom = QRect(
            int(pv_pos.x() + wx0),
            int(pv_pos.y() + wy0),
            max(220, int(wx1 - wx0)),
            max(44, int(wy1 - wy0) + 20),
        )
        self._text_edit_info = {"page": page_idx, "bbox": target["bbox"], "font_size": font_size}
        self._text_overlay = TextEditOverlay(text, geom, self)

    def _commit_text_edit(self, overlay):
        info = self._text_edit_info
        overlay.close()
        self._text_overlay = None
        self._text_edit_info = None
        if not info:
            return
        new_text = overlay.toPlainText()
        self._push_undo(T('undo_edit_text'))
        page = self.fitz_doc[info["page"]]
        rect = fitz.Rect(info["bbox"])
        # Draw a white rectangle to cover the old text, then insert new text on top.
        # apply_redactions() is intentionally avoided — it fails on PDFs with incremental
        # update chains ("save must be incremental") which are very common in practice.
        page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
        page.insert_text(
            fitz.Point(rect.x0, rect.y0 + info["font_size"]),
            new_text,
            fontsize=info["font_size"],
            color=(0, 0, 0),
        )
        self._reload_view()

    # ---- Signature --------------------------------------------------------

    def open_signature_dialog(self):
        dlg = SignatureDialog(current_file=self.current_file, parent=self)
        dlg.digital_signed.connect(self.open_file)
        if dlg.exec():
            stroke = dlg.get_stroke()
            if stroke and self.fitz_doc:
                page_idx = self.pdf_view.pageNavigator().currentPage()
                page = self.fitz_doc[page_idx]
                pw, ph = page.rect.width, page.rect.height
                xs = [p[0] for p in stroke]
                ys = [p[1] for p in stroke]
                sw = max(xs) - min(xs) or 1
                target_w = pw * 0.38
                scale = target_w / sw
                ox = pw * 0.55 - min(xs) * scale
                oy = ph * 0.82 - min(ys) * scale
                pts = [(x * scale + ox, y * scale + oy) for x, y in stroke]
                self._push_undo(T('undo_sign'))
                for i in range(1, len(pts)):
                    page.draw_line(fitz.Point(*pts[i-1]), fitz.Point(*pts[i]),
                                   color=(0, 0, 0.5), width=1.8)
                self._reload_view()
        self.set_tool("none")

    def open_cert_sign_dialog(self):
        dlg = SignatureDialog(current_file=self.current_file, parent=self)
        dlg.digital_signed.connect(self.open_file)
        dlg.tabs.setCurrentIndex(1)
        dlg.exec()
        self.act_cert_sign.setChecked(False)

    def closeEvent(self, event):
        if self._temp_view and os.path.exists(self._temp_view):
            try:
                os.unlink(self._temp_view)
            except OSError:
                pass
        super().closeEvent(event)
