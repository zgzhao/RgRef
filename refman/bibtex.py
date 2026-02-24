import html, xml.dom.minidom
import os, re, time, math, requests
import pandas as pd
from nltk.tokenize import sent_tokenize
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QDialog, QLineEdit, QLabel, QWidget, QMessageBox, QPushButton, QFormLayout, QHBoxLayout
from refman.config import UserConfig
from refman.widget import popwarning
from refman.functions import readLines, inList, unlist, listuniq, runCMD, pdf2text, colorKeywords, l2set, s2list, formatRegKeyword
from refman.ripgrep import rgPipeFind, rgExtFind, rgBkeyFind
from refman.journal import journal2issn, issn2abbr

USR_CNF = UserConfig()
USR_DIR = USR_CNF.get('dir_user')
PDF_DIR = os.path.join(USR_DIR, 'pdf')
TXT_DIR = os.path.join(USR_DIR, 'fulltext')
SEN_DIR = os.path.join(USR_DIR, 'stoken')
BIB_DIR = os.path.join(USR_DIR, 'bibtex')

MAX_PAGE_LEN = 6
PmdFields = {
    'title': ['TI', 'JT'],
    'issn': ['IS'],
    'journal': ['TA', 'JT'],
    'author': ['FAU', 'AU'],
    'abstract': ['AB'],
    'institution': ['AD'],
    'year': ['PY', 'DP'],
    'volume': ['VI'],
    'issue': ['IP'],
    'pages': ['PG'],
    'doi': ['AID', 'LID'],
    'PMID': ['PMID']
}
PmdExtra = {
    'issn': [r'^(\d+)(-[^ ]+) *.*$', r'\1\2'],
    'year': [r'^(\d{4}) *.*$', r'\1'],
    'doi':  [r'^(.*doi\.org/)*(\d+\.\d+/\S+).*$', r'\2']
}
RisFields = {
    'title': ['TI', 'T1', 'ST'],
    'issn': ['SN'],
    'journal': ['JA', 'J1', 'J2', 'JF', 'JO', 'T2'],
    'author': ['AU', 'A1', 'A2', 'A3', 'A4'],
    'abstract': ['AB', 'N1'],
    'keywords': ['KW'],
    'institution': ['AD'],
    'year': ['PY', 'DA'],
    'volume': ['NL'],
    'issue': ['IS'],
    'startpage': ['SP'],
    'endpage': ['EP'],
    'doi': ['DO', 'UR']
}
CnkiFields = {
    'title': ['Title'],
    'journal': ['Source'],
    'author': ['Author'],
    'institution': ['Organ'],
    'keyword': ['Keyword'],
    'abstract': ['Summary'],
    'pages': ['PageCount'],
    'year': ['Year'],
    'volume': ['Volume'],
    'issue': ['Peroid'],
    'issn': ['ISSN'],
    'doi': ['DOI']
}
RisExtra = {
    'issn': [r'^(\d+)(-[^ ]+) *.*$', r'\1\2'],
    'year': [r'^(\d{4}) *.*$', r'\1'],
    'doi':  [r'^(.*doi\.org/)*(\d+\.\d+/\S+).*$', r'\2']
}

class ListActiveBitems(list):
    def __init__(self, blist: list= None):
        super().__init__()
        self.clear()
        self.extend(blist)
    def append(self, bitem: dict):
        ekeys = self.bibkeys()
        xkey = bitem.get('bibkey')
        if inList(xkey, ekeys):
            ndx = self.keyIndex(xkey)
            self[ndx].update(bitem)
        else:
            xitem = BibitemActive(bitem)
            self.insert(len(self), xitem)
    def extend(self, blist: list):
        if not blist:
            return None
        for bitem in blist:
            self.append(bitem)
    def removeByKey(self, bkey):
        ndx = self.keyIndex(bkey)
        if ndx < 0:
            return False
        self.remove(self[ndx])
    def deleteByKey(self, bkey):
        xitem = self.bitem(bkey)
        if not isinstance(xitem, BibitemActive):
            return 0
        if xitem.deleteBibFiles():
            print(f"{bkey} removed.")
            self.removeByKey(bkey)
            return 1
        else:
            return 0
    def bitem(self, bkey):
        return self[self.keyIndex(bkey)]
    def bitems(self, bkeys):
        if isinstance(bkeys, set):
            bkeys = [x for x in bkeys]
        ans = [x for x in self if inList(x.get('bibkey'), bkeys)]
        return ans
    def bibkeys(self):
        return [x.get('bibkey') for x in self]
    def keyIndex(self, bkey: str):
        bkeys = self.bibkeys()
        if inList(bkey, bkeys):
            return bkeys.index(bkey)
        else:
            return -1
    def update(self, blist: list):
        if len(blist) < 1 or not isinstance(blist, list):
            return False
        for xitem in blist:
            bkey = xitem.get('bibkey')
            ndx = self.keyIndex(bkey)
            if ndx >= 0:
                self[ndx].update(xitem)
                self[ndx].save()
