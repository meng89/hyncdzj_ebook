#!/usr/bin/env python3


import os


import p5a_to_simple


xmls = [
    "N/N01/N01n0001.xml",
    "N/N02/N02n0001.xml"
]


def main():
    book = p5a_to_simple.load_from_p5a(xmls)
    import tempfile

    print(tempfile.gettempdir())
    book.write(os.path.join(tempfile.gettempdir(), "sv"))

if __name__ == "__main__":
    main()