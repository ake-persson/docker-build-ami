#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Setup script for docker-build-ami
'''

from setuptools import setup, find_packages

# VERSION MUST be defined on line 10
VERSION = '0.7.0'

with open('requirements.txt') as f:
    requires = f.read().splitlines()

with open('requirements-test.txt') as f:
    test_deps = f.read().splitlines()
extras = {
    "test": test_deps,
}


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

with open('README.rst', 'r') as fh:
    long_description = fh.read()

setup(
    name='jamieleecho-docker-build-ami',
    version=VERSION,

    description='Build Amazon EC2 AMI image using a Dockerfile',
    long_description=long_description,
    long_description_content_type='text/x-rst',

    # The project's main homepage.
    url='https://github.com/jamieleecho/docker-build-ami.git',

    # Author details
    author='Michael Persson',
    author_email='michael.ake.persson@gmail.com',

    # Choose your license
    license='Apache License, Version 2.0',
    license_files=('LICENSE.txt',),

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=CLASSIFIERS,

    # What does your project relate to?
    keywords='docker aws ami ec2',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages(where='src'),
    package_dir={
        '': 'src',
    },
    data_files=[('/etc', ['etc/docker-build-ami.conf'])],
    install_requires=requires,
    tests_require=test_deps,
    extras_require=extras,
    python_requires=">=3.6",

    entry_points={
        "console_scripts": [
            "docker-build-ami=docker2ami.docker2ami:main",
        ],
    },
)
