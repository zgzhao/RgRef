import sys, os, shutil
from tempfile import mktemp
from PyQt5 import QtCore
from PyQt5.QtGui import QCloseEvent, QPixmap, QIcon
from PyQt5.QtWidgets import (QMainWindow, QApplication, QMessageBox, QSplashScreen, QStatusBar, QMenuBar, QMenu, QWidget,
                             QToolBar, QAction)
from refman.varsys import *
from refman.config import UserConfig, setFontSize
from refman.widget import CleanSpacer, DbJournalStat
from refman.appmain import AppLayout

def statJournals():
    DbJournalStat()

def check_program(program):
    """检测程序是否安装"""
    path = shutil.which(program)
    if path:
        return True
    else:
        return False
class XSplashScreen(QSplashScreen):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.p = parent
    def mouseReleaseEvent(self, a0):
        self.finish(self.p)
        self.deleteLater()
class APPwindow(object):
    ready = QtCore.pyqtSignal(QStatusBar)
    def __init__(self, MainWindow):
        super().__init__()
        self.MainWindow = MainWindow
        self.centralwidget = QWidget()
        self.centralwidget.setObjectName("centralwidget")
        self.centralwidget.setParent(MainWindow)
        MainWindow.setCentralWidget(self.centralwidget)
        MainWindow.setObjectName("MainWindow")
        self.UIs = AppLayout()
        self.centralwidget.setLayout(self.UIs)
        ##
        font = setFontSize()
        self.menubar = QMenuBar()
        self.menubar.setObjectName("menubar")
        self.menubar.setFont(font)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 28))
        self.menuFile = QMenu(self.menubar)
        self.toolBar = QToolBar()
        self.toolBar.setMovable(False)
        self.toolBar.setFloatable(False)
        self.toolBar.setContentsMargins(0, 0, 50, 0)
        self.toolBar.setObjectName("toolBar")
        self.menubar.setParent(MainWindow)
        self.toolBar.setParent(MainWindow)
        # 文件菜单 ------------------------
        self.menuFile.setObjectName("menuFile")
        self.menubar.addAction(self.menuFile.menuAction())
        self.menuFile.setFont(font)
        # 导入-raw
        self.actionImportRaw = QAction(MainWindow)
        self.actionImportRaw.setObjectName("actImportSpringer")
        self.menuFile.addAction(self.actionImportRaw)
        # 导入-springer
        self.actionImportSpringer = QAction(MainWindow)
        self.actionImportSpringer.setObjectName("actImportSpringer")
        self.menuFile.addAction(self.actionImportSpringer)
        # PubMed查询
        self.actionImportPubmed = QAction(MainWindow)
        self.actionImportPubmed.setObjectName("actImportRaw")
        self.menuFile.addAction(self.actionImportPubmed)
        # 系统设置
        self.menuFile.addSeparator()
        self.actionConfig = QAction(MainWindow)
        self.actionConfig.setObjectName("actConfig")
        self.menuFile.addAction(self.actionConfig)
        # 退出
        self.menuFile.addSeparator()
        self.actionExit = QAction(MainWindow)
        self.actionExit.setObjectName("actExit")
        self.menuFile.addAction(self.actionExit)
        # 数据菜单 menuData ----------------------------------
        self.menuData= QMenu(self.menubar)
        self.menuData.setObjectName("menuData")
        self.menubar.addAction(self.menuData.menuAction())
        self.menuData.setFont(font)
        # 文献清理
        self.menuData.addSection('文献清理')
        self.actionDbStats = QAction(MainWindow)
        self.menuData.addAction(self.actionDbStats)
        # self.actionDbCleanBlackList = QAction(MainWindow)
        # self.actionDbCleanBlackList.setObjectName("actDbCleanBlackList")
        # self.menuData.addAction(self.actionDbCleanBlackList)
        # 期刊映射
        self.menuData.addSection('期刊信息')
        self.actionMapISSN2impact= QAction(MainWindow)
        self.actionMapISSN2impact.setObjectName("actMapISSN2impact")
        self.menuData.addAction(self.actionMapISSN2impact)
        self.actionMapISSN2journal = QAction(MainWindow)
        self.actionMapISSN2journal.setObjectName("actMapISSN2journal")
        self.menuData.addAction(self.actionMapISSN2journal)
        # 历史记录
        self.menuData.addSection('历史记录')
        self.actionEditHistory = QAction(MainWindow)
        self.actionEditHistory.setObjectName("actEditHistory")
        self.menuData.addAction(self.actionEditHistory)
        # 文献统计
        self.actionDbInfo = QAction(MainWindow)
        self.actionDbInfo.setObjectName("actDbInfo")
        self.menuData.addAction(self.actionDbInfo)
        # 工具菜单 menuTools ----------------------------------
        self.menuTools = QMenu(self.menubar)
        self.menuTools.setObjectName("menuTools")
        self.menubar.addAction(self.menuTools.menuAction())
        self.menuTools.setFont(font)
        # 分组管理
        self.menuTools.addSection('分组管理')
        # 新建分组
        self.actionGroupAdd= QAction(MainWindow)
        self.actionGroupAdd.setObjectName("actGroupAdd")
        self.menuTools.addAction(self.actionGroupAdd)
        # 删除分组
        self.actionGroupDelete = QAction(MainWindow)
        self.actionGroupDelete.setObjectName("actGroupDelete")
        self.menuTools.addAction(self.actionGroupDelete)
        # 视图菜单 -----------------------------------------
        self.menuView = QMenu(self.menubar)
        self.menuView.setObjectName("menuView")
        self.menubar.addAction(self.menuView.menuAction())
        self.menuView.setFont(font)
        #
        self.actionSwitchView = QAction(MainWindow)
        self.actionSwitchView.setObjectName("actViewSwitch")
        self.actionSwitchView.setCheckable(True)
        self.menuView.addAction(self.actionSwitchView)
        #
        self.toggleViewToolBar = QAction('隐藏工具栏', MainWindow)
        self.toggleViewToolBar.setCheckable(True)
        self.toggleViewToolBar.triggered.connect(self.toggleToolBar)
        self.menuView.addAction(self.toggleViewToolBar)
        #
        self.toggleViewLeftPanel = QAction('隐藏左边栏', MainWindow)
        self.toggleViewLeftPanel.setCheckable(True)
        self.toggleViewLeftPanel.triggered.connect(self.toggleLeftPanel)
        self.menuView.addAction(self.toggleViewLeftPanel)
        # 帮助菜单 ----------------------------------
        self.menuHelp = QMenu(self.menubar)
        self.menuHelp.setObjectName("menuHelp")
        self.menuHelp.setFont(font)
        self.menubar.addAction(self.menuHelp.menuAction())
        #
        self.actionAbout = QAction(MainWindow)
        self.actionAbout.setObjectName("actAbout")
        self.menuHelp.addAction(self.actionAbout)
        #
        ## 工具栏 ======================================
        self.toolBar.addWidget(CleanSpacer())
        # 工具栏分隔符
        self.toolBar.addSeparator()
        # 导入ris/pubmed文本
        self.toolBar.addAction(self.actionImportRaw)
        self.toolBar.addAction(self.actionImportSpringer)
        self.toolBar.addAction(self.actionImportPubmed)
        # 工具栏分隔符
        # 保存导入
        self.actionSave= QAction(MainWindow)
        self.actionSave.setToolTip('保存已导入记录')
        self.toolBar.addAction(self.actionSave)
        # 附件
        self.toolBar.addSeparator()
        self.actionFileAdd = QAction(MainWindow)
        self.toolBar.addAction(self.actionFileAdd)
        self.actionFileAdd.setToolTip('添加附件')
        # 更新所选记录
        self.actionUpdateItem = QAction(MainWindow)
        self.actionUpdateItem.setToolTip('更新当前记录')
        self.toolBar.addAction(self.actionUpdateItem)
        # 工具栏分隔符 ---------------------------------
        self.toolBar.addSeparator()
        # prev
        self.actionPrevRow = QAction(MainWindow)
        self.toolBar.addAction(self.actionPrevRow)
        # next
        self.actionNextRow = QAction(MainWindow)
        self.toolBar.addAction(self.actionNextRow)
        ## ====================================================
        # 音频播放
        self.toolBar.addSeparator()
        self.actionAudioCurrent = QAction(MainWindow)
        self.toolBar.addAction(self.actionAudioCurrent)
        self.actionAudioStop = QAction(MainWindow)
        self.toolBar.addAction(self.actionAudioStop)
        self.actionAudioPlay = QAction(MainWindow)
        self.toolBar.addAction(self.actionAudioPlay)
        self.actionAudioPrev = QAction(MainWindow)
        self.toolBar.addAction(self.actionAudioPrev)
        self.actionAudioNext= QAction(MainWindow)
        self.toolBar.addAction(self.actionAudioNext)
        self.actionAudioDelete= QAction(MainWindow)
        self.toolBar.addAction(self.actionAudioDelete)
        self.toolBar.addSeparator()
        ## ====================================================
        # 数据分析
        self.actionWordCount = QAction(MainWindow)
        self.toolBar.addAction(self.actionWordCount)
        # 工具栏分隔符
        self.toolBar.addSeparator()
        # 统计信息
        self.toolBar.addAction(self.actionDbInfo)
        self.actionDbInfo.setToolTip('文献统计信息')
        self.toolBar.addSeparator()
        # 阅读笔记
        self.showNoteBook = QAction(MainWindow)
        self.showNoteBook.setToolTip('阅读笔记')
        self.showNoteBook.setIcon(QIcon(ICON_EDIT2))
        self.showNoteBook.triggered.connect(self.showDlgNoteBook)
        self.toolBar.addAction(self.showNoteBook)
        # 记录分页
        self.pageUp= QAction(MainWindow)
        self.pageUp.setToolTip('上一页')
        self.pageUp.setIcon(QIcon(ICON_PAGEUP))
        #self.pageUp.triggered.connect(self.showPrevPage)
        self.toolBar.addAction(self.pageUp)
        self.pageUp.setVisible(False)     ## 条件显示
        ##
        self.pageDown= QAction(MainWindow)
        self.pageDown.setToolTip('下一页')
        self.pageDown.setIcon(QIcon(ICON_PAGEDOWN))
        #self.pageDown.triggered.connect(self.showNextPage)
        self.toolBar.addAction(self.pageDown)
        self.pageDown.setVisible(False)   ## 条件显示
        # 工具栏分隔符 ----------------------------------
        self.toolBar.addSeparator()
        # 切换视图（菜单动作）
        # self.toolBar.addAction(self.actionSwitchView)
        # 大分隔符
        self.toolBar.addWidget(CleanSpacer())
        # 总装 =====================================
        MainWindow.setMenuBar(self.menubar)
        MainWindow.setStatusBar(self.UIs.statusbar)
        MainWindow.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, self.toolBar)
        for wx in self.centralwidget.findChildren(QWidget):
            wx.setFont(font)
        for wx in self.centralwidget.findChildren(QMenu):
            wx.setFont(font)
        self.retranslateUi()
        self.setShortCuts()
        self.setActions()
        self.setIcons()
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        ##
    def retranslateUi(self):
        _translate = QtCore.QCoreApplication.translate
        self.MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        # 主菜单
        self.menuFile.setTitle(_translate("MainWindow", "文件"))
        self.menuData.setTitle(_translate("MainWindow", "数据"))
        self.menuTools.setTitle(_translate("MainWindow", "工具"))
        self.menuView.setTitle(_translate("MainWindow", "视图"))
        self.menuHelp.setTitle(_translate("MainWindow", "帮助"))
        # 文件
        self.actionImportRaw.setText(_translate("MainWindow", "导入-raw..."))
        self.actionImportSpringer.setText(_translate("MainWindow", "导入-springer..."))
        self.actionImportPubmed.setText(_translate("MainWindow", "导入-PubMed查询..."))
        self.actionConfig.setText(_translate("MainWindow", "系统设置..."))
        self.actionExit.setText(_translate("MainWindow", "退出"))
        # 数据
        self.actionDbStats.setText(_translate("MainWindow", "期刊文献统计与清理"))
        self.actionMapISSN2impact.setText(_translate("MainWindow", "导入：issn-影响因子"))
        self.actionMapISSN2journal.setText(_translate("MainWindow", "更新：issn-期刊名"))
        self.actionEditHistory.setText(_translate("MainWindow", "清理查询历史"))
        self.actionDbInfo.setText(_translate("MainWindow", "文献统计"))
        # 工具
        self.actionGroupAdd.setText(_translate("MainWindow", "新建分组"))
        self.actionGroupDelete.setText(_translate("MainWindow", "删除分组"))
        # 视图
        self.actionSwitchView.setText(_translate("MainWindow", "阅读模式"))
        # 数据分析
        self.actionWordCount.setText(_translate("MainWindow", "关键词统计"))
        # 帮助
        self.actionAbout.setText(_translate("MainWindow", "关于..."))
    def setIcons(self):
        self.MainWindow.setWindowIcon(QIcon(ICON_APP))
        self.actionConfig.setIcon(QIcon(ICON_CONFIG))
        self.actionExit.setIcon(QIcon(ICON_APPEXIT))
        self.actionImportRaw.setIcon(QIcon(ICON_FILE_OPEN))
        self.actionImportSpringer.setIcon(QIcon(ICON_SPRINGER))
        self.actionImportPubmed.setIcon(QIcon(ICON_SEARCH_WEB))
        self.actionSwitchView.setIcon(QIcon(ICON_VIEW_FULLSCREEN))
        self.actionDbInfo.setIcon(QIcon(ICON_INFO))
        self.actionAbout.setIcon(QIcon(ICON_FAVORITE))
        self.actionSave.setIcon(QIcon(ICON_SAVE))
        self.actionFileAdd.setIcon(QIcon(ICON_FILE_PDF))
        self.actionUpdateItem.setIcon(QIcon(ICON_UPDATE))
        self.actionPrevRow.setIcon(QIcon(ICON_PREV))
        self.actionNextRow.setIcon(QIcon(ICON_NEXT))
        ## ----------------------
        ## audio
        self.actionAudioCurrent.setIcon(QIcon(ICON_AUDIO_PLAY))
        self.actionAudioStop.setIcon(QIcon(ICON_AUDIO_STOP))
        self.actionAudioPlay.setIcon(QIcon(ICON_MEDIA_PLAY))
        self.actionAudioPrev.setIcon(QIcon(ICON_MEDIA_PREV))
        self.actionAudioNext.setIcon(QIcon(ICON_MEDIA_NEXT))
        self.actionAudioDelete.setIcon(QIcon(ICON_AUDIO_DEL))
        self.actionWordCount.setIcon(QIcon(ICON_WC))
        #
    def setActions(self):
        def toggleView():
            self.UIs.switchView()
            if self.UIs.GlobLPanel.isVisible():
                self.actionSwitchView.setIcon(QIcon(ICON_VIEW_FULLSCREEN))
            else:
                self.actionSwitchView.setIcon(QIcon(ICON_VIEW_RESTORE))
        # 菜单 ================================
        # 文件
        self.actionConfig.triggered.connect(self.UIs.EdConfig)
        self.actionExit.triggered.connect(self.MainWindow.close)
        self.actionImportRaw.triggered.connect(self.UIs.importFromFiles)
        self.actionImportSpringer.triggered.connect(self.UIs.downloadSpringer)
        self.actionImportPubmed.triggered.connect(self.UIs.WebSearchDialog)
        # 视图
        self.actionSwitchView.triggered.connect(toggleView)
        self.actionEditHistory.triggered.connect(self.UIs.EdHistory)
        # 数据
        self.actionDbStats.triggered.connect(statJournals)
        self.actionDbInfo.triggered.connect(self.UIs.showBibInfo)
        # 工具
        self.actionGroupAdd.triggered.connect(self.UIs.ToolsGroupNew)
        self.actionGroupDelete.triggered.connect(self.UIs.ToolsGroupDel)
        # 关于
        self.actionAbout.triggered.connect(self.UIs.about)
        # 工具栏 =================================
        self.actionSave.triggered.connect(self.UIs.saveImported)
        self.actionFileAdd.triggered.connect(self.UIs.GlobFileList.setBibFiles)
        self.actionUpdateItem.triggered.connect(self.UIs.GlobTable.updateSelectedItems)
        self.actionPrevRow.triggered.connect(self.UIs.GlobTable.prevRow)
        self.actionNextRow.triggered.connect(self.UIs.GlobTable.nextRow)
        self.actionWordCount.triggered.connect(self.UIs.showWCdialog)
        ## audio
        self.actionAudioCurrent.triggered.connect(self.UIs.audioPlayCurrent)
        self.actionAudioPlay.triggered.connect(self.UIs.audioPlayAll)
        self.actionAudioStop.triggered.connect(self.UIs.audioStop)
        self.actionAudioPrev.triggered.connect(self.UIs.audioPlayPrev)
        self.actionAudioNext.triggered.connect(self.UIs.audioPlayNext)
        self.actionAudioDelete.triggered.connect(self.UIs.audioDeleteSelected)
        ##
        #
    def setShortCuts(self):
        self.actionImportRaw.setToolTip('从文件导入记录 Ctrl-F')
        self.actionImportRaw.setShortcut('Ctrl+F')
        self.actionImportSpringer.setToolTip('读取Springer文件（csv）并下载文献记录')
        self.actionImportPubmed.setToolTip('PubMed在线查询')
        self.actionExit.setShortcut('Ctrl+X')
        self.toggleViewToolBar.setShortcut('F9')
        self.actionSwitchView.setShortcut('F10')
        self.actionNextRow.setToolTip('下一条记录 Ctrl-J')
        self.actionNextRow.setShortcut('Ctrl+J')
        self.actionPrevRow.setToolTip('上一条记录 Ctrl-K')
        self.actionPrevRow.setShortcut('Ctrl+K')
        self.actionAudioCurrent.setToolTip('朗读当前')
        self.actionAudioPlay.setToolTip('朗读所有 F7')
        self.actionAudioStop.setToolTip('暂停朗读 F8')
        self.actionAudioNext.setToolTip('朗读下一摘要')
        self.actionAudioPrev.setToolTip('朗读上一摘要')
        self.actionAudioDelete.setToolTip('删除当前音频')
        self.actionAudioPlay.setShortcut('F7')
        self.actionAudioStop.setShortcut('F8')
    def showDlgNoteBook(self):
        self.UIs.winNoteBook.show()
    def toggleToolBar(self, chk):
        self.toolBar.setVisible(not chk)
    def toggleLeftPanel(self, chk):
        self.UIs.GlobLPanel.setVisible(not chk)
class XWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        mainWin = APPwindow(self)
        self.setWindowTitle('rgRef - 基于ripgrep的文献管理')
        self.UIs = mainWin.UIs
        # stylesheet
        sfile = os.path.join(DIR_CSS, 'styles.css')
        if os.path.exists(sfile):
            with open(sfile) as f:
                self.setStyleSheet(f.read())
        self.setLocation()
    def setLocation(self):
        uconf = UserConfig()
        x = int(uconf.get('window_x', 200))
        y = int(uconf.get('window_y', 200))
        w = int(uconf.get('window_w', 800))
        h = int(uconf.get('window_h', 600))
        self.setGeometry(x, y, w, h)
        sn = self.screen().geometry()
        dt = {'screen_w': sn.width(),
              'screen_h': sn.height()}
        uconf = UserConfig()
        uconf.update(dt)
        uconf.save()
    def closeEvent(self, e: QCloseEvent) -> None:
        uconf = UserConfig()
        dt = self.UIs.GlobTable.getSettings()
        uconf.update(dt)
        geo = self.geometry()
        dt = {'window_x': geo.x(),
              'window_y': geo.y(),
              'window_w': geo.width(),
              'window_h': geo.height()}
        uconf.update(dt)
        uconf.save()
        reply = QMessageBox.warning(
            self, '退出程序', '是否关闭rgRef文献管理器？',
            QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes)
        if reply == QMessageBox.StandardButton.Yes:
            ## 删除已知临时文件
            opath = os.path.dirname(mktemp())
            os.system(f'rm -rf {opath}/bib*.wav')
            e.accept()
        else:
            e.ignore()
if __name__ == '__main__':
    app = QApplication(sys.argv)
    splash = XSplashScreen()
    splash.setPixmap(QPixmap(os.path.join(DIR_IMG, 'splash.jpg')))
    splash.showMessage('程序加载中，请稍候...', QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.AlignmentFlag.AlignHCenter)
    win = XWindow()
    msn = [x for x in ['rg', 'sdcv', 'sox', 'espeak-ng', 'git-lfs', 'pdfinfo', 'pdftotext']
           if not check_program(x)]
    if msn:
        QMessageBox.warning(win, '警告', '请先安装必要程序：\n' + ", ".join(msn))
        sys.exit(1)
    splash.show()
    win.show()
    sys.exit(app.exec())