class BibitemActive(dict):
    def __init__(self, bitem: dict=None):
        super().__init__()
        if isinstance(bitem, dict):
            self.update(bitem)
    def filepath(self, st: str, bkey: str=None):
        if not bkey:
            bkey = self.bibkey()
        UDIR = UserConfig().get('dir_user')
        if st == 'pdf' or st == 'speech':
            ans = os.path.join(UDIR, st)
        else:
            if bkey:
                year = re.sub(r'^(\d+)-.*$', r'\1', bkey)
            else:
                year = '0000'
            ans = os.path.join(UDIR, st, year)
        return ans
    def save(self, overwrite: bool=True):
        bibkey = self.get('bibkey')
        if not bibkey:
            return False
        fdir = self.filepath('bibtex')
        bfile = os.path.join(fdir, f'{bibkey}.txt')
        if not overwrite and os.path.exists(bfile):
            return False
        elif not os.path.exists(fdir):
            os.mkdir(fdir)
        patt = re.compile(r'^(oldkey|fulltext|sentences|files|impact|highlight|note)', re.I)
        bitem = {k: str(v).strip() for k, v in self.items() if not patt.search(k) and not isinstance(v, list)}
        bitem = {k:v for k,v in bitem.items() if v != ''}
        fkeys = ['bibkey', 'title', 'journal']
        contents = [f'{k}=' + bitem.get(k, '') for k in fkeys]
        contents.extend([f'{k}=' + re.sub(r'\n', ' ', v)
                         for k, v in bitem.items() if not inList(k, fkeys)])
        contents = '\n'.join(contents) + '\n'
        with open(bfile, 'w') as f:
            f.write(contents)
            self.updateSentFile()
        return True
    def str4search(self):
        bkey = self.get('bibkey', 'NOKEY')
        ans = [bkey, self.get('title', ''), self.get('abstract', '')]
        year = self.get('year', '0000')
        UCNF = UserConfig()
        if int(UCNF.get('fulltext_search', '0')) > 0:
            UDIR = UCNF.get('dir_user')
            SDIR = os.path.join(UDIR, 'stoken')
            sfile = os.path.join(SDIR, year, f'{bkey}.txt')
            if os.path.exists(sfile):
                ans.extend(readLines(sfile))
        return ' '.join(ans)
    def deleteBibFiles(self):
        bibkey = self.get('bibkey')
        if len(findAttaches(self)) > 0:
            return False
        bfile = os.path.join(self.filepath('bibtex'), f'{bibkey}.txt')
        if os.path.exists(bfile):
            os.remove(bfile)
        sfile = os.path.join(self.filepath('stoken'), f'{bibkey}.txt')
        if os.path.exists(sfile):
            os.remove(sfile)
        ## remove speech mp3 files
        MP3_DIR = self.filepath('speech')
        mdirs = runCMD(f'find "{MP3_DIR}" -type d -name "{bibkey}"')
        for xdd in mdirs:
            os.system(f'rm -rf {xdd}')
        return not os.path.exists(bfile)
    def marked(self):
        bkey = self.get('bibkey')
        xdir = UserConfig().get("dir_meta")
        rfile = f'{xdir}/marked_bibkeys'
        xkeys = readLines(rfile) if os.path.exists(rfile) else []
        if not inList(bkey, xkeys):
            xkeys.append(bkey)
            with open(rfile, 'w') as f:
                f.write('\n'.join(xkeys))
                f.close()
        return xkeys
    def unmarked(self):
        bkey = self.get('bibkey')
        xdir = UserConfig().get("dir_meta")
        rfile = f'{xdir}/marked_bibkeys'
        xkeys = readLines(rfile) if os.path.exists(rfile) else []
        if inList(bkey, xkeys):
            xkeys = [x for x in xkeys if x != bkey]
            with open(rfile, 'w') as f:
                f.write('\n'.join(xkeys))
                f.close()
        return xkeys
    def setRank(self, n: int):
        n = n if n >= 0 else 0
        n = n if n <= 9 else 9
        self.update({'rank': n})
        self.save()
    def renameAttaches(self):
        efiles = findAttaches(self)
        if len(efiles) < 1:
            return False
        okey = self.get('oldkey', '')
        nkey = self.get('bibkey', '')
        if nkey == '' or nkey == okey:
            return False
        # rename to tempfiles
        fn = 0
        tfiles = []
        for ss in efiles:
            fn += 1
            xdir = os.path.dirname(ss)
            sx = os.path.basename(ss)
            _, ext = os.path.splitext(sx)
            tx = f'{nkey}-T{fn}{ext.lower()}'
            tt = os.path.join(xdir, tx)
            os.rename(ss, tt)
            tfiles.append(tt)
        ## --------------------------------------
        fn = 0
        for ss in tfiles:
            fn += 1
            xdir = os.path.dirname(ss)
            sx = os.path.basename(ss)
            _, ext = os.path.splitext(sx)
            tx = f'{nkey}-s{fn}{ext.lower()}'
            tt = os.path.join(xdir, tx)
            os.rename(ss, tt)
        ## --------------------------------------
        return fn
    def checkISSN(self):
        issn = self.get('issn', '')
        if re.search(';', issn):
            issn = listuniq(re.split(r' *; *', issn))
            issn.sort()
            issn = '; '.join(issn)
            self.update({'issn': issn})
        return issn
    def setJournalInfo(self):
        journal = self.get('journal', 'EMPTYJOURNAL')
        issn = self.checkISSN()
        xssn = journal2issn(journal)
        if xssn and issn != xssn:
            issn = xssn
            self.update({'issn': issn})
        if issn:
            abbr = issn2abbr(issn)
        else:
            abbr = journal
        if abbr:
            abbr = re.sub(r' *\([^()]+\)$', '', abbr)
            if abbr and abbr != journal:
                self.update({'journal': abbr})
    def cleanInstitute(self):
        oldins = self.get('institution')
        if oldins:
            ins = oldins.split(";")
            ins = [x.strip() for x in ins]
            ins = listuniq(ins)
            ins = "; ".join(ins)
            if ins != oldins:
                self.update({'institution': ins})
    def uniform(self):
        oldkey = self.bibkey()
        newkey = formatBibkey(self)
        if newkey != oldkey:
            self.deleteBibFiles()
            self.update({'oldkey': oldkey, 'bibkey': newkey})
            self.renameAttaches()
            self.save()
        self.setJournalInfo()
        self.cleanInstitute()
    def bibkey(self):
        return self.get('bibkey')
    def setFiles(self):
        files = findAttaches(self)
        self.update({'files': files})
    def files(self):
        return findAttaches(self)
    def pdfs(self):
        return [x for x in self.files() if re.search(r'\.pdf$', x, flags=re.I)]
    def updateSentFile(self, check: bool=False, patts=None):
        bkey = self.bibkey()
        if not bkey:
            return False
        bdir = self.filepath('bibtex')
        bfile = os.path.join(bdir, f'{bkey}.txt')
        if not os.path.exists(bdir):
            os.system(f'mkdir -p "{bdir}"')
        if not os.path.exists(bfile):
            ans = self.save() ## 已包含 updateSentFile
            return ans
        ###
        sdir = self.filepath('stoken')
        sfile = os.path.join(sdir, f'{bkey}.txt')
        if not os.path.exists(sdir):
            os.system(f'mkdir -p "{sdir}"')
        if check and os.path.exists(sfile):
            return False
        sentences = unicodeSentToken(self.get('abstract', ''))
        for fx in self.pdfs():
            txt = pdf2text(fx)
            sentences.extend(unicodeSentToken(txt))
        sentences = CleanSentences(sentences)
        sentences = uniqSentences(sentences)
        with open(sfile, 'w') as f:
            f.write('\n'.join(sentences))
        if patts:
            self.matchSentences(patts)
        return True
    def matchSentences(self, patts: list):
        bkey = self.bibkey()
        if not bkey:
            return False
        bdir = self.filepath('stoken')
        sfile = os.path.join(bdir, f'{bkey}.txt')
        slist = rgPipeFind(patts, sfile)
        slist = [re.sub(r'^[^:]+:', '', x) for x in slist if len(x) < 300]
        if len(slist) > 0:
            slist = listuniq(slist)
            slist.sort()
            self.update({'sentences': slist})
        elif self.get('sentences'):
            self.pop('sentences')
