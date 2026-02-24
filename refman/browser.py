from PyQt5.QtWidgets import QFrame, QFormLayout, QHBoxLayout, QLineEdit, QPushButton
from PyQt5.QtGui import QIcon
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEngineProfile
from PyQt5.QtCore import QUrl, QSize
from refman.varsys import ICON_CLEAR, ICON_REFRESH

class XBrowser(QWebEngineView):
    def __init__(self):
        QWebEngineView.__init__(self)
        self.setAcceptDrops(False)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
    def sizeHint(self):
        return QSize(800, 900)
    def minimumSizeHint(self):
        return QSize(400, 200)
class QWebBrowser(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        flayout = QFormLayout()
        self.setLayout(flayout)
        menubar = QFrame()
        mlayout = QHBoxLayout()
        menubar.setLayout(mlayout)
        self.urledit = QLineEdit()
        self.btnstop = QPushButton()
        self.btnstop.setIcon(QIcon(ICON_CLEAR))
        self.btnreload = QPushButton()
        self.btnreload.setIcon(QIcon(ICON_REFRESH))
        mlayout.addWidget(self.urledit)
        mlayout.addWidget(self.btnstop)
        mlayout.addWidget(self.btnreload)
        self.browser = XBrowser()
        flayout.addRow(menubar)
        flayout.addRow(self.browser)
        self.browser.page().load(QUrl('https://www.lzu.edu.cn'))