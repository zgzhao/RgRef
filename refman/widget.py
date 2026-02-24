import re, os
from PyQt5 import QtCore
from PyQt5.QtCore import QSize, QStringListModel, Qt
from PyQt5.QtGui import QIcon, QFont, QCursor, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import (QLabel, QWidget, QFrame, QDialog, QTextBrowser, QMessageBox, QLineEdit, QPushButton,
                             QFormLayout, QHBoxLayout, QVBoxLayout, QSizePolicy, QMenu, QAction, QPlainTextEdit,
                             QToolBar, QSplitter, QTableWidget, QTableView, QListView, QAbstractItemView)
from refman.varsys import *
from refman.config import UserConfig
from refman.speech import read_text
from refman.functions import readLines, runCMD, inList, unlist, hasAnyKeyword, sdcvFind

class WH2(QLabel):
    def __init__(self, label: str):
        super().__init__()
        self.setContentsMargins(0,0,0,0)
        self.setText(label)
def findWidget(currentObj, widgetType=QWidget, name=None):
    ans = currentObj
    while currentObj is not None:
        ans = currentObj
        currentObj = ans.parent()
    oo = ans.findChild(widgetType, name)
    return oo
class CleanSpacer(QFrame):
    def __init__(self):
        super().__init__()
        self.setContentsMargins(0,0,0,0)

    def sizeHint(self):
        return QSize(8000, 5)
def popwarning(parent: QWidget, msn: str = '功能待完善', title: str = '警告'):
    QMessageBox.warning(parent, title, msn)
class InputDialog(QDialog):
    submitted = QtCore.pyqtSignal(dict)
    def __init__(self, parent, title='请输入', xtype='text'):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(600, 240)
        xlayout = QFormLayout()
        xlayout.setSpacing(20)
        xlayout.setFormAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        xlayout.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.setLayout(xlayout)
        self.intext = QLineEdit()
        if xtype == 'password':
            self.intext.setEchoMode(QLineEdit.EchoMode.Password)
        confirm = QPushButton('确定')
        cancel = QPushButton('取消')
        confirm.setObjectName('confirm')
        cancel.setObjectName('cancel')
        xlayout.addRow(self.intext)
        vlayout = QHBoxLayout()
        vlayout.addWidget(cancel)
        vlayout.addWidget(confirm)
        xlayout.addRow(QLabel(''))
        xlayout.addRow(self.intext)
        xlayout.addRow(QLabel(''))
        xlayout.addRow(vlayout)

    def onConfirm(self):
        self.submitted.emit(
            {'input': self.intext.text().strip(),
             'state': 1})
        self.close()

    def onCancel(self):
        self.submitted.emit(
            {'input': '',
             'state': 0})
        self.close()
class CustomTextBrowser(QTextBrowser):
    sdcv_result = QtCore.pyqtSignal(str, list)
    def __init__(self, inDialog: bool=False, parent=None):
        super().__init__(parent)
        # 启用自定义上下文菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.inDialog = inDialog
    def sizeHint(self):
        return QSize(800, 100)
    def minimumSizeHint(self):
        return QSize(80, 50)
    def show_context_menu(self, position):
        # 创建菜单
        menu = QMenu(self)
        # 获取选中的文本
        selected_text = self.textCursor().selectedText()
        # 添加标准动作
        copy_action = QAction(QIcon(ICON_COPY), "复制", self)
        copy_action.triggered.connect(self.copy)
        copy_action.setEnabled(bool(selected_text))
        menu.addAction(copy_action)

        menu.addSeparator()

        # 自定义动作：获取选中文本
        if not self.inDialog:
            find_sdcv = QAction(QIcon(ICON_SEARCH), "查字典", self)
            find_sdcv.triggered.connect(self.sdcv_selected_word)
            find_sdcv.setEnabled(bool(selected_text))
            menu.addAction(find_sdcv)
            #

        # 自定义动作：获取选中文本
        read_action = QAction(QIcon(ICON_AUDIO_PLAY), "朗读", self)
        read_action.triggered.connect(lambda: read_text(selected_text))
        read_action.setEnabled(bool(selected_text))
        menu.addAction(read_action)

        # 显示菜单
        menu.exec_(self.viewport().mapToGlobal(position))
    #
    def sdcv_selected_word(self):
        cursor = self.textCursor()
        selected_text = cursor.selectedText().strip()
        if not selected_text:
            return None
        ans = sdcvFind(selected_text)
        self.sdcv_result.emit(ans.get("word"), ans.get("result"))
