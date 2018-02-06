#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Setup for ooservice
"""

from setuptools import setup, find_packages

PACKAGES_DATA = {}

INSTALL_REQUIRES = [
    'osconf'
]

setup(name='ooservice',
      description='OpenERP Service',
      author='GISCE-TI, S.L.',
      author_email='devel@gisce.net',
      url='http://www.gisce.net',
      version='0.1.1',
      license='General Public Licence 2',
      long_description='''Long description''',
      provides=['ooservice'],
      install_requires=INSTALL_REQUIRES,
      packages=find_packages(exclude=['tests']),
      package_data=PACKAGES_DATA
      )
