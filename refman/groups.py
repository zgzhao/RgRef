import os.path, re
from PyQt5 import QtCore
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QFrame, QLineEdit, QFormLayout, QHBoxLayout, QVBoxLayout, QPushButton, QMessageBox, QCheckBox
from refman.varsys import ICON_APP
from refman.functions import readLines, inList
from refman.config import UserConfig
GROUPFIELDS = ['name', 'title', 'journal', 'abstract', 'author']

class BibGroups:
    def __init__(self, file_path: str=None):
        if file_path and os.path.exists(file_path):
            self.gfile = file_path
        else:
            uconf = UserConfig()
            udir = uconf.get('dir_user')
            self.gfile = f'{udir}/meta/groups.txt'
        self.data = {}
        if os.path.exists(self.gfile):
            patt = re.compile(r'^\d+@([^#]+)#(.+)$')
            lls = [x for x in readLines(self.gfile) if patt.search(x)]
            ans = {patt.sub(r'\1', x): patt.sub(r'\2', x) for x in lls}
            self.data = {k: v for k, v in ans.items() if re.search(r'\w+', v)}
        pass

    def update(self, dt: dict):
        self.data.update(dt)
    def delete(self, gname: str):
        try:
            self.data.pop(gname)
        finally:
            return True
    def save(self):
        try:
            gnames = [x for x in self.data.keys()]
            gnames.sort()
            contents = [f'{k}#{v}' for k, v in self.data.items()]
            contents.sort()
            contents = [f'{i + 1}@'+contents[i] for i in range(len(contents))]
            contents =  '\n'.join(contents)
            with open(self.gfile, 'w') as f:
                f.write(contents)
                f.close()
            return True
        except SystemError:
            return False
    # end of BibGroups definition

class GroupEdit(QDialog):
    ## edit list data of groups only
    updated = QtCore.pyqtSignal(str)
    def __init__(self, parent, groupName: str=''):
        super().__init__(parent)
        #
        self.setWindowTitle('文献分组设置')
        self.setWindowIcon(QIcon(ICON_APP))
        self.setToolTip('输入规则：关键词间用分号或竖线分隔\n查询规则：同组关键词使用“或”、不同组关键词用“与”查询')
        # Dialog UI settings
        uconf = UserConfig()
        sw = uconf.get('screen_w')/3
        sh = uconf.get('screen_h')/3
        sw = int(max(sw, 800))
        sh = int(max(sh, 600))
        self.setFixedSize(sw, sh)
        # data containers
        self.myGroups = BibGroups()
        self.currentGroupName = groupName.strip()
        self.currentGroupData = self.myGroups.data.get(self.currentGroupName, {})
        ##
        form = QFrame(self)
        form.setFixedSize(self.width()-10, self.height()-10)
        form.setContentsMargins(20, 40, 20, 20)
        layout = QFormLayout()
        layout.setSpacing(20)
        layout.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        form.setLayout(layout)
        self.newGroupName = QLineEdit(self)
        self.newGroupName.setObjectName('gname')
        self.newGroupName.setStyleSheet('font-weight: bold; color: red;')
        layout.addRow('分组名称：', self.newGroupName)
        for i in range(6):
            wgt = QLineEdit(self)
            wgt.setObjectName(f'kstring{i}')
            layout.addRow(f'关键词 {i}：', wgt)
        # buttons
        btnLayout = QHBoxLayout()
        btnLayout.setSpacing(40)
        if self.currentGroupName == '':
            btnNew = QPushButton('新建')
            btnLayout.addWidget(btnNew)
            btnNew.clicked.connect(self.newGroup)
        else:
            btnDelete = QPushButton('删除')
            btnLayout.addWidget(btnDelete)
            btnDelete.clicked.connect(self.deleteGroup)
            btnUpdate = QPushButton('更新')
            btnLayout.addWidget(btnUpdate)
            btnUpdate.clicked.connect(self.save)
        layout.addRow('', btnLayout)
        self.setInputs()
    def clearInputs(self):
        for w in self.findChildren(QLineEdit):
            w.setText('')
    def validGroupName(self):
        xname = self.newGroupName.text().strip().lower()
        if inList(xname, ['', 'all references', 'marked', 'find free', 'find sents', 'imported']):
            QMessageBox.warning(self, '警告', '非法分组名称！')
            return False
        return True
    def getInputs(self):
        ans = {}
        if not self.validGroupName():
            return ans
        kwds = []
        gname = None
        for w in self.findChildren(QLineEdit):
            val = w.text().strip()
            if re.search(r'[()|{}\\+.?]', val, flags=re.I):
                QMessageBox.warning(self, '警告', '分组名称和关键词不允许使用特殊字符！')
                return ans
            if val != '':
                val = re.sub(r'\s+', ' ', val)
                if w.objectName() == 'gname':
                    gname = val
                else:
                    kwds.append(val)
        if not gname or len(kwds) < 1:
            return ans
        kwds = "#".join(kwds)
        ans.update({gname: kwds})
        return ans
    def setInputs(self):
        kwds = self.myGroups.data.get(self.currentGroupName)
        self.newGroupName.setText(self.currentGroupName)
        if kwds:
            kwds = [x.strip() for x in kwds.split('#')]
            kwds = [x for x in kwds if x != '']
            for i in range(len(kwds)):
                wgt = self.findChild(QLineEdit, f'kstring{i}')
                if wgt:
                    wgt.setText(kwds[i])
        else:
            self.clearInputs()
    def deleteGroup(self):
        self.myGroups.delete(self.currentGroupName)
        if self.myGroups.save():
            self.updated.emit('')
            self.close()
        else:
            QMessageBox.warning(self, '警告', '分组保存失败！')

    def updateGroup(self):
        new_data = self.getInputs()
        if len(new_data) < 1:
            return False
        ## 先删除再添加！！
        if self.currentGroupName != '':
            self.myGroups.delete(self.currentGroupName)
        self.currentGroupName = self.newGroupName.text().strip()
        self.myGroups.update(new_data)
        return True
        #
    def save(self):
        if self.updateGroup() and self.myGroups.save():
            self.updated.emit(self.currentGroupName)
    def newGroup(self):
        self.hide()
        self.save()
        self.close()


