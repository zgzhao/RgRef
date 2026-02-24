import os, re, random, platform
import seaborn as sns
from tempfile import mktemp
from refman.config import UserConfig
from refman.varsys import DIR_APP
from hashlib import md5

def text2md5(text):
    md5_hash = md5()
    md5_hash.update(text.encode('utf-8'))
    md5_hex = md5_hash.hexdigest()
    return md5_hex
def systemInfo():
    ans = {}
    ans.update({'os_name': platform.system()})
    ans.update({'os_version': platform.version()})
    ans.update({'python_version': platform.python_version()})
    ans.update({'perl_info': runCMD('perl -v')})
    ans.update({'pdftotext': runCMD('pdftotext -v')})
    return ans
def pdf2text(pdfname):
    ans = ''
    if not os.path.exists(pdfname):
        return ans
    ftxt = mktemp()
    PROGRAM = os.path.join(DIR_APP, 'assets', 'bin', 'pdf2txt.pl')
    os.system(f'{PROGRAM} "{pdfname}" "{ftxt}"')
    if os.path.exists(ftxt):
        ans = readLines(ftxt)
        ans = ' '.join(ans)
        os.remove(ftxt)
    return ans
class PDFinfo:
    def __init__(self, fp: str):
        txt = pdf2text(fp)
        self.text = re.sub(r'\s*/\s*', '/', txt)
        patts = [r'doi[:/]\s*\S+', r'doi\.org/\S+']
        dois = list()
        for px in patts:
            dois.extend(re.findall(px, self.text, re.I))
        self.dois = {re.sub(r'doi[:/]\s*|doi\.org/', '', x.strip(' ,;.'))
                     for x in dois}
def colorKeywords(n: int=10):
    ans = sns.color_palette('pastel', n + 2)
    ans = ans.as_hex()
    ans.reverse()
    return ans
def rankColors():
    uconf = UserConfig()
    apply = int(uconf.get('color_apply_rank', 1))
    if apply < 1:
        return None
    cname = uconf.get('rank_color', '#FFA07A')
    raw = sns.light_palette('#FFA07A', 10)
    try:
        raw = sns.light_palette(cname, 10)
    finally:
        return raw.as_hex()
def runCMD(cmd, asList: bool=True):
    with os.popen(cmd) as pid:
        ans = pid.read().strip()
    ans = ans if ans else ''
    if asList:
        ans = ans.split('\n')
        ans = [x for x in ans if x.strip() != '']
    return ans
def randstr(n: int) -> str:
    ans = ''
    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    for i in range(n):
        ans += random.choice(chars)
    return ans
def str2wordlist(textstring: str) -> list:
    ans = re.sub(r'\s+', ' ', textstring)
    ans = re.split(r'[,;，；、\n]+', ans)
    ans = [x.strip() for x in ans]
    ans = [x for x in ans if x != '']
    ans = [f'\\b{x}\\b' if len(x) < 4 or re.search(r'\d', x) else x for x in ans]
    return ans
def l2set(xlist: list):
    return {x for x in xlist}
def s2list(xset: set):
    return [x for x in xset]
def listuniq(lst: list):
    ans = []
    for x in lst:
        if not inList(x, ans):
            ans.append(x)
    return ans
def unique(lst: list):
    return listuniq(lst)
def unlist(lst: list, rm_dup=True):
    ans = []
    for x in [lst]:
        if not isinstance(x, str) and (isinstance(x, list) or isinstance(x, set)):
            ans.extend([y for y in x])
        elif isinstance(x, dict):
            ans.extend([y for y in x.values()])
        else:
            ans.append(x)
    anx = [x for x in ans if isinstance(x, list) or isinstance(x, set)]
    ans = [x for x in ans if not isinstance(x, list) and not isinstance(x, set)]
    if len(anx) > 0:
        for x in anx:
            # recursive unlist
            ans.extend(unlist(x))
    if rm_dup:
        ans = unique(ans)
        ans.sort()
    return ans
def readLines(fp, no_empty_lines=True):
    contents = []
    if os.path.exists(fp):
        with open(fp) as f:
            contents = [x.strip() for x in f]
            f.close()
    if no_empty_lines:
        contents = [x for x in contents if re.search(r'\S', x)]
    return contents