class BibitemXView(BibitemActive):
    def __init__(self, item: dict, xsent: bool=False):
        super().__init__(item)
        self.xsent = xsent
        self.setEscapes()
    def setEscapes(self):
        for k,v in self.items():
            if k!= 'institution' and isinstance(v, str):
                self.update({k: html.escape(v)})
        sentences = self.get('sentences')
        if self.xsent and sentences:
            sentences = [html.escape(x) for x in sentences]
            self.update({'sentences': sentences})
    def abstractHtml(self):
        bibkey = self.get('bibkey')
        author = self.get('author', '')
        institute = self.get('institution', '')
        rtitle = self.get('title', '').strip('. ')
        abstract = self.get('abstract', '')
        hlkeywords = self.get('highlight')
        # set hightlight keywords and color index --------------
        if not self.xsent:
            title = hiLight(rtitle, hlkeywords)
            abstract = hiLight(abstract, hlkeywords)
        else:
            title = rtitle
        # -----------------------
        journal = self.get('journal', '')
        year = self.get('year', '')
        pages = self.get('pages', '')
        doi = self.get('doi', '')
        jtif = float(self.get('impact', 0))
        auths = auth4reference(author)
        htmls = f'<div>'
        ## formated reference
        reference = f'{auths}. {rtitle}. <b>{journal}</b>, {year}: {pages}'
        htmls += f'<p style="font-size: medium;">{bibkey}: {reference}</p><hr>'
        ## Sentences
        sentences = self.get('sentences')
        if self.xsent and sentences:
            if isinstance(sentences, list):
                sentences = formatSent(sentences, hlkeywords)
                htmls += f'<h2 style="font-size: larger;">Matched sentence</h2>{sentences}<hr>'
        ## journal info
        htmls += f'<p style="font-weight: bold;"><span style="font-size: medium; color: #4682B4;">{journal}</span>'
        if jtif > 0:
            htmls += f'&nbsp;&nbsp;<span style="color: #DB7093; font-size: small;"> [ IF: {jtif} ]</span>'
        if not doi == "":
            htmls += f'<span style="font-size: medium;">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;doi: <a href="http://dx.doi.org/{doi}">{doi}</a></span>'
        htmls += '</p>'
        ## title
        htmls += f'<p style="font-size: medium; font-weight: 600;">{title}</p>'
        ## authors
        htmls += f'<p style="font-size: small;">{author}</p>'
        ## abstract
        htmls += f'<hr/><h2 style="font-size: larger;">Abstract</h2><p style="font-size: medium;">{abstract}</p>'
        if institute != '':
            ins = re.split(r' *; *', institute)
            ins = [html.escape(x) for x in listuniq(ins) if x.strip() != '']
            ins = [f'<li style="font-size: small;">{x}</li>' for x in ins]
            institute = ''.join(unlist(ins))
            htmls += f'<hr><ol>{institute}</ol>'
        htmls += '</div>'
        return htmls
class BibitemRaw(dict):
    def __init__(self, ss: list):
        super().__init__()
        self.filetype = bibFileType(ss)
        self.fields = {}
        self.extra = {}
        if self.filetype == 'pubmed':
            self.fields = PmdFields
            self.extra = PmdExtra
        elif self.filetype == 'ris':
            self.fields = RisFields
            self.extra = RisExtra
        elif self.filetype == 'cnki':
            self.fields = CnkiFields
        else:
            pass
        if self.filetype != 'cnki':
            self.multi = ['author', 'issn', 'doi', 'institution']
        else:
            self.multi = []
        self.setData(ss)
        self.transFields()
        self.cleanFields()
        self.aggregate()
        bkey = formatBibkey(self)
        self.update({'bibkey': bkey})
        self.valid()
    def setData(self, blist: list):
        self.clear()
        self.parseRaw(blist)
    def valid(self):
        chk1 = self.get('bibkey')
        chk2 = self.get('journal')
        chk3 = self.get('title')
        if not chk1 or not chk2 or not chk3:
            self.clear()
            return False
        else:
            return True
    def parseRaw(self, blist: list):
        pt = re.compile(r'^([a-z][a-z0-9]+)\s*-\s*(.*)$', flags=re.I)
        for x in blist:
            xx = x.strip()
            if xx == '' or not pt.search(xx):
                continue
            kk = pt.sub(r'\1', xx).upper()
            vv = pt.sub(r'\2', xx)
            vx = self.get(kk, [])
            vx.append(vv)
            self.update({kk: vx})
    def transFields(self):
        if len(self) < 1:
            return False
        okeys = [x for x in self.keys()]
        for bf, klist in self.fields.items():
            xlist = [x.upper() for x in klist]
            for kx in xlist:
                if inList(kx, okeys):
                    vals = self.get(kx)
                    self.update({bf: vals})
                    break
        if self.get('startpage') or self.get('endpage'):
            pages = [self.get('startpage'), self.get('endpage')]
            pages = [x for x in pages if x]
            pages = '-'.join(unlist(pages))
            self.update({'pages': pages})
        for kx in okeys:
            self.pop(kx)
    def cleanCNKI(self):
        auths = self.get('author')
        if auths:
            self.update({'author': splitjoin(auths)})
        keyword = self.get('keyword')
        if keyword:
            self.update({'keyword': splitjoin(keyword)})
    def cleanXScript(self):
        title = self.get('title')
        abstract = self.get('abstract')
        if title:
            self.update({'title': formatXScript(title)})
        if abstract:
            self.update({'abstract': formatXScript(abstract)})
    def cleanInstitute(self):
        ans = self.get('institution')
        if ans:
            ans = listuniq(ans)
            self.update({'institution': ans})
    def cleanFields(self):
        if len(self) < 1:
            return False
        self.cleanInstitute()
        xfields = [x for x in self.extra.keys()]
        for k, v in self.items():
            if inList(k, xfields):
                pt = self.extra.get(k)
                vals = {re.sub(pt[0], pt[1], x) for x in v if re.search(pt[0], x)}
                vals = [x for x in vals]
                self.update({k: vals})
        ans = {k:v for k,v in self.items() if len(v) > 0}
        self.clear()
        self.update(ans)
    def aggregate(self):
        for k, v in self.items():
            if inList(k, self.multi):
                ans = '; '.join(v)
            else:
                ans = v[0]
            self.update({k: ans})
        self.cleanXScript()
        if self.filetype == 'cnki':
            self.cleanCNKI()
