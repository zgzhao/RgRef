import re
import time

from PyQt5 import QtCore
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QDialog, QFrame, QRadioButton, QButtonGroup, QTextEdit, QSpinBox, QWidget, QCheckBox, QPushButton,
                               QHBoxLayout, QVBoxLayout, QLineEdit, QFormLayout, QTableWidget, QAbstractItemView, QTableWidgetItem, QMessageBox)
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as cvs
from nltk import word_tokenize, pos_tag
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer, LancasterStemmer, PorterStemmer
from string import punctuation
from sklearn.feature_extraction import text
from wordcloud import WordCloud
from refman.varsys import ICON_APP
from refman.widget import WH2
from refman.config import UserConfig
from PyQt5.QtCore import QThread

STOP_WORDS = text.ENGLISH_STOP_WORDS.union(stopwords.words('english'))
STOP_WORDS = STOP_WORDS.union({
    'plant', 'plants',
    'tree', 'trees',
    'result', 'results'})

def partialIn(w, words):
    if len(words) < 1:
        return False
    ans = False
    for x in words:
        if w.find(x) > -1:
            ans = True
            break
    return ans

def asyear(yy):
    ans = re.sub(r'\D+', '', yy)
    if ans == '':
        return 0
    else:
        return int(ans)

def getTokens(txt: str, stem: str, xwords: list):
    xwords = {w for w in xwords if w.strip() != ''}
    tt = re.sub('[%s]' % re.escape(punctuation), ' ', txt.lower())
    tt = re.sub('\w*\d+\w*', '', tt)
    tt_tokens = word_tokenize(tt)
    is_noun = lambda pos: pos[:2] == 'NN'
    tt_tokens = [word for (word, pos) in pos_tag(tt_tokens) if is_noun(pos) and len(word) > 2]
    if stem == 'none':
        ans = [w for w in tt_tokens if w not in STOP_WORDS]
    else:
        if stem == 'Snowball':
            pst = SnowballStemmer('english')
        elif stem == 'Porter':
            pst = PorterStemmer()
        else:
            pst = LancasterStemmer()
        ans = [pst.stem(w) for w in tt_tokens if w not in STOP_WORDS]
    return {x for x in ans if not partialIn(x, xwords)}

def plotWCloud(tlist: list, xwords: list):
    swords = []
    swords.extend(STOP_WORDS)
    swords.extend(xwords)
    swords = {x for x in swords}
    wc = WordCloud(stopwords=swords,
                   background_color='white',
                   colormap='Dark2',
                   max_font_size=150, random_state=50,
                   max_words=50, margin=0)
    plt.rcParams['figure.figsize'] = [16, 6]
    nn = 0
    titles = ['Title', 'Abstract']
    for ws in tlist:
        pp = wc.generate(ws)
        plt.subplot(1, 2, nn + 1)
        plt.imshow(pp, interpolation='bilinear')
        plt.axis('off')
        plt.title(titles[nn])
        nn += 1
    plt.show()