def listinter(lst: list):
    nl = len(lst)
    if nl < 2:
        return unlist(lst)
    ans = lst[0]
    ans = {x for x in ans}
    for i in range(nl - 1):
        anx = lst[i + 1]
        anx = {x for x in anx}
        ans = ans.intersection(anx)
    return [x for x in ans]
def listdiff(lst1, lst2):
    return [x for x in lst1 if not inList(x, lst2)]
def inList(value, lst: list):
    for x in lst:
        if x==value:
            return True
    return False
# dict with list as items
def setinter(s1: set, s2: set):
    return s1.intersection(s2)
def setunion(s1: set, s2: set):
    return s1.union(s2)
def dictListMerge(d1: dict, d2:dict, keep=None):
    if keep:
        keep = {keep: d1.get(keep)}
    dt1 = {k:v for k,v in d1.items() if isinstance(v, list)}
    dt2 = {k:v for k,v in d2.items() if isinstance(v, list)}
    k1 = {x for x in dt1.keys()}
    k2 = {x for x in dt2.keys()}
    ks = k1.union(k2)
    for k in ks:
        v1 = dt1.get(k, [])
        v2 = dt2.get(k, [])
        vv = unlist([v1, v2])
        dt1.update({k: vv})
    if keep:
        dt1.update(keep)
    return dt1
def dictFlat(d: dict):
    ans = {}
    for k in d.keys():
        v = d.get(k)
        if isinstance(v, list):
            v.sort()
            v = " ".join(v)
        else:
            v = str(v)
        ans.update({k: v.strip()})
    ans = [f"{k}-{v}" for k,v in ans.items() if v != '']
    return ans
def klist2str(lst: list, sep: str):
    xlist = unlist(lst)
    xlist.sort()
    sep = f' {sep.strip()} '
    return sep.join(xlist)
def klistIdentical(l1: list, l2: list):
    if len(l1) != len(l2):
        return False
    if len(l1) < 1 and len(l2) < 1:
        return True
    lx1 = [klist2str(x, '|') for x in l1]
    lx2 = [klist2str(x, '|') for x in l2]
    lx1 = klist2str(lx1, '&')
    lx2 = klist2str(lx2, '&')
    return lx1 == lx2
def dictListIdentical(d1: dict, d2: dict):
    s1 = {x for x in dictFlat(d1)}
    s2 = {x for x in dictFlat(d2)}
    uu = s1.union(s2)
    xx = s1.intersection(s2)
    return len(uu) == len(xx)
# list with dict as items
def listDictSort(listDict: list, keys: list, direct: list):
    if len(keys) < 1:
        return listDict
    nn = len(listDict)
    ndx1 = ['' for x in listDict]
    ndx2 = [str(i) for i in range(nn)]
    for i in range(len(keys)):
        xlist = [listDict[int(j)] for j in ndx2]
        xlist = [ndx1[j] + '@' + str(xlist[j].get(keys[i])) + '#' + ndx2[j] for j in range(nn)]
        xlist = [x.lower() for x in xlist]
        xlist.sort(reverse=direct[i])
        ndx1 = [re.sub(r'^([^@]*)@.+$', r'\1', x) for x in xlist]
        ndx2 = [re.sub(r'^.+#(\d+)$', r'\1', x) for x in xlist]
        ## 产生新索引
        nxx = [0]
        k = 0
        xlist = [re.sub(r'#\d+$', r'', x) for x in xlist]
        for j in range(nn - 1):
            if xlist[j+1] != xlist[j]:
                k += 1
            nxx.append(k)
        ndx1 = [ndx1[j] + "{:0>4d}".format(nxx[j]) for j in range(nn)]
    ## 最终按照新索引排序
    xlist = [ndx1[i] + "#" + ndx2[i] for i in range(nn)]
    xlist.sort()
    ndx2 = [re.sub(r'^.+#(\d+)$', r'\1', x) for x in xlist]
    return [listDict[int(i)] for i in ndx2]
def hasAllKeywords(textstring: str, keywords: list):
    for kw in keywords:
        kx = formatRegKeyword(kw)
        if not re.search(kx, textstring, flags=re.I):
            return False
    return True
