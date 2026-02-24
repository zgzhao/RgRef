import platform
import sys, re, os.path, shutil, json
from PyQt5 import QtCore
from PyQt5.QtWidgets import (QDialog, QLineEdit, QSpinBox, QFormLayout, QVBoxLayout, QHBoxLayout, QSplitter, QFrame,
                             QPushButton, QWidget, QFileDialog, QCheckBox, QColorDialog, QAction, QRadioButton, QComboBox)
from PyQt5.QtGui import QIcon, QFont
from refman.varsys import *

def setDesktopFile():
    if platform.system() != 'Linux':
        return False
    pid = os.popen('which python')
    python = pid.read().strip()
    home_dir = os.path.expandvars('$HOME')
    dfile = os.path.join(home_dir, '.local/share/applications/', 'RgRef.desktop')
    if not os.path.exists(dfile) and python != '':
        with open(dfile, 'w') as f:
            contents = ['[Desktop Entry]',
                        'Type = Application',
                        'Name = ripgrep Reference Manager',
                        'Comment = 基于ripgrep的文献管理器',
                        f'Icon = {DIR_APP}/images/ppmb.png',
                        'Terminal = false',
                        f'Exec = {python} {DIR_APP}/RgRef.py',
                        'Categories = Office;']
            f.write('\n'.join(contents))
    #
class UserConfig(dict):
    def __init__(self):
        super().__init__()
        self.conf_dir = os.path.expandvars('$HOME/.RgRef')
        self.conf_file = os.path.join(self.conf_dir, 'config.json')
        self.update({
            'dir_user': self.conf_dir,
            'screen_w': 800,
            'screen_h': 600,
            'font_size_basic': 12,
            'font_size_html': 12,
            'font_size_table': 10,
            'table_width_col1': 80,
            'table_width_col2': 200,
            'table_width_col3': 400,
            'table_width_col4': 600,
            'table_width_col5': 800,
            'table_width_col6': 80,
            'pubmed_key': ''
        })
        if os.path.exists(self.conf_file):
            with open(self.conf_file, 'r', encoding='utf-8') as f:
                self.update(json.load(f))
        else:
            self.save()
        ##
        usrdir = self.get('dir_user')
        if usrdir == "":
            usrdir = self.conf_dir
        dir_meta = os.path.join(usrdir, 'meta')
        self.update({'dir_meta': dir_meta})
        if not os.path.exists(usrdir):
            os.mkdir(usrdir)
        if not os.path.exists(dir_meta):
            os.mkdir(dir_meta)
        if not os.path.exists(self.conf_dir):
            os.mkdir(self.conf_dir)
        ##
    def save(self):
        with open(self.conf_file, 'w', encoding='utf-8') as f:
            json.dump(self, f, ensure_ascii=False, indent=4)