class BibitemTex(dict):
    def __init__(self, blist: list):
        super().__init__()
        pt = re.compile(r'^[^= ]* *(\w+) *= *{')
        blist = [pt.sub(r'\1={', x) for x in blist]
        blist = [x for x in blist if re.search(r'^\w+=\{.+}$', x)]
        self.setData(blist)
        self.valid()
    def setData(self, blist: list):
        self.clear()
        pt = re.compile(r'^(\w+)=\{(.+)}$')
        ans = {pt.sub(r'\1', s).lower(): pt.sub(r'\2', s) for s in blist}
        self.update(ans)
        self.splitAuthors()
        bkey = formatBibkey(self)
        self.update({'bibkey': bkey})
        self.updateISSN()
        self.mergeAuthors()
    def splitAuthors(self):
        authors = self.get('author', '')
        authors = authors.split(' and ')
        authors = [x.strip() for x in authors]
        self.update({'author': authors})
    def mergeAuthors(self):
        authors = self.get('author', '')
        self.update({'author': '; '.join(authors)})
    def valid(self):
        bibkey = self.get('bibkey', '')
        if bibkey == '':
            self.clear()
            return False
        else:
            return True
    def updateISSN(self):
        issn = self.get('issn', '')
        # NOTE: 去除括号内说明文字
        issn = re.sub(r'\s*\([^)]*\)\s*', '', issn)
        self.update({'issn': issn})
class PubMedQuery(QThread):
    ready = QtCore.pyqtSignal(dict)
    def __init__(self, qterms: str):
        super().__init__()
        self.terms = re.sub(r'\s+', ' ', qterms.strip())
        self.apikey = UserConfig().get('pubmed_key', '')
    def run(self):
        baseurl = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi'
        data = {'db': 'pubmed', 'term': self.terms, 'usehistory': 'y'}
        if self.apikey != '':
            data.update({'api_key': self.apikey})
        ans = requests.get(baseurl, params=data)
        xinfo = xml.dom.minidom.parseString(ans.content)
        einfo = xinfo.documentElement
        eCount = einfo.getElementsByTagName('Count')
        eWebev = einfo.getElementsByTagName('WebEnv')
        nn = eCount[0].childNodes[0].data if eCount else 0
        nbibs = int(nn)
        webenv = eWebev[0].childNodes[0].data if eCount else ''
        self.ready.emit({'webenv': webenv, 'nbibs': nbibs})
class PubMedGet(QThread):
    ready = QtCore.pyqtSignal(str)
    def __init__(self, webenv: str, nbibs: int):
        super().__init__()
        self.nbibs = nbibs
        self.webenv = webenv
        self.apikey = UserConfig().get('pubmed_key', '')
    def run(self):
        xurl = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        xset = "db=pubmed&&query_key=1&rettype=medline&retmode=text&retstart=1"
        qstr = f'{xurl}?{xset}&WebEnv={self.webenv}&retmax={self.nbibs}'
        if self.apikey != '':
            qstr = f'{qstr}&api_key={self.apikey}'
        ans = requests.get(qstr)
        self.ready.emit(ans.text)
