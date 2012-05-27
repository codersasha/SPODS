#!/usr/bin/env python

from setuptools import setup, find_packages
import sys, os

version = '0.4'

setup(name='SPODS',
      version=version,
      description="A lightweight database object serialiser for Python.",
      long_description="""\
""",
      classifiers=["Topic :: Software Development :: Libraries :: Python Modules"], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Sasha Bermeister',
      author_email='sbermeister@gmail.com',
      url='https://github.com/sbermeister/SPODS/',
      license='',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
