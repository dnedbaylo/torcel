#!/usr/bin/env python

from distutils.core import setup

version = '0.0.1'

with open('README.md') as f:
    long_description = f.read()

setup(
    name='torcel',
    version=version,
    description='Celery integration with Tornado: get task result async',
    long_description=long_description,
    author='Dmitry Nedbaylo',
    author_email='dmitry.nedbaylo@gmail.com',
    url='http://github.com/dnedbaylo/torcel',
    license="http://www.apache.org/licenses/LICENSE-2.0",
    packages=['torcel'],
    requires=['tornado', 'celery'],
)
