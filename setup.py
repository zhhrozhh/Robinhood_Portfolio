import sys
from os import path,listdir
from setuptools import setup,find_packages
from setuptools.command.test import test as TestCommand

HERE = path.abspath(path.dirname(__file__))
__version__ = "0.0.2.1"
REQUIRES = [
    'pandas>=0.20.1',
    'numpy>=1.12.1',
] 
setup(
    name = 'Robinhood_Portfolio',
    author = 'zhhrozhh',
    author_email = 'zhangh40@msu.edu',
    url = 'https://github.com/zhhrozhh/Robinhood_Portfolio',
    version = __version__,
    license = 'MIT',
    classifiers = [
        'Programming Language :: Python :: 3.5'
    ],
    keywords = 'Robinhood portfolio manager',
    packages = find_packages(),
    install_requires = REQUIRES,
)