class QPKeywords(QLineEdit):
    def __init__(self):
        super().__init__()
        xdir = UserConfig().get("dir_meta")
        self.hfile = f'{xdir}/history_pubmed'
        self.history = None
        self.currIndex = 0
        self.loadHistory()
    def loadHistory(self):
        self.history = ['']
        if os.path.exists(self.hfile):
            self.history.extend(readLines(self.hfile))
    def updateHistory(self):
        xterms = self.text().strip()
        if xterms == '':
            return False
        klist = [xterms]
        if os.path.exists(self.hfile):
            klist.extend(readLines(self.hfile))
        klist = listuniq(klist)
        with open(self.hfile, 'w') as f:
            f.write('\n'.join(klist))
            f.close()
        self.history = klist
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
class PubMedSearch(QDialog):
    results = QtCore.pyqtSignal(list)
    def __init__(self, parent):
        super().__init__(parent)
        uconf = UserConfig()
        sw = uconf.get('screen_w')/3
        sh = uconf.get('screen_h')/3
        sw = int(max(sw, 800))
        sh = int(max(sh, 400))
        self.setFixedSize(sw, sh)
        self.setWindowTitle('PubMed查询')
        xlayout = QFormLayout()
        xlayout.setSpacing(20)
        xlayout.setFormAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        xlayout.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.setLayout(xlayout)
        self.intext = QPKeywords()
        self.message = QLabel()
        self.message.setStyleSheet('color: red;')
        self.btn1 = QPushButton('查询')
        self.btn1.setEnabled(False)
        xlayout.addRow(self.intext)
        vlayout = QHBoxLayout()
        vlayout.addWidget(QWidget())
        vlayout.addWidget(QWidget())
        vlayout.addWidget(self.btn1)
        xurl = 'https://www.nlm.nih.gov/bsd/mms/medlineelements.html'
        xlayout.addRow(QLabel(f'参考资料：{xurl}'))
        xlayout.addRow(QLabel('Example 1: "green revolution"[TIAB] and nature[TA]'))
        xlayout.addRow(QLabel('Example 2: "green revolution"[TIAB] and "last 2 months"[DP]'))
        xlayout.addRow(QLabel('Example 3: "green revolution"[TIAB] and 2010/01/01:2020/12/01[DP]'))
        xlayout.addRow(QLabel('Example 4: "green revolution"[TIAB] and 2010:2020[DP]'))
        xlayout.addRow(self.intext)
        xlayout.addRow(QLabel(''))
        xlayout.addRow(self.message)
        xlayout.addRow(vlayout)
        self.intext.textChanged.connect(self.checkinput)
        self.ThreadQuery = None
        self.ThreadGet = None
        self.webenv = ''
        self.nbibs = 0
        self.btn1.clicked.connect(self.step1)
    def checkinput(self):
        self.btn1.setEnabled(False)
        xterms = self.intext.text().strip()
        terms = re.sub(r'[&?=/\\]', '', xterms)
        if len(terms) > 2:
            self.btn1.setEnabled(True)
    def step1(self):
        xterms = self.intext.text()
        xterms = re.sub(r'[&?=/\\]', '', xterms.strip())
        if xterms == '':
            popwarning(self, msn='请输入合法的PubMed查询字符串！')
            return None
        self.hide()
        self.intext.updateHistory()
        if self.ThreadQuery and self.ThreadQuery.isFinished():
            self.ThreadQuery.deleteLater()
            time.sleep(0.1)
        self.ThreadQuery = PubMedQuery(xterms)
        self.ThreadQuery.start()
        self.ThreadQuery.ready.connect(self.step2)
    def step2(self, result):
        webenv = result.get('webenv')
        nbibs = result.get('nbibs', 0)
        if 0 < nbibs < 3000 and webenv:
            self.step3(webenv, nbibs)
        else:
            self.show()
            if nbibs > 3000:
                QMessageBox.warning(self, 'PubMed查询', f'匹配文献过多（{self.nbibs}），请优化查询条件！')
            elif nbibs < 1 and webenv:
                QMessageBox.warning(self, 'PubMed查询', '没有匹配记录！')
            else:
                QMessageBox.warning(self, 'PubMed查询', '网络错误，查询已终止！')
    def step3(self, webenv, nbibs):
        if self.ThreadGet and self.ThreadGet.isFinished():
            self.ThreadGet.deleteLater()
            time.sleep(0.1)
        self.ThreadGet = PubMedGet(webenv, nbibs)
        self.ThreadGet.start()
        self.ThreadGet.ready.connect(self.step4)
    def step4(self, contents: str):
        contents = contents.split('\n')
        bitems = rawLines2bibList(contents)
        self.results.emit(bitems)
        time.sleep(0.1)
        self.close()
class JournalBlackList:
    issn = set()
    journal = set()
    __udir = UserConfig().get('dir_meta')
    __ifile = os.path.join(__udir, 'blacklist_issn')
    __jfile = os.path.join(__udir, 'blacklist_journal')
    def __init__(self):
        self.issn = l2set(readLines(self.__ifile))
        self.journal = l2set(readLines(self.__jfile))
    def clear(self):
        self.issn.clear()
        self.journal.clear()
        if os.path.exists(self.__ifile):
            os.remove(self.__ifile)
        if os.path.exists(self.__jfile):
            os.remove(self.__jfile)
    def append(self, bitem: dict):
        ISSNs = splitISSN(bitem.get('issn'), 'set')
        if len(ISSNs) > 0:
            self.issn = self.issn.union(ISSNs)
            with open(self.__ifile, 'w') as f:
                f.write("\n".join(s2list(self.issn)))
        journal = bitem.get('journal', 'NOTFOUND')
        if journal != 'NOTFOUND':
            self.journal = self.journal.union({journal})
            with open(self.__jfile, 'w') as f:
                f.write("\n".join(s2list(self.journal)))
    def remove(self, bitem: dict):
        patt = re.compile(r'\b([0-9]{4}-[0-9a-z]{4})\b', flags=re.I)
        xssn = bitem.get('issn')
        if xssn and patt.search(xssn):
            ISSNs = re.split(r' *; *', xssn)
            ISSNs = {x for x in ISSNs if patt.search(x)}
            self.issn = self.issn.difference(ISSNs)
            with open(self.__ifile, 'w') as f:
                f.write("\n".join(s2list(self.issn)))
        journal = bitem.get('journal', '')
        if journal != '':
            self.journal = self.journal.difference({journal})
            with open(self.__jfile, 'w') as f:
                f.write('\n'.join(s2list(self.journal)))
    def insituCleanBlist(self, blist: list):
        if USR_CNF.get('remove_blacklist', 0) < 1:
            return False
        for bitem in blist:
            xssn = splitISSN(bitem.get('issn', 'NOTFOUND'), 'set')
            xssn = xssn.intersection(self.issn)
            xournal = {bitem.get('journal', 'NOTFOUND')}
            xournal = xournal.intersection(self.journal)
            if len(xssn) < 1 and len(xournal) < 1:
                continue
            if isinstance(bitem, BibitemActive):
                if bitem.deleteBibFiles():
                    blist.remove(bitem)
            else:
                blist.remove(bitem)
    def findBkeys(self):
        bkeys = set()
        if len(self.issn) < 1 and len(self.journal) < 1:
            return bkeys
        xdir = os.path.join(self.__udir, 'bibtex')
        for xssn in self.issn:
            patt = [f'^issn *=.*{xssn}']
            xkeys = rgExtFind([patt], xdir)
            bkeys = bkeys.union(l2set(xkeys))
        for xournal in self.journal:
            patt = [f'^journal *= *{xournal} *$']
            xkeys = rgExtFind([patt], xdir)
            bkeys = bkeys.union(l2set(xkeys))
        return bkeys
