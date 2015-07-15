#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import glob
import codecs
import difflib
import logging
from readability import Readability


# TODO string similarity comparision

os.chdir(os.path.join(os.path.dirname(__file__), 'cases'))
HTML_FILES = glob.glob('*.html')


def distance_rate(a, b):
    return difflib.SequenceMatcher(a=a, b=b).ratio()


def test_readability():
    for filename in HTML_FILES:
        yield check_readability, filename


def check_readability(filename):
    with codecs.open(filename, 'r', 'utf8') as f:
        html = f.read()
    with codecs.open(filename.replace('.html', '.txt'), 'r', 'utf8') as f:
        text = f.read()

    parser = Readability(html)
    article_text = parser.article.get_text()
    rate = distance_rate(article_text, text)
    print 'rate', rate
    print article_text
    assert rate > 0.95


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    for fn, arg in test_readability():
        fn(arg)
