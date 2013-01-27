#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import glob
import codecs
from readability import *
from torext.utils import start_shell
import logging

logging.basicConfig(level=logging.DEBUG)


os.chdir(os.path.join(os.path.dirname(__file__), 'test/cases'))

htmls = []

for i in glob.glob('*.html'):
    with codecs.open(i, 'r', 'utf8') as f:
        htmls.append(f.read())

start_shell(globals())
