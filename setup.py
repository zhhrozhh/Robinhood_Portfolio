import sys
from os import path,listdir
from setuptools import setup,find_packages
from setuptools.command.test import test as TestCommand

HERE = path.abspath(path.dirname(__file__))
__version__ = "0.0.1"
REQUIRES = [
    'pandas>=0.20.1',
    'numpy>=1.12.1',
    'scipy>=0.19.0',
    'Robinhood>=1.0.2',
    'Quandl>=3.2.0'
]
def include_all_subfiles(*args):
    file_list = []
    for path_included in args:
        local_path = path.join(HERE,path_included)
        for file in listdir(local_path):
            file_abspath = path.join(local_path,file)
            if path.isdir(file_abspath):
                continue
            if '_local.cfg' in file_abepath:
                continue
            file_list.append(path_included+'/'+file)
    return file_list

setup(
    name = 'Robinhood_Portfolio',
    author = 'Hanghang Zhang',
    author_email = 'zhangh40@msu.edu',
    url = 'https://github.com/zhhrozhh/Robinhood_Portfolio',
    download_url = 'TODO',
    version = __version__,
    license = 'MIT',
    classifiers = [
        'Programming Language :: Python :: 3.5'
    ]
    keywords = 'Robinhood portfolio manager',
    packages = find_packages(),
    install_requires = lambda x:[],

        
)