class WordCloudDialog(QDialog):
    def __init__(self, parent, data: list, xwords: list):
        super().__init__(parent)
        self.data = data
        self.exwords = xwords
        # window
        self.setWindowTitle('文献研究主题分析（词云）')
        self.setWindowIcon(QIcon(ICON_APP))
        self.setWindowFlag(QtCore.Qt.WindowType.WindowMinMaxButtonsHint)
        # container
        divset = QFrame()
        divfig = QFrame()
        uconf = UserConfig()
        sw = uconf.get('screen_w')/10
        sw = int(max(sw, 300))
        divset.setFixedWidth(sw)
        layoutmain = QHBoxLayout()
        layoutmain.setContentsMargins(0, 0, 0, 0)
        layoutmain.addWidget(divset)
        layoutmain.addWidget(divfig)
        self.setLayout(layoutmain)
        # left panel
        layoutleft = QFormLayout()
        layoutleft.setSpacing(0)
        divset.setLayout(layoutleft)
        btn1a = QRadioButton('不处理')
        btn1b = QRadioButton('Snowball')
        btn1c = QRadioButton('Porter')
        btn1d = QRadioButton('Lancaster')
        btn1a.setObjectName('none')
        btn1b.setObjectName('Lancaster')
        btn1c.setObjectName('Snowball')
        btn1d.setObjectName('Porter')
        btn1a.setChecked(True)
        self.group_stem = QButtonGroup(self)
        self.group_stem.addButton(btn1a)
        self.group_stem.addButton(btn1b)
        self.group_stem.addButton(btn1c)
        self.group_stem.addButton(btn1d)
        lbx1 = WH2('词干提取方法')
        layoutleft.addRow(lbx1)
        layoutleft.addRow(btn1a)
        layoutleft.addRow(btn1b)
        layoutleft.addRow(btn1c)
        layoutleft.addRow(btn1d)
        # ------------
        years = [asyear(x.get('year', '')) for x in data]
        years = [x for x in years if x > 0]
        yearmin = min(years)
        yearmax = max(years)
        self.yearstart = QSpinBox()
        self.yearstart.setRange(yearmin, yearmax)
        self.yearstart.setValue(yearmin)
        self.yearend = QSpinBox()
        self.yearend.setRange(yearmin, yearmax)
        self.yearend.setValue(yearmax)
        lbx = WH2('分析年度')
        layoutleft.addRow(lbx)
        layoutleft.addRow('起始年度', self.yearstart)
        layoutleft.addRow('结束年度', self.yearend)
        # ------------
        self.yearseg = QSpinBox()
        self.yearseg.setRange(1, 10)
        self.yearseg.setValue(1)
        layoutleft.addRow('年度分段', self.yearseg)
        # ------------
        layoutleft.addRow(WH2('排除关键词'))
        self.xwords = QTextEdit()
        layoutleft.addRow(self.xwords)
        # ------------
        self.includeKeys = QCheckBox('包含查询关键词')
        self.includeKeys.setChecked(False)
        layoutleft.addRow(self.includeKeys)
        # ------------
        self.figcol = QSpinBox()
        self.figcol.setRange(1, 6)
        self.figcol.setValue(1)
        layoutleft.addRow('绘图列数', self.figcol)
        # ------------
        btnPlot = QPushButton('分析/绘图')
        layoutleft.addRow('  ', QWidget())
        layoutleft.addRow(btnPlot)
        # ----------------------
        btnPlot.clicked.connect(self.plot)
        # right panel
        layoutright = QVBoxLayout()
        divfig.setLayout(layoutright)
        self.figure = plt.Figure()
        self.canvas = cvs(self.figure)
        layoutright.addWidget(self.canvas)

    def plot(self):
        swords = self.xwords.toPlainText().strip()
        swords = re.split(r'\s+', swords)
        if not self.includeKeys.isChecked():
            swords.extend(self.exwords)
        stem = self.group_stem.checkedButton().objectName()
        y1 = self.yearstart.value()
        y2 = self.yearend.value()
        year1 = min(y1, y2)
        year2 = max(y1, y2)
        nseg = self.yearseg.value()
        yval = (year2 - year1 + 1)/nseg
        wss = []
        for i in range(nseg):
            yx1 = year1 + i*yval
            yx2 = yx1 + yval - 1
            dtx = [(x.get('title'), x.get('abstract'))
                    for x in self.data
                    if yx1 <= asyear(x.get('year', '')) <= yx2]
            txt1 = [getTokens(x[0], stem, swords) for x in dtx]
            txt2 = [getTokens(x[1], stem, swords) for x in dtx]
            txt1 = [" ".join(x) for x in txt1]
            txt2 = [" ".join(x) for x in txt2]
            txts = [' '.join(txt1), ' '.join(txt2)]
            for kk, vv in zip(['Title', 'Abstract'], txts):
                ws = vv.strip()
                if ws != '':
                    title = "%s: %d~%d" %(kk, yx1, yx2)
                    wss.append({'text': ws, 'title': title})
        # TODO: 先获取ws列表,再计算行列数
        wc = WordCloud(stopwords=STOP_WORDS,
                       background_color='white',
                       colormap='Dark2',
                       max_font_size=150, random_state=50,
                       max_words=50, margin=0)
        nfigs = len(wss)
        ncol = self.figcol.value()
        nrow = nfigs//ncol
        nrow = nrow + 1 if ncol*nrow < nfigs else nrow
        self.figure.clear()
        ndx = 0
        fdict = {'fontsize': 20, 'fontweight': 600, 'color': '#666666'}
        for dd in wss:
            gg = self.figure.add_subplot(nrow, ncol, ndx + 1)
            gg.set_title(dd.get('title'), fontdict=fdict, loc='left')
            gg.axis('off')
            pp = wc.generate(dd.get('text'))
            gg.imshow(pp, interpolation='bilinear')
            ndx += 1
        self.canvas.draw()