class DlgTextInfo(QDialog):
    def __init__(self, parent, title, msn):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(ICON_APP))
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.browser = QTextBrowser()
        self.browser.setStyleSheet('padding: 0; margin: 0;')
        self.layout.addWidget(self.browser)
        self.browser.setHtml(f'<div style="margin: 20px;">{msn}</div>')
class DlgTextEditor(QDialog):
    saved = QtCore.pyqtSignal(bool)
    def __init__(self, title='Editor', w: int=800, h: int=600, emptylines: bool=True):
        super().__init__()
        self.file = None
        self.emptylines = emptylines
        self.rsort = True
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(ICON_APP))
        self.setMinimumSize(w+10, h+60)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        # tool bar
        toolbar = QToolBar(self)
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setContentsMargins(0, 0, 50, 0)
        # editor
        self.editor = QPlainTextEdit()
        self.editor.setStyleSheet('padding: 0; margin: 0;')
        self.editor.setMinimumSize(w, h)
        #
        layout.addWidget(toolbar)
        layout.addWidget(self.editor)
        # toolbar item: save
        toolbar.addSeparator()
        actionSave = QAction(self)
        actionSave.setToolTip('保存')
        actionSave.setIcon(QIcon(ICON_SAVE))
        actionSave.triggered.connect(self.save)
        toolbar.addAction(actionSave)
        toolbar.addSeparator()
        # toolbar item: sort
        actionSort = QAction(self)
        actionSort.setToolTip('排序')
        actionSort.setIcon(QIcon(ICON_SORT))
        actionSort.triggered.connect(self.xsort)
        toolbar.addAction(actionSort)
    def contentList(self):
        contents = self.editor.toPlainText()
        contents = contents.split('\n')
        contents = [x.strip() for x in contents]
        return contents
        #
    def xsort(self):
        clist = self.contentList()
        if self.rsort:
            clist.sort()
            self.rsort = False
        else:
            clist.sort(reverse=True)
            self.rsort = True
        self.editor.setPlainText('\n'.join(clist))
    def save(self):
        if not self.file:
            QMessageBox.warning(self, '警告', '编辑器没有设置文件！')
            return False
        contents = self.contentList()
        if not self.emptylines:
            contents = [x for x in contents if x != '']
        if len(contents) > 0:
            contents = "\n".join(contents)
        else:
            contents = "\n"
        with open(self.file, 'w') as f:
            f.write(contents)
        self.saved.emit(True)
        QMessageBox.information(self, '信息', '内容已保存到指定文件！')
        return True
class EditorHistory(DlgTextEditor):
    def __init__(self, title='编辑查询历史'):
        super().__init__(title=title)
        self.setModal(True)
        xdir = UserConfig().conf_dir
        self.file = f'{xdir}/history_keywords'
        contents = '\n'.join(readLines(self.file))
        self.editor.setPlainText(contents)
        # NOTE: exec不能放到父类，否则super.init后通信中断
        self.exec()
class QOneColumnList(QListView):
    signalXlist = QtCore.pyqtSignal(set)
    def __init__(self):
        super().__init__()
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QListView.SelectionBehavior.SelectRows)
        self.doubleClicked.connect(self.removeJournal)
    def removeJournal(self):
        ndx = {x.row() for x in self.selectedIndexes()}
        self.signalXlist.emit(ndx)
    ##
