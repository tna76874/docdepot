#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
from setuptools import find_packages, setup

import ddclient

setup(
    name='ddclient',
    version=ddclient.__version__,
    description='Docdepot Client',
    url='https://github.com/tna76874/docdepot.git',
    author='maaaario',
    author_email='',
    license='BSD 2-clause',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "Requests",
    ],
    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.6',
    ],
    python_requires = ">=3.6",
    entry_points={
        "console_scripts": [
            "ddclient = ddclient.ddclient:main",
        ],
    },
    )
