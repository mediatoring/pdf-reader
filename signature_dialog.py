"""Signature dialog — drawn signature or certified digital signature from Keychain."""
import os
from lang import T
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTabWidget, QWidget, QComboBox, QLineEdit, QFormLayout,
    QMessageBox, QFileDialog, QProgressDialog,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor


# ---------------------------------------------------------------------------
# Drawn signature canvas
# ---------------------------------------------------------------------------

class SignatureCanvas(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(500, 180)
        self.strokes = []
        self.current = []
        self.drawing = False
        self._refresh()

    def _refresh(self):
        pix = QPixmap(self.size())
        pix.fill(QColor("white"))
        painter = QPainter(pix)
        pen = QPen(QColor("#000080"), 2.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        for stroke in self.strokes:
            for i in range(1, len(stroke)):
                painter.drawLine(
                    int(stroke[i-1][0]), int(stroke[i-1][1]),
                    int(stroke[i][0]), int(stroke[i][1])
                )
        if self.current:
            for i in range(1, len(self.current)):
                painter.drawLine(
                    int(self.current[i-1][0]), int(self.current[i-1][1]),
                    int(self.current[i][0]), int(self.current[i][1])
                )
        painter.end()
        self.setPixmap(pix)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            pos = e.position()
            self.current = [(pos.x(), pos.y())]

    def mouseMoveEvent(self, e):
        if self.drawing:
            pos = e.position()
            self.current.append((pos.x(), pos.y()))
            self._refresh()

    def mouseReleaseEvent(self, e):
        if self.drawing and len(self.current) > 1:
            self.strokes.append(list(self.current))
        self.current = []
        self.drawing = False

    def clear(self):
        self.strokes = []
        self._refresh()

    def has_content(self):
        return bool(self.strokes)

    def get_combined_stroke(self):
        combined = []
        for stroke in self.strokes:
            combined.extend(stroke)
        return combined


# ---------------------------------------------------------------------------
# Digital signature worker thread
# ---------------------------------------------------------------------------

class SignWorker(QThread):
    done = pyqtSignal(bool, str)

    def __init__(self, input_path, output_path, p12_path, p12_password, reason, location, contact):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.p12_path = p12_path
        self.p12_password = p12_password
        self.reason = reason
        self.location = location
        self.contact = contact

    def run(self):
        from keychain_sign import sign_pdf_p12
        ok, msg = sign_pdf_p12(
            self.input_path, self.output_path,
            self.p12_path, self.p12_password,
            self.reason, self.location, self.contact,
        )
        self.done.emit(ok, msg)


# ---------------------------------------------------------------------------
# Main dialog
# ---------------------------------------------------------------------------

class SignatureDialog(QDialog):
    # Emitted when a digital signature was applied directly (not drawn)
    digital_signed = pyqtSignal(str)  # output_path

    def __init__(self, current_file=None, parent=None):
        super().__init__(parent)
        self.current_file = current_file
        self.setWindowTitle(T('sig_title'))
        self.setMinimumWidth(540)
        self._stroke = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # ---- Tab 1: drawn ----
        tab_draw = QWidget()
        vl = QVBoxLayout(tab_draw)
        vl.addWidget(QLabel(T('sig_draw_label')))
        self.canvas = SignatureCanvas()
        self.canvas.setStyleSheet("border: 1px solid #ccc; border-radius: 4px;")
        vl.addWidget(self.canvas)
        row = QHBoxLayout()
        btn_clear = QPushButton(T('sig_clear'))
        btn_clear.clicked.connect(self.canvas.clear)
        row.addWidget(btn_clear)
        row.addStretch()
        btn_cancel1 = QPushButton(T('sig_cancel'))
        btn_cancel1.clicked.connect(self.reject)
        row.addWidget(btn_cancel1)
        btn_insert = QPushButton(T('sig_insert'))
        btn_insert.setDefault(True)
        btn_insert.clicked.connect(self._accept_drawn)
        row.addWidget(btn_insert)
        vl.addLayout(row)
        self.tabs.addTab(tab_draw, T('sig_tab_draw'))

        # ---- Tab 2: digital cert via P12 ----
        tab_cert = QWidget()
        cert_layout = QVBoxLayout(tab_cert)
        cert_layout.setSpacing(8)

        info = QLabel(T('sig_cert_info'))
        info.setStyleSheet("color: #555; font-size: 12px;")
        info.setWordWrap(True)
        cert_layout.addWidget(info)

        fl = QFormLayout()
        fl.setSpacing(10)

        p12_row = QHBoxLayout()
        self.p12_path_edit = QLineEdit()
        self.p12_path_edit.setPlaceholderText(T('sig_p12_placeholder'))
        self.p12_path_edit.setReadOnly(True)
        p12_row.addWidget(self.p12_path_edit)
        btn_browse = QPushButton(T('sig_browse'))
        btn_browse.clicked.connect(self._browse_p12)
        p12_row.addWidget(btn_browse)
        fl.addRow(T('sig_p12_label'), p12_row)

        self.p12_pw_edit = QLineEdit()
        self.p12_pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.p12_pw_edit.setPlaceholderText(T('sig_pw_placeholder'))
        fl.addRow(T('sig_pw_label'), self.p12_pw_edit)

        self.reason_edit = QLineEdit()
        self.reason_edit.setPlaceholderText(T('sig_reason_ph'))
        fl.addRow(T('sig_reason_label'), self.reason_edit)

        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText(T('sig_location_ph'))
        fl.addRow(T('sig_location_label'), self.location_edit)

        self.contact_edit = QLineEdit()
        self.contact_edit.setPlaceholderText(T('sig_contact_ph'))
        fl.addRow(T('sig_contact_label'), self.contact_edit)

        self.output_label = QLabel()
        self._update_output_label()
        fl.addRow(T('sig_output_label'), self.output_label)

        cert_layout.addLayout(fl)

        row2 = QHBoxLayout()
        row2.addStretch()
        btn_cancel2 = QPushButton(T('sig_cancel'))
        btn_cancel2.clicked.connect(self.reject)
        row2.addWidget(btn_cancel2)
        btn_sign = QPushButton(T('sig_sign_btn'))
        btn_sign.setDefault(True)
        btn_sign.clicked.connect(self._sign_with_cert)
        row2.addWidget(btn_sign)
        cert_layout.addLayout(row2)
        cert_layout.addStretch()

        self.tabs.addTab(tab_cert, T('sig_tab_cert'))

    def _browse_p12(self):
        path, _ = QFileDialog.getOpenFileName(
            self, T('sig_open_p12_dlg'), "", T('sig_p12_filter')
        )
        if path:
            self.p12_path_edit.setText(path)

    def _update_output_label(self):
        if self.current_file:
            base, ext = os.path.splitext(self.current_file)
            self.output_label.setText(os.path.basename(base + "_signed" + ext))
        else:
            self.output_label.setText(T('sig_no_pdf_label'))

    def _accept_drawn(self):
        if not self.canvas.has_content():
            return
        self._stroke = self.canvas.get_combined_stroke()
        self.accept()

    def _sign_with_cert(self):
        if not self.current_file:
            QMessageBox.warning(self, T('err_open'), T('sig_err_no_pdf'))
            return
        p12_path = self.p12_path_edit.text().strip()
        if not p12_path:
            QMessageBox.warning(self, T('err_open'), T('sig_err_no_p12'))
            return

        base, ext = os.path.splitext(self.current_file)
        output_path = base + "_signed" + ext

        p12_password = self.p12_pw_edit.text()
        reason = self.reason_edit.text().strip()
        location = self.location_edit.text().strip()
        contact = self.contact_edit.text().strip()

        prog = QProgressDialog(T('sig_progress'), None, 0, 0, self)
        prog.setWindowModality(Qt.WindowModality.WindowModal)
        prog.show()

        self._worker = SignWorker(
            self.current_file, output_path,
            p12_path, p12_password, reason, location, contact,
        )
        self._worker.done.connect(lambda ok, msg: self._on_signed(ok, msg, output_path, prog))
        self._worker.start()

    def _on_signed(self, ok, msg, output_path, prog):
        prog.close()
        if ok:
            QMessageBox.information(self, T('sig_done_title'), T('sig_done_msg', path=output_path))
            self.digital_signed.emit(output_path)
            self.accept()
        else:
            QMessageBox.critical(self, T('sig_err_sign'), msg)

    def get_stroke(self):
        return self._stroke
