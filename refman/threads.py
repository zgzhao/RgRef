import subprocess
import time, os.path, re
from PyQt5 import QtCore
from PyQt5.QtCore import QThread
from refman.bibtex import (RGBKeySearch, RGPipeSearch, RGExtSearch, RGvipSentences, getSpringerByDOI, parseSpringDOIs,
                           doisPresented, requestAbstract, BibitemActive, ListActiveBitems, readMarked)
from refman.functions import unlist, readLines, pdfAnnoGet, pdfAnnoTidy, runCMD, text2md5
from refman.config import UserConfig
from refman.speech import abstract2mp3

# 线程的生命周期包括创建、就绪、运行和终止四个阶段。线程创建后，会进入就绪状态，等待系统调度它的执行；
# 当线程获得CPU时间片后，就会进入运行状态，执行相应的任务；当任务执行完成或发生异常时，线程将进入终止状态。
# NOTE: 在终止状态下的线程对象，不能再次被调度执行任务
# 因此，我们需要确保及时销毁终止的线程对象

def runXSearch(gname: str, keywords: list=None, searchin: str='bibtex'):
    if gname == 'Marked':
        return ThreadGetMarked()
    elif gname == 'Find sents':
        return ThreadVipSentences(gname, keywords)
    else:
        ## key, pipe or ext search
        return ThreadKeywordSearch(gname, keywords, searchin)
class ThreadGetMarked(QThread):
    ready = QtCore.pyqtSignal(dict)
    def __init__(self):
        super().__init__()
        self.tstart = time.perf_counter()
    def run(self):
        blist = readMarked()
        ans = {'gname': 'Marked', 'blist': blist, 'time': time.perf_counter() - self.tstart}
        self.ready.emit(ans)
class ThreadKeywordSearch(QThread):
    ## NOTE: 仅查询bibtex目录
    ready = QtCore.pyqtSignal(dict)
    def __init__(self, gname: str, klist: list, searchin: str='bibtex'):
        super().__init__()
        self.keywords = klist
        self.gname = gname
        self.searchin = searchin
        self.tstart = time.perf_counter()
    def run(self):
        if self.searchin == 'bibkey':
            blist = RGBKeySearch(self.keywords)
        elif self.searchin == 'bibtex':
            blist = RGPipeSearch(self.keywords)
        else:
            blist = RGExtSearch(self.keywords)
        ans = {'gname': self.gname, 'blist': blist, 'time': time.perf_counter() - self.tstart}
        self.ready.emit(ans)
class ThreadSpringDownload(QThread):
    ready = QtCore.pyqtSignal(dict)
    def __init__(self, fp: str):
        super().__init__()
        self.tstart = time.perf_counter()
        self.dois = parseSpringDOIs(fp)
    def run(self):
        edois = doisPresented()
        xdois = self.dois.difference(edois)
        blist = []
        if len(xdois) > 0:
            for doi in xdois:
                ans = getSpringerByDOI(doi)
                blist.extend(ans)
        ans = {'blist': blist, 'time': time.perf_counter() - self.tstart}
        self.ready.emit(ans)
class ThreadGetAbstract(QThread):
    ready = QtCore.pyqtSignal(dict)
    def __init__(self, data: dict):
        super().__init__()
        self.bibkey = data.get('bibkey')
        self.doi = data.get('doi')
    def run(self):
        ans = requestAbstract(self.doi)
        self.ready.emit({'bibkey': self.bibkey, 'abstract': ans})
class ThreadVipSentences(QThread):
    ready = QtCore.pyqtSignal(dict)
    def __init__(self, gname: str, keywords: list):
        super().__init__()
        self.gname = gname
        self.tstart = time.perf_counter()
        self.keywords = keywords
    def run(self):
        blist = RGvipSentences(self.keywords)
        ans = {'gname': self.gname, 'blist': blist, 'time': time.perf_counter() - self.tstart}
        self.ready.emit(ans)
class ThreadSaveBitems(QThread):
    ready = QtCore.pyqtSignal(list)
    def __init__(self, bitems: list, overwrite: bool):
        super().__init__()
        self.bitems = [BibitemActive(x) for x in bitems]
        self.overwrite = overwrite
    def run(self):
        counts = 0
        for x in self.bitems:
            if x.save(self.overwrite):
                x.updateSentFile()
                counts += 1
        ans = [f'操作完成，保存记录{counts}条！', 'ok']
        self.ready.emit(ans)
class ThreadGetPDFanno(QThread):
    ready = QtCore.pyqtSignal(list)
    def __init__(self, bitem: BibitemActive, force: bool=False):
        super().__init__()
        self.bitem = bitem
        self.forceUpdate = force
    def run(self):
        ans = []
        pdfs = self.bitem.files()
        if len(pdfs) < 1:
            self.ready.emit(ans)
        else:
            bkey = self.bitem.get('bibkey')
            udir = UserConfig().get('dir_user')
            mdf = os.path.join(udir, 'notes', f'{bkey}@file.md')
            updated = 10
            if os.path.exists(mdf):
                updated = sum([1 if os.path.getmtime(fx) > os.path.getmtime(mdf) else 0  for fx in pdfs])
            if updated > 0 or self.forceUpdate:
                ans = [pdfAnnoGet(fx) for fx in pdfs]
                ans = unlist(ans)
                with open(mdf, 'w') as f:
                    f.write('\n'.join(ans))
            else:
                ans = readLines(mdf)
        ans = pdfAnnoTidy(ans)
        self.ready.emit(ans)
class ThreadCheckPDFanno(QThread):
    ready = QtCore.pyqtSignal(bool)
    def __init__(self, blist: ListActiveBitems):
        super().__init__()
        self.blist = blist
    def run(self):
        udir = UserConfig().get('dir_user')
        for bitem in self.blist:
            pdfs = bitem.files()
            if len(pdfs) < 1:
                continue
            bkey = bitem.get('bibkey')
            mdf = os.path.join(udir, 'notes', f'{bkey}@file.md')
            updated = 10
            if os.path.exists(mdf):
                updated = sum([1 if os.path.getmtime(fx) > os.path.getmtime(mdf) else 0  for fx in pdfs])
            if updated < 1:
                continue
            ans = [pdfAnnoGet(fx) for fx in pdfs]
            ans = unlist(ans)
            with open(mdf, 'w') as f:
                f.write('\n'.join(ans))
        self.ready.emit(True)
class ThreadMakeMP3(QThread):
    ready = QtCore.pyqtSignal(dict)
    def __init__(self, bitem: BibitemActive):
        super().__init__()
        self.bitem= bitem
    def run(self):
        bkey = self.bitem.get('bibkey')
        title = self.bitem.get('title', '').strip()
        abstract = self.bitem.get('abstract', '').strip()
        if not title.endswith("."):
            title += "."
        if not abstract.endswith("."):
            abstract += "."
        txt = f'{title} Abstract: {abstract}'
        mp3file = None
        md5name = None
        try:
            mp3file = abstract2mp3(txt, bkey=bkey)
            md5name = text2md5(mp3file)
        except SystemError:
            print("系统错误，可能GPU显存不足！")
        ans = {'bibkey': bkey, 'md5name': md5name, 'mp3file': mp3file}
        self.ready.emit(ans)
