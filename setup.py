#!/usr/bin/env python

from setuptools import setup, find_packages
setup(
    name = "SPODS",
    version = "0.4",
    scripts = [],

    packages=['spods'],
    namespace_packages=['spods'],
    package_dir={'spods': 'spods'},    

    # metadata for upload to PyPI
    author = "Sasha Bermeister",
    author_email = "sbermeister@gmail.com",
    description = "A lightweight database object serializer for Python",
    license = "",
    keywords = "SQL object serailizer ORM map sqlite mysql postgresql API CGI",
    url = "https://github.com/sbermeister/SPODS/",   # project home page, if any
    long_description=open('README.md').read(),
    classifiers = [
        "Topic :: Software Development :: Libraries :: Python Modules"
    ],
)
