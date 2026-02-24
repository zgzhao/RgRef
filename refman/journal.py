import os
import re
from PyQt5 import QtCore
from PyQt5.QtWidgets import (QTableWidget, QAbstractItemView, QDialog, QVBoxLayout, QHBoxLayout, QFrame, QTableWidgetItem, QLineEdit,
                               QPushButton, QComboBox, QLabel, QFileDialog, QMessageBox)
from PyQt5.QtGui import QFont, QIcon
from refman.varsys import ICON_APP, ICON_FILE_IMPORT, ICON_FILE_EXPORT, ICON_OK
from refman.config import UserConfig
from refman.functions import inList, unlist, listuniq, readLines, runCMD
import pandas as pd

USR_DIR = UserConfig().get('dir_user')
META_DIR = os.path.join(USR_DIR, 'meta')
def readMapFile(file: str, rev: bool=False) -> dict:
    ans = {}
    p = re.compile(r'^([^=]+) *= *(.+)$')
    if os.path.exists(file):
        lls = readLines(file)
        keys = [p.sub(r'\1', x) for x in lls]
        vals = [p.sub(r'\2', x) for x in lls]
        if rev:
            ans = {v.lower():k for k,v in zip(keys, vals)}
        else:
            ans = {k.lower():v for k,v in zip(keys, vals)}
    return ans
def journal2issn(journal_name: str):
    if not journal_name:
        return None
    mfile = os.path.join(META_DIR, 'map.journal2issn.txt')
    mdict = readMapFile(mfile)
    return mdict.get(journal_name.lower())
def issn2abbr(issns):
    if not issns:
        return None
    kwds = [re.split(r' *; *', x) for x in unlist(issns)]
    kwds = "|".join(unlist(kwds))
    mfile = os.path.join(META_DIR, 'map.issn2abbr.txt')
    abbr = runCMD(f'rg -L -i -e "^({kwds})=" "{mfile}"')
    abbr = [re.sub(r'^[^=]+=(.+)$', r'\1', x)
            for x in abbr if re.search(r'^\d{4}-\w{4}=', x)]
    if len(abbr) < 1:
        return None
    return abbr[0]
def issn_to_impact_factor():
    USER_DIR = UserConfig().get('dir_user')
    return readMapFile(f'{USER_DIR}/meta/map.issn2impact.txt')
def journal_to_issns() -> dict:
    USER_DIR = UserConfig().get('dir_user')
    info = readMapFile(f'{USER_DIR}/meta/map.journal2issn.txt')
    ans = {}
    for k,v in info.items():
        anx = ans.get(k, [])
        anx.append(v)
        ans.update({k: anx})
    return ans
def readJournals():
    USER_DIR = UserConfig().get('dir_user')
    META_DIR = f'{USER_DIR}/meta'
    impact = readMapFile(f'{META_DIR}/issn2impact.txt')
    jfull = readMapFile(f'{META_DIR}/issn2full.txt')
    jabbr = readMapFile(f'{META_DIR}/issn2abbr.txt')
    issn = [k for k in impact.keys()]
    ans = {k: {'impact': impact.get(k, 0),
               'full': jfull.get(k, ''),
               'abbr': jabbr.get(k, '')}
           for k in issn}
    return ans