exwords = text.ENGLISH_STOP_WORDS.union(stopwords.words('english'))
def hasStopWords(word):
    words = {x for x in re.split(r'[ -]+', word)}
    ans = words.intersection(exwords)
    return len(ans) > 0

class ThreadWordCount(QThread):
    """ 数据库无关键词查询"""
    ready = QtCore.pyqtSignal(list)
    def __init__(self, data: list=[], kstr: str=''):
        super().__init__()
        self.data = data
        self.keywords = kstr.strip()

    def run(self):
        kwd = re.sub(r'\s+', ' ', self.keywords)
        patts = [
            f'\\b[a-z]*{kwd}[a-z]*\\b',
            f'[a-z]+[ -]+{kwd}[a-z]*\\b',
            f'[a-z]+[ -]+[a-z]+[ -]+{kwd}[a-z]*\\b',
            f'[a-z]+[ -]+[a-z]+[ -]+[a-z]+[ -]+{kwd}[a-z]*\\b',
            f'\\b{kwd}[a-z]*[ -]+[a-z]+[ -]+[a-z]+[ -]+[a-z]+',
            f'\\b{kwd}[a-z]*[ -]+[a-z]+[ -]+[a-z]+',
            f'\\b{kwd}[a-z]*[ -]+[a-z]+']
        words = []
        for bib in self.data:
            txt = bib.get('abstract', '')
            ans = set()
            for pp in patts:
                anx = {x for x in re.findall(pp, txt)}
                ans = ans.union(anx)
            if len(ans) > 0:
                words.extend([x for x in ans])
        keywords = {x for x in words if x != ''}
        kdict = {k: words.count(k) for k in keywords if not hasStopWords(k)}
        kdict = {k: "{:0>3d}".format(v) for k,v in kdict.items()}
        counts = {x for x in kdict.values()}
        counts = [x for x in counts]
        counts.sort()
        counts.reverse()
        result = []
        for cc in counts:
            ans = [k for k,v in kdict.items() if v == cc and k != '']
            if len(ans) < 1:
                continue
            ans.sort()
            result.append([cc, ", ".join(ans)])
        self.ready.emit(result)

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
        # self.btnrun = QPushButton('分析')
        # self.btnrun.setFixedWidth(100)
        # self.btnrun.clicked.connect(self.statKeywords)
        layoutInput.addWidget(self.kwdinput)
        layoutInput.addWidget(self.withAll)
        # layoutInput.addWidget(self.btnrun)
        layoutMain.addRow(layoutInput)
        self.wc = None
        self.kwdinput.setFocus()

    def drawTable(self, result: list):
        self.table.clear()
        if len(result) < 1:
            # QMessageBox.warning(self, '错误', '无效统计！')
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
        keywords = self.kwdinput.text().strip()
        if keywords == '' or hasStopWords(keywords):
            QMessageBox.warning(self, '警告', '无意义关键词！')
            return False
        if self.withAll.isChecked():
            data = self.data[1]
        else:
            data = self.data[0]
        if not self.wc:
            self.wc = ThreadWordCount(data, keywords)
        elif self.wc.isRunning():
            return False
        elif self.wc.isFinished():
            self.wc.deleteLater()
            time.sleep(1)
            self.wc = ThreadWordCount(data, keywords)
        self.wc.start()
        self.wc.ready.connect(self.drawTable)
