import sys
from setuptools import setup, find_packages


requirements = [
    'scruffington>=0.3.2',
    'flask',
    'flask_restful',
    'blessed',
    'pygments',
    'requests',
    'requests_unixsocket',
    'six',
    'pysigset'
]
if sys.platform == 'win32':
    requirements.append('cursor')

setup(
    name="voltron",
    version="0.1.5",
    author="snare",
    author_email="snare@ho.ax",
    description=("A debugger UI"),
    license="MIT",
    keywords="voltron debugger ui gdb lldb vdb vivisect vtrace windbg cdb pykd",
    url="https://github.com/snare/voltron",
    packages=find_packages(exclude=['tests', 'examples']),
    install_requires=requirements,
    package_data={'voltron': ['config/*']},
    entry_points={
        'console_scripts': ['voltron=voltron:main']
    },
    zip_safe=False
)
