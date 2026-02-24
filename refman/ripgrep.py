import os, re
from refman.config import UserConfig
from refman.functions import unlist, listinter, runCMD, formatRegKeyword

def totalbibs():
    USR_DIR = UserConfig().get('dir_user')
    BIB_DIR = os.path.join(USR_DIR, 'bibtex')
    ans = runCMD(f'find "{BIB_DIR}" -type f | wc -l', False)
    return int(ans)
def BkeysHasNote():
    USR_DIR = UserConfig().get('dir_user')
    xdir = os.path.join(USR_DIR, 'notes')
    ans = runCMD(f'find "{xdir}" -type f -size +1b')
    ans = {re.sub(r'(@file)*\.md$', '', os.path.basename(x)) for x in ans}
    return [x for x in ans]
    #
def BkeysHasFile():
    USR_DIR = UserConfig().get('dir_user')
    xdir = os.path.join(USR_DIR, 'pdf')
    ans = runCMD(f'find "{xdir}" -type f -size +1b')
    ans = {re.sub(r'(-s\d+)*\.pdf$', '', os.path.basename(x), flags=re.I) for x in ans}
    return [x for x in ans]
    #
def rgPipeFind(patts : list, fpath: str):
    # ripgrep in directory or file
    keywords = [[formatRegKeyword(kwd) for kwd in kwds] for kwds in patts]
    keywords = ['|'.join(unlist(x)) for x in keywords]
    # keywords = ['|'.join(unlist(x)) for x in patts]
    keywords = [f'({x})' for x in keywords]
    if not os.path.exists(fpath):
        return []
    kwd = keywords[0]
    xcmd = f'rg -N -t txt -i -e "{kwd}" "{fpath}"'
    nk = len(keywords)
    if nk > 1:
        for i in range(nk - 1):
            kwd = keywords[i+1]
            xcmd = f'{xcmd} | rg -N -i -e "{kwd}"'
    mlist = runCMD(xcmd)
    return mlist
def rgExtFind(patts : list, fpath: str):
    if not os.path.exists(fpath):
        return []
    keywords = [[formatRegKeyword(kwd) for kwd in kwds] for kwds in patts]
    keywords = ['|'.join(unlist(x)) for x in keywords]
    # keywords = ['|'.join(unlist(x)) for x in patts]
    keywords = [f'({x})' for x in keywords]
    bkeys = []
    for kwd in keywords:
        xcmd = f'rg -l -L -m 1 -t txt -i -e "{kwd}" "{fpath}"'
        bkeys.append(runCMD(xcmd))
    bkeys = listinter(bkeys)
    bkeys = [re.sub(r'\.txt$', '', os.path.basename(x)) for x in bkeys]
    return bkeys
def rgBkeyFind(patts : list, fpath: str):
    keywords = ['|'.join(unlist(x)) for x in patts]
    keywords = '|'.join(keywords)
    xcmd = f'find "{fpath}" -name "*.txt" | grep -E "{keywords}"'
    mlist = runCMD(xcmd)
    bkeys = {re.sub(r'\.txt$', '', os.path.basename(x)) for x in mlist}
    return bkeys

