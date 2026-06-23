#!/usr/bin/env python3
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QEvent
from viewer import PDFViewerWindow


class PDFApp(QApplication):
    """Handles macOS file-open events (Finder double-click, Drag & Drop on icon)."""

    def __init__(self, argv):
        super().__init__(argv)
        self.window = None

    def event(self, event):
        if event.type() == QEvent.Type.FileOpen:
            path = event.file()
            if self.window:
                self.window.open_file(path)
            else:
                # Store for later — window not yet created
                self._pending_file = path
        return super().event(event)


def main():
    app = PDFApp(sys.argv)
    app.setApplicationName("PDF Reader")
    app.setOrganizationName("Kubicek.AI")

    window = PDFViewerWindow()
    app.window = window
    window.show()

    # File from command-line argument (e.g. terminal, older py2app)
    pending = getattr(app, '_pending_file', None)
    if pending:
        window.open_file(pending)
    elif len(sys.argv) > 1 and sys.argv[1].endswith('.pdf'):
        window.open_file(sys.argv[1])

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
