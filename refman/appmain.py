import re, math, time, shutil, os.path, subprocess, markdown
from markdown.extensions.tables import TableExtension
from refman.varsys import *
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QSize, QRegularExpression, QUrl, QTimer
from PyQt5.QtGui import QIcon, QFont, QRegularExpressionValidator, QCursor, QTextCursor, QBrush, QColor
from PyQt5.QtWidgets import (QWidget, QAction, QFrame, QFileDialog, QTableWidget, QAbstractItemView, QMessageBox, QMenu, QLineEdit, QTextEdit,
                             QHBoxLayout, QVBoxLayout, QTextBrowser, QInputDialog, QPushButton, QSpinBox, QFormLayout, QSplitter, QLabel, QStatusBar,
                             QColorDialog, QToolBar, QTreeWidget, QTreeWidgetItem, QTabWidget, QTableWidgetItem, QCheckBox,
                             QComboBox, QSizePolicy, QDialog, QCalendarWidget)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEngineProfile
from PyQt5.QtMultimedia import QMediaPlayer, QMediaPlaylist, QMediaContent
from refman.config import UserConfig, EditorConfig
from refman.functions import (rankColors, PDFinfo, hasAnyKeyword, hasAllKeywords, unlist, inList, listuniq, listinter, listDictSort,
                              readLines, str2wordlist, runCMD)
from refman.widget import CleanSpacer, popwarning, findWidget, CustomTextBrowser
from refman.widget import DlgTextInfo, EditorHistory, SdcvResultDialog
from refman.journal import issn_to_impact_factor, journal_to_issns
from refman.bibtex import auth4reference, PubMedSearch, importFile2bibList, readNativeByKey
from refman.bibtex import BibitemActive, ListActiveBitems, BibitemXView, findAttaches, JournalBlackList
from refman.wcloud import WordCountDialog
from refman.groups import BibGroups, GroupEdit, GroupDelete
from refman.ripgrep import totalbibs, BkeysHasNote, BkeysHasFile
from refman.threads import runXSearch, ThreadSaveBitems, ThreadSpringDownload, ThreadCheckPDFanno, ThreadGetPDFanno, ThreadMakeMP3
from refman.speech import getAudioFolders

class AudioPlayer(QMediaPlayer):
    signalPlayNext = QtCore.pyqtSignal(bool)
    signalMPlaying = QtCore.pyqtSignal(bool)
    signalMPaused = QtCore.pyqtSignal(bool)
    playall = False
    def __init__(self):
        super().__init__()
        self.setObjectName('DefaultAudioPlayer')
        self.PlayList = QMediaPlaylist(self)
        self.bibkey = ''
        self.setPlaylist(self.PlayList)
        self.stateChanged.connect(self.checkStatus)
    def setPlayAll(self, b: bool):
        self.playall = b
    def checkStatus(self):
        if self.state() == QMediaPlayer.State.StoppedState:
            if self.playall and self.PlayList.mediaCount() > 0:
                self.signalPlayNext.emit(True)
        elif self.state() == QMediaPlayer.State.PlayingState:
            self.signalMPlaying.emit(True)
        elif self.state() == QMediaPlayer.State.PausedState:
            self.signalMPaused.emit(True)
    def addMedia(self, localfile: str):
        song = QMediaContent(QtCore.QUrl.fromLocalFile(localfile))
        self.PlayList.addMedia(song)
    def clearList(self):
        self.PlayList.clear()
    def setBibkey(self, bibkey: str=''):
        self.bibkey = bibkey
    def getBibkey(self):
        return self.bibkey
class QHSpliter(QSplitter):
    def __init__(self):
        super().__init__()
        self.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    def sizeHint(self):
        return QSize(1200, 600)
    def minimumSizeHint(self):
        return QSize(200, 400)
class TabPDFandNote(QFrame):
    # DEPRECATED: use TabNoteBook instead
    message = QtCore.pyqtSignal(list)
    def __init__(self):
        super().__init__()
        self.data = ''
        hlayout = QHBoxLayout()
        self.setLayout(hlayout)
        self.setObjectName('NoName') # for filename
        # File panel
        filePanel = QFrame()
        vlayout1 = QVBoxLayout()
        vlayout1.setContentsMargins(0, 0, 0, 0)
        filePanel.setLayout(vlayout1)
        # Notebook panel
        self.NoteBook = ENoteBook()
        self.FileList = QViewerFileList()
        self.FileList.setMinimumHeight(50)
        ##
        vspliter = QSplitter(QtCore.Qt.Orientation.Vertical)
        vspliter.addWidget(self.NoteBook)
        vspliter.addWidget(self.FileList)
        vlayout1.addWidget(vspliter)
        vspliter.setSizes([400, 100])
        vspliter.setFrameShape(QFrame.Shape.Box)
        vspliter.setFrameShadow(QFrame.Shadow.Plain)
        vspliter.setLineWidth(2)
        # main spliter
        self.pdfviewer = QViewerPDF()
        hspliter = QSplitter(QtCore.Qt.Orientation.Horizontal)
        hspliter.addWidget(self.pdfviewer)
        hspliter.addWidget(filePanel)
        hlayout.addWidget(hspliter)
        hspliter.setSizes([400, 100])
class EBrowser(QTextBrowser):
    def sizeHint(self):
        return QSize(800, 100)
    def minimumSizeHint(self):
        return QSize(100, 100)
class EWidget(QWidget):
    def sizeHint(self):
        return QSize(800, 100)
    def minimumSizeHint(self):
        return QSize(100, 100)
class EFrame(QFrame):
    def sizeHint(self):
        return QSize(800, 100)
    def minimumSizeHint(self):
        return QSize(100, 100)
class QViewerCalender(QFrame):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.calendar = QCalendarWidget()
        self.calendar.setMaximumHeight(600)
        self.dateinfo = QFrame()
        self.dateinfo.setMinimumHeight(100)
        layout.addWidget(self.calendar)
        layout.addWidget(self.dateinfo)
    def sizeHint(self):
        return QSize(300, 100)
    def minimumSizeHint(self):
        return QSize(100, 100)
class QSysGroupItem(QTreeWidgetItem):
    def __init__(self, parent):
        super().__init__(parent)
        self.setForeground(0, QBrush(QColor('#A52A2A')))
    #
class QViewerPDF(QWebEngineView):
    """
    PDFjs必须通过使用WEB服务器使用，而且PDF文件不能使用软链接。
    请设置本地web服务
    """
    def __init__(self):
        QWebEngineView.__init__(self)
        self.file = ''
        self.setAcceptDrops(False)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        # 文件另存请求
        QWebEngineProfile.defaultProfile().downloadRequested.connect(self.on_downloadRequested)
        self.pdfjs_viewer = UserConfig().get("pdfviewer", "")
    def sizeHint(self):
        return QSize(800, 900)
    def minimumSizeHint(self):
        return QSize(400, 200)
    def loadFile(self, filename):
        url = QUrl.fromLocalFile(filename).toString()
        url = f'file://{self.pdfjs_viewer}?file={url}'
        self.load(QUrl.fromUserInput(url))
    def on_downloadRequested(self, download):
        path, _ = QFileDialog.getSaveFileName(
            self, "文件另存为...", os.path.basename(self.file), "*.pdf")
        if path:
            download.setPath(path)
            download.accept()