class JournalTable(QTableWidget):
    signalTableDataChanged = QtCore.pyqtSignal(bool)
    def __init__(self):
        super().__init__()
        font = QFont()
        font.setPointSize(UserConfig().get('font_size_table'))
        self.setFont(font)
        self.setDragEnabled(False)
        self.setMinimumHeight(600)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.setAlternatingRowColors(True)
        self.setGridStyle(QtCore.Qt.PenStyle.SolidLine)
        self.setSortingEnabled(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.horizontalHeader().setCascadingSectionResizes(False)
        self.horizontalHeader().setSortIndicatorShown(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        ## data ---------------
        self.jlist = list()
        self.headers = None
        self.setTable(self.jlist)
    def setRowData(self, dt: dict, row: int):
        ncol = len(self.headers)
        for i in range(ncol):
            xitem = QTableWidgetItem()
            value = dt.get(self.headers[i])
            if type(value) != str:
                # NOTE: 数值与文本设置方法不同！
                xitem.setData(QtCore.Qt.ItemDataRole.DisplayRole, value)
            else:
                xitem.setText(value)
            self.setItem(row, i, xitem)
            del xitem
    def setTable(self, data: list):
        self.jlist = data.copy()
        self.clear()
        ncol = len(self.headers)
        nrow = len(self.jlist)
        self.setColumnCount(ncol)
        self.setRowCount(nrow)
        self.setHorizontalHeaderLabels(self.headers)
        row = 0
        for dx in self.jlist:
            self.setRowData(dx, row)
            self.item(row, 2).setToolTip(dx.get('full'))
            row += 1
class JournalMain(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('期刊信息编辑')
        self.setMinimumSize(1200, 800)
        self.setContentsMargins(0, 0, 0, 0)
        self.icon = QIcon(ICON_APP)
        self.setWindowIcon(self.icon)
        ## main layout ----------------------------
        mainlayout = QVBoxLayout()
        mainlayout.setContentsMargins(0, 10, 0, 0)
        self.setLayout(mainlayout)
        ## sub layout 1: header line ------------------------
        flayout = QHBoxLayout()
        flayout.setContentsMargins(0, 0, 0, 0)
        fileframe = QFrame()
        fileframe.setLayout(flayout)
        self.btnExport = QPushButton()
        self.btnExport.setFixedSize(60, 40)
        self.btnExport.setIcon(QIcon(ICON_FILE_EXPORT))
        flayout.addWidget(self.btnExport)
        self.searchKeys = QLineEdit()
        self.searchKeys.setPlaceholderText('input keywords and hit ENTER to filter')
        flayout.addWidget(self.searchKeys)
        ## sub layout 2: table -------------------------------
        self.table = JournalTable()
        ## sub layout 3: bottom line -------------------------
        hframe = QFrame()
        slayout = QHBoxLayout()
        slayout.setContentsMargins(0, 0, 0, 0)
        hframe.setLayout(slayout)
        self.btnImport = QPushButton()
        self.btnImport.setFixedSize(60, 40)
        self.btnImport.setIcon(QIcon(ICON_FILE_IMPORT))
        self.btnImport.setToolTip('Open and import journal info from CSV file.')
        ## set imported table header
        self.colISSN= QComboBox()
        self.colISSN.setObjectName('issn')
        self.colISSN.setToolTip('Select issn column from imported table.')
        # self.colISSN.setFixedWidth(160)
        self.colABBR= QComboBox()
        self.colABBR.setObjectName('abbr')
        self.colABBR.setToolTip('Select journal abbreviation column from imported table.')
        # self.colABBR.setFixedWidth(160)
        self.colFULL= QComboBox()
        self.colFULL.setObjectName('full')
        self.colFULL.setToolTip('Select journal fullname column from imported table.')
        # self.colFULL.setFixedWidth(160)
        self.colJIF= QComboBox()
        self.colJIF.setObjectName('impact')
        self.colJIF.setToolTip('Select impact factor column from imported table.')
        # self.colJIF.setFixedWidth(160)
        slayout.addWidget(self.btnImport)
        labelISSN = QLabel('ISSN:')
        labelISSN.setFixedWidth(80)
        labelISSN.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        slayout.addWidget(labelISSN)
        slayout.addWidget(self.colISSN)
        labelABBR= QLabel('abbr:')
        labelABBR.setFixedWidth(80)
        labelABBR.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        slayout.addWidget(labelABBR)
        slayout.addWidget(self.colABBR)
        labelFULL = QLabel('full:')
        labelFULL.setFixedWidth(80)
        labelFULL.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        slayout.addWidget(labelFULL)
        slayout.addWidget(self.colFULL)
        labelJIF = QLabel('impact:')
        labelJIF.setFixedWidth(120)
        labelJIF.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        slayout.addWidget(labelJIF)
        slayout.addWidget(self.colJIF)
        self.btnSetImport = QPushButton()
        self.btnSetImport.setFixedSize(60, 40)
        self.btnSetImport.setIcon(QIcon(ICON_OK))
        slayout.addWidget(self.btnSetImport)
        ## SET main layout contents
        mainlayout.addWidget(fileframe)
        mainlayout.addWidget(self.table)
        mainlayout.addWidget(hframe)
        ## init table
        self.defaultData = None
        self.dataImported = None
        # self.initTable()
        # self.btnImport.clicked.connect(self.readOpenFile)
        # self.searchKeys.returnPressed.connect(self.kwdfilter)
        # self.btnSetImport.clicked.connect(self.fillImport)
    def initTable(self, jlist: list=None):
        if not jlist:
            jlist = self.defaultData
        self.table.setTable(jlist)
    def readOpenFile(self):
        uconf = UserConfig()
        upath = uconf.get('dir_user')
        opath = uconf.get('recent', upath)
        infile, _ = QFileDialog.getOpenFileName(
            self,
            '选择导入文件',
            opath,
            '*.csv(*.csv);;*.txt (*.txt)')
        if infile:
            opath = os.path.dirname(infile)
            uconf.update({'recent': opath})
            uconf.save()
            jlist = pd.read_csv(infile)
            # xcols = jlist.to_dict('list')
            jlist = jlist.to_dict('records')
            self.dataImported = jlist
            cnames = [x for x in jlist[0].keys()]
            combox = self.findChildren(QComboBox)
            for cc in combox:
                cc.clear()
                cc.addItem('')
                cc.addItems(cnames)
            # QMessageBox.warning(self, 'Warning', '; '.join(cnames))
    def kwdfilter(self):
        patt = self.searchKeys.text().strip()
        if patt == '':
            self.table.setTable(self.defaultData)
        else:
            patt = re.escape(patt)
            p = re.compile(patt, flags=re.I)
            jlist = [x for x in self.defaultData if p.search(x.get('issn', '')) or p.search(x.get('full', '')) or p.search(x.get('abbr', ''))]
            self.table.setTable(jlist)
    def fillImport(self):
        combox = self.findChildren(QComboBox)
        dname = []
        dmap = {}
        for cc in combox:
            val = cc.currentText()
            if val != '':
                k = cc.objectName()
                dname.append(k)
                dmap.update({k: val})
        if not inList('issn', dname):
            QMessageBox.warning(self, '错误', '导入数据必须包含ISSN！')
            return False


