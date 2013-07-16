from setuptools import setup
import glob

setup(
    name = "voltron",
    version = "0.1",
    author = "snare",
    author_email = "snare@ho.ax",
    description = ("A UI for GDB & LLDB"),
    license = "Buy snare a beer",
    keywords = "voltron gdb lldb",
    url = "https://github.com/snarez/voltron",
    packages=['voltron'],
    install_requires = ['termcolor'],
    data_files=['voltron.gdb', 'voltron.cfg', ('voltron', glob('voltron/*'))],
    entry_points = {
        'console_scripts': ['voltron = voltron:main']
    }
)