class QJstatTable(QTableView):
    signalUpdateList = QtCore.pyqtSignal()
    def __init__(self, cnames: list):
        super().__init__()
        self.headers = cnames
        self.jfiles = dict()
        self.dataModel = QStandardItemModel()
        self.dataList = list()
        self.dataShow = list()
        self.j2delete = list()
        font = QFont()
        font.setPointSize(UserConfig().get('font_size_table'))
        self.setFont(font)
        self.setDragEnabled(False)
        self.setAlternatingRowColors(True)
        self.setGridStyle(QtCore.Qt.PenStyle.SolidLine)
        self.setSortingEnabled(False)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.horizontalHeader().setCascadingSectionResizes(False)
        self.horizontalHeader().setSortIndicatorShown(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.doubleClicked.connect(self.addJournals)
    def statJournal(self):
        xdir = UserConfig().get('dir_user')
        xdir = os.path.join(xdir, 'bibtex')
        jpatt = r'^journal *='
        jlist = runCMD(f'rg -N -t txt -i -e "{jpatt}" "{xdir}"')
        patx = re.compile(r'^([^:]+): *journal *= *(.+)$')
        self.jfiles.clear()
        jkeys = []
        for ll in jlist:
            fx = patx.sub(r'\1', ll)
            jx = patx.sub(r'\2', ll).strip()
            if inList(jx, jkeys):
                fs = self.jfiles.get(jx)
                fs.append(fx)
                self.jfiles.update({jx: fs})
            else:
                self.jfiles.update({jx: [fx]})
                jkeys.append(jx)
        xlist = ["{:0>4d}@@".format(len(v)) + k for k,v in self.jfiles.items()]
        xlist.sort()
        xlist.reverse()
        xlist = [x.split('@@') for x in xlist]
        self.dataList = [[x[1], str(int(x[0]))] for x in xlist]
        self.dataShow = self.dataList.copy()
        self.setTable()
    def dataFilter(self, kwdstr: str):
        kwds = re.split(r' *; *', kwdstr)
        kwds = [x.strip() for x in kwds if x.strip() != '']
        if len(kwds) > 0:
            self.dataShow = [x for x in self.dataList if hasAnyKeyword(x[0], kwds)]
        else:
            self.dataShow = self.dataList.copy()
        self.setTable()
    def setTable(self):
        self.dataModel.clear()
        self.dataModel.setHorizontalHeaderLabels(self.headers)
        if len(self.dataShow) < 1:
            return False
        for i in range(len(self.dataShow)):
            xrow = list()
            for content in self.dataShow[i]:
                xrow.append(QStandardItem(str(content)))
            self.dataModel.appendRow(xrow)
        self.setModel(self.dataModel)
        self.setColumnWidth(0, 400)
        ##
    def addJournals(self):
        indices = {x.row() for x in self.selectedIndexes()}
        xset = {self.dataShow[i][0] for i in indices}
        for x in xset:
            if not inList(x, self.j2delete):
                self.j2delete.append(x)
        self.j2delete.sort()
        self.signalUpdateList.emit()
        ##
    def execDelete(self):
        njs = len(self.j2delete)
        if njs < 1:
            QMessageBox.warning(self, '警告', '请选择需要删除的期刊！')
            return False
        reply = QMessageBox.warning(
            self, '警告', f'将删除右边列表中{njs}种选定期刊的所有文献。删除不可恢复，是否继续？',
            QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes)
        if reply != QMessageBox.StandardButton.Yes:
            return False
        xfiles = [self.jfiles.get(x) for x in self.j2delete]
        xfiles = [x for x in unlist(xfiles) if re.search(r'\.txt$', x) and os.path.exists(x)]
        udir = UserConfig().get('dir_user')
        pdir = os.path.join(udir, 'pdf')
        sdir = os.path.join(udir, 'stoken')
        xcount = 0
        fcount = 0
        for bfile in xfiles:
            bkey = re.sub(r'\.txt$', '', os.path.basename(bfile))
            fs = runCMD(f'find {pdir} -name "{bkey}*" | grep -E "{bkey}[^0-9]+"')
            fs = [x for x in fs if x.strip() != '']
            if len(fs) > 0:
                fcount += 1
                continue
            os.remove(bfile)
            if os.path.exists(bfile):
                fcount += 1
            else:
                sfile = os.path.join(sdir, f'{bkey}.txt')
                if os.path.exists(sfile):
                    os.remove(sfile)
                xcount += 1
        self.j2delete.clear()
        self.signalUpdateList.emit()
        QMessageBox.information(self, '信息', f'删除了{xcount}条文献，保留了{fcount}条含附件的文献。')
        ##
    def sizeHint(self):
        return QSize(1200, 800)
    def minimumSizeHint(self):
        return QSize(1000, 400)
    def contextMenuEvent(self, evt):
        menu = QMenu()
        menu.addSection('动作')
        actStat = QAction(u'获取统计数据', self)
        actClean = QAction(u'删除选定期刊文献', self)
        actStat.triggered.connect(self.statJournal)
        menu.addAction(actStat)
        menu.addAction(actClean)
        menu.exec(QCursor.pos())
class DbJournalStat(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('期刊文献统计与清理')
        self.setContentsMargins(0, 0, 0, 0)
        self.setWindowIcon(QIcon(ICON_APP))
        self.setMinimumSize(1400, 960)
        self.setModal(True)
        layout1 = QVBoxLayout()
        layout1.setContentsMargins(0,0,0,0)
        self.setLayout(layout1)
        # toolbar --------------
        toolbar = QToolBar(self)
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setFixedHeight(60)
        layout1.addWidget(toolbar)
        #
        vspliter = QSplitter(QtCore.Qt.Orientation.Horizontal)
        vspliter.setContentsMargins(0, 0, 0, 0)
        # 期刊统计列表
        self.table = QJstatTable(['Journal', 'N'])
        vspliter.addWidget(self.table)
        # 已选期刊列表
        self.xournals = QOneColumnList()
        self.xournals.setMaximumWidth(800)
        self.xournals.setMinimumWidth(400)
        vspliter.addWidget(self.xournals)
        # toolbar items
        toolbar.addSeparator()
        actionStat = QAction(self)
        actionStat.setToolTip('期刊文献统计')
        actionStat.setIcon(QIcon(ICON_SEARCH))
        toolbar.addAction(actionStat)
        ##
        toolbar.addSeparator()
        actionPlus = QAction(self)
        actionPlus.setToolTip('添加到列表')
        actionPlus.setIcon(QIcon(ICON_PLUS))
        actionPlus.triggered.connect(self.table.addJournals)
        actionMinus = QAction(self)
        actionMinus.setToolTip('从列表删除')
        actionMinus.setIcon(QIcon(ICON_MINUS))
        actionMinus.triggered.connect(self.xournals.removeJournal)
        toolbar.addAction(actionPlus)
        toolbar.addAction(actionMinus)
        ## 执行删除
        toolbar.addSeparator()
        actionExec = QAction(self)
        actionExec.setToolTip('删除选定期刊文献')
        actionExec.setIcon(QIcon(ICON_OK))
        actionExec.triggered.connect(self.table.execDelete)
        toolbar.addAction(actionExec)
        toolbar.addSeparator()
        # -----------------------
        # button actions
        actionStat.triggered.connect(self.table.statJournal)
        #
        self.fkeyword = QLineEdit()
        self.fkeyword.setContentsMargins(0,0,0,0)
        layout1.addWidget(vspliter)
        layout1.addWidget(self.fkeyword)
        self.fkeyword.returnPressed.connect(self.emitFilter)
        self.table.signalUpdateList.connect(self.updateXlist)
        self.xournals.signalXlist.connect(self.removeJournals)
        self.j2delete = self.table.j2delete
        self.exec()
    def emitFilter(self):
        self.table.dataFilter(self.fkeyword.text())
    def updateXlist(self):
        self.j2delete.sort()
        jmodel = QStringListModel(self)
        jmodel.setStringList(self.j2delete)
        self.xournals.setModel(jmodel)
    def removeJournals(self, indices: set):
        xitems = [self.j2delete[i] for i in indices]
        for x in xitems:
            if inList(x, self.j2delete):
                self.j2delete.remove(x)
        self.updateXlist()
def sdcv2markdown(word: str, result: list):
    result = [x for x in result if not re.search(r'^save to cache .+ idx$', x)]
    patt1 = re.compile(r'^-->')
    patt2 = re.compile(r'^-->' + word, re.I)
    patt3 = re.compile(r'^(\(*\d+\)*|\([a-z]\))')
    patt4 = re.compile(r'[a-z]', re.I)
    contents = []
    last_is_entry = False
    for ll in result:
        txt = ll.strip()
        if patt1.search(txt):
            txt = patt1.sub('', txt)
            if not patt2.search(ll) and not last_is_entry:
                contents.append(f'### {txt}')
                last_is_entry = True
            else:
                contents.append(f'#### {txt}')
                last_is_entry = False
        elif patt3.search(txt):
            last_is_entry = False
            contents.append(f'- **{txt}**\n')
        elif patt4.search(txt):
            last_is_entry = False
            contents.append(f'{txt}\n')
    return '\n'.join(contents)
    #
def sdcv2html(word: str, result: list):
    patt1 = re.compile(r'^@#dict:')
    patt2 = re.compile(r'^@#word:')
    patt3 = re.compile(r'^(\(*\d+\)*|\([a-z]\))')
    patt3x = re.compile(r'^\[.+]$')
    patt4 = re.compile(r'^/[^/]+/$')
    patt5 = re.compile(r'^ *□')
    patt6 = re.compile(r'^((vt|vi|ad|adj|adv|prep|pl|noun|n|v)\.?)\b')
    contents = []
    for ll in result:
        txt = ll.strip()
        if patt1.search(txt):
            txt = patt1.sub('', txt)
            contents.append(f'<hr/><h2 style="color: #db7093;">{txt}</h2>')
        elif patt2.search(ll):
            txt = patt2.sub('', txt)
            contents.append(f'<hr style="color:#fff;"><h3>{txt}</h3>')
        elif patt3.search(txt) or patt3x.search(txt):
            contents.append(f'<p><b>{txt}</b></p>')
        elif patt4.search(txt):
            contents.append(f'<p style="color: #1e90ff;">{txt}</p>')
        elif patt5.search(txt):
            contents.append(f'<li style="margin-left: 20px;">{txt}</li>')
        else:
            if patt6.search(txt):
                txt = patt6.sub(r'<b style="font-style: italic; color: #4682b4;">[ \1 ]</b> ', txt)
            contents.append(f'<p>{txt}</p>')
    return '\n'.join(contents)
    #
class SdcvResultDialog(QDialog):
    """显示字典查询结果的对话框"""
    def __init__(self, word, result, parent=None):
        super().__init__(parent)
        self.setWindowIcon(QIcon(ICON_APP))
        self.setMinimumSize(500, 400)
        self.setMaximumSize(1200, 800)
        self.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("margin: 0; padding: 0;")
        ## toolbar
        toolbar = QToolBar(self)
        toolbar.setMovable(False)
        toolbar.setFloatable(True)
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setFixedHeight(40)
        self.history_prev = QAction(QIcon(ICON_GO_BACK), "后退")
        self.history_next = QAction(QIcon(ICON_GO_FORWARD), "前进")
        self.history_prev.triggered.connect(self.go_prev)
        self.history_next.triggered.connect(self.go_next)
        self.readWord = QAction(QIcon(ICON_AUDIO_PLAY), '读音')
        self.readWord.triggered.connect(self.read)
        toolbar.addSeparator()
        toolbar.addAction(self.history_prev)
        toolbar.addAction(self.history_next)
        toolbar.addSeparator()
        toolbar.addAction(self.readWord)
        toolbar.addSeparator()
        ## contents
        self.result_widget = CustomTextBrowser()
        self.result_widget.setContentsMargins(0, 0, 0, 0)
        self.result_widget.setStyleSheet("margin: 0; padding: 0;")
        ##
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(toolbar)
        layout.addWidget(self.result_widget)
        ##
        self.current_index = 0
        self.history_list = []
        self.newData(word, result)
        self.result_widget.sdcv_result.connect(self.newData)
        #
    def newData(self, word: str, result: list):
        self.history_list.append([word, result])
        self.current_index = len(self.history_list) - 1
        self.setData(word, result)
    def setData(self, word: str, result: list):
        html = sdcv2html(word, result)
        self.setWindowTitle(f"字典查询: {word}")
        self.result_widget.setHtml(html)
        self.history_prev.setDisabled(False)
        self.history_next.setDisabled(False)
        if self.current_index <= 0:
            self.history_prev.setDisabled(True)
        if self.current_index >= len(self.history_list) - 1:
            self.history_next.setDisabled(True)
        ## content = sdcv2markdown(word, result)
        ## result_widget.setMarkdown(content)
    def load_history(self, n: int):
        if self.history_list:
            hlist = self.history_list[n]
            self.current_index = n
            self.setData(hlist[0], hlist[1])
    def go_prev(self):
        hn = len(self.history_list)
        nn = self.current_index - 1
        if 0 <= nn < hn:
            self.load_history(nn)
    def go_next(self):
        hn = len(self.history_list)
        nn = self.current_index + 1
        if 0 <= nn < hn:
            self.load_history(nn)
    def read(self):
        n = self.current_index
        hlist = self.history_list[n]
        read_text(hlist[0])
