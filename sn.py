#!/usr/bin/env python3
import re
import os

from typing import List

import xl


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
xmlp5_dir = os.path.join(PROJECT_ROOT, "xml-p5a")


xmls = [
    "N/N13/N13n0006.xml",
    "N/N14/N14n0006.xml",
    "N/N15/N15n0006.xml",

    "N/N16/N16n0006.xml",
    "N/N17/N17n0006.xml",

    "N/N18/N18n0006.xml"
]


class SN(object):
    def __init__(self):
        self.terms: List[Container] = []


class Container(object):
    def __init__(self, mulu=None):
        self.mulu = mulu
        self.head = None
        self.level = None
        self.terms: List[Container or Term] = []


def is_pin_sub(xy_cbdiv):
    pin_count = 0
    for div in xy_cbdiv.find_kids("cb:div"):
        mulu = div.find_kids("cb:mulu")[0]
        mulu_text = mulu.kids[0]
        m = re.match("^第[一二三四五六七八九十]+.*品.*$", mulu_text)
        if m:
            pin_count += 1

    if pin_count == 1 and len(xy_cbdiv.find_kids("cb:div")) == 1:
        return True
    if pin_count > 1:
        return True
    return False


########################################################################################################################
class Term(object):
    pass


class ExposedStr(Term):
    def __init__(self, string):
        self.s = string


class Note(Term):
    def __init__(self, enote: xl.Element):
        self.contents = enote.kids
        self.n = enote.attrs["n"]


class P(Term):
    def __init__(self, atoms=None):
        self.atoms = atoms or []


class G(Term):
    def __init__(self, ref):
        self.ref = ref


class Ref(Term):
    def __init__(self, cref):
        self.cref = cref


class Lg(Term):
    def __init__(self, lg_element):
        self.speaker = None
        self.body = []

        for le in lg_element.find_kids("l"):
            line = []
            sentence = []
            for _lkid in le.kids:
                if isinstance(_lkid, str):
                    m = re.match(r"^(〔.+〕)(.+)$", _lkid)
                    if m:
                        assert self.speaker is None
                        self.speaker = m.group(1)
                        sentence.append(m.group(2))
                    else:
                        sentence.append(_lkid)

                elif isinstance(_lkid, xl.Element):
                    if _lkid.tag == "caesura":
                        line.append(sentence)
                        sentence = []
                        continue

                    match do_atom(e=_lkid, funs=[do_note, do_g, do_ref, do_app]):
                        case True, atom:
                            sentence.append(atom)
                        case False, _:
                            raise Exception(_lkid)

            assert sentence
            line.append(sentence)
            self.body.append(line)


########################################################################################################################


def do_str(e):
    if isinstance(e, str):
        return True, [e]
    else:
        return False, e


def do_note(e):
    if isinstance(e, xl.Element) and e.tag == "note":
        return True, Note(e)
    else:
        return False, e


def do_g(e):
    if isinstance(e, xl.Element) and e.tag == "g":
        return True, [G(e.attrs["ref"])]
    else:
        return False, e


def do_ref(e):
    if isinstance(e, xl.Element) and e.tag == "ref":
        return True, [Ref(e.attrs["cRef"])]
    else:
        return False, e


def do_app(e):
    if isinstance(e, xl.Element) and e.tag == "app":
        lem = e.kids[0]
        if isinstance(lem.kids[0], str):
            return True, [lem.kids[0]]
        elif isinstance(lem.kids[0], xl.Element) and lem.kids[0].tag == "space":
            return True, []
    else:
        return False, e


def do_atoms(atoms, funs):
    new_atoms = []
    for i in range(len(atoms)):
        answer, value = do_atom(atoms[i], funs)
        if answer is True:
            new_atoms.append(value)
        else:
            return new_atoms, atoms[i:]

    return new_atoms, []


def do_atom(e, funs):
    for fun in funs:
        try:
            answer, x = fun(e)
            if answer is True:
                return True, x
        except TypeError:
            print((fun, e))
            exit()

    return False, None


########################################################################################################################


class ElementError(Exception):
    pass


def note_filter(objs: list):
    new_objs = []
    for i in range(len(objs)):
        obj = objs[i]
        if isinstance(obj, Note):
            if exist_same_note_n(obj.n, objs[i+1]):
                continue
        new_objs.append(obj)


def exist_same_note_n(n, objs):
    for obj in objs:
        if isinstance(obj, Note) and obj.n == n:
            return True
    return False


def get_parent_container(container, level):
    if level == 1:
        return container
    else:
        for term in reversed(container.terms):
            if isinstance(term, Container):
                return get_parent_container(term, level - 1)

    raise Exception("cant be here")


def get_last_container(container):
    for term in reversed(container.terms):
        if isinstance(term, Container):
            return get_last_container(term)

    return container