## ----------------------------------
## bibitem basic
def findAttaches(bitem) -> set:
    ks = [k for k in [bitem.get('bibkey', ''), bitem.get('oldkey', '')] if k != '']
    files = []
    for kx in ks:
        files.extend(runCMD(f'find {PDF_DIR} -name "{kx}*" | grep -E "{kx}[^0-9]+"'))
    return {x for x in files if x.strip() != ''}
def RGBKeySearch(patts : list):
    ## NOTE：bkey查询
    if len(patts) < 1:
        return []
    bibkeys = rgBkeyFind(patts, BIB_DIR)
    ans = []
    for kx in bibkeys:
        bitem = readNativeByKey(kx)
        if len(bitem) > 0:
            ## nfile = len(findAttaches(bitem))
            ## bitem.update({"nfile": nfile})
            ans.append(bitem)
    return ans
def RGExtSearch(patts : list):
    ## NOTE：扩展查询 = bibtex + 全文
    if len(patts) < 1:
        return []
    bibkeys = set(rgExtFind(patts, BIB_DIR))
    bibkeys = bibkeys.union(set(rgExtFind(patts, SEN_DIR)))
    ans = []
    for kx in bibkeys:
        bitem = readNativeByKey(kx)
        if len(bitem) > 0:
            ans.append(bitem)
    return ans
def RGPipeSearch(patts : list):
    if len(patts) < 1:
        return []
    mlist = rgPipeFind(patts, BIB_DIR)
    files = [re.sub(r'^([^:]+):.+$', r'\1', x) for x in mlist]
    files = listuniq(files)
    ans = []
    for fx in files:
        bitem = readNativeFile(fx)
        if len(bitem) > 0:
            ans.append(bitem)
    return ans
def RGvipSentences(patts : list):
    if len(patts) < 1:
        return []
    mlist = rgPipeFind(patts, SEN_DIR)
    mlist = [re.sub(f'{SEN_DIR}/\\d+/', '', x) for x in mlist]
    bkeys = [re.sub(r'^([^:]+):(.+)$', r'\1', x) for x in mlist]
    bkeys = [re.sub(r'\.txt$', '', x) for x in bkeys]
    bkeys = listuniq(bkeys)
    ans = []
    for kx in bkeys:
        ptx = re.compile(f'^{kx}\\.txt:(.+)$')
        sents = [ptx.sub(r'\1', x) for x in mlist if ptx.search(x)]
        sents = listuniq(sents)
        sents = [x for x in sents if len(x) < 300]
        bitem = readNativeByKey(kx)
        if len(sents) > 0 and len(bitem) > 0:
            sents.sort()
            bitem.update({'sentences': sents})
            ans.append(bitem)
    return ans
def moreChineseThanENG(x):
    ss = ''.join(unlist(x)) if isinstance(x, list) else x
    en = re.sub(r'[\u4e00-\u9fa5]+', '', ss)
    cn = re.sub(r'[a-zA-Z]+', '', ss)
    return len(cn) > len(en)
def formatChineseSep(textstr: str):
    ans = re.sub(r'\. *([\u4e00-\u9fa5])', r'。\1', textstr)
    ans = re.sub(r'([\u4e00-\u9fa5]) *\.', r'\1。', ans)
    ans = re.sub(r', *([\u4e00-\u9fa5])', r'，\1', ans)
    ans = re.sub(r'([\u4e00-\u9fa5]) *,', r'\1，', ans)
    return ans
def unicodeSentToken(textstr: str):
    if moreChineseThanENG(textstr):
        ans = formatChineseSep(textstr)
        ans = re.sub(r'\. *([\u4e00-\u9fa5])', r'。\1', ans)
        ans = re.sub(r'([\u4e00-\u9fa5]) *\.', r'\1。', ans)
        ans = re.sub(r'([。？！?!;；]+)', r'\1@SRET#@', ans)
        ans = re.split('@SRET#@', ans)
    else:
        ans, mdict = maskENsentence(textstr)
        ans = sent_tokenize(ans)
        ans = [unmaskENsentence(x, mdict) for x in ans]
        ans = [x if len(x) < 300 else sent_tokenize(x) for x in ans]
    return unlist(ans)
def maskENsentence(sentence):
    patt = re.compile(r'(\([^()]+\))')
    i = 0
    ans = sentence
    mdict = {}
    while patt.search(ans):
        mm = patt.search(ans)
        if mm:
            ss = {x for x in mm.groups()}
            for x in [s for s in ss]:
                i += 1
                key = f'@#{i}#@'
                ans = ans.replace(x, key)
                mdict.update({key: x})
    return [ans, mdict]
def unmaskENsentence(sentence: str, mdict: dict):
    ans = sentence
    while re.search(r'(@#\d+#@)', ans):
        xkeys = re.search(r'(@#\d+#@)', ans)
        xkeys = [x for x in xkeys.groups()]
        for k in xkeys:
            v = mdict.get(k)
            ans = ans.replace(k, v)
    return ans
def CleanSentences(slist):
    ans = [re.sub(r'^\w+ *=', '', x) for x in slist]
    ans = [re.sub(r'^[\'"\[\].:, ]+', '', x) for x in ans]
    ans = [re.sub(r'[\'"\[\]:, ]+$', '', x) for x in ans]
    ans = [re.sub('^ *（*\d+）', '', x) for x in ans]
    ans = [re.sub('^ *\d+\) *', '', x) for x in ans]
    if moreChineseThanENG(ans):
        ans = [re.sub(' *【[^】]*】 *', '', x) for x in ans]
        ans = [re.sub('^ *\([^)]+\) *', '', x) for x in ans]
    else:
        ans = [re.sub(r'^([^a-z]+ )+', '', x, flags=re.I) for x in ans]
        # ans = [x for x in ans if x.count(';') < 5 and x.count(',') < 6 and x.count(' ') > 4]
    ans = [x.strip() for x in ans]
    return [x for x in ans if x!= '']