class GroupDelete(QDialog):
    deleted = QtCore.pyqtSignal(str)
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle('删除文献分组')
        self.setWindowIcon(QIcon(ICON_APP))
        self.setBaseSize(600, 400)
        # data containers
        self.myGroups = BibGroups()
        ##
        left_frame = QFrame()
        right_frame = QFrame()
        layout_left = QVBoxLayout(left_frame)
        layout_right = QVBoxLayout(right_frame)
        layout_btn = QHBoxLayout()
        # 2. 上半部分：水平等分
        h_layout = QHBoxLayout()
        h_layout.addWidget(left_frame, 1)  # 1:1 拉伸
        h_layout.addWidget(right_frame, 1)
        h_layout.setContentsMargins(0, 0, 0, 0)
        # 3. 整个窗口：垂直 3:1
        v_layout = QVBoxLayout(self)
        v_layout.addLayout(h_layout, 3)  # 3 份
        v_layout.addLayout(layout_btn, 1)  # 1 份
        v_layout.setContentsMargins(0, 0, 0, 20)
        ##
        btnDelete = QPushButton('删除选定分组')
        layout_btn.addSpacing(100)
        layout_btn.addWidget(btnDelete)
        layout_btn.addSpacing(100)
        i = 0
        for gname in self.myGroups.data.keys():
            i += 1
            wgt = QCheckBox(gname)
            wgt.setObjectName(gname)
            if i % 2 == 1:
                layout_left.addWidget(wgt)
            else:
                layout_right.addWidget(wgt)
        btnDelete.clicked.connect(self.deleteGroups)
    def deleteGroups(self):
        reply = QMessageBox.warning(
            self, '警告', '删除分组不可回复，是否继续删除？',
            QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes)
        if reply != QMessageBox.StandardButton.Yes:
            return False
        for w in self.findChildren(QCheckBox):
            if w.isChecked():
                gname = w.objectName()
                self.myGroups.delete(gname)
            if self.myGroups.save():
                self.deleted.emit("All references")
                self.close()
