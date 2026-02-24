import re
import time

from PyQt5 import QtCore
from PyQt5.QtWidgets import QDialog, QFormLayout, QTableWidget, QAbstractItemView, QLineEdit, QHBoxLayout, QCheckBox, QMessageBox, QTableWidgetItem
from PyQt5.QtGui import QIcon
from nltk import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from sklearn.feature_extraction import text
from refman.varsys import ICON_APP
from PyQt5.QtCore import QThread
from refman.functions import inList, unlist

STOP_WORDS = text.ENGLISH_STOP_WORDS.union(stopwords.words('english'))
STOP_WORDS = STOP_WORDS.union({
    'plant', 'plants',
    'tree', 'trees',
    'result', 'results'})

class ThreadWordCount(QThread):
    """ 数据库无关键词查询"""
    ready = QtCore.pyqtSignal(dict)
    def __init__(self, data: list, keywords: str):
        super().__init__()
        self.data = [x for x in data if x]
        self.keywords = self.splitWords(keywords)
    def splitWords(self, sentence: str):
        stemmer = PorterStemmer()
        words = word_tokenize(sentence)
        words = {stemmer.stem(x) for x in words}
        words = {x for x in words if not inList(x, STOP_WORDS)}
        words = {x for x in words if re.search(r'^[a-z]+$', x, flags=re.I)}
        return words
    def concurrence(self, words: set):
        if len(self.keywords.intersection(words)) < len(self.keywords):
            return []
        return words.difference(self.keywords)
    def run(self):
        result = []
        ans = {'keywords': self.keywords, 'result': result}
        wcount = {}
        for item in self.data:
            sentences = sent_tokenize(item)
            wordList = [self.splitWords(x) for x in sentences]
            wordList = [self.concurrence(x) for x in wordList]
            wordList = unlist(wordList)
            for w in wordList:
                cc = wcount.get(w, 0)
                wcount.update({w: cc + 1})
        kdict = {k: "{:0>3d}".format(v) for k,v in wcount.items()}
        counts = {x for x in kdict.values()}
        counts = [x for x in counts]
        counts.sort()
        counts.reverse()
        for cc in counts:
            anx = [k for k,v in kdict.items() if v == cc and k != '']
            if len(anx) < 1:
                continue
            anx.sort()
            result.append([cc, ", ".join(anx)])
        ans.update({'result': result})
        self.ready.emit(ans)

class WordCountDialog(QDialog):
    def __init__(self, parent, data: list):
        super().__init__(parent)
        self.data = data
        self.setWindowTitle('关键词上下文分析')
        self.setWindowIcon(QIcon(ICON_APP))
        self.setWindowFlag(QtCore.Qt.WindowType.WindowMinMaxButtonsHint)
        # container
        layoutMain = QFormLayout()
        layoutMain.setContentsMargins(10, 0, 10, 10)
        layoutMain.setFormAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.setMinimumSize(1400, 800)
        self.setLayout(layoutMain)
        ## result panel
        self.table = QTableWidget()
        self.table.setDragEnabled(True)
        self.table.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.table.setAlternatingRowColors(True)
        self.table.setGridStyle(QtCore.Qt.PenStyle.SolidLine)
        self.table.setSortingEnabled(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setCascadingSectionResizes(True)
        self.table.horizontalHeader().setSortIndicatorShown(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        # self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_headers = ['Frequency', 'Keywords']
        layoutMain.addRow(self.table)
        ## input and run button
        layoutInput = QHBoxLayout()
        self.kwdinput = QLineEdit()
        self.kwdinput.returnPressed.connect(self.statKeywords)
        self.withAll = QCheckBox('分组内所有文献')
        self.withAll.setChecked(False)
        self.withAll.setFixedWidth(300)
        layoutInput.addWidget(self.kwdinput)
        layoutInput.addWidget(self.withAll)
        layoutMain.addRow(layoutInput)
        self.wc = None
        self.kwdinput.setFocus()
    def drawTable(self, data: dict):
        self.table.clear()
        keywords = data.get('keywords')
        result = data.get('result')
        if len(keywords) < 1:
            QMessageBox.warning(self, '警告', '关键词设置错误！')
            return False
        if len(result) < 1:
            QMessageBox.warning(self, '警告', '您设置的关键词不会同时出现在一个句子中！')
            return False
        nrow = len(result)
        ncol = len(self.table_headers)
        self.table.setRowCount(nrow)
        self.table.setColumnCount(ncol)
        self.table.setHorizontalHeaderLabels(self.table_headers)
        self.table.setColumnWidth(0, 200)
        for row in range(nrow):
            dt = result[row]
            self.table.setItem(row, 0, QTableWidgetItem(dt[0]))
            self.table.setItem(row, 1, QTableWidgetItem(dt[1]))
    def statKeywords(self):
        kstr = self.kwdinput.text().strip()
        if self.withAll.isChecked():
            data = self.data[1]
        else:
            data = self.data[0]
        data = [x.get('abstract') for x in data]
        if not self.wc:
            self.wc = ThreadWordCount(data, kstr)
        elif self.wc.isRunning():
            return False
        elif self.wc.isFinished():
            self.wc.deleteLater()
            time.sleep(1)
            self.wc = ThreadWordCount(data, kstr)
        self.wc.start()
        self.wc.ready.connect(self.drawTable)
