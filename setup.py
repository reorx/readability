#!/usr/bin/env python
# -*- coding: utf-8 -*-

__version__ = '1.0'

from setuptools import setup


def get_requires():
    with open('requirements.txt', 'r') as f:
        requires = [i for i in map(lambda x: x.strip(), f.readlines()) if i]
    return requires

get_requires()

setup(
    name='readability',
    version=__version__,
    author='reorx',
    description='html main body extractor',
    py_modules=['readability'],
    install_requires=get_requires()
)
