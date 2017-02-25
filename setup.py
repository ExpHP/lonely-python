
from __future__ import print_function

from setuptools import setup
from setuptools import find_packages

setup(
	name='lonely',
	version = '0.1',
	description = 'Lonely personal-use libraries',
	url = 'https://github.com/ExpHP/python-lonely',
	author = 'Michael Lamparski',
	author_email = 'lampam@rpi.edu',

	install_requires=[
		'numpy',
		'scipy',
	],

	packages=find_packages(),
)
