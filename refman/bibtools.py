import os, re
from refman.config import UserConfig
from refman.functions import runCMD
from refman.bibtex import readNativeFile

## ---------------------------------
## cleaning

## ---------------------------------
def prepareSToken():
    USR_DIR = UserConfig().get('dir_user')
    BIB_DIR = os.path.join(USR_DIR, 'bibtex')
    bfiles = runCMD(f'find {BIB_DIR} -type f')
    for fx in bfiles:
        readNativeFile(fx)
# prepareSToken()
def allAttaches():
    USR_DIR = UserConfig().get('dir_user')
    PDF_DIR = os.path.join(USR_DIR, 'pdf')
    mfiles = os.listdir(PDF_DIR)
    return mfiles
def renameAttaches(bitem: dict, mfiles: list):
    if len(mfiles) < 1:
        return False
    okey = bitem.get('oldkey')
    bkey = bitem.get('bibkey')
    if not okey:
        return 0
    if not re.search('^\d{4}-.+\d+$', bkey):
        return 0
    USR_DIR = UserConfig().get('dir_user')
    PDF_DIR = os.path.join(USR_DIR, 'pdf')
    xcount = 0
    xfiles = [f for f in mfiles if f.startswith(okey) and os.path.exists(f'{PDF_DIR}/f')]
    if len(xfiles) > 0:
        for i in range(len(xfiles)):
            ofile = xfiles[i]
            ext = re.sub(r'^.+\.([a-z]+)$', r'\1', ofile, flags=re.I)
            nfile = f'{bkey}-s{i + 1}.{ext}'
            os.system(f'cd "{PDF_DIR}" && mv {ofile} {nfile}')
            if not os.path.exists(f'{PDF_DIR}/{ofile}'):
                xcount += 1
    return xcount
