import re, random

def authEast(x: str):
    """
    Author format: LastName, FirstName
    """
    x = x.strip()
    if x.find(' ') < 0:
        return x
    lname = re.sub(r'^.+ ([^ ]+)$', r'\1', x)
    fname = re.sub(r' +([^ ]+)$', '', x)
    return lname.strip() + ", " + fname.strip()
def authWest(x: str):
    """
    Author format: FirstName LastName
    """
    x = x.strip()
    if x.find(' ') < 0:
        return x
    lname = re.sub(r'^.+ ([^ ]+)$', r'\1', x)
    fname = re.sub(r' +([^ ]+)$', '', x)
    return fname.strip() + " " + lname.strip()
def authTex2Db(s: str):
    s = re.sub(r'[;\.]', '', s)
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'\sAND\s', ' and ', s)
    authors = re.split(r'\sand\s', s)
    ans = []
    for aa in authors:
        if aa.find(',') > 0:
            ans.append(aa)
        elif aa.find(' ') > 0:
            ax = re.sub(r'^(.+) ([^ ]+)$', r'\2, \1', aa)
            ans.append(ax)
        else:
            ans.append(aa)

    return "; ".join(ans)
def styleNSFC(bitem: dict):
    """
    NSFC Output style. Bib item should be retrieved from database.
    """
    # TODO:
    author = bitem.get('author', '')
    title = bitem.get('title', '')
    journal = bitem.get('journal', '')
    year = bitem.get('year', '')
    volume = bitem.get('volume', '')
    pages = bitem.get('pages', '')
    doi = bitem.get('doi', '')

    htmls = '<div style="font-size: 20px;">'
    htmls += '<p style="font-size:22px;">'
    htmls += '<span style="font-style:italic; font-weight:bold;">'
    htmls += journal + '</span>'
    pass

def absFormat(content: str, field: str):
    if field == 'journal':
        ans = '<span style="font-style:italic; font-weight:bold;">' + content + '</span>'
    elif field == 'jtif':
        ans = '<span style="font-size:18px;"> [ IF: ' + str(content) + ' ]</span>'
    elif field == 'doi':
        ans = '<p style="font-size:18px;"><a href="http://dx.doi.org/' +\
            content + '">' + content + '</a>'
    elif field == 'author':
        ans = '<p style="font-size: 16px;">' + content + '</p>'
    elif field == 'title':
        ans = '<p style="font-size:24px; font-weight:bold; color:red;">' + content + '</p>'
    elif field == 'insitute':
        ans = '<p style="font-size: 14px;">' + content + '</p>'
    else:
        ans = content

    return ans

