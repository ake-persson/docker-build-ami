#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Setup script for docker-build-ami
'''

from setuptools import setup, find_packages
import sys, os, glob

with open('requirements.txt') as f:
    requires = f.read().splitlines()

CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Environment :: Console',
    'Intended Audience :: System Administrators',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: Apache Software License',
    'Operating System :: POSIX :: Linux',
    'Operating System :: MacOS :: MacOS X',
    'Programming Language :: Python',
]

setup(
    name             = 'docker-build-ami',
    version          = '0.3.7',

    description      = 'Build Amazon EC2 AMI image using a Dockerfile',
    long_description = open("README.rst").read(),

    author           = 'Michael Persson',
    author_email     = 'michael.ake.persson@gmail.com',
    url              = 'https://github.com/mickep76/docker-build-ami.git',
    license          = 'Apache License, Version 2.0',

    packages         = find_packages(),
    classifiers      = CLASSIFIERS,
    scripts          = ['scripts/docker-build-ami'],
    data_files	     = [('/etc', ['etc/docker-build-ami.conf'])],
    install_requires = requires,
)
