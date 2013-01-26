#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import glob
import codecs
from readability import Readability


# TODO string similarity comparision

os.chdir(os.path.join(__file__, 'cases'))
HTML_FILES = glob.glob('*.html')


def test_readability():
    for filename in HTML_FILES:
        yield check_readability, filename


def check_readability(filename):
    with codecs.open('utf8', filename, 'r') as f:
        html = f.read()
    with codecs.open('utf8', filename.replace('.html', '.txt'), 'r') as f:
        text = f.read()

    parser = Readability(html)
