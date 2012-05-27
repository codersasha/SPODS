#!/usr/bin/env python

from distutils.core import setup
#from setuptools import setup

version = "0.4"

setup(name='SPODS',
      version=version,
      description='A lightweight database object serialiser for Python',
      author='Sasha Bermeister',
      author_email='sbermeister@gmail.com',
      url='https://github.com/sbermeister/SPODS/',
      packages=['spods'],
      classifiers=["Topic :: Software Development :: Libraries :: Python Modules"]
     )

