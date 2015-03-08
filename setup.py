#!/usr/bin/env python
# -*- coding: utf-8 -*-

__version__ = '1.0'

from setuptools import setup


def get_requires():
    with open('requirements.txt', 'r') as f:
        requires = [i for i in map(lambda x: x.strip(), f.readlines()) if i]
    return requires


def get_long_description():
    with open('README.rst', 'r') as f:
        return f.read()


setup(
    name='readability',
    version=__version__,
    license='License :: OSI Approved :: MIT License',
    author='reorx',
    author_email='novoreorx@gmail.com',
    url='https://github.com/reorx/readability',
    description='html main body extractor',
    long_description=get_long_description(),
    py_modules=['readability'],
    install_requires=get_requires()
)