class QViewerBibTable(QTableWidget):
    """
    QTableWidget for bib items.
    """
    rowSelectionChanged = QtCore.pyqtSignal(dict)
    signalDisableTable = QtCore.pyqtSignal(bool)
    markedItemChanged = QtCore.pyqtSignal(bool)
    message = QtCore.pyqtSignal(list)
    def __init__(self):
        super().__init__()
        font = QFont()
        font.setPointSize(UserConfig().get('font_size_table'))
        self.setFont(font)
        self.gCachedBitemList = ListActiveBitems()
        self.gGroupBkeys = {}
        self.currentGroup = 'UNSET'
        self.groupNbibs = 0
        self.dataShow = []      ## 排序/过滤后的数据列表
        self.kwdInput = []      ## 用于查询非分组文献
        self.kwdGroup = []      ## 用于查询非分组文献
        self.kwdFilter = []     ## 用于过滤缓存
        self.filterInField = ""
        self.arrangeList = []   ## 排序标准
        self.filterSearch = ''
        self.filterImpactVal = ''
        self.filterHasNotes = False
        self.filterHasFiles = False
        self.filterHasAbstr = False
        self.ctrlPressed = False
        self.lastBibkey = {}
        self.status = 0
        self.rcolors = None
        self.setDragEnabled(False)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.setAlternatingRowColors(True)
        self.setGridStyle(QtCore.Qt.PenStyle.SolidLine)
        self.setSortingEnabled(False)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.horizontalHeader().setCascadingSectionResizes(False)
        self.horizontalHeader().setSortIndicatorShown(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.headers = ['Rank', 'Bibkey', 'Author', 'Title', 'Journal']
        self.itemSelectionChanged.connect(self.triggerRowChange)
    ## ---------------------
    ## selection
    def selectedRows(self):
        ans = {x.row() for x in self.selectedItems()}
        ans = [x for x in ans]
        ans.sort()
        return ans
    def selectedShow(self):
        sitems = [self.dataShow[i] for i in self.selectedRows()]
        return sitems
    def selectedKeys(self):
        sitems = [self.dataShow[i] for i in self.selectedRows()]
        return [x.get('bibkey') for x in sitems]
    def setLastBibkey(self, n):
        if len(self.dataShow) < 1:
            return False
        ndx = min(n, len(self.dataShow) - 1)
        ndx = max(0, ndx)
        self.lastBibkey.update({self.currentGroup: self.dataShow[ndx].get('bibkey')})
    ## ---------------------
    ## filter
    def klistMatchedIndex(self, kwds:list):
        # NOTE：所有过滤的对象都是dataShow
        if len(self.dataShow) < 1:
            return []
        filterin = self.filterSearch
        if inList(filterin, ['bibkey', 'journal']):
            txt = [x.get(filterin, '') for x in self.dataShow]
        else:
            txt = [x.str4search() for x in self.dataShow]
        ans = {i for i in range(len(txt)) if txt[i] and hasAnyKeyword(txt[i], kwds)}
        return [i for i in ans]
    def filterSearchKeys(self):
        ## 使用左边栏关键词输入
        # NOTE：所有过滤的对象都是dataShow
        filters = self.kwdInput.copy()
        if len(filters) < 1 or inList(self.currentGroup, ['Find free', 'Find sents']):
            return False
        nds = []
        # print(filters)
        for klist in filters:
            ndx = self.klistMatchedIndex(klist)
            nds.append(ndx)
        if len(nds) < 2:
            nds = unlist(nds)
        else:
            nds = listinter(nds)
        self.dataShow = [self.dataShow[i] for i in nds]
    def filterSimpleKeys(self):
        ## 使用右侧顶端关键词输入
        # NOTE：所有过滤的对象都是dataShow
        if len(self.dataShow) < 1 or len(self.kwdFilter) < 1:
            return False
        xdata = self.dataShow.copy()
        filterin = self.filterInField
        if filterin == 'journal':
            self.dataShow = [dd for dd in xdata
                             if hasAnyKeyword(dd.get(filterin, ''), self.kwdFilter, exact=True)]
        elif filterin != '':
            self.dataShow = [dd for dd in xdata
                             if hasAllKeywords(dd.get(filterin, ''), self.kwdFilter)]
        else:
            self.dataShow = []
            hasSentence = xdata[0].get('sentences')
            for dd in xdata:
                if hasSentence:
                    xlst = unlist(dd.get('sentences'))
                    xlst = [x for x in xlst if x]
                else:
                    xlst = [dd.str4search()]
                if len(xlst) < 1:
                    continue
                if hasSentence and len(xlst) > 0:
                    senlist = [x for x in xlst if hasAllKeywords(x, self.kwdFilter)]
                    if len(senlist) > 0:
                        dd.update({'sentences': senlist})
                        self.dataShow.append(dd)
                else:
                    tt = '&'.join(xlst)
                    if hasAllKeywords(tt, self.kwdFilter):
                        self.dataShow.append(dd)
        return True
    def filterByImpact(self):
        ## TODO: 有问题
        if (not re.search(r'^\d+$', self.filterImpactVal)
                and not re.search(r'^\d+\.\d+$', self.filterImpactVal)):
            return False
        ifval = int(self.filterImpactVal)
        assns = issn_to_impact_factor()
        # 影响因子大于ｎ的期刊
        xssns = [k for k,v in assns.items() if eval(f'{v} > {ifval}')]
        xssns = ";".join(xssns)
        # issn筛选
        issns = [x.get('issn', '') for x in self.dataShow]
        issns = [re.sub(" *; *", "|", x.strip()) for x in issns]
        # 有影响因子的记录
        nds1 = {i for i in range(len(self.dataShow))
               if issns[i] != '' and re.search(issns[i], xssns)}
        jrns = [self.dataShow[i].get('journal') for i in nds1]
        nds2 = {i for i in range(len(self.dataShow))
                if inList(self.dataShow[i].get('journal'), jrns)}
        nds = nds1.union(nds2)
        if not self.filterimpactGT:
            nss = {i for i in range(len(self.dataShow))}
            nds = nss.difference(nds)
        self.dataShow = [self.dataShow[i] for i in nds]
    def setRowItemView(self, bib: dict, row: int, font):
        cnames = [s.lower() for s in self.headers]
        ncols = len(cnames)
        # 列宽设置
        if self.status < 1:
            uconf = UserConfig()
            cwidth = [uconf.get(f'table_width_col{i+1}', 60)
                  for i in range(ncols)]
            for i in range(ncols - 1):
                self.setColumnWidth(i, cwidth[i])
        # 数据设置
        for i in range(ncols):
            value = bib.get(cnames[i], '')
            value = str(value)
            xitem = QTableWidgetItem(value)
            xitem.setFont(font)
            rank = int(bib.get('rank', 0))
            rank = max(0, min(9, rank))
            if  self.rcolors and rank > 0:
                xcol = self.rcolors[rank]
                xitem.setBackground(QtGui.QBrush(QtGui.QColor(xcol)))
            self.setItem(row, i, xitem)
    def setTableView(self):
        font = QFont()
        font.setPointSize(UserConfig().get('font_size_table'))
        # NOTE：所有过滤的对象都是dataShow
        self.clear()
        self.rcolors = rankColors()
        if len(self.arrangeList) > 0:
            self.dataShow = listDictSort(self.dataShow, self.arrangeList[0], self.arrangeList[1])
        nrow = min(1000, len(self.dataShow))
        self.dataShow = self.dataShow[0:nrow]
        self.setRowCount(nrow)
        self.setColumnCount(len(self.headers))
        self.setHorizontalHeaderLabels(self.headers)
        for i in range(nrow):
            self.setRowItemView(self.dataShow[i], i, font)
        nshw = len(self.dataShow)
        msn = f'当前分组缓存文献记录 {self.groupNbibs} 条，显示 { nshw} 条'
        self.message.emit([msn, 'normal'])
        if nrow < 1:
            return False
        skey = self.lastBibkey.get(self.currentGroup)
        ndx = [i for i in range(nrow) if self.dataShow[i].get('bibkey') == skey]
        ndx = 0 if len(ndx) < 1 else ndx[0]
        self.selectRow(ndx)
        self.setFocus()
        self.status = 1
    def updateTableView(self):
        if self.currentGroup == 'All references':
            blist = self.gCachedBitemList
        else:
            bkeys = self.gGroupBkeys.get(self.currentGroup, [])
            blist = self.gCachedBitemList.bitems(bkeys)
        self.groupNbibs = len(blist)
        self.dataShow = blist.copy()
        if self.filterHasNotes:
            bkeys = BkeysHasNote()
            self.dataShow = [x for x in self.dataShow if inList(x.get('bibkey'), bkeys)]
        if self.filterHasFiles:
            bkeys = BkeysHasFile()
            self.dataShow = [x for x in self.dataShow if inList(x.get('bibkey'), bkeys)]
        if self.filterHasAbstr:
            self.dataShow = [x for x in self.dataShow if re.search(r'\w', x.get('abstract', ''))]
        self.filterSearchKeys()
        self.filterSimpleKeys()
        self.setTableView()
        if len(self.dataShow) < 1:
            self.signalDisableTable.emit(True)
    def triggerRowChange(self):
        if len(self.dataShow) < 1:
            return False
        if len(self.selectedRows()) != 1:
            return False
        ndx = self.currentRow()
        ndx = 0 if ndx >= self.rowCount() else ndx
        bitem = self.dataShow[ndx]
        self.lastBibkey.update({self.currentGroup: bitem.get('bibkey')})
        ans = self.asTableItem(bitem)
        self.rowSelectionChanged.emit(ans)
    def asTableItem(self, item: dict):
        ans = BibitemActive(item)
        hlkwds = unlist([self.kwdInput, self.kwdFilter, self.kwdGroup])
        hlkwds = [x for x in hlkwds if x != '']
        if hlkwds:
            ans.update({'highlight': hlkwds})
        return ans
    def getSettings(self):
        ans = dict()
        if not self.status:
            return ans
        nc = self.columnCount()
        for i in range(nc):
            kk = f'table_width_col{i + 1}'
            vv = self.columnWidth(i)
            ans.update({kk: vv})
        return ans
    ## ---------------------
    ## edit, update and delete bibitem(s)
    def updateSingleItem(self, bitem: dict):
        self.gCachedBitemList.update([bitem])
        self.updateTableView()
    def updateSelectedItems(self):
        blist = self.selectedShow()
        for bitem in blist:
            bitem.uniform()
        self.gCachedBitemList.update(blist)
        self.updateTableView()
    def saveSelected(self):
        if self.currentGroup != 'Imported':
            return False
        blist = self.selectedShow()
        nsaved = 0
        for bitem in blist:
            xitem = BibitemActive(bitem)
            if xitem.save():
                nsaved += 1
        if nsaved > 0:
            self.message.emit([f'选定的{nsaved}条文献已保存到磁盘', 'ok'])
    def delSelectedItems(self):
        nmax = len(self.dataShow) - 1
        ndx = self.selectedRows()
        nsel = len(ndx)
        if nsel > 1:
            reply = QMessageBox.warning(
                self, '删除确认', f'选中 {nsel} 条文献，是否删除？',
                QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes)
            if reply != QMessageBox.StandardButton.Yes:
                return False
        xkeys = self.selectedKeys()
        snn = len(xkeys)
        if self.currentGroup == 'Imported':
            for k in xkeys:
                self.gCachedBitemList.removeByKey(k)
        else:
            snn = [self.gCachedBitemList.deleteByKey(k) for k in xkeys]
            snn = sum(snn)
            xnn = len(ndx) - snn
            msn = f'删除文献记录 {snn} 条'
            msn = msn if xnn < 1 else f'{msn}，另有 {xnn} 条因含附件无法删除'
            self.message.emit([msn, 'alert'])
        ndx = min(nmax - snn, max(ndx) - 1)
        self.setLastBibkey(ndx)
        self.updateTableView()
        #
    def updateBSents(self):
        blist = self.selectedShow()
        for xitem in blist:
            xitem.updateSentFile(patts=self.kwdInput)
        self.gCachedBitemList.update(blist)
        self.triggerRowChange()
    ## ---------------------
    ## black list journal
    def addBlackList(self):
        jblist = JournalBlackList()
        xitems = self.selectedShow()
        for xit in xitems:
            jblist.append(xit)
    def delBlackList(self):
        jblist = JournalBlackList()
        xitems = self.selectedShow()
        for xit in xitems:
            jblist.remove(xit)
    ## ---------------------
    ## mark and rank
    def markSelectedItems(self):
        if self.currentGroup == 'Marked':
            return False
        self.setLastBibkey(min(self.selectedRows()))
        for bitem in self.selectedShow():
            bitem.marked()
        n = len(self.selectedShow())
        self.message.emit([f'Marked {n} items.', 'normal'])
        self.markedItemChanged.emit(True)
    def unmarkSelectedItems(self):
        if self.currentGroup != 'Marked':
            return False
        for bitem in self.selectedShow():
            bitem.unmarked()
        self.setLastBibkey(min(self.selectedRows()) - 1)
        self.updateTableView()
        self.markedItemChanged.emit(True)
    def setRank(self, n, ndx=None):
        if not ndx:
            bkeys = self.selectedKeys()
        else:
            bkeys = [self.dataShow[ndx].get('bibkey')]
        for item in self.gCachedBitemList:
            if inList(item.get('bibkey'), bkeys):
                item.update({'rank': n})
        self.updateTableView()
    def decRank(self):
        for i in self.selectedRows():
            rank = int(self.dataShow[i].get('rank', 0))
            if rank < 1:
                continue
            rank -= 1
            self.setRank(rank, i)
    def incRank(self):
        for i in self.selectedRows():
            rank = int(self.dataShow[i].get('rank', 0))
            if rank > 8:
                continue
            rank += 1
            self.setRank(rank, i)
    def zeroRank(self):
        self.setRank(0)
    ## ---------------------
    ## mark and rank
    def showTextInfo(self, title, msn):
        xdlg = DlgTextInfo(self, title, msn)
        uconf = UserConfig()
        sw = uconf.get('screen_w')/3
        sh = uconf.get('screen_h')/2
        sw = int(max(sw, 800))
        sh = int(max(sh, 600))
        xdlg.setMinimumSize(sw, sh)
        xdlg.show()
        #
    def exportDocx(self):
        ndx = self.selectedRows()
        items = [self.dataShow[n] for n in ndx]
        msn = ''
        for bitem in items:
            bibkey = bitem.get('bibkey', '')
            author = bitem.get('author', '')
            rtitle = bitem.get('title', '').strip('. ')
            journal = bitem.get('journal', '')
            year = bitem.get('year', '')
            volume = bitem.get('volume', '')
            doi = bitem.get('doi', '')
            if volume != '':
                volume = f'({volume})'
            if doi != '':
                doi = f'. DOI: <a href="http://dx.doi.org/{doi}">{doi}</a>'
            pages = bitem.get('pages', '')
            auths = auth4reference(author)
            reference = f'[{bibkey}]：{auths}. {rtitle}. <i>{journal}</i>, {year}{volume}: {pages}{doi}'
            msn = f'{msn}<p>{reference}</p>'
        self.showTextInfo('格式化文献列表', msn)
    def exportBibtex(self):
        fkeys = ['bibkey', 'journal', 'title', 'author', 'year', 'pages', 'abstract']
        ndx = self.selectedRows()
        blist = [self.dataShow[n] for n in ndx]
        contents = []
        for xitem in blist:
            ans = ['@Article{' + xitem.get("bibkey") + ',']
            xct = [k + ' = {' + xitem.get(k, '') + '},' for k in fkeys]
            ans.extend(xct)
            ans.append('}\n')
            contents.extend(ans)
        ofile, _ = QFileDialog.getSaveFileName(
            self, "导出为文件", "")
        if ofile:
            with open(ofile, 'w') as f:
                f.write("\n".join(contents))
    def showBibDetails(self):
        n = self.currentRow()
        dt = self.dataShow[n]
        msn = [f'<li><span style="font-weight:bold; color: #4682b4;">{k}:</span> {v}</li>'
               for k,v in dt.items()
               if k not in ['abstract', 'institution']]
        msn = "".join(msn)
        self.showTextInfo('文献详情', f'<ul style="list-style-type: circle;">{msn}</ul>')
    def exportPDFs(self):
        ndx = self.selectedRows()
        if len(ndx) < 0:
            return False
        uconf = UserConfig()
        opath = uconf.get('dir_copyto')
        dir_selected = QFileDialog.getExistingDirectory(
            self,
            '选择目标位置',
            opath)
        if not dir_selected:
            return False
        files = unlist([findAttaches(self.dataShow[i]) for i in ndx])
        ncopied = 0
        for src in files:
            tfile = f'{dir_selected}/{os.path.basename(src)}'
            if os.path.exists(tfile):
                continue
            try:
                shutil.copyfile(src, tfile)
            except:
                pass
            finally:
                ncopied += 1
        uconf.update({'dir_copyto': dir_selected})
        uconf.save()
        popwarning(self, '复制了' + str(ncopied) + f'个文件到目录{dir_selected}.')
    def goToFirstRow(self):
        nrow = self.rowCount()
        if nrow < 1:
            return False
        if self.currentRow() == 0:
            return False
        self.clearSelection()
        self.selectRow(0)
    def goToLastRow(self):
        nrow = self.rowCount()
        if nrow < 1:
            return False
        if self.currentRow() == nrow:
            return False
        self.clearSelection()
        self.selectRow(nrow - 1)
    def nextRow(self):
        nrow = self.rowCount()
        rndx = self.currentRow()
        if rndx < nrow - 1:
            xndx = rndx + 1
        else:
            xndx = 0
        self.clearSelection()
        self.selectRow(xndx)
    def prevRow(self):
        nrow = self.rowCount()
        rndx = self.currentRow()
        if rndx > 0:
            xndx = rndx - 1
        else:
            xndx = nrow - 1
        self.clearSelection()
        self.selectRow(xndx)
    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        if e.key() == QtCore.Qt.Key.Key_Control:
            self.ctrlPressed = True
    def keyReleaseEvent(self, e: QtGui.QKeyEvent) -> None:
        if not self.hasFocus():
            return None
        if e.key() == QtCore.Qt.Key.Key_Control:
            self.ctrlPressed = False
            return None
        if e.key() == QtCore.Qt.Key.Key_Delete:
            self.delSelectedItems()
        elif 47 < e.key() < 58:
            self.setRank(int(e.key()) - 48)
        elif e.key() == QtCore.Qt.Key.Key_Plus or e.key() == QtCore.Qt.Key.Key_Equal:
            self.incRank()
        elif e.key() == QtCore.Qt.Key.Key_Minus:
            self.decRank()
        elif e.key() == QtCore.Qt.Key.Key_0:
            self.zeroRank()
        elif e.key() == QtCore.Qt.Key.Key_A:
            self.selectAll()
        elif e.key() == QtCore.Qt.Key.Key_Down:
            self.nextRow()
        elif e.key() == QtCore.Qt.Key.Key_Up:
            self.prevRow()
        elif not self.ctrlPressed and e.key() == QtCore.Qt.Key.Key_J:
            self.nextRow()
        elif not self.ctrlPressed and e.key() == QtCore.Qt.Key.Key_K:
            self.prevRow()
        elif e.key() == QtCore.Qt.Key.Key_H:
            self.goToFirstRow()
        elif e.key() == QtCore.Qt.Key.Key_Home:
            self.goToFirstRow()
        elif e.key() == QtCore.Qt.Key.Key_L:
            self.goToLastRow()
        elif e.key() == QtCore.Qt.Key.Key_End:
            self.goToLastRow()
        elif e.key() == QtCore.Qt.Key.Key_U:
            self.unmarkSelectedItems()
        elif e.key() == QtCore.Qt.Key.Key_M:
            self.markSelectedItems()
        e.setAccepted(True)
    def contextMenuEvent(self, evt):
        # TODO: 键盘快捷键
        menu = QMenu()
        menu.setObjectName('PopMenuBibList')
        if self.currentGroup == 'Imported':
            actSelectedSave = QAction(u'保存选定文献', self)
            actSelectedSave.setIcon(QIcon(ICON_SAVE))
            menu.addAction(actSelectedSave)
            actSelectedSave.triggered.connect(self.saveSelected)
        #
        menu.addSection('导出')
        actExportBibtex= QAction(u'导出为bibtex...', self)
        actExportBibtex.setIcon(QIcon(ICON_FILE_TEX))
        menu.addAction(actExportBibtex)
        actExportBibtex.triggered.connect(self.exportBibtex)
        #
        actExportDocx = QAction(u'导出为docx...', self)
        actExportDocx.setIcon(QIcon(ICON_FILE_WORD))
        menu.addAction(actExportDocx)
        actExportDocx.triggered.connect(self.exportDocx)
        #
        actExportPDFs = QAction(u'导出附件...', self)
        actExportPDFs.setIcon(QIcon(ICON_FILE_PDF))
        menu.addAction(actExportPDFs)
        actExportPDFs.triggered.connect(self.exportPDFs)
        # 期刊黑名单
        menu.addSection('期刊黑名单')
        actAddBlackList = QAction(u'添加', self)
        menu.addAction(actAddBlackList)
        actAddBlackList.triggered.connect(self.addBlackList)
        actDelBlackList = QAction(u'移除', self)
        menu.addAction(actDelBlackList)
        actDelBlackList.triggered.connect(self.delBlackList)
        #
        menu.addSection('评分')
        actRankInc = QAction(u'评分增加 (+)', self)
        actRankDec = QAction(u'评分减小 (-)', self)
        actRank0 = QAction(u'评分清零 (0)', self)
        menu.addAction(actRankInc)
        menu.addAction(actRankDec)
        menu.addAction(actRank0)
        actRankInc.triggered.connect(self.incRank)
        actRankDec.triggered.connect(self.decRank)
        actRank0.triggered.connect(self.zeroRank)
        #
        menu.addSection('标记')
        actMark = QAction(u'标记文献 (m)', self)
        actUnMark = QAction(u'取消标记 (u)', self)
        menu.addAction(actMark)
        menu.addAction(actUnMark)
        actMark.triggered.connect(self.markSelectedItems)
        actUnMark.triggered.connect(self.unmarkSelectedItems)
        #
        menu.addSection('信息')
        actViewInfo = QAction(u'显示文献详情', self)
        menu.addAction(actViewInfo)
        actViewInfo.triggered.connect(self.showBibDetails)
        actUpdateSToken= QAction(u'更新查询文本...', self)
        menu.addAction(actUpdateSToken)
        actUpdateSToken.triggered.connect(self.updateBSents)
        #
        menu.addSeparator()
        actDelete = QAction(u'删除记录 (Delete)', self)
        actDelete.setIcon(QIcon(ICON_DELETE))
        menu.addAction(actDelete)
        actDelete.triggered.connect(self.delSelectedItems)
        #
        menu.exec(QCursor.pos())
class QInputKeywords(QLineEdit):
    def __init__(self, name):
        super().__init__()
        self.setObjectName(name)
        xreg = QRegularExpression(r'[^\|\(\)\*\{\}]*')
        validator = QRegularExpressionValidator(xreg)
        self.setValidator(validator)
        self.history = None
        self.currIndex = 0
        self.loadHistory()
    def loadHistory(self):
        xdir = UserConfig().conf_dir
        hfile = f'{xdir}/history_keywords'
        self.history = ['']
        if os.path.exists(hfile):
            self.history.extend(readLines(hfile))
    def keyReleaseEvent(self, e: QtGui.QKeyEvent):
        if e.key() == QtCore.Qt.Key.Key_Up or e.key() == QtCore.Qt.Key.Key_Down:
            nn = len(self.history) - 1
            if nn > 0:
                n = self.currIndex
                n = n-1 if e.key() == QtCore.Qt.Key.Key_Up else n + 1
                if n < 0:
                    n = nn
                elif n > nn:
                    n = 0
                self.setText(self.history[n])
                self.currIndex = n
        elif e.key() == QtCore.Qt.Key.Key_Escape:
            self.setText('')
            return super().keyReleaseEvent(e)
        #
class QViewerFileItem(QPushButton):
    signalPDFopened = QtCore.pyqtSignal(bool)
    signalDeleted = QtCore.pyqtSignal(bool)
    def __init__(self, fp: str, menu: bool=True, bitem: BibitemActive=None):
        super().__init__()
        self.file = fp
        self.hasMenu = menu
        self.bitem = bitem
        fname = os.path.basename(fp)
        self.setStyleSheet('border: none; text-align: left; padding: 5px 10px;')
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setText(fname)
        font = QFont()
        font.setPointSize(UserConfig().get('font_size_basic'))
        self.setFont(font)
        if self.hasMenu:
            self.clicked.connect(self.preview)
        else:
            self.clicked.connect(self.open)
    def preview(self):
        xtg = findWidget(self, QViewerFileList)
        xtg.pdfView(self.file)
    def open(self):
        self.signalPDFopened.emit(True)
        os.system(f'open {self.file}')
    def openWithFoxit(self):
        self.signalPDFopened.emit(True)
        os.system(f'/usr/bin/FoxitReader {self.file}')
    def openWithOkular(self):
        self.signalPDFopened.emit(True)
        os.system(f'/usr/bin/okular {self.file}')
    def copyto(self):
        uconf = UserConfig()
        opath = uconf.get('dir_copyto')
        dir_selected = QFileDialog.getExistingDirectory(
            self,
            '选择目标位置',
            opath)
        if dir_selected:
            try:
                tfile = f'{dir_selected}/{os.path.basename(self.file)}'
                shutil.copyfile(self.file, tfile)
            except:
                QMessageBox.warning(self, '错误', '文件另存失败，请重试！')
            finally:
                uconf.update({'dir_copyto': dir_selected})
                uconf.save()
    def delete(self):
        reply = QMessageBox.warning(
            self, '文件删除警告',
            f'是否删除文件：\n{self.file}',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return False
        os.remove(self.file)
        if os.path.exists(self.file):
            popwarning(self, '文件删除失败，请重试！')
        else:
            self.bitem.updateSentFile()
            self.signalDeleted.emit(True)
            findWidget(self, QViewerBibTable).triggerRowChange()
    def rename(self):
        dname = os.path.dirname(self.file)
        fname = os.path.basename(self.file)
        xname, preceed = QInputDialog.getText(
            self, '文件更名', f'原文件名：\n{fname}\n请输入新文件名：',
            text=fname)
        if not preceed:
            return False
        if not re.match(r'^\d{4}-\w+', xname):
            popwarning(self, '文件名不符合规则，请重试！', '错误警告')
            return False

        xfile = os.path.join(dname, xname)
        if os.path.exists(xfile):
            popwarning(self, '同名文件已存在，请设置其他文件名！', '错误警告')
            return False
        os.rename(self.file, xfile)
        if os.path.exists(xfile):
            findWidget(self, QViewerBibTable).triggerRowChange()
    def showInfo(self):
        msn = '无法检测该文件的doi信息'
        dois = []
        _, ext = os.path.splitext(self.file)
        if ext.lower() == '.pdf':
            xinfo = PDFinfo(self.file)
            dois = [x for x in xinfo.dois]
            dois.sort()
        if len(dois) > 0:
            msn = '\n'.join(dois)
        QMessageBox.information(
            self,
            os.path.basename(self.file),
            msn)
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        #
        actInfo= QAction(u'文件信息', self)
        actInfo.setIcon(QIcon(ICON_INFO))
        menu.addAction(actInfo)
        actInfo.triggered.connect(self.showInfo)
        #
        menu.addSeparator()
        actOpen = QAction(u'使用默认程序打开', self)
        actOpen.setIcon(QIcon(ICON_FILE_OPEN))
        menu.addAction(actOpen)
        actOpen.triggered.connect(self.open)
        #
        actOpenWithFoxit = QAction(u'使用Foxit打开', self)
        actOpenWithFoxit.setIcon(QIcon(ICON_FILE_OPEN))
        menu.addAction(actOpenWithFoxit)
        actOpenWithFoxit.triggered.connect(self.openWithFoxit)
        #
        actOpenWithOkular = QAction(u'使用Okular打开', self)
        actOpenWithOkular.setIcon(QIcon(ICON_FILE_OPEN))
        menu.addAction(actOpenWithOkular)
        actOpenWithOkular.triggered.connect(self.openWithOkular)
        #
        actCopyto = QAction(u'拷贝...', self)
        actCopyto.setIcon(QIcon(ICON_SAVEAS))
        menu.addAction(actCopyto)
        actCopyto.triggered.connect(self.copyto)
        #
        actRename= QAction(u'重命名', self)
        actRename.setIcon(QIcon(ICON_RENAME))
        menu.addAction(actRename)
        actRename.triggered.connect(self.rename)
        #
        menu.addSeparator()
        actDelete = QAction(u'删除', self)
        actDelete.setIcon(QIcon(ICON_DELETE))
        menu.addAction(actDelete)
        actDelete.triggered.connect(self.delete)
        #
        menu.exec(QCursor.pos())
class QViewerFileList(QWidget):
    signalChanged = QtCore.pyqtSignal(bool)
    def __init__(self, menu: bool=True):
        super().__init__()
        self.bitem = None
        self.hasMenu = menu
        self.layout = QVBoxLayout(self)
        self.setAcceptDrops(True)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
    def clearlist(self):
        for x in self.findChildren(QWidget):
            self.layout.removeWidget(x)
            x.deleteLater()  ## NOTE：important!!
    def setLists(self):
        self.clearlist()
        files = self.bitem.files()
        if not files:
            return False
        files = [x for x in files]
        files.sort()
        for f in files:
            wx = QViewerFileItem(f, self.hasMenu, self.bitem)
            wx.signalDeleted.connect(self.signalChanged.emit)
            self.layout.addWidget(wx)
    def setFiles(self, xfiles):
        bibkey = self.bitem.bibkey()
        efiles = self.bitem.files()
        duser = UserConfig().get('dir_user')
        dpdf = os.path.join(duser, 'pdf')
        fn = len(efiles)
        for fsource in xfiles:
            _, ext = os.path.splitext(fsource)
            ext = ext.lower()
            fn += 1
            fpdf = f'{bibkey}-s{fn}{ext}'
            fpdf = os.path.join(dpdf, fpdf)
            ## move file
            shutil.move(fsource, fpdf)
        self.bitem.updateSentFile()
        self.signalChanged.emit(True)
        wx1 = findWidget(self, QViewerBibTable)
        if wx1:
            wx1.triggerRowChange()
    def setBitem(self, bitem: dict):
        self.bitem = BibitemActive(bitem)
        self.setLists()
    def setBibFiles(self):
        uconf = UserConfig()
        opath = uconf.get('dir_import')
        xfiles, _ = QFileDialog.getOpenFileNames(
            self, '选择/设置文献附件',
            opath, 'pdf(*.pdf)')
        nf = len(xfiles)
        if nf < 1:
            return False
        # update import directory
        opath = os.path.dirname(xfiles[0])
        uconf.update({'dir_import': opath})
        uconf.save()
        self.setFiles(xfiles)
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    def dropEvent(self, event):
        skey = self.bitem.get('bibkey')
        if skey == '':
            return False
        xfiles = [u.toLocalFile() for u in event.mimeData().urls()]
        xfiles = [x for x in xfiles if os.path.isfile(x)]
        if len(xfiles) < 1:
            return False
        self.setFiles(xfiles)
    def pdfView(self, fp=None):
        if not fp:
            files = [x for x in self.bitem.get('files', [])]
        else:
            files = [fp]
        if len(files) > 0:
            file = files[0]
        else:
            file = os.path.join(DIR_DOC, '404.pdf')
        # check current file
        viewer = findWidget(self, QViewerPDF)
        if viewer.file == file:
            return False
        viewer.file = file
        viewer.loadFile(file)
    def sizeHint(self):
        return QSize(100, 200)
    def minimumSizeHint(self):
        return QSize(100, 100)
class QEditorMemo(QTextEdit):
    def __int__(self):
        super().__init__()
        self.setAcceptDrops(False)
        font = QFont()
        font.setPointSize(UserConfig().get('font_size_basic'))
        self.setFont(font)
    def sizeHint(self):
        return QSize(100, 800)
    def minimumSizeHint(self):
        return QSize(100, 200)
class ENoteBook(EWidget):
    signalForceExPDFanno = QtCore.pyqtSignal(bool)
    def __init__(self):
        super().__init__()
        xlayout = QVBoxLayout()
        self.setLayout(xlayout)
        self.setContentsMargins(0, 0, 0, 0)
        xlayout.setContentsMargins(0, 0, 0, 0)
        ##
        toolbar = QToolBar(self)
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setContentsMargins(50, 1, 50, 1)
        toolbar.setStyleSheet("background-color: #eee;")
        ## Edit mode
        self.EdtNotes = QTextEdit()
        self.EdtNotes.setObjectName('EdtNotes')
        self.EdtNotes.setPlaceholderText("无文献笔记，可在此编辑/粘贴")
        self.EdtNotes.textChanged.connect(self.auto_save)
        ## View mode
        self.ViewNotes = QWebEngineView()
        ##
        xlayout.addWidget(toolbar)
        xlayout.addWidget(self.EdtNotes)
        xlayout.addWidget(self.ViewNotes)
        ## toolbar actions --------------
        toolbar.addSeparator()
        self.btn_edit = QAction(QIcon(ICON_EDIT), "编辑")
        self.btn_view = QAction(QIcon(ICON_VIEWHTML), "查看")
        self.btn_edit.triggered.connect(self.showEdit)
        self.btn_view.triggered.connect(self.showView)
        toolbar.addAction(self.btn_edit)
        toolbar.addAction(self.btn_view)
        toolbar.addSeparator()
        #
        toolbar.addWidget(CleanSpacer())
        self.btn_pdf_redo = QAction(QIcon(ICON_FILE_PDF), '重新提取pdf注释')
        self.btn_pdf_redo.triggered.connect(self.emitForceUpdate)
        toolbar.addAction(self.btn_pdf_redo)
        #
        ## init folder -----------------------
        duser = UserConfig().get('dir_user')
        dnote = os.path.join(duser, 'notes')
        if not os.path.exists(dnote):
            os.system(f'mkdir -p "{dnote}"')
        self.styleCSS = ""
        self.last_content = ""
        self.loading = True
        self.md_file = "NoName.md"
        ##
    def emitForceUpdate(self):
        self.signalForceExPDFanno.emit(True)
    def setData(self, data: dict):
        self.loading = True
        bkey = data.get('bibkey', 'NoName')
        duser = UserConfig().get('dir_user')
        dnote = os.path.join(duser, 'notes')
        filepath = os.path.join(dnote, bkey)
        self.md_file = f'{filepath}.md'
        html_file = f'{filepath}.html'
        content = ""
        if os.path.exists(html_file):
            with open(html_file, 'r', encoding='utf-8') as f:
                html = f.read()
                self.ViewNotes.setHtml(html)
                self.EdtNotes.setHtml(html)
                content = self.EdtNotes.toMarkdown()
            os.unlink(html_file)
        elif os.path.exists(self.md_file):
            with open(self.md_file, 'r', encoding='utf-8') as f:
                content = f.read()
        ##
        self.last_content = content
        self.EdtNotes.setPlainText(content)
        self.setView(content)
        if content.strip() == "":
            self.showEdit()
        else:
            self.showView()
        self.loading = False
    def reload(self):
        self.loading = True
        content = ""
        if os.path.exists(self.md_file):
            with open(self.md_file, 'r', encoding='utf-8') as f:
                content = f.read()
        self.EdtNotes.setPlainText(content)
        self.setView(content)
        self.last_content = content
        self.loading = False
    def showEdit(self):
        self.btn_edit.setDisabled(True)
        self.btn_view.setDisabled(False)
        self.EdtNotes.show()
        self.ViewNotes.hide()
    def showView(self):
        self.btn_edit.setDisabled(False)
        self.btn_view.setDisabled(True)
        self.EdtNotes.hide()
        content = self.EdtNotes.toPlainText()
        if self.last_content != content:
            self.setView(content)
        self.ViewNotes.show()
    def setView(self, content):
        if self.styleCSS == "":
            style_file = os.path.join(DIR_CSS, 'notebook.css')
            if os.path.exists(style_file):
                with open(style_file, 'r', encoding='utf-8') as f:
                    self.styleCSS = f.read()
        # 渲染Markdown为HTML
        html = markdown.markdown(content, extensions=[TableExtension()])
        html = f"""
            <html>
            <head>
            <style>
            {self.styleCSS}
            </style>
            </head>
            <body>
            {html}
            </body>
            </html>
        """
        self.ViewNotes.setHtml(html)
        ##
    def auto_save(self):
        if self.loading or self.md_file.endswith("NoName.md"):
            return False
        content = self.EdtNotes.toPlainText()
        # 检查内容是否有变化
        if content != self.last_content:
            if content.strip():
                # 有内容则保存
                with open(self.md_file, 'w', encoding='utf-8') as f:
                    f.write(content)
            else:
                # 无内容则删除文件
                if os.path.exists(self.md_file):
                    os.remove(self.md_file)
            self.setView(content)
            self.last_content = content
class DNoteBook(QDialog):
    showed = QtCore.pyqtSignal(bool)
    def __init__(self):
        super().__init__()
        self.setWindowTitle('文献阅读笔记')
        self.setWindowIcon(QIcon(ICON_APP))
        self.editor = ENoteBook()
        layout = QHBoxLayout(self)
        layout.addWidget(self.editor)
        self.setContentsMargins(0,0,0,0)
        layout.setContentsMargins(0,0,0,0)
        uconf = UserConfig()
        ww = math.ceil(float(uconf.get('window_w', 800)) / 2)
        hh = math.ceil(float(uconf.get('window_h', 600)) / 2)
        self.resize(ww, hh)
        font = QFont()
        font.setPointSize(UserConfig().get('font_size_basic'))
        self.setFont(font)
        #
    def setData(self, bitem):
        wtitle = bitem.get('bibkey') + ': ' + bitem.get('title')
        self.setWindowTitle(wtitle)
        self.editor.setData(bitem)
    def showMSN(self, msn: list):
        QMessageBox.information(self, '文献笔记', msn[0])
    def showEvent(self, a0):
        self.editor.reload()
        self.showed.emit(True)
    def closeEvent(self, a0):
        self.showed.emit(False)
class QReaderWidget(EWidget):
    play = QtCore.pyqtSignal(str)
    def __init__(self):
        super().__init__()
        xlayout = QVBoxLayout()
        self.setLayout(xlayout)
        self.setContentsMargins(0, 0, 0, 0)
        xlayout.setContentsMargins(0, 0, 0, 0)
        ##
        toolbar = QToolBar(self)
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setContentsMargins(0, 0, 50, 0)
        self.RNotes = QTextEdit()
        self.RNotes.setObjectName('RNotes')
        self.RNotes.setPlaceholderText('在此输入/粘贴需朗读的文本')
        xlayout.addWidget(toolbar)
        xlayout.addWidget(self.RNotes)
        ## --------------
        self.CNread = QAction(self)
        self.CNread.setToolTip('中文朗读')
        self.CNread.setIcon(QIcon(ICON_REFRESH))
        self.CNread.triggered.connect(self.PlayCN)
        self.ENread = QAction(self)
        self.ENread.setToolTip('英文朗读')
        self.ENread.setIcon(QIcon(ICON_REFRESH))
        self.ENread.triggered.connect(self.PlayEN)
        self.BtnPause = QAction(self)
        self.BtnPause.setToolTip('暂停')
        self.BtnPause.setIcon(QIcon(ICON_AUDIO_STOP))
        self.BtnPause.triggered.connect(self.Pause)
        toolbar.addAction(self.ENread)
        toolbar.addAction(self.CNread)
        toolbar.addAction(self.BtnPause)
        ##
    def PlayCN(self):
        self.play.emit('cn')
    def PlayEN(self):
        self.play.emit('en')
    def Pause(self):
        self.play.emit('pause')
class QDlgReader(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('文本朗读')
        self.setWindowIcon(QIcon(ICON_APP))
        self.reader = QReaderWidget()
        layout = QHBoxLayout(self)
        layout.addWidget(self.reader)
        self.setContentsMargins(0,0,0,0)
        layout.setContentsMargins(0,0,0,0)
        uconf = UserConfig()
        ww = math.ceil(float(uconf.get('window_w', 800)) / 2)
        hh = math.ceil(float(uconf.get('window_h', 600)) / 2)
        self.resize(ww, hh)
class QViewerNotes(QWidget):
    data = dict()
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout()
        self.setLayout(layout)
        self.setContentsMargins(0,0,0,0)
        layout.setContentsMargins(0,0,0,0)
        spliter = QSplitter(QtCore.Qt.Orientation.Horizontal)
        layout.addWidget(spliter)
        self.ViewPDFanno = CustomTextBrowser()
        self.ManualNotes = ENoteBook()
        spliter.addWidget(self.ManualNotes)
        spliter.addWidget(self.ViewPDFanno)
        ## NOTE: 添加控件后方可设置spliter延展因子
        spliter.setStretchFactor(0, 3)
        spliter.setStretchFactor(1, 1)
        self.ThreadNotes = None
        self.ManualNotes.signalForceExPDFanno.connect(self.getPDFannos)
    def getPDFannos(self, force: bool=False):
        if force:
            reply = QMessageBox.warning(self, '请确认',
                f'是否重新提取PDF注释内容？',
                QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes)
            if reply != QMessageBox.StandardButton.Yes:
                return False
            else:
                self.setPDFannos([])
        while self.ThreadNotes and self.ThreadNotes.isRunning():
            time.sleep(0.1)
        if self.ThreadNotes and self.ThreadNotes.isFinished():
            self.ThreadNotes.deleteLater()
            time.sleep(0.1)
        self.ThreadNotes = ThreadGetPDFanno(self.data, force)
        self.ThreadNotes.start()
        self.ThreadNotes.ready.connect(self.setPDFannos)
        #
    def setEdtData(self, data: BibitemActive):
        self.data = data
        if not self.isVisible():
            return False
        self.ManualNotes.setData(self.data)
        self.getPDFannos()
    def reloadData(self):
        self.setEdtData(self.data)
    def setPDFannos(self, alist):
        self.ViewPDFanno.setMarkdown('\n'.join(alist))
class TabAbstractViewer(CustomTextBrowser):
    def __init__(self):
        super().__init__()
        self.setStyleSheet('padding: 20px 10px 20px 10px; margin: 0;')
        self.setOpenLinks(True)
        self.setAcceptDrops(True)
        self.setAcceptDrops(True)
        self.setOpenExternalLinks(True)
        self.bibitem = None
        self.dict_issn2if = {}
        self.dict_jr2issn = {}
        self.currentGroup = ''
        self.dict_issn2if.update(issn_to_impact_factor())
        self.dict_jr2issn.update(journal_to_issns())
    def updateData(self):
        bitem = readNativeByKey(self.bibitem.get('bibkey'))
        self.setData(bitem)
    def setImpact(self):
        # if not self.bibitem.get('journal'):
        #     print(self.bibitem)
        issn = self.bibitem.get('issn')
        if issn:
            issn = re.split(r' *; *', issn)
        else:
            journal = self.bibitem.get('journal').lower()
            issn = self.dict_jr2issn.get(journal, [])
        ans = [self.dict_issn2if.get(x.lower()) for x in issn]
        ans = [x for x in ans if x]
        if len(ans) > 0:
            ans = ans[0]
        else:
            ans = 0
        self.bibitem.update({'impact': ans})
    def setData(self, bitem):
        if len(bitem) < 1:
            return False
        self.bibitem = BibitemXView(bitem, xsent=self.currentGroup == 'Find sents')
        self.setImpact()
        html = self.bibitem.abstractHtml()
        self.setHtml(html)
    def dragEnterEvent(self, event):
        # NOTE: dropEvent处理前，必须设置此事件！
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    def dropEvent(self, event):
        findWidget(self, QViewerFileList).dropEvent(event)
    def sizeHint(self):
        return QSize(1000, 200)
    def minimumSizeHint(self):
        return QSize(600, 100)
class TabBitemEditor(QFrame):
    signalEditorSaved = QtCore.pyqtSignal(dict)
    def __init__(self):
        super().__init__()
        layoutEditor = QFormLayout()
        layoutEditor.setContentsMargins(0, 10, 0, 0)
        layoutEditor.setFormAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        layoutEditor.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.setLayout(layoutEditor)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        layoutEdtBtn = QHBoxLayout()
        self.btnClear = QPushButton('清空')
        self.btnSave = QPushButton('更新')
        self.btnNew = QPushButton('新建')
        layoutEdtBtn.addWidget(self.btnClear)
        layoutEdtBtn.addWidget(self.btnSave)
        layoutEdtBtn.addWidget(self.btnNew)
        layoutEditor.addRow('', layoutEdtBtn)
        # title
        edx = QTextEdit()
        edx.setFixedHeight(80)
        edx.setObjectName('title')
        layoutEditor.addRow('题目:', edx)
        # journal
        layoutJournal = QHBoxLayout()
        jlabel = QLabel('期刊：')
        jlabel.setFixedWidth(80)
        self.issn = QLabel()
        self.issn.setFixedWidth(400)
        self.issn.setStyleSheet('margin-left: 5px; color: red;')
        edx = QLineEdit()
        edx.setObjectName('journal')
        layoutJournal.addWidget(self.issn)
        layoutJournal.addWidget(jlabel)
        layoutJournal.addWidget(edx)
        layoutEditor.addRow('ISSN：', layoutJournal)
        # main fields
        fields = ['year', 'volume', 'issue', 'pages']
        layoutEdtYMD = QHBoxLayout()
        for f in fields:
            edx = QLineEdit()
            edx.setObjectName(f)
            edx.setToolTip(f)
            layoutEdtYMD.addWidget(edx)
        layoutEditor.addRow('年/卷/期/页:', layoutEdtYMD)
        # doi
        edx = QLineEdit()
        edx.setObjectName('doi')
        layoutEditor.addRow('DOI:', edx)
        # authors
        edx = QTextEdit()
        edx.setFixedHeight(80)
        edx.setObjectName('author')
        layoutEditor.addRow('作者:', edx)
        # abstract
        edx = QTextEdit()
        edx.setObjectName('abstract')
        edx.setMinimumHeight(200)
        layoutEditor.addRow('摘要:', edx)
        # note = QLineEdit()
        # note.setObjectName('note')
        # layoutEditor.addRow('笔记:', note)
        #
        self.btnClear.clicked.connect(self.clear)
        self.btnSave.clicked.connect(self.triggerUpdate)
        self.btnNew.clicked.connect(self.triggerNew)
        self.data = {}
    def setContents(self, data: dict):
        self.data = data.copy()
        self.issn.setText(data.get('issn'))
        names = [x.objectName() for x in self.children()]
        names = [x for x in names if x != '']
        for k in names:
            dx = data.get(k, '')
            obj = self.findChild(QWidget, k)
            if obj:
                obj.setText(str(dx))
        self.btnSave.setEnabled(True)
        self.btnNew.setEnabled(False)
    def getData(self):
        ans = {}
        for edt in self.findChildren(QLineEdit):
            ans.update({edt.objectName(): edt.text()})
        for edt in self.findChildren(QTextEdit):
            ans.update({edt.objectName(): edt.toPlainText()})
        return ans
    def clear(self):
        for edt in self.findChildren(QLineEdit):
            edt.setText('')
        for edt in self.findChildren(QTextEdit):
            edt.setText('')
        self.btnSave.setEnabled(False)
        self.btnNew.setEnabled(True)
    def triggerUpdate(self):
        bitem = self.getData()
        bitem.update({'bibkey': self.data.get('bibkey')})
        self.signalEditorSaved.emit(bitem)
    def triggerNew(self):
        QMessageBox.warning(self, 'TODO', '功能待完善')
class TabDiary(QFrame):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        hspliter = QSplitter(QtCore.Qt.Orientation.Horizontal)
        layout.addWidget(hspliter)
        self.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.calendar = QViewerCalender()
        self.diary = ENoteBook()
        hspliter.addWidget(self.calendar)
        hspliter.addWidget(self.diary)
class QDataButton(QPushButton):
    UDIR = UserConfig().get('dir_user')
    bdir = os.path.join(UDIR, 'data')
    basic_path = bdir
    def __init__(self):
        super().__init__()
        self.setText('数据目录')
        self.data_path = None
        self.clicked.connect(self.onClick)
    def setData(self, data: dict):
        bkey = data.get('bibkey', 'NOKEY')
        self.data_path = os.path.join(self.basic_path, bkey)
        if os.path.isdir(self.data_path):
            self.setIcon(QIcon(ICON_FOLDER_OPEN))
            self.setText(' 打开数据')
        else:
            self.setIcon(QIcon(ICON_FOLDER_NEW))
            self.setText(' 新建数据')
    def onClick(self):
        if os.path.isdir(self.data_path):
            os.system(f'xdg-open {self.data_path}')
        else:
            reply = QMessageBox.warning(
                self, '警告', '是否为当前文献新建数据目录？',
                QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes)
            if reply == QMessageBox.StandardButton.Yes:
                os.system(f'mkdir -p {self.data_path}')
                if os.path.isdir(self.data_path):
                    self.setText(' 打开数据')
                    os.system(f'xdg-open {self.data_path}')
                else:
                    QMessageBox.warning(self, '警告', '目录创建失败！',
                                        QMessageBox.StandardButton.Ok)
class FrameFileTools(QFrame):
    def __init__(self):
        super().__init__()
        mlayout = QHBoxLayout()
        self.setLayout(mlayout)
        self.setMinimumWidth(200)
        self.setMaximumWidth(600)
        self.setContentsMargins(0,0,0,0)
        mlayout.setContentsMargins(0,0,0,0)
        vspliter = QSplitter(QtCore.Qt.Orientation.Vertical)
        vspliter.setContentsMargins(0, 0, 0, 0)
        vspliter.setSizes([80, 240])
        mlayout.addWidget(vspliter)
        fileFrame = QFrame()
        fileFrame.setFrameShape(QFrame.Shape.Box)
        fileFrame.setFrameShadow(QFrame.Shadow.Sunken)
        fileLayout = QFormLayout()
        fileLayout.setContentsMargins(20, 20, 20, 5)
        fileFrame.setLayout(fileLayout)
        self.FileList = QViewerFileList(False)
        self.AddFile = QPushButton(QIcon(ICON_FILE_PDF), '添加附件')
        self.OpenDataPath = QDataButton()
        fileLayout.addRow(self.AddFile)
        fileLayout.addRow(self.FileList)
        fileLayout.addRow(self.OpenDataPath)
        xmemo = QEditorMemo()
        xmemo.setPlaceholderText('便签本')
        vspliter.addWidget(fileFrame)
        vspliter.addWidget(xmemo)
class FrameGroupTree(QTreeWidget):
    signalGroupChanged = QtCore.pyqtSignal()
    def __init__(self):
        super().__init__()
        self.data = None
        self.root = None         ## 根分支
        self.freefind = None
        self.fulltext = None
        self.marked = None
        self.imported = None
        self.sysGroups = ['All references', 'Marked', 'Find free', 'Find sents', 'Imported']
        self.gCachedBitemList = ListActiveBitems()
        self.gGroupBkeys = {}
        self.setColumnCount(1)
        self.setHeaderHidden(True)
        self.autoExpandDelay()
        font = QFont()
        font.setPointSize(UserConfig().get('font_size_basic'))
        self.setFont(font)
        self.setTree()
        self.itemSelectionChanged.connect(self.signalGroupChanged.emit)
        self.itemDoubleClicked.connect(self.resetCurrent)
    def setTree(self, current: str=''):
        self.clear()
        self.data = BibGroups().data
        self.root = QTreeWidgetItem(self)
        self.root.setText(0, 'All references')
        self.root.setData(0, QtCore.Qt.ItemDataRole.UserRole, {})
        self.root.setToolTip(0, "All cached references")
        self.marked = QSysGroupItem(self.root)
        self.marked.setText(0, 'Marked')
        self.marked.setData(0, QtCore.Qt.ItemDataRole.UserRole, {})
        self.freefind = QSysGroupItem(self.root)
        self.freefind.setText(0, 'Find free')
        self.freefind.setData(0, QtCore.Qt.ItemDataRole.UserRole, {})
        self.fulltext = QSysGroupItem(self.root)
        self.fulltext.setText(0, 'Find sents')
        self.fulltext.setData(0, QtCore.Qt.ItemDataRole.UserRole, {})
        self.imported = QSysGroupItem(self.root)
        self.imported.setText(0, 'Imported')
        self.imported.setData(0, QtCore.Qt.ItemDataRole.UserRole, {})
        citem = self.marked
        if len(self.data) > 0:
            gnames = [x for x in self.data.keys()]
            gnames.sort()
            for gname in gnames:
                gitem = QTreeWidgetItem(self.root)
                gitem.setText(0, gname)
                if gname == current:
                    citem = gitem
        self.expandAll()
        self.setCurrentItem(citem)
        if current != '':
            self.signalGroupChanged.emit()
    def currentGroup(self):
        return self.currentItem().text(0)
    def cachedGroups(self):
        return [x for x in self.gGroupBkeys.keys()]
    def resetCaches(self):
        self.gCachedBitemList.clear()
        self.gGroupBkeys.clear()
        self.signalGroupChanged.emit()
    def resetGroup(self, gname):
        if not inList(gname, self.cachedGroups()):
            return False
        xkeys = self.gGroupBkeys.get(gname)
        for gx in self.gGroupBkeys.keys():
            if gx != gname:
                xkeys = xkeys.difference(self.gGroupBkeys.get(gx))
        for bkey in xkeys:
            self.gCachedBitemList.removeByKey(bkey)
        self.gGroupBkeys.pop(gname)
        if self.currentGroup() == gname:
            self.signalGroupChanged.emit()
    def resetCurrent(self):
        self.resetGroup(self.currentGroup())
    def exportBibtex(self):
        fkeys = ['bibkey', 'journal', 'title', 'author', 'year', 'pages', 'abstract']
        gname = self.currentGroup()
        bkeys = self.gGroupBkeys.get(gname)
        blist = self.gCachedBitemList.bitems(bkeys)
        contents = []
        for xitem in blist:
            ans = ['@Article{' + xitem.get("bibkey") + ',']
            xct = [k + ' = {' + xitem.get(k, '') + '},' for k in fkeys]
            ans.extend(xct)
            ans.append('}\n')
            contents.extend(ans)
        ofile, _ = QFileDialog.getSaveFileName(
            self, "导出为文件", "")
        if ofile:
            with open(ofile, 'w') as f:
                f.write("\n".join(contents))
    def editGroup(self):
        gname = self.currentGroup()
        gname = '' if inList(gname, self.sysGroups) else gname
        xdlg = GroupEdit(self, gname)
        xdlg.updated.connect(self.setTree)
        xdlg.open()
    def sizeHint(self):
        return QSize(400, 600)
    def minimumSizeHint(self):
        return QSize(200, 400)
    def contextMenuEvent(self, evt):
        menu = QMenu()
        menu.setObjectName('PopMenuGroupList')
        menu.addSection(u'分组动作')
        menu.addSeparator()
        gname = self.currentGroup()
        if gname == 'All references':
            actEdtGroup = QAction(QIcon(ICON_FAVORITE), u'新建分组', self)
            actEdtGroup.triggered.connect(self.editGroup)
            actClearCached = QAction(QIcon(ICON_CLEAR), u'清空所有缓存', self)
            actClearCached.triggered.connect(self.resetCaches)
            menu.addAction(actEdtGroup)
            menu.addAction(actClearCached)
        if inList(gname, ['Find sents', 'Find free', 'Imported']):
            actClear= QAction(QIcon(ICON_CLEAR), u'清空分组缓存', self)
            actClear.triggered.connect(self.resetCurrent)
            menu.addAction(actClear)
        elif gname != 'All references':
            actReload = QAction(QIcon(ICON_REFRESH), u'重载分组', self)
            actReload.triggered.connect(self.resetCurrent)
            menu.addAction(actReload)
        if not inList(self.currentGroup(), self.sysGroups):
            actEdtGroup = QAction(QIcon(ICON_EDIT2), u'编辑分组', self)
            actEdtGroup.triggered.connect(self.editGroup)
            menu.addAction(actEdtGroup)
        actExportBibtex = QAction(QIcon(ICON_FILE_TEX), u'导出为bibtex', self)
        actExportBibtex.triggered.connect(self.exportBibtex)
        menu.addAction(actExportBibtex)
        menu.exec(QCursor.pos())   # 此语句必须放在最后
class FrameSearchKeyEdit(QFrame):
    find = QtCore.pyqtSignal(str)
    def __init__(self):
        super().__init__()
        layoutSearch = QFormLayout()
        layoutSearch.setContentsMargins(20, 0, 10, 20) # left, top, right, bottom
        layoutSearch.setFormAlignment(QtCore.Qt.AlignmentFlag.AlignBottom)
        self.setLayout(layoutSearch)
        self.setFrameShape(QFrame.Shape.Panel)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        # tool tips
        layoutSearch.addRow(QLabel('* 同组关键词“或”运算，不同组关键词“与”运算\n* 关键词间分号分隔'))
        # Line edit
        for i in range(6):
            xinput = QInputKeywords(f'searchKeys{i}')
            layoutSearch.addRow(xinput)
            xinput.returnPressed.connect(self.emitXFind)
        # buttons
        self.btnReset = QPushButton(QIcon(ICON_CLEAR), '重置')
        self.btnKFind = QPushButton(QIcon(ICON_SEARCH), 'BKey')
        self.btnXFind = QPushButton(QIcon(ICON_SEARCH), '全域')
        self.btnReset.setToolTip('清空输入内容')
        self.btnXFind.setToolTip('查询或重新查询文献并更新缓存')
        layoutButton = QHBoxLayout()
        layoutButton.addWidget(self.btnReset)
        layoutButton.addWidget(self.btnKFind)
        layoutButton.addWidget(self.btnXFind)
        layoutSearch.addRow(layoutButton)
        # 内部信号触发条件，外部直接监控 triggered 即可
        self.btnReset.clicked.connect(self.resetInputs)
        self.btnXFind.clicked.connect(self.emitXFind)
        self.btnKFind.clicked.connect(self.emitKFind)
    def resetInputs(self):
        inputs = self.findChildren(QInputKeywords)
        for ww in inputs:
            ww.setText('')
        self.emitXFind()
    def reloadHistory(self):
        for obj in self.findChildren(QInputKeywords):
            obj.loadHistory()
    def updateHistory(self):
        xdir = UserConfig().conf_dir
        hfile = f'{xdir}/history_keywords'
        klist = []
        wobjs = self.findChildren(QInputKeywords)
        for obj in wobjs:
            kwds = obj.text().strip()
            if kwds != '':
                kwds = re.sub(r'\s+', ' ', kwds)
                klist.append(kwds)
        if os.path.exists(hfile):
            klist.extend(readLines(hfile))
        klist = listuniq(klist)
        if len(klist) > 100:
            klist = klist[0:100]
        with open(hfile, 'w') as f:
            f.write('\n'.join(klist))
            f.close()
        for obj in wobjs:
            obj.history = klist
    def emitKFind(self):
        self.updateHistory()
        self.find.emit('bibkey')
    def emitXFind(self):
        self.updateHistory()
        self.find.emit('bibtex')
class FrameBitemListView(QFrame):
    message = QtCore.pyqtSignal(list)
    def __init__(self):
        super().__init__()
        layoutMain = QVBoxLayout()
        layoutMain.setContentsMargins(0,10,0,0) # 主
        self.setLayout(layoutMain)
        layoutTop = QHBoxLayout()
        layoutTop.setContentsMargins(0,0,0,0) # 排序栏
        # 总体上下布局：上面板设置垂直布局，放置按钮；下面板为表格
        self.Table = QViewerBibTable()
        layoutMain.addLayout(layoutTop)
        layoutMain.addWidget(self.Table)
        # 上面板内容 ==========================================
        self.sortEnabled = QCheckBox('应用规则')
        self.sortEnabled.setChecked(False)
        self.sort1 = QComboBox()
        self.sort2 = QComboBox()
        self.sort3 = QComboBox()
        # self.sort1.setStyleSheet('min-width: 3em;')
        self.sort1.setToolTip('第1排序依据')
        self.sort2.setToolTip('第2排序依据')
        self.sort3.setToolTip('第3排序依据')
        self.order1 = QCheckBox('逆序')
        self.order2 = QCheckBox('逆序')
        self.order3 = QCheckBox('逆序')
        layoutTop.addWidget(QLabel('排序规则：'))
        layoutTop.addWidget(self.sortEnabled)
        layoutTop.addWidget(self.sort1)
        layoutTop.addWidget(self.order1)
        layoutTop.addWidget(self.sort2)
        layoutTop.addWidget(self.order2)
        layoutTop.addWidget(self.sort3)
        layoutTop.addWidget(self.order3)
        # 排序选项
        options = ['', 'journal', 'year', 'rank', 'author', 'title']
        for x in [self.sort1, self.sort2, self.sort3]:
            x.addItems(options)  ## sort1/2/3
            x.currentIndexChanged.connect(self.checkBeforePass)
        for x in [self.order1, self.order2, self.order3]:
            x.stateChanged.connect(self.checkBeforePass)
        ## 默认排序依据
        self.sort1.setCurrentIndex(1)
        self.sort2.setCurrentIndex(2)
        self.sort3.setCurrentIndex(3)
        self.order2.setChecked(True)
        self.order3.setChecked(True)
        # 过滤 ---------------------
        layoutTop.addSpacing(10)
        ## 过滤查询范围
        self.filterInField = QComboBox()
        self.filterInField.addItems(['', 'title', 'journal', 'abstract', 'author'])
        self.filterInField.currentIndexChanged.connect(self.passFilterAndSort)
        layoutTop.addWidget(self.filterInField)
        ## 过滤关键词
        self.input_filter_keywords = QLineEdit()
        self.input_filter_keywords.setObjectName('filterKeywords')
        self.input_filter_keywords.setMinimumWidth(400)
        self.input_filter_keywords.setPlaceholderText('快速过滤关键词')
        self.input_filter_keywords.setToolTip('关键词间使用逗号或分号分隔')
        layoutTop.addWidget(self.input_filter_keywords)
        self.hasNotes = QCheckBox('有笔记')
        self.hasFiles = QCheckBox('有全文')
        self.hasAbstr = QCheckBox('有摘要')
        layoutTop.addWidget(self.hasNotes)
        layoutTop.addWidget(self.hasFiles)
        layoutTop.addWidget(self.hasAbstr)
        ##
        # 分隔符
        layoutTop.addSpacing(10)
        layoutTop.addWidget(CleanSpacer())
        # 控件动作
        self.sortEnabled.stateChanged.connect(self.passFilterAndSort)
        self.input_filter_keywords.returnPressed.connect(self.passFilterAndSort)
        self.hasNotes.stateChanged.connect(self.passFilterAndSort)
        self.hasFiles.stateChanged.connect(self.passFilterAndSort)
        self.hasAbstr.stateChanged.connect(self.passFilterAndSort)
    def sizeHint(self):
        return QSize(1200, 600)
    def minimumSizeHint(self):
        return QSize(200, 100)
    def checkBeforePass(self):
        if self.sortEnabled.isChecked():
            self.passFilterAndSort()
    def passFilterAndSort(self):
        kwds = self.input_filter_keywords.text().strip()
        if not kwds == '':
            self.input_filter_keywords.setStyleSheet('background-color: #FFE4B5;')
        kwds = re.sub(r'\s+', ' ', kwds)
        self.Table.filterInField = self.filterInField.currentText()
        self.Table.kwdFilter = [x for x in re.split(r' *[，；;,]+ *', kwds) if x !='']
        self.Table.filterHasNotes = self.hasNotes.isChecked()
        self.Table.filterHasFiles = self.hasFiles.isChecked()
        self.Table.filterHasAbstr = self.hasAbstr.isChecked()
        ans = []
        if self.sortEnabled.isChecked():
            sorts = [x.currentText() for x in (self.sort1, self.sort2, self.sort3)]
            sorts = ['bibkey' if x=='year' else x for x in sorts]
            orders = [x.isChecked() for x in (self.order1, self.order2, self.order3)]
            orders = [orders[i] for i in range(3) if sorts[i] != '']
            sorts = [sorts[i] for i in range(3) if sorts[i] != '']
            if len(sorts) > 0:
                ans = [sorts, orders]
        self.Table.arrangeList = ans
        self.Table.updateTableView()
    def keyReleaseEvent(self, e: QtGui.QKeyEvent) -> None:
        escape = e.key() == QtCore.Qt.Key.Key_Escape
        if escape and self.input_filter_keywords.hasFocus():
            self.input_filter_keywords.setText('')
            self.input_filter_keywords.setStyleSheet('background-color: white;')
            self.passFilterAndSort()
            self.input_filter_keywords.setFocus()
        elif self.input_filter_keywords.hasFocus():
            kwds = self.input_filter_keywords.text().strip()
            if kwds == '':
                self.input_filter_keywords.setStyleSheet('background-color: white;')
                self.passFilterAndSort()
            self.input_filter_keywords.setFocus()
class FrameDetailsView(QTabWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName('bibTabViews')
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # 摘要与文件浏览器
        xviewer = QFrame()
        xviewer.setContentsMargins(0, 0, 0, 0)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        xviewer.setLayout(layout)
        self.BibAbstract = TabAbstractViewer()
        layout.addWidget(self.BibAbstract)
        self.addTab(xviewer, '预览')
        # 编辑器
        self.BitemEditor = TabBitemEditor()
        self.addTab(self.BitemEditor, '编辑')
        # 文献阅读笔记
        self.NotesViewer = QViewerNotes()
        self.addTab(self.NotesViewer, '笔记')
        # # 日记
        # self.DiaryEditor = TabDiary()
        # self.addTab(self.DiaryEditor, '日记')
        self.currentChanged.connect(self.NotesViewer.reloadData)
        # PDF展示时机，减少非必要资源使用
        # self.currentChanged.connect(self.showPDF)
        # TODO: 内嵌浏览器
        # self.browser = QWebBrowser()
        # self.addTab(self.browser, '浏览器')
    def sizeHint(self):
        return QSize(1200, 600)
    def minimumSizeHint(self):
        return QSize(200, 100)
class PanelLeft(QFrame):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        # self.setFrameShape(QFrame.StyledPanel)
        # self.setFrameShadow(QFrame.Raised)
        self.setStyleSheet('padding: 5px 5px 0 0; margin: 0;')
        gframe = QFrame()
        glayout = QVBoxLayout()
        glayout.setContentsMargins(0, 0, 0, 0)
        gframe.setLayout(glayout)
        gframe.setFrameShape(QFrame.Shape.Panel)
        gframe.setFrameShadow(QFrame.Shadow.Sunken)
        # group view
        self.GroupFrame= FrameGroupTree()
        self.GroupFrame.setStyleSheet('padding: 5px; margin: 0;')
        glayout.addWidget(self.GroupFrame)
        # search form
        self.SearchFrame = FrameSearchKeyEdit()
        # spliter
        vspliter = QSplitter(QtCore.Qt.Orientation.Vertical)
        vspliter.setContentsMargins(0, 0, 0, 0)
        vspliter.setStyleSheet('padding: 0; margin: 0;')
        vspliter.setSizes([600, 300])
        vspliter.addWidget(gframe)
        vspliter.addWidget(self.SearchFrame)
        self.layout.addWidget(vspliter)
    def sizeHint(self):
        return QSize(400, 600)
    def minimumSizeHint(self):
        return QSize(200, 400)
class PanelRight(QFrame):
    signalCurrentBitem = QtCore.pyqtSignal(dict)
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet('margin: 0; padding: 0;')
        self.ListFrame = FrameBitemListView()
        self.DetailFrame = FrameDetailsView()
        self.FileFrame = FrameFileTools()
        self.ViewerAbstract = self.DetailFrame
        self.BibTable = self.ListFrame.Table
        self.BibAbstract = self.DetailFrame.BibAbstract
        self.NotesViewer = self.DetailFrame.NotesViewer
        self.NotesEditor = self.NotesViewer.ManualNotes
        self.BitemEditor = self.DetailFrame.BitemEditor
        self.FileListViewer = self.FileFrame.FileList
        # 可拖拽窗口布局设置步骤
        # 1. 将控件添加到QSpliter上
        # 2. 将Qspliter添加的布局中
        vspliter = QSplitter(QtCore.Qt.Orientation.Vertical)
        vspliter.setSizes([800, 600])
        vspliter.setContentsMargins(0, 0, 0, 0)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(vspliter)
        # hspliter = QSplitter(QtCore.Qt.Orientation.Horizontal)
        hspliter = QHSpliter()
        vspliter.addWidget(self.ListFrame)
        vspliter.addWidget(hspliter)
        hspliter.addWidget(self.DetailFrame)
        hspliter.addWidget(self.FileFrame)
        # 文献列表信号
        self.BibTable.rowSelectionChanged.connect(self.viewItemChanged)
        self.BibTable.signalDisableTable.connect(self.clearContents)
        self.FileListViewer.signalChanged.connect(self.BibTable.updateBSents)
        self.FileListViewer.signalChanged.connect(self.BibAbstract.updateData)
        self.BitemEditor.signalEditorSaved.connect(self.BibTable.updateSingleItem)
        #
    def viewItemChanged(self, data):
        self.DetailFrame.setDisabled(False)
        self.FileFrame.setDisabled(False)
        self.FileFrame.OpenDataPath.setData(data)
        self.BibAbstract.setData(data)
        self.FileListViewer.setBitem(data)
        self.BitemEditor.setContents(data)
        self.NotesViewer.setEdtData(data)
        self.signalCurrentBitem.emit(data)
    def sizeHint(self):
        return QSize(800, 600)
    def minimumSizeHint(self):
        return QSize(400, 200)
    def clearContents(self):
        self.FileFrame.setDisabled(True)
        self.DetailFrame.setDisabled(True)
class AppLayout(QVBoxLayout):
    groupedChanged = QtCore.pyqtSignal(str)
    pageChanged = QtCore.pyqtSignal(dict)
    def __init__(self):
        super().__init__()
        self.setContentsMargins(0, 0, 0, 0)
        self.GlobLPanel = PanelLeft()
        self.GlobRPanel = PanelRight()
        self.GlobSearch = self.GlobLPanel.SearchFrame
        self.GlobGroup = self.GlobLPanel.GroupFrame
        self.GlobFilterKeywords = self.GlobRPanel.ListFrame.input_filter_keywords
        self.GlobTable = self.GlobRPanel.BibTable
        self.GlobAbstract = self.GlobRPanel.BibAbstract
        self.GlobBEditor = self.GlobRPanel.BitemEditor
        self.GlobFileList = self.GlobRPanel.FileListViewer
        self.GlobNEditor = self.GlobRPanel.NotesEditor
        # NOTE: 通过分割条组织主控件
        hspliter = QSplitter(QtCore.Qt.Orientation.Horizontal)
        hspliter.addWidget(self.GlobLPanel)
        hspliter.addWidget(self.GlobRPanel)
        hspliter.setSizes([200, 800])
        self.addWidget(hspliter)
        ## 面板间共享数据
        self.gGroupBkeys = {}
        self.gCachedBitemList = ListActiveBitems()
        self.GlobTable.gCachedBitemList = self.gCachedBitemList
        self.GlobTable.gGroupBkeys = self.gGroupBkeys
        self.GlobGroup.gCachedBitemList = self.gCachedBitemList
        self.GlobGroup.gGroupBkeys = self.gGroupBkeys
        self.cachedGroups = self.GlobGroup.cachedGroups
        ##
        self.DialogWSearch = None
        self.lastgroup = ''
        self.sysGroups = ['All references', 'Find free', 'Find sents', 'Imported']
        self.findin = "bibtex"
        ## 状态栏定义
        self.statusbar = QStatusBar()
        self.statusbar.setObjectName("statusbar")
        ## 数据初始化
        self.ThreadSearch = None
        self.ThreadMisc = None
        self.ThreadMP3 = None
        self.tasknum = 0
        self.msnTimer = QTimer()
        self.msnTimer.timeout.connect(self.resetMSN)
        ## 面板间通讯
        self.GlobRPanel.ListFrame.message.connect(self.receiveMSN)
        self.GlobRPanel.FileFrame.AddFile.clicked.connect(self.GlobFileList.setBibFiles)
        self.GlobSearch.find.connect(self.dispatchFind)
        self.GlobGroup.signalGroupChanged.connect(self.dispatchGrpChanged)
        self.GlobTable.message.connect(self.receiveMSN)
        self.GlobTable.markedItemChanged.connect(self.reloadMarked)
        ## 系统设置对话框
        self.ConfigDialog = EditorConfig()
        #self.ConfigDialog.signalSaved.connect(self.xconfig)
        self.winNoteBook = DNoteBook()
        self.winNoteBook.setDisabled(True)
        self.winNoteBook.editor.btn_pdf_redo.setVisible(False)
        self.winNoteBook.showed.connect(self.NoteBookToggled)
        self.GlobRPanel.signalCurrentBitem.connect(self.winNoteBook.setData)
        ##
        self.gKeywordsCached = dict()
        self.executeSearch()
        self.Player = AudioPlayer()
        self.Player.signalPlayNext.connect(self.audioPlayNext)
        ## 字典查询显示窗口
        self.GlobAbstract.sdcv_result.connect(self.showSdcvResult)
        self.GlobRPanel.NotesViewer.ViewPDFanno.sdcv_result.connect(self.showSdcvResult)
    def NoteBookToggled(self, dlgshowed: bool):
        self.winNoteBook.setDisabled(not dlgshowed)
        self.GlobNEditor.setDisabled(dlgshowed)
        if not dlgshowed:
            self.GlobNEditor.reload()
    def switchView(self):
        if self.GlobLPanel.isVisible():
            self.GlobLPanel.hide()
            self.GlobRPanel.ListFrame.hide()
        else:
            self.GlobLPanel.show()
            self.GlobRPanel.ListFrame.show()
            self.GlobTable.setFocus()
    def resetMSN(self):
        nshow = len(self.GlobTable.dataShow)
        msn = f'当前分组缓存文献记录 {self.GlobTable.groupNbibs} 条，显示 {nshow} 条'
        sstr = 'background-color: #F5F5F5; color: black;'
        self.statusbar.setStyleSheet(sstr)
        self.statusbar.showMessage(msn)
        if self.msnTimer.isActive():
            self.msnTimer.stop()
        #
    def receiveMSN(self, info: list):
        msn = info[0]
        style = 'normal' if len(info) < 2 else info[1]
        self.showMessage(msn, style)
        if self.msnTimer.isActive():
            self.msnTimer.stop()
        if style != 'normal':
            self.msnTimer.start(1000*5)
    def showMessage(self, msn: str, style: str='normal'):
        self.statusbar.showMessage(msn)
        style = style.lower()
        ## default style
        sstr = 'background-color: #F5F5F5; color: black;'
        if style == 'warn' or style == 'alert':
            sstr = 'background-color: #FF7F50;'
        elif style == 'mode':
            sstr = 'background-color: #87CEFA;'
        elif style == 'ok':
            sstr = 'background-color: #90EE90;'
        self.statusbar.setStyleSheet(sstr)
    def keepCurrentKeywords(self):
        # 查询*前*触发保存临时关键词
        self.GlobSearch.reloadHistory()
        objs = self.GlobLPanel.findChildren(QInputKeywords)
        kwds = {x.objectName(): x.text().strip() for x in objs}
        gname = self.currentGroup()
        self.gKeywordsCached.update({gname: kwds})
        return kwds
    def restoreCurrentKeywords(self):
        # 分组改变触发。仅包括左侧搜索关键词，不包括过滤关键词和分组关键词
        gname = self.currentGroup()
        kwds = self.gKeywordsCached.get(gname)
        for obj in self.GlobLPanel.findChildren(QInputKeywords):
            if not kwds:
                obj.setText('')
            else:
                oname = obj.objectName()
                obj.setText(kwds.get(oname, ''))
    def kwdsInput(self):
        ans = [str2wordlist(x.text())
               for x in self.GlobSearch.findChildren(QLineEdit)
               if x.text().strip() != '']
        ans = [x for x in ans if len(x) > 0]
        return ans
    def kwdsGroup(self):
        ans = []
        gname = self.currentGroup()
        kstr = self.GlobGroup.data.get(gname)
        if kstr:
            ans = kstr.split('#')
            ans = [str2wordlist(v) for v in ans]
        return ans
    def kwdFilter(self):
        kwds = self.GlobFilterKeywords.text().strip()
        kwds = re.sub(r'\s+', ' ', kwds)
        kwds = [x for x in re.split(r' *[，；;,]+ *', kwds) if x !='']
        return kwds
    def currentGroup(self):
        return self.GlobGroup.currentItem().text(0)
    def resetGroup(self, gname):
        if not inList(gname, self.cachedGroups()):
            return False
        xkeys = self.gGroupBkeys.get(gname)
        if len(xkeys) < 1:
            return False
        for gx in self.gGroupBkeys.keys():
            if gx != gname:
                xkeys = xkeys.difference(self.gGroupBkeys.get(gx))
        for bkey in xkeys:
            self.gCachedBitemList.removeByKey(bkey)
        self.gGroupBkeys.pop(gname)
        if self.currentGroup() == gname:
            self.syncNfilterCached()
    def appendBlistCached(self, data):
        gname = data.get('gname')
        blist = data.get('blist')
        etime = data.get('time')
        self.gCachedBitemList.extend(blist)
        if etime and gname != 'Marked':
            nbibs = len(blist)
            self.showMessage(f'{gname}查询完成，缓存文献数量：{nbibs} (查询耗时{etime:.3f}秒)', 'ok')
        bkeys = {x.get('bibkey') for x in blist}
        self.gGroupBkeys.update({gname: bkeys})
        if gname == self.currentGroup():
            self.syncNfilterCached()
        ## TODO: delete
        #self.bgTaskCheckNotes()
    def dispatchFind(self, findin: str):
        self.keepCurrentKeywords()
        gname = self.currentGroup()
        self.findin = findin
        if inList(gname, ['Find sents', 'Find free']):
            self.executeSearch()
        else:
            self.syncNfilterCached()
    def dispatchGrpChanged(self):
        self.findin = "bibtex"
        self.restoreCurrentKeywords()
        gname = self.currentGroup()
        self.GlobSearch.btnXFind.setEnabled(True)
        self.GlobSearch.btnKFind.setEnabled(True)
        if inList(gname, ['Find sents']):
            self.GlobSearch.btnKFind.setEnabled(False)
        egroups = [x for x in self.gGroupBkeys.keys()]
        if inList(gname, self.sysGroups) or inList(gname, egroups):
            self.syncNfilterCached()
        else:
            self.executeSearch()
        self.groupedChanged.emit(gname)
    def syncNfilterCached(self):
        gname = self.currentGroup()
        self.GlobTable.kwdGroup = self.kwdsGroup()
        self.GlobTable.kwdInput = self.kwdsInput()
        self.GlobTable.kwdFilter = self.kwdFilter()
        self.GlobTable.filterSearch = self.findin
        self.GlobTable.currentGroup = gname
        self.GlobRPanel.BibAbstract.currentGroup = gname
        self.GlobRPanel.ListFrame.passFilterAndSort()
    def reloadMarked(self):
        self.executeSearch("Marked")
    def executeSearch(self, gname: str=""):
        if gname == "":
            gname = self.currentGroup()
        self.resetGroup(gname)
        while self.ThreadSearch and self.ThreadSearch.isRunning():
            time.sleep(0.1)
        if self.ThreadSearch and self.ThreadSearch.isFinished():
            self.ThreadSearch.deleteLater()
            time.sleep(0.1)
        ## ----------------------
        if inList(gname, ['Find free', 'Find sents']):
            ## 自由查询
            manualKeywords = self.kwdsInput()
            if len(manualKeywords) < 1:
                return False
            if gname == 'Find sents':
                ## `Find sents`组忽略 `searchin`设置
                self.ThreadSearch = runXSearch(gname, manualKeywords)
            else:
                if self.findin == 'bibkey':
                    searchin = 'bibkey'
                else:
                    searchin = 'fulltext' if UserConfig().get('fulltext_search', 0) > 0 else 'bibtex'
                self.ThreadSearch = runXSearch(gname, manualKeywords, searchin)
        else:
            ## 获取分组文献
            groupKeywords = self.kwdsGroup()
            searchin = 'fulltext' if UserConfig().get('fulltext_search', 0) > 0 else 'bibtex'
            self.ThreadSearch = runXSearch(gname, groupKeywords, searchin)
        ## ----------------------
        self.tasknum += 1
        if gname != "Marked":
            self.showMessage(f'查询任务 <No.{self.tasknum}> 运行中，请稍候 ...', 'alert')
        self.ThreadSearch.start()
        if self.ThreadSearch and self.ThreadSearch.isRunning():
            self.ThreadSearch.setPriority(QtCore.QThread.Priority.HighestPriority)
        self.ThreadSearch.ready.connect(self.appendBlistCached)
    def audioStop(self):
        if self.Player.state() > 0:
            self.Player.pause()
    def audioExPlay(self, info: dict):
        if self.Player.playall:
            ## prepare audio for next item
            self.audioGetOrPlay(current=False)
        bibkey  = info.get('bibkey')
        mp3file = info.get('mp3file')
        newname = info.get('md5name')
        curname = self.Player.objectName()
        if newname == curname:
            if self.Player.state() != 1:
                self.Player.play()
            return True
        ## ------------
        self.audioStop()
        self.Player.clearList()
        if mp3file:
            self.Player.addMedia(mp3file)
            self.Player.setObjectName(newname)
            self.Player.setBibkey(bibkey)
            self.Player.play()
        else:
            QMessageBox.warning(
                self.GlobTable, '警告',
                '语音生成失败，请尝试关闭ollama: sudo systemctl stop ollama')
    def audioGetOrPlay(self, current: bool=True):
        while self.ThreadMP3 and self.ThreadMP3.isRunning():
            time.sleep(0.1)
        if self.ThreadMP3 and self.ThreadMP3.isFinished():
            self.ThreadMP3.deleteLater()
            time.sleep(0.1)
        ## -------------------
        ndx = self.GlobTable.currentRow()
        if not current:
            ndx += 1
            nmax = len(self.GlobTable.dataShow) - 1
            if ndx > nmax:
                ndx = 0
        bitem = self.GlobTable.dataShow[ndx]
        self.ThreadMP3 = ThreadMakeMP3(bitem)
        self.ThreadMP3.start()
        if current:
            self.ThreadMP3.ready.connect(self.audioExPlay)
    def audioPlayCurrent(self):
        self.audioStop()
        self.Player.setPlayAll(False)
        self.audioGetOrPlay()
    def audioPlayAll(self):
        self.audioStop()
        self.Player.setPlayAll(True)
        self.audioGetOrPlay()
    def audioPlayPrev(self):
        ndx = self.GlobTable.currentRow()
        xitem = self.GlobTable.dataShow[ndx]
        xbkey = xitem.get('bibkey')
        if xbkey == self.Player.getBibkey():
            self.GlobTable.prevRow()
        self.audioGetOrPlay()
    def audioPlayNext(self):
        ndx = self.GlobTable.currentRow()
        xitem = self.GlobTable.dataShow[ndx]
        xbkey = xitem.get('bibkey')
        if xbkey == self.Player.getBibkey():
            self.GlobTable.nextRow()
        self.audioGetOrPlay()
    def audioDeleteSelected(self):
        self.audioStop()
        xkeys = self.GlobTable.selectedKeys()
        ndels = 0
        for bkey in xkeys:
            xdirs = getAudioFolders(bkey)
            if len(xdirs) > 0:
                [os.system(f'rm -rf {dx}') for dx in xdirs if os.path.isdir(dx)]
                ndels += 1
        QMessageBox.warning(self.GlobTable, '执行结果', f'找到删除了{ndels}条文献的音频！')
    def showBibInfo(self):
        nall = totalbibs()
        ngroup = self.GlobTable.groupNbibs
        nshow = len(self.GlobTable.dataShow)
        mb = QMessageBox(self.GlobTable)
        mb.setWindowTitle('文献数据库信息')
        mb.setIcon(QMessageBox.Icon.Information)
        msn = f'<p>文献记录总数：<span style="color:red;">{nall}</span></p>'
        msn += f'<p>分组/缓存记录：<span style="color:red;">{ngroup}</span></p>'
        msn += f'<p>关键词匹配记录：<span style="color:red;">{nshow}</span></p>'
        mb.setText(msn)
        mb.show()
    def setImportedBlist(self, blist: list, msn=True):
        nbibs = len(blist)
        if nbibs > 0:
            reply = QMessageBox.warning(
                self.GlobRPanel,
                '请确认',
                f'将导入{nbibs}条记录，是否清空缓存再导入？',
                QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes)
            if reply == QMessageBox.StandardButton.Yes:
                self.resetGroup('Imported')
            self.appendBlistCached({'gname': 'Imported',  'blist': blist})
            if msn:
                self.showMessage(f'文件导入完成，导入文献记录{nbibs}条')
        else:
            QMessageBox.warning(self.GlobTable, '警告', '没有下载或解析到文献记录！')
    def importFromFiles(self):
        uconf = UserConfig()
        opath = uconf.get('dir_import')
        file_selected, _ = QFileDialog.getOpenFileNames(
            self.GlobRPanel,
            '选择导入文件',
            opath,
            '*.* (*.*);;*.bib (*.bib);;*.ris (*.ris);;*.txt (*.txt)')
        # 确认
        nf = len(file_selected)
        if nf < 1:
            return False
        # update import directory
        opath = os.path.dirname(file_selected[0])
        uconf.update({'dir_import': opath})
        uconf.save()
        # ---------
        blist = []
        for f in file_selected:
            ans = importFile2bibList(f)
            blist.extend(ans)
        self.setImportedBlist(blist)
    def saveImported(self):
        if self.ThreadSearch and self.ThreadSearch.isRunning():
            return False
        reply = QMessageBox.warning(
            self.GlobTable, '选择操作', '是否覆盖已有文献记录？',
            QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        if reply == QMessageBox.StandardButton.Cancel:
            return False
        if reply == QMessageBox.StandardButton.Yes:
            overwrite = True
        else:
            overwrite = False
        bkeys = self.gGroupBkeys.get('Imported', {})
        if len(bkeys) > 0:
            bimported = self.gCachedBitemList.bitems(bkeys)
            self.showMessage('文献记录保存中，请稍候 ...', 'alert')
            if self.ThreadSearch and self.ThreadSearch.isFinished():
                self.ThreadSearch.deleteLater()
                time.sleep(0.1)
            self.ThreadSearch = ThreadSaveBitems(bimported, overwrite)
            self.ThreadSearch.start()
            self.ThreadSearch.ready.connect(self.receiveMSN)
    def about(self):
        with open(f'{DIR_APP}/doc/about.html') as f:
            msn = ''.join(f.readlines())
            mb = QMessageBox(self.GlobTable)
            mb.setWindowTitle('关于RgRef')
            mb.setText(msn)
            mb.open()
    def setSpringerResults(self, data: dict):
        if not dict:
            QMessageBox.warning(self.GlobTable, '警告', 'Spring文献查询错误！')
        blist = data.get('blist')
        etime = data.get('time')
        nbibs = len(blist)
        self.showMessage(f'Srpinger文献下载完成，获得文献数：{nbibs} (查询耗时{etime:.3f}秒)', 'ok')
        self.setImportedBlist(blist, msn=False)
    def downloadSpringer(self):
        uconf = UserConfig()
        opath = uconf.get('dir_import')
        file, _ = QFileDialog.getOpenFileName(
            self.GlobRPanel,
            '选择导入文件',
            opath,
            '*.csv (*.csv);;*.txt (*.txt)')
        if file:
            # update import directory
            opath = os.path.dirname(file)
            uconf.update({'dir_import': opath})
            uconf.save()
            if self.ThreadSearch and self.ThreadSearch.isRunning():
                self.showMessage('有未完成任务，请稍候重试 ...', 'alert')
                return False
            self.showMessage('Spring下载任务已在后台运行，耗时可能较长，请稍候 ...', 'alert')
            if self.ThreadSearch and self.ThreadSearch.isFinished():
                self.ThreadSearch.deleteLater()
                time.sleep(0.1)
            self.ThreadSearch = ThreadSpringDownload(file)
            self.ThreadSearch.start()
            self.ThreadSearch.ready.connect(self.setSpringerResults)
    def showSdcvResult(self, word, result):
        dlg = SdcvResultDialog(word, result, self.GlobAbstract)
        dlg.show()
    def WebSearchDialog(self):
        if not self.DialogWSearch:
            self.DialogWSearch = PubMedSearch(self.GlobTable)
            self.DialogWSearch.results.connect(self.setImportedBlist)
        self.DialogWSearch.show()
    def editJournalDlg(self):
        pass
    def showWCdialog(self):
        dlg = WordCountDialog(self.GlobRPanel,  [self.GlobTable.dataShow, self.gCachedBitemList])
        dlg.show()
    def EdHistory(self):
        xdlg = EditorHistory()
        xdlg.saved.connect(self.GlobSearch.reloadHistory)
    def EdConfig(self):
        self.ConfigDialog.exec()
    def xconfig(self):
        QMessageBox.warning(self.GlobTable, '注意', '更改界面字体请手动重启程序！')
    def bgTaskCheckNotes(self):
        while self.ThreadMisc and self.ThreadMisc.isRunning():
            time.sleep(0.1)
        if self.ThreadMisc and self.ThreadMisc.isFinished():
            self.ThreadMisc.deleteLater()
            time.sleep(0.1)
        self.ThreadMisc = ThreadCheckPDFanno(self.gCachedBitemList)
        self.ThreadMisc.start()
        if self.ThreadMisc and self.ThreadMisc.isRunning():
            self.ThreadMisc.setPriority(QtCore.QThread.Priority.IdlePriority)

    def ToolsGroupNew(self):
        xdlg = GroupEdit(self.GlobTable, "")
        xdlg.updated.connect(self.GlobGroup.setTree)
        xdlg.open()

    def ToolsGroupDel(self):
        xdlg = GroupDelete(self.GlobTable)
        xdlg.deleted.connect(self.GlobGroup.setTree)
        xdlg.open()