def hasAnyKeyword(textstring: str, keywords: list, exact: bool=False):
    for kw in keywords:
        if exact:
            kx = f'^{kw}$'
        else:
            kx = formatRegKeyword(kw)
        if re.search(kx, textstring, flags=re.I):
            return True
    return False
def getDictItems(d: dict, keys: list):
    ans = {k:v for k,v in d.items() if inList(k, keys)}
    return ans
def formatRegKeyword(kwd):
    kwd = kwd.strip()
    if len(kwd) < 4:
        ans = f'\\b{kwd}\\b'
    else:
        kwd = re.sub(r'[ -]+', ' ', kwd)
        if kwd.count(' ') < 1:
            ans = f'{kwd}\\w*'
        elif kwd.count(' ') < 3:
            ans = re.sub(r' +', '[ -]([a-z0-9]+[ -]){0,3}', kwd)
        else:
            ans = re.sub(r' +', '[ -]', kwd)
        ans = f'\\b{ans}\\b'
    return ans
def pdfAnnoGet(file):
    ans = []
    if not os.path.exists(file):
        return ans
    prog = runCMD('which pdfannots', asList=False)
    if prog == "":
        prog = UserConfig().get("pdfannots")
    if prog == "":
        return ""
    tmpfile = mktemp('.markdown')
    ans = os.system(f'{prog} "{file}" > {tmpfile}')
    if os.path.exists(tmpfile):
        ans = readLines(tmpfile)
        os.remove(tmpfile)
    return ans
def pdfAnnoTidy(alist: list):
    alist = [x.strip() for x in alist if not re.search(r' *#+ ', x)]
    # 两种形式的Page标注
    alist = [re.sub(r'^\* +page +#*\d+ *\(.+\):', '', x, flags=re.I) for x in alist]
    alist = [re.sub(r'^\* +page +#*\d+:', '', x, flags=re.I) for x in alist]
    alist = [re.sub(r'^\W+', '', x) for x in alist]
    alist = [x.strip('"\',') for x in alist]
    alist = [f'- {x}' for x in listuniq(alist) if re.search(r'[a-zA-Z]', x)]
    ans = []
    if len(alist) > 0:
        ans = ['## PDF annotations']
        ans.extend(alist)
    return ans
#
def arrangeSdcv(result: list):
    result = "<br>".join(result)
    result = result.split("<br>")
    patt1 = re.compile(r'-->')
    patt2 = re.compile(r'^[^_]+_')
    ans = dict()
    dns = ""
    isDict = False
    results = []
    for ll in result:
        if patt1.search(ll):
            isDict = not isDict
            dw = patt1.sub('', ll)
            if isDict:
                dns = dw
            else:
                dns = f'{dns}_{dw}'
        elif dns != "":
            if ll != patt2.sub('', dns) and ll != '':
                anx = ans.get(dns, [])
                anx.append(ll)
                ans.update({dns: anx})
                ##
        elif ll != '':
            results.append(ll)
    ##
    ans = {k:v for k,v in ans.items() if len(v) > 0}
    dss = [re.sub(r'_.+$', '', x) for x in ans.keys()]
    words = []
    for dx in listuniq(dss):
        results.append(f'@#dict:{dx}')
        word = [patt2.sub('', x) for x in ans.keys() if x.startswith(f'{dx}_')]
        words.extend(word)
        for wx in word:
            results.append(f'@#word:{wx}')
            kw = f'{dx}_{wx}'
            anx = listuniq(ans.get(kw, []))
            if anx:
                results.extend(anx)
    xword = ""
    if len(words) > 0:
        xword = words[0]
    return [xword, results]

def sdcvFind(word: str):
    word = word.strip()
    if word:
        result = runCMD(f'sdcv -n -e --utf8-output "{word}"')
        result = arrangeSdcv(result)
        if result[0] == "":
            result = runCMD(f'sdcv -n --utf8-output "{word}"')
            result = arrangeSdcv(result)
        if result[0] != "":
            return {"word": result[0], "result": result[1]}
    return {"word": word, "result": ["No item found."]}