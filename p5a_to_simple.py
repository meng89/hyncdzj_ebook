import re
import os

import xl

import base
import config


def trans_elements(elements) -> list:
    new_elements = []
    for e in elements:
        new_es = trans_element(e)
        new_elements.extend(new_es)

    return new_elements


def trans_element(element):
    for fun in (head, string, lg, p, note, app, space, ref, g):
        result = fun(element)
        if result is not None:
            return result
        else:
            continue

    print("cannot handle this element:", element.to_str())
    raise Exception


# pass
def head(e):
    if isinstance(e, xl.Element) and e.tag == "head":
        es = trans_elements(e.kids)
        h1 = xl.Element("h1", kids=es)
        return [h1]
    else:
        return None


def string(e):
    if isinstance(e, str):
        return [e]
    else:
        return None


# 禍從欲望生
# <note n="0032074" resp="NanChuan" place="foot" type="orig">禍（agha）Pañcakkhandha dukkha 註釋為（五蘊之苦）。</note>
# <note n="0032074" resp="CBETA" type="mod">
# 禍（agha）Pañcakkhandha dukkha 註釋為（五蘊之苦）。（CBETA 按：漢譯南傳大藏經此頁中缺相對應之註標[74]，今於此處加上[74]之註標。）
# </note>
# <caesura style="text-indent:5em;"/>
# 苦惱從欲生
##

# <note type="cf1">S. 1.72 (PTS 1990: I 41,23)</note>
# <note type="cf2">T02n0099_p0266b22</note>

# <note n="0062a1201" resp="CBETA" type="add" note_key="N13.0062a12.03">國【CB】，王【南傳】</note>

def note(e):
    if isinstance(e, xl.Element) and e.tag == "note":
        if len(e.kids) == 0:
            return []

        elif len(e.kids) == 1 and isinstance(e.kids[0], xl.Element) and e.kids[0].tag == "space":
            return []

        elif "【CB】" in e.kids[0] and "【南傳】" in e.kids[0]:
            return []

        elif "add" in e.attrs.keys():
            return []

        else:
            ewn = xl.Element("ewn")
            ewn.ekid("a")
            _note = ewn.ekid("note")
            _note.kids.extend(e.kids)
            return [ewn]

    else:
        return None

# 〔一六〕睡
# <note n="0009a1201" resp="CBETA" type="add">眠【CB】，眼【南傳】</note>
# <app n="0009a1201">
#   <lem wit="【CB】" resp="CBETA.maha">眠</lem>
#   <rdg wit="【南傳】">眼</rdg>
# </app>
# 、懶惰
def app(e):
    if isinstance(e, xl.Element) and e.tag == "app":
        lem = e.kids[0]
        return trans_elements(lem.kids)
    else:
        return None


def space(e):
    if isinstance(e, xl.Element) and e.tag == "space":
        quantity = int(e.attrs["quantity"])
        return [" " * quantity]

    else:
        return None


# <head>
# <ref cRef="PTS.S.1.2"/>
# 〔二〕解脫
####
#
def ref(e):
    if isinstance(e, xl.Element) and e.tag == "ref":
        return [e]
    else:
        return None


# <lg type="regular" xml:id="lgN13p0003a0101" style="margin-left:0em;text-indent:0em;">
# <l style="text-indent:2em">
# 〔世尊：〕有喜之滅盡
# <caesura style="text-indent:5em;"/>
# 亦盡想與識
# </l>
# <lb ed="N" n="0003a02"/>
# <l style="text-indent:7em">
# 受滅皆寂靜
# <caesura style="text-indent:5em;"/>
# 友我之如是
# </l>
# <lb ed="N" n="0003a03"/>
# <l style="text-indent:7em">
# 知眾生解脫
# <caesura style="text-indent:5em;"/>
# 令解脫遠離
# </l>
# </lg>
####
# 偈子
def lg(e):
    if isinstance(e, xl.Element) and e.tag == "lg":
        person = None
        sentences = []

        for le in e.find_kids("l"):
            sentence = []

            for _lkid in le.kids:
                if isinstance(_lkid, str):
                    # 〔世尊：〕他醒於五眠
                    #          他眠於五醒
                    #          染塵依於五
                    #          依五而得清
                    m = re.match(r"^〔(.+)：〕(.+)$", _lkid)
                    if m:
                        assert person is None  # 预估每个偈子仅有一位咏颂人
                        person = m.group(1)
                        sentence.append(m.group(2))
                    else:
                        sentence.append(_lkid)

                elif isinstance(_lkid, xl.Element) and _lkid.tag == "caesura":
                    sentences.append(sentence)
                    sentence = []
                    continue

                else:
                    es = trans_element(_lkid)
                    sentence.extend(es)

            sentences.append(sentence)

        j = xl.Element("j")
        if person:
            j.attrs["p"] = person
        for s in sentences:
            j.kids.append(xl.Element("s", kids=s))

        return [j]

    else:
        return None


# 遠離於
# <g ref="#CB03020"/>
# 欲
# <caesura style="text-indent:5em;"/>
# 無欲修梵行
####
# 不在 Unicode 里的生僻字
g_map = {
    "#CB03020": "婬"
}


def g(e):
    if isinstance(e, xl.Element) and e.tag == "g":
        s = g_map[e.attrs["ref"]]
        return [s]
    else:
        return None


# 普通句子
def p(e):
    element = xl.Element("p")
    if isinstance(e, xl.Element) and e.tag == "p":
        kids = trans_elements(e.kids)
        element.kids[:] = kids
        return [element]
    else:
        return None

########################################################################################################################

def get_body(filename) -> xl.Element:

    file = open(filename, "r")

    xmlstr = file.read()
    file.close()
    xml = xl.parse(xmlstr, strip=True)
    tei = xml.root
    text = tei.find_kids("text")[0]
    body = text.find_kids("body")[0]
    return body


def load_from_p5a(xmls) -> base.Book:
    book = base.Book()
    for xml in xmls:
        filename = os.path.join(config.xmlp5a_dir, xml)
        print("xml:", xml.removeprefix(config.xmlp5a_dir))
        file = open(filename, "r")

        xmlstr = file.read()
        file.close()
        xml = xl.parse(xmlstr)
        tei = xml.root
        text = tei.find_kids("text")[0]
        body = text.find_kids("body")[0]

        body = base.filter_(body)
        for cb_div in body.find_kids("cb:div"):
            base.make_tree(book, cb_div)

    return book