def make_tree(sn: Container or SN, cbdiv: xl.Element):
    # cb:mulu 出现在目录中，而 head 出现在正文的标题中。head 有时会有 note 。两者似乎有冗余，也许该在上游精简。
    # 少数 cb:div 标签中无 head。

    # 少数 cb:div 标签中第一个子标签不是cb:mulu.

    kids = cbdiv.kids

    if kids[0].tag == "cb:mulu":
        _str_level = kids[0].attrs["level"]
        level = int(_str_level)
        parent = get_parent_container(sn, level)

        if level == 1:
            _pian_mulu = kids[0].kids[0]  # 篇
            m = re.match(r"^(.+篇).* \(\d+-\d+\)$", _pian_mulu)
            assert m
            mulu = m.group(1)
            if len(parent.terms) == 0 or parent.terms[-1].mulu != mulu:
                container = Container()
                container.level = level
                container.mulu = mulu
                #print("mulu1:", container.mulu)
                parent.terms.append(container)
            else:
                container = parent.terms[-1]
        else:
            container = Container()
            container.level = level
            assert len(kids[0].kids) == 1
            container.mulu = kids[0].kids[0]
            #print("mulu2:", container.mulu)
            parent.terms.append(container)

        kids.pop(0)

    # SN.46.6
    else:
        #input("hehe")
        for kid in kids:
            if isinstance(kid, xl.Element):
                if kid.tag == "cb:mulu":
                    input(kid.tag)

        container = get_last_container(sn)

    first = cbdiv.kids[0]
    if isinstance(first, xl.Element) and first.tag == "head":
        container.head = first.kids[:]
        # input(container.head)
        cbdiv.kids.pop(0)

    for kid in cbdiv.kids:
        if isinstance(kid, xl.Element) and kid.tag == "cb:div":
            make_tree(sn, kid)

        if isinstance(kid, str):
            container.terms.append(ExposedStr(kid))

        elif kid.tag == "p":
            # 略过只有数字的行
            if len(kid.kids) == 1 and re.match(r"^[〇一二三四五六七八九十]+$", kid.kids[0]):
                pass
            else:
                atoms, left = do_atoms(kid.kids, funs=[do_str, do_note, do_g, do_ref, do_app])
                if left:
                    print(("left:", repr(left)))
                    exit()
                container.terms.append(P(atoms))

        elif kid.tag == "lg":
            lg = Lg(kid)
            container.terms.append(lg)

    # return container


def get_tree():
    snikaya = SN()
    for one in xmls:
        xmlstr = open(os.path.join(xmlp5_dir, one), "r").read()

        xml = xl.parse(xmlstr, do_strip=True)

        tei = xml.root

        tei = filter_element(tei, is_lb)
        tei = filter_element(tei, is_pb)

        text = tei.find_kids("text")[0]
        body = text.find_kids("body")[0]
        print(one)

        for cb_div in body.find_kids("cb:div"):
            make_tree(snikaya, cb_div)

    return snikaya


def is_lb(x):
    # <lb ed="N" n="0206a14"/>
    if isinstance(x, xl.Element):
        if x.tag == "lb":
            if x.attrs["ed"] == "N":
                if "n" in x.attrs.keys():
                    if not x.kids:
                        return True
    return False


def is_pb(x):
    # <pb ed="N" xml:id="N18.0006.0207a" n="0207a"/>
    if isinstance(x, xl.Element):
        if x.tag == "pb":
            if x.attrs["ed"] == "N":
                if "n" in x.attrs.keys():
                    if "xml:id" in x.attrs.keys():
                        if not x.kids:
                            return True
    return False


def filter_element(x: xl.Element or str, fun: callable):
    if isinstance(x, xl.Element):
        new_e = xl.Element(tag=x.tag, attrs=x.attrs)
        for kid in x.kids:
            if fun(kid):
                pass
            else:
                new_e.kids.append(filter_element(kid, fun))
        return new_e

    elif isinstance(x, str):
        return x

    raise TypeError


def is_sutta(parent_container: Container):
    len_of_container = 0
    lot_of_match = 0
    for sub in parent_container.terms:
        if isinstance(sub, Container):
            len_of_container += 1

            if not isinstance(sub.mulu, str):
                input(sub.mulu)

            m = re.match(r"^〔[、～〇一二三四五六七八九十]+〕.*$", sub.mulu)
            if m:
                lot_of_match += 1

    if lot_of_match:
        if lot_of_match == len_of_container:
            return True
        else:
            print("需要检查子div:{}".format(parent_container.mulu, 1))
            print("len_of_container:", len_of_container)
            print("lot_of_match:", lot_of_match)
            input()
            return False
    else:
        return False


def traverse_sn(sn: SN):
    for pian in sn.terms:
        print(pian)


def print_title(sn):
    for pian in sn.terms:
        print_title2(pian, 0)


def print_title2(container, depth):
    for term in container.terms:
        if isinstance(term, Container):
            if is_sutta(container):
                print(" " * depth, "<Sutta>:", term.mulu, sep="")
            else:
                print(" " * depth, term.mulu, sep="")
            print_title2(term, depth + 4)


def check_x_first_term(sn):
    for pian in sn.terms:
        term = pian.terms[0]
        print(pian.mulu)
        if not isinstance(term, Container):
            print(term)

def main():
    sn = get_tree()
    #print_title2(sn, 0)
    check_x_first_term(sn)


if __name__ == "__main__":
    main()