def uniqSentences(slist: list):
    if moreChineseThanENG(slist):
        return listuniq(slist)
    ss = [re.sub(r'[^0-9a-z]+', '', x.lower()) for x in slist]
    ans = []
    sx = []
    for i in range(len(ss)):
        if not inList(ss[i], sx):
            ans.append(slist[i])
            sx.append(ss[i])
    return ans
def formatSent(sentences: list, hlkeys: list):
    ans = [hiLight(x, hlkeys) for x in sentences]
    ans = [f'<li style="font-size: medium; margin: 10px 0 0 0;">{x}</li>'
           for x in ans]
    ans = ''.join(ans)
    return f'<ul style="list-style: circle;">{ans}</ul>'
# ---------------------------------
# Format misc
def scaleFont(n: int, s):
    return math.ceil(round(n * s, 0))
def formatXScript(textstr: str):
    while re.search(r'\((\d+)\)(\w*)', textstr):
        textstr = re.sub(r'\((\d+)\)(\w*)', r'\1\2', textstr)
    while re.search(r'(\w+)\((\d+)\)', textstr):
        textstr = re.sub(r'(\w+)\((\d+)\)', r'\1\2', textstr)
    return textstr
def authLastName(s: str):
    """
    Get last name from an author string.
    Make sure that there is only one name in the string!
    """
    s = s.strip()
    if s.find(',') > 0:
        anx = re.sub(r'^([^,]+).*$', r'\1', s)
    else:
        anx = re.sub(r'^.+ +([^ ]+)$', r'\1', s)

    # NOTE: some person may have last name of multi words
    anx = re.sub(r'[{}]', '', anx)
    anx = re.sub(r' +', '-', anx)
    return anx
def authFirstName(s: str):
    """
    Get first name of an author string.
    Make sure that there is only one name in the string!
    """
    s = s.strip()
    if s.find(',') > 0:
        anx = s.split(',').pop().strip()
    else:
        ## remove last name
        anx = re.sub('[^ ]+$', '', s).strip()

    # NOTE: some person may have last name of multi words
    anx = re.sub(r'[{}]', '', anx)
    # get first letters only
    anx = [re.sub(r'^(.).*$', r'\1', x).upper() for x in anx.split(' ')]
    return "".join(anx)
def authAbbr(s: str):
    return " ".join([authLastName(s), authFirstName(s)])
def getFirstAuth(auths):
    ans = ''
    if isinstance(auths, str):
        auths = re.split(r' *; *', auths)
        auths = [x.strip() for x in auths if x.strip() != '']
    elif not isinstance(auths, list):
        return ans
    if auths:
        author = auths[0]
        if re.search('^[^,]+,', author):
            ans = re.sub(r'^([^,]+),.*$', r'\1', author)
        else:
            ans = re.sub(r' .+$', '', author)
        ans = re.sub(r'\s+', '-', ans)
    return ans
def formatDoiKey(bitem: dict):
    firstauth = getFirstAuth(bitem.get('author', ''))
    year = bitem.get('year', '')
    doi = bitem.get('doi', '')
    dxx = doi.split('/').pop()
    dxx = re.sub(r'\D', '', dxx)
    if len(dxx) > MAX_PAGE_LEN:
        pt = '^.*(.{' + str(MAX_PAGE_LEN) + '})$'
        dxx = re.sub(pt, r'\1', dxx)
    doikey = ''
    if year != '' and firstauth != '' and dxx != '':
        doikey = "-".join([year, firstauth, dxx])
    return doikey
def formatPageKey(bitem: dict):
    firstauth = getFirstAuth(bitem.get('author', ''))
    pages = bitem.get('pages', '')
    year = bitem.get('year', '')
    firstpage = re.sub(r'\W+.*$', '', pages)
    year = re.sub(r'\D', '', year)
    pagekey = ''
    if year != '' and firstauth != '' and firstpage != '':
        pagekey = "-".join([year, firstauth, 'p' + firstpage])
    return pagekey
def formatBibkey(bitem):
    okey = bitem.get('bibkey')
    if okey:
        bitem.update({'oldkey': okey})
    dkey = formatDoiKey(bitem)
    pkey = formatPageKey(bitem)
    if re.search(r'\d{4}-.+\d+$', dkey):
        ans = dkey
    elif re.search(r'\d{4}-.+\d+$', pkey):
        ans = pkey
    else:
        ans = ''
    return ans
def formatREkey(kx, allowREX: bool=False):
    kx = kx.strip()
    if not allowREX:
        kx = re.sub(r'[\'"(){}\[\]*.]', '', kx)
    kx = re.sub(r'(\d+)', r' \1 ', kx)
    ans = re.sub(r' +', f' *', kx)
    return ans
def hiLight(content: str, keywords: list):
    if (not keywords) or len(keywords) < 1:
        return content
    colors = colorKeywords(len(keywords))
    icount = 0
    for kk in keywords:
        kx = re.sub(r'\^\$=', '', kk)
        if kx == '':
            continue
        # px = formatREkey(kx, allowREX=True)
        # if not re.search(r'[a-zA-Z]', kx):
        #     px = f'({kx})'
        # else:
        #     px = f'(\\b{px}\\b)' if len(kx) < 4 or re.search(r'\d', kx) else f'(\\w*{px}\\w*)'
        px = formatRegKeyword(kx)
        content = re.sub(f'({px})', f'<span style="background-color:#COLOR#;">\\1</span>',
                         content, flags=re.I)
        if re.search(r'#COLOR#', content):
            content = re.sub(r'#COLOR#', colors[icount], content)
        icount += 1
    return content
def auth4reference(s: str):
    """
    Author format input: LastName, FirstName
    Author format output: Zhao ABC
    """
    alist = [x.strip() for x in re.split(r';', s)]
    alist = [authAbbr(x) for x in alist]
    nn = len(alist)
    if nn < 3:
        return " & ".join(alist)
    elif nn < 4:
        anx = ", ".join(alist[0:2])
        anx = " & ".join([anx, alist[2]])
        return anx
    else:
        anx = f'{alist[0]} et al'
        return anx
