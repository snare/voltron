from __future__ import print_function

import sys
import platform
import textwrap
from subprocess import check_output
from setuptools import setup, find_packages


def check_install():
    """
    Try to detect the two most common installation errors:

    1. Installing on macOS using a Homebrew version of Python
    2. Installing on Linux using Python 2 when GDB is linked with Python 3
    """
    if platform.system() == 'Darwin' and sys.executable != '/usr/bin/python':
        print("*" * 79)
        print(textwrap.fill(
            "WARNING: You are not using the version of Python included with "
            "macOS. If you intend to use Voltron with the LLDB included "
            "with Xcode, or GDB installed with Homebrew, it will not work "
            "unless it is installed using the system's default Python. If "
            "you intend to use Voltron with a debugger installed by some "
            "other method, it may be safe to ignore this warning. See the "
            "following documentation for more detailed installation "
            "instructions: "
            "https://github.com/snare/voltron/wiki/Installation", 79))
        print("*" * 79)
    elif platform.system() == 'Linux':
        try:
            output = check_output([
                "gdb", "-batch", "-q", "--nx", "-ex",
                "pi print(sys.version_info.major)"
            ]).decode("utf-8")
            gdb_python = int(output)

            if gdb_python != sys.version_info.major:
                print("*" * 79)
                print(textwrap.fill(
                    "WARNING: You are installing Voltron using Python {0}.x "
                    "and GDB is linked with Python {1}.x. GDB will not be "
                    "able to load Voltron. Please install using Python {1} "
                    "if you intend to use Voltron with the copy of GDB that "
                    "is installed. See the following documentation for more "
                    "detailed installation instructions: "
                    "https://github.com/snare/voltron/wiki/Installation"
                    .format(sys.version_info.major, gdb_python), 79))
                print("*" * 79)
        except:
            pass


check_install()


requirements = [
    'scruffington>=0.3.6',
    'flask',
    'flask_restful',
    'blessed',
    'pygments',
    'requests',
    'requests_unixsocket',
    'six',
    'pysigset',
    'pygments',
]
if sys.platform == 'win32':
    requirements.append('cursor')


setup(
    name="voltron",
    version="0.1.7",
    author="snare",
    author_email="snare@ho.ax",
    description="A debugger UI",
    license="MIT",
    keywords="voltron debugger ui gdb lldb vdb "
             "vivisect vtrace windbg cdb pykd",
    url="https://github.com/snare/voltron",
    packages=find_packages(exclude=['tests', 'examples']),
    install_requires=requirements,
    package_data={'voltron': ['config/*']},
    entry_points={
        'console_scripts': ['voltron=voltron:main'],
        'pygments.lexers': [
            'lldb_intel = voltron.lexers:LLDBIntelLexer',
            'lldb_att = voltron.lexers:LLDBATTLexer',
            'gdb_intel = voltron.lexers:GDBIntelLexer',
            'gdb_att = voltron.lexers:GDBATTLexer',
            'vdb_intel = voltron.lexers:VDBIntelLexer',
            'vdb_att = voltron.lexers:VDBATTLexer',
            'windbg_intel = voltron.lexers:WinDbgIntelLexer',
            'windbg_att = voltron.lexers:WinDbgATTLexer',
            'capstone_intel = voltron.lexers:CapstoneIntelLexer',
        ],
        'pygments.styles': [
            'volarized = voltron.styles:VolarizedStyle',
        ]
    },
    zip_safe=False
)