class EditorConfig(QDialog):
    signalSaved = QtCore.pyqtSignal(bool)
    def __init__(self):
        super().__init__()
        self.setModal(True)
        self.setWindowTitle('系统设置')
        self.setWindowIcon(QIcon(ICON_APP))
        self.setWindowFlags(QtCore.Qt.WindowType.WindowTitleHint |
                            QtCore.Qt.WindowType.WindowCloseButtonHint)
        self.setContentsMargins(0,0,0,0)
        # container
        self.uconf = UserConfig()
        sw = self.uconf.get('screen_w')/3
        sh = self.uconf.get('screen_h')/3
        sw = int(max(sw, 800))
        sh = int(max(sh, 600))
        self.setFixedSize(sw, sh)
        self.conf_file = self.uconf.conf_file
        ##
        panel1 = QFormLayout()
        panel1.setFormAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        panel1.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        label1 = ['用户目录', 'Kokoro-82M目录', 'pdfannots程序', 'pdfjs viewer', 'PubMed API key', '评分底色']
        item1 = ['dir_user', 'dir_kokoro', 'pdfannots', 'pdfviewer', 'pubmed_key', 'rank_color']
        for lbx,itx in zip(label1, item1):
            wgt = QLineEdit()
            val = self.uconf.get(itx, '')
            wgt.setText(str(val))
            wgt.setObjectName('CONFIGTXT' + itx)
            if itx == 'dir_user' or itx=='dir_kokoro':
                iconOpen= QAction(wgt)
                iconOpen.setIcon(QIcon(ICON_FOLDER_OPEN))
                wgt.addAction(iconOpen, QLineEdit.ActionPosition.TrailingPosition)
                if itx == 'dir_user':
                    iconOpen.triggered.connect(self.getDirUser)
                else:
                    iconOpen.triggered.connect(self.getDirKokoro)
            elif itx == 'pdfannots':
                iconOpen= QAction(wgt)
                iconOpen.setIcon(QIcon(ICON_FILE_OPEN))
                wgt.addAction(iconOpen, QLineEdit.ActionPosition.TrailingPosition)
                iconOpen.triggered.connect(self.getPathPDFanno)
            elif itx == 'pdfviewer':
                iconOpen = QAction(wgt)
                iconOpen.setIcon(QIcon(ICON_FILE_OPEN))
                wgt.addAction(iconOpen, QLineEdit.ActionPosition.TrailingPosition)
                iconOpen.triggered.connect(self.getPathPDFviewer)
            elif itx == 'rank_color':
                iconOpen= QAction(wgt)
                iconOpen.setIcon(QIcon(ICON_COLOR))
                wgt.addAction(iconOpen, QLineEdit.ActionPosition.TrailingPosition)
                iconOpen.triggered.connect(self.getColor)
            panel1.addRow(lbx, wgt)
        wgt = QCheckBox('应用评分颜色')
        val = True if int(self.uconf.get('color_apply_rank', 1)) > 0 else False
        wgt.setChecked(val)
        wgt.setObjectName('CONFIGCHK' + 'color_apply_rank')
        panel1.addRow('', wgt)
        # 查询模式
        wgt = QCheckBox('全文匹配')
        val = True if int(self.uconf.get('fulltext_search', 0)) > 0 else False
        wgt.setChecked(val)
        wgt.setObjectName('CONFIGCHK' + 'fulltext_search')
        panel1.addRow('文献查询模式', wgt)
        # 数字类型
        panel2 = QFormLayout()
        labls = ['基本字体', '表格字体']
        items = ['font_size_basic', 'font_size_table']
        for lbx,itx in zip(labls, items):
            wgt = QSpinBox()
            wgt.setObjectName('CONFIGNUM' + itx)
            val = self.uconf.get(itx, 10)
            wgt.setValue(val)
            wgt.setMinimum(6)
            wgt.setMaximum(60)
            if lbx == '基本字体':
                wgt.setToolTip('修改基本字体需重启程序生效！')
            panel2.addRow(lbx, wgt)
        ##
        wgt = QComboBox()
        wgt.setObjectName('CONFIGCMB' + 'kokoro_voice')
        wgt.setToolTip('选择`Kokoro-82M`语音模型')
        dir_kk = self.uconf.get("dir_kokoro", "")
        if os.path.isdir(dir_kk):
            pts = os.listdir(os.path.join(dir_kk, "voices"))
            pts = [re.sub(r'\.pt$', '', x)
                   for x in pts if re.search(r'\.pt$', x)]
            pts.sort()
        else:
            pts = ['af_heart', 'bf_alice', 'zf_xiaoyi']
        for x in pts:
            wgt.addItem(x)
        val = self.uconf.get('kokoro_voice', 'af_heart')
        wgt.setCurrentText(val)
        panel2.addRow('语音模型', wgt)
        # ----------------------------------
        panel2.addRow(QSplitter())
        self.btnSave = QPushButton(QIcon(ICON_SAVE), '保存更改')
        panel2.addRow(self.btnSave)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(QFrame())
        self.layout().addWidget(QFrame())
        self.layout().itemAt(0).widget().setLayout(panel1)
        self.layout().itemAt(1).widget().setLayout(panel2)
        self.btnSave.clicked.connect(self.save)
    def close(self):
        self.hide()
    def getFilePath(self, cname: str, ft: str=None):
        xname = f'CONFIGTXT{cname}'
        wgt = self.findChild(QLineEdit, xname)
        info = QFileDialog.getOpenFileName(None, '选择文件', wgt.text(), ft)
        if info[0]:
            wgt.setText(info[0])
    def getFolder(self, cname: str):
        xname = f'CONFIGTXT{cname}'
        wgt = self.findChild(QLineEdit, xname)
        udir = QFileDialog.getExistingDirectory(None, '选择目录', wgt.text())
        if udir:
            wgt.setText(udir)
    def getDirUser(self):
        self.getFolder('dir_user')
    def getDirKokoro(self):
        self.getFolder('dir_kokoro')
    def getPathPDFanno(self):
        self.getFilePath('pdfannots')
    def getPathPDFviewer(self):
        self.getFilePath('pdfviewer', "html(*.html)")
    def getColor(self):
        wgt = self.findChild(QLineEdit, "CONFIGTXTrank_color")
        color = QColorDialog().getColor()
        if color.isValid():
            wgt.setText(color.name())
    def save(self):
        setDesktopFile()
        ## 使用正则表达式查询控件名称以获取控件
        wgts = self.findChildren(QWidget, QtCore.QRegularExpression('^CONFIG'))
        for itx in wgts:
            name = itx.objectName()
            if re.match('^CONFIGCMB', name):
                key = re.sub('^CONFIGCMB', '', name)
                val = itx.currentText()
                self.uconf.update({key: val})
            if re.match('^CONFIGCHK', name):
                key = re.sub('^CONFIGCHK', '', name)
                val = 1 if itx.isChecked() else 0
                self.uconf.update({key: val})
            if re.match('^CONFIGTXT', name):
                key = re.sub('^CONFIGTXT', '', name)
                val = itx.text()
                self.uconf.update({key: val})
            if re.match('^CONFIGNUM', name):
                key = re.sub('^CONFIGNUM', '', name)
                val = itx.value()
                self.uconf.update({key: val})
        ## save data and exit
        self.uconf.save()
        self.signalSaved.emit(True)
        self.hide()
def setFontSize(t: str='basic'):
    fontsize = UserConfig().get(f'font_size_{t}', 18)
    font = QFont()
    font.setPointSize(fontsize)
    return font