def splitISSN(issn: str, rt: str):
    ans = set()
    if issn:
        patt = re.compile(r'\b([0-9]{4}-[0-9a-z]{4})\b', flags=re.I)
        if patt.search(issn):
            ans = re.split(r' *; *', issn)
            ans = {x for x in ans if patt.search(x)}
    if rt.lower() == 'list':
        ans = [x for x in ans]
    return ans
def splitjoin(ss: str):
    ans = re.split(r' *; *', ss)
    ans = [x.strip() for x in ans if x.strip() != '']
    return '; '.join(ans)
def readNativeFile(fp: str):
    if not os.path.exists(fp):
        return {}
    p = re.compile(r'^([a-z]+) *= *(.+)$', re.IGNORECASE)
    ans = {p.sub(r'\1', x): p.sub(r'\2', x)
           for x in readLines(fp) if p.match(x)}
    ans = BibitemActive(ans)
    ans.updateSentFile(check=True)
    rank = ans.get('rank', '')
    if rank == '':
        ans.update({'rank': '0'})
    return ans
def readNativeByKey(bkey: str):
    fp = re.sub(r'^(\d+)(-.+)$', r'\1/\1\2', bkey)
    fp = f'{USR_DIR}/bibtex/{fp}.txt'
    return readNativeFile(fp)
def bibFileType(lines: list):
    ris = [x for x in lines if re.search(r'^ER *- *$', x)]
    if len(ris) > 0:
        return 'ris'
    pmd = [x for x in lines if re.search(r'^PMID *- *\d+ *$', x)]
    if len(pmd) > 0:
        return 'pubmed'
    tex = [x for x in lines if re.search(r'^@\w+ *{.*$', x)]
    if len(tex) > 0:
        return 'bibtex'
    cnki = [x for x in lines if re.search(r'^SrcDatabase', x)]
    if len(cnki) > 0:
        return 'cnki'
def texLines2bibList(lines) -> list:
    contents = [re.sub(r'^(@\w+) *\{', r'#%ITEMSEP\1{', x) for x in lines]
    contents = [re.sub(r' *},* *$', r'}#%FIELDSEP', x) for x in contents]
    contents = ' '.join(contents)
    contents = re.sub(r' +', ' ', contents)
    ans = contents.split("#%ITEMSEP")
    ans = [x.split('#%FIELDSEP') for x in ans if re.search(r'\S', x)]
    ans = [BibitemTex(x) for x in ans]
    ans = [x for x in ans if len(ans) > 0]
    return ans
def rawLines2bibList(lines) -> list:
    if len(lines) < 1:
        return []
    lines = [re.sub(r'\s+', ' ', x) for x in lines]
    contents = []
    for ll in lines:
        if re.search(r'^[a-z][a-z0-9]+\s*-', ll, flags=re.I):
            contents.append(f'\n{ll}')
        elif re.search(r'^ *$', ll):
            contents.append('#@RET#')
        else:
            contents.append(ll)
    contents = " ".join(contents)
    ans = contents.split("#@RET#")
    ans = [x.strip().split('\n') for x in ans if re.search(r'\S', x)]
    ans = [BibitemRaw(x) for x in ans]
    ans = [x for x in ans if len(x) > 3]
    return ans
def importFile2bibList(fp):
    lines = readLines(fp, no_empty_lines=False)
    filetype = bibFileType(lines)
    if filetype == 'bibtex':
        blist = texLines2bibList(lines)
    else:
        if filetype == 'cnki':
            lines = [re.sub(r'^ *([a-zA-Z]+)[^:]+: *(.+)$', r'\1 - \2', x) for x in lines]
        blist = rawLines2bibList(lines)
    blist = [BibitemActive(x) for x in blist if len(x) > 0]
    return blist
def readMarked():
    xdir = UserConfig().get("dir_meta")
    rfile = f'{xdir}/marked_bibkeys'
    bkeys = readLines(rfile) if os.path.exists(rfile) else []
    blist = [readNativeByKey(k) for k in bkeys]
    blist = [x for x in blist if len(x) > 4]
    if len(blist) != len(bkeys):
        bkeys = [x.get('bibkey') for x in blist]
        with open(rfile, 'w') as f:
            f.write('\n'.join(bkeys))
    return blist
def requestAbstract(doi: str):
    contents = ''
    url = f'https://onlinelibrary.wiley.com/doi/{doi}'
    try:
        robj = requests.get(url)
        contents = robj.text
    finally:
        return contents
def parseSpringDOIs(fp):
    dois = []
    try:
        info = pd.read_csv(fp)
        info = info.to_dict('list')
        dois = info.get('Item DOI')
    finally:
        return {x for x in dois}
def getSpringerByDOI(doi: str):
    # TODO: check doi
    bitem = []
    rdata = {'format': 'refman', 'flavour': 'citation'}
    url = f'https://citation-needed.springer.com/v2/references/{doi}'
    try:
        robj = requests.get(url, params=rdata)
        contents = robj.text
        contents = contents.split('\n')
        bitem = rawLines2bibList(contents)
    finally:
        return bitem
def doisPresented():
    patt = r'^doi *= *\d+\.\d+/.+$'
    dois = runCMD(f'rg -N -t txt -i -e "{patt}" "{BIB_DIR}"')
    paxx = re.compile(r'^[^:]+: *doi *= *')
    dois = {paxx.sub('', x) for x in dois}
    # with open(os.path.join(USR_DIR, 'dois.test.txt'), 'w') as f:
    #     f.write('\n'.join(dois))
    return dois
def cleanSentencesFiles():
    bfiles = [os.path.basename(x) for x in runCMD(f'find "{BIB_DIR}" -type f')]
    sfiles = runCMD(f'find "{SEN_DIR}" -type f')
    sfiles = [x for x in sfiles if not inList(os.path.basename(x), bfiles)]
    [os.remove(fx) for fx in sfiles if fx.strip() != '' and os.path.exists(fx)]